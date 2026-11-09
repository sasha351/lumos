"""Tests for the ESPHome command generator in tools.analyze_captures."""

import copy
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.analyze_captures import (
    GENERATED_HEADER,
    GeneratorError,
    analyze_dir,
    build_raw_code,
    main,
    render_esphome,
)
from tools.lumos_captures import decode_frame

REPO = Path(__file__).resolve().parents[1]
CAPTURES = REPO / "captures" / "original"
MANIFEST = REPO / "captures" / "commands.json"
GENERATED = REPO / "esphome" / "lamp-commands.generated.yaml"


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def entry(manifest, command_id):
    return next(c for c in manifest["commands"] if c["id"] == command_id)


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = {r["file"]: r for r in analyze_dir(CAPTURES)}

    def test_power_code_is_one_clean_frame(self):
        code = build_raw_code(0x7B50020C, self.reports["Pwr.sub"]["timings"])
        self.assertEqual(len(code), 66)
        self.assertTrue(all(isinstance(v, int) for v in code))
        for i, value in enumerate(code):
            self.assertEqual(value > 0, i % 2 == 0, f"sign at {i}")
        self.assertEqual(decode_frame(code[:-1]), (0x7B50020C, None))
        self.assertEqual(code[-1], self.reports["Pwr.sub"]["timings"]["gap"])
        self.assertEqual(code[-2], self.reports["Pwr.sub"]["timings"]["sync_high"])

    def test_generated_power_entry_in_yaml(self):
        text = render_esphome(load_manifest(), self.reports)
        self.assertTrue(text.startswith(GENERATED_HEADER + "\n"))
        self.assertIn("id: cmd_power", text)
        self.assertIn("transmitter_id: tx", text)
        self.assertIn("times: ${tx_repeat}", text)
        power = text.split("id: cmd_power", 1)[1]
        code = [int(v) for v in re.search(r"code: \[([^\]]*)\]", power).group(1).split(",")]
        self.assertEqual(len(code), 66)
        self.assertEqual(decode_frame(code[:-1]), (0x7B50020C, None))

    def test_only_exposed_commands_are_emitted(self):
        manifest = load_manifest()
        entry(manifest, "neutral_50")["expose"] = False
        text = render_esphome(manifest, self.reports)
        ids = re.findall(r"id: (cmd_\w+)", text)
        self.assertNotIn("cmd_neutral_50", ids)
        self.assertEqual(len(ids), 11)

    def test_exposed_buttons_emitted_in_remote_order(self):
        text = render_esphome(load_manifest(), self.reports)
        names = re.findall(r'name: "([^"]+)"', text)
        self.assertEqual(
            names,
            ["Night mode", "Power", "Color warmer", "Brightness up", "Color cooler", "Brightness down",
             "Cool 100%", "Warm 100%", "Warm 50%", "Cool 50%", "Neutral 100%", "Neutral 50%"],
        )

    def test_timer_is_known_but_never_exposed(self):
        timer = entry(load_manifest(), "timer")
        self.assertEqual((timer["pattern"], timer["position"], timer["expose"]), ("7B500D03", 13, False))
        self.assertNotIn("cmd_timer", render_esphome(load_manifest(), self.reports))

    def test_every_emitted_code_decodes_to_its_pattern(self):
        text = render_esphome(load_manifest(), self.reports)
        blocks = re.findall(r"# (\w+): ([0-9A-F]{8}) .*?code: \[([^\]]*)\]", text, flags=re.S)
        self.assertEqual(len(blocks), 12)
        for cid, pattern, body in blocks:
            with self.subTest(command=cid):
                code = [int(v) for v in body.split(",")]
                self.assertEqual(len(code), 66)
                self.assertEqual(decode_frame(code[:-1]), (int(pattern, 16), None))

    def test_learned_code_uses_timing_source_timings(self):
        text = render_esphome(load_manifest(), self.reports)
        block = text.split("# color_warmer:", 1)[1].split("  - platform", 2)[1]
        self.assertIn("learned in H4, timings from Pwr.sub", text)
        pwr = self.reports["Pwr.sub"]["timings"]
        self.assertIn(f"{pwr['sync_high']}, {pwr['gap']}", block)

    def test_learned_code_needs_timing_source_and_evidence(self):
        manifest = load_manifest()
        del entry(manifest, "cool_50")["timing_source"]
        with self.assertRaisesRegex(GeneratorError, "set timing_source"):
            render_esphome(manifest, self.reports)
        manifest = load_manifest()
        entry(manifest, "cool_50")["evidence"] = ""
        with self.assertRaisesRegex(GeneratorError, "needs evidence"):
            render_esphome(manifest, self.reports)
        manifest = load_manifest()
        entry(manifest, "cool_50")["timing_source"] = "Nope.sub"
        with self.assertRaisesRegex(GeneratorError, "not found among captures"):
            render_esphome(manifest, self.reports)

    def test_timing_source_with_a_capture_is_refused(self):
        manifest = load_manifest()
        entry(manifest, "power")["timing_source"] = "Bup.sub"
        with self.assertRaisesRegex(GeneratorError, "only for codes without a source"):
            render_esphome(manifest, self.reports)

    def test_per_command_repeat_and_wait_override(self):
        manifest = load_manifest()
        entry(manifest, "power").update({"repeat": 5, "wait_time_ms": 12})
        text = render_esphome(manifest, self.reports)
        self.assertIn("times: 5", text)
        self.assertIn("wait_time: 12ms", text)

    def test_exposing_unknown_is_refused(self):
        manifest = load_manifest()
        entry(manifest, "warm_50")["id"] = "unknown_0b"
        with self.assertRaisesRegex(GeneratorError, "unknown"):
            render_esphome(manifest, self.reports)

    def test_exposing_unverified_is_refused(self):
        manifest = load_manifest()
        entry(manifest, "brightness_up").update({"expose": True, "verified": False})
        with self.assertRaisesRegex(GeneratorError, "only verified"):
            render_esphome(manifest, self.reports)

    def test_button_without_code_cannot_be_exposed(self):
        manifest = load_manifest()
        entry(manifest, "color_warmer").update({"source": None, "pattern": None})
        with self.assertRaisesRegex(GeneratorError, "no captured code"):
            render_esphome(manifest, self.reports)

    def test_duplicate_position_is_refused(self):
        manifest = load_manifest()
        entry(manifest, "cool_50")["position"] = 2
        with self.assertRaisesRegex(GeneratorError, "duplicate position 2"):
            render_esphome(manifest, self.reports)

    def test_one_pattern_maps_to_one_entry(self):
        manifest = load_manifest()
        entry(manifest, "cool_50")["pattern"] = "7B50020C"
        with self.assertRaisesRegex(GeneratorError, "already belongs to power"):
            render_esphome(manifest, self.reports)

    def test_manifest_lists_the_13_remote_buttons_in_order(self):
        buttons = sorted((c for c in load_manifest()["commands"] if c.get("position")), key=lambda c: c["position"])
        self.assertEqual([c["position"] for c in buttons], list(range(1, 14)))
        self.assertEqual(
            [c["label"] for c in buttons],
            ["Night mode", "Power", "Color warmer", "Brightness up", "Color cooler", "Brightness down",
             "Cool 100%", "Warm 100%", "Warm 50%", "Cool 50%", "Neutral 100%", "Neutral 50%", "Timer (10/40 min auto off)"],
        )

    def test_every_exposed_command_is_verified_and_logged(self):
        log = (REPO / "docs" / "hardware-test-log.md").read_text(encoding="utf-8")
        # A command counts as verified once the log has a passing H4 row (the
        # original remote sends this code and the lamp effect was observed) or a
        # passing H5 row (transmitted from Home Assistant).
        rows = [line for line in log.splitlines() if line.startswith(("| H4", "| H5"))]
        for cmd in load_manifest()["commands"]:
            if not cmd["expose"]:
                continue
            with self.subTest(command=cmd["id"]):
                self.assertIs(cmd["verified"], True)
                self.assertTrue(
                    any(cmd["pattern"] in row and "pass" in row for row in rows),
                    f"no H4/H5 row with 'pass' mentions {cmd['pattern']}",
                )

    def test_non_dominant_pattern_is_refused(self):
        manifest = load_manifest()
        entry(manifest, "power").update({"source": "Read.sub", "pattern": "7B50050B"})
        with self.assertRaisesRegex(GeneratorError, "dominant"):
            render_esphome(manifest, self.reports)

    def test_checksum_failure_is_refused(self):
        manifest = load_manifest()
        entry(manifest, "power")["pattern"] = "7B50020D"
        with self.assertRaisesRegex(GeneratorError, "checksum"):
            render_esphome(manifest, self.reports)

    def test_too_few_clean_frames_is_refused(self):
        reports = copy.deepcopy(self.reports)
        reports["Pwr.sub"]["dominant_count"] = 9
        with self.assertRaisesRegex(GeneratorError, "fewer than 10"):
            render_esphome(load_manifest(), reports)

    def test_missing_source_is_refused(self):
        manifest = load_manifest()
        entry(manifest, "power")["source"] = "Nope.sub"
        with self.assertRaisesRegex(GeneratorError, "Nope.sub"):
            render_esphome(manifest, self.reports)

    def test_duplicate_id_is_refused(self):
        manifest = load_manifest()
        manifest["commands"].append(dict(entry(manifest, "power")))
        with self.assertRaisesRegex(GeneratorError, "duplicate"):
            render_esphome(manifest, self.reports)

    def test_output_is_deterministic(self):
        first = render_esphome(load_manifest(), analyze_dir(CAPTURES))
        second = render_esphome(load_manifest(), analyze_dir(CAPTURES))
        self.assertEqual(first, second)


class GeneratorCliTests(unittest.TestCase):
    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main([str(CAPTURES), *args])
        return code, out.getvalue(), err.getvalue()

    def test_check_passes_on_committed_file(self):
        code, _, err = self.run_main("--emit-esphome", str(GENERATED), "--check")
        self.assertEqual(code, 0, err)

    def test_check_fails_on_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.yaml"
            target.write_text(GENERATED.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
            code, _, err = self.run_main("--emit-esphome", str(target), "--check")
            self.assertEqual(code, 1)
            self.assertIn("out of date", err)

    def test_emit_writes_identical_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.yaml"
            self.assertEqual(self.run_main("--emit-esphome", str(target))[0], 0)
            self.assertEqual(target.read_bytes(), GENERATED.read_bytes())

    def test_refusal_exits_non_zero(self):
        manifest = load_manifest()
        entry(manifest, "warm_50")["id"] = "unknown_0b"
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "commands.json"
            bad.write_text(json.dumps(manifest), encoding="utf-8")
            target = Path(tmp) / "out.yaml"
            code, _, err = self.run_main("--emit-esphome", str(target), "--manifest", str(bad))
            self.assertEqual(code, 2)
            self.assertIn("unknown", err)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
