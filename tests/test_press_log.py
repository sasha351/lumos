"""Tests for tools.press_log, the H4 receive-session decoder.

The fixture holds frames the board really received from the original remote
on 2026-11-09 (Brightness up at 17:09:55, Power at 17:09:58 and 17:09:59),
split across lines the way `esphome logs` prints them, plus noise lines.
"""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.press_log import (
    RawJoiner,
    Session,
    evaluate,
    find_command,
    format_report,
    load_manifest,
    main,
    parse_log,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "h4_plain_esphome_logs.txt"


def fixture_lines():
    return FIXTURE.read_text(encoding="utf-8").splitlines()


class RawJoinerTests(unittest.TestCase):
    def test_rebuilds_a_frame_split_over_two_lines(self):
        joiner = RawJoiner()
        done = []
        for line in fixture_lines()[3:6]:  # first frame (2 lines) + start of the next
            done += joiner.feed(line)
        self.assertEqual(len(done), 1)
        stamp, values = done[0]
        self.assertEqual(stamp, "17:09:55.258")
        self.assertEqual(len(values), 65)
        self.assertEqual(values[:3], [261, -726, 742])
        self.assertEqual(values[-1], 256)

    def test_strips_colour_codes_and_ignores_other_components(self):
        joiner = RawJoiner()
        self.assertEqual(joiner.feed("[17:00:00.000][C][wifi:1688]: WiFi:"), [])
        joiner.feed("\x1b[0;32m[17:00:00.001][I][remote.raw:035]: Received Raw: 100, -200\x1b[0m")
        self.assertEqual(joiner.flush(), [("17:00:00.001", [100, -200])])


class PlainLogTests(unittest.TestCase):
    def test_bursts_are_split_by_silence(self):
        steps = parse_log(fixture_lines())
        self.assertEqual([len(s.frames) for s in steps], [3, 3, 2])

    def test_order_labels_bursts_and_all_pass(self):
        results = evaluate(parse_log(fixture_lines()), load_manifest(), ["Brightness up", "power", "Power"])
        self.assertEqual([r.verdict for r in results], ["PASS", "PASS", "PASS"])
        self.assertEqual(results[0].counts, {"7B50030D": 3})
        self.assertEqual(results[1].timings["long_high"] // 10, 73)

    def test_wrong_order_is_reported(self):
        results = evaluate(parse_log(fixture_lines()), load_manifest(), ["power", "power", "power"])
        self.assertEqual(results[0].verdict, "WRONG: got Brightness up")

    def test_without_order_reports_what_was_heard(self):
        results = evaluate(parse_log(fixture_lines()), load_manifest())
        self.assertEqual([r.verdict for r in results], ["GOT Brightness up", "GOT Power", "GOT Power"])


class SessionTests(unittest.TestCase):
    def record(self, plan):
        """Feed fixture lines through a Session; plan maps line index -> (name, effect)."""
        out = io.StringIO()
        session = Session(out)
        effect = None
        for i, line in enumerate(fixture_lines()):
            if i in plan:
                if effect is not None:
                    session.set_effect(effect)
                name, effect = plan[i]
                session.start_step(name)
            session.on_log_line(line)
        session.set_effect(effect)
        session.finish()
        return out.getvalue()

    def test_session_file_round_trip(self):
        text = self.record({3: ("Brightness up", "got brighter"), 9: ("power", "turned off"), 15: ("Night mode", "nothing")})
        self.assertNotIn("Received Raw", text)  # frames are stored compactly
        self.assertNotIn("192.168", text)  # no network details
        steps = parse_log(text.splitlines())
        self.assertEqual([s.name for s in steps], ["Brightness up", "power", "Night mode"])
        self.assertEqual([s.effect for s in steps], ["got brighter", "turned off", "nothing"])
        results = evaluate(steps, load_manifest())
        self.assertEqual(results[0].verdict, "PASS")
        self.assertEqual(results[1].verdict, "PASS")
        self.assertEqual(results[2].verdict, "WRONG: got Power")

    def test_noise_only_step_is_none(self):
        text = self.record({0: ("Color cooler", "nothing"), 3: ("brightness_up", "brighter")})
        results = evaluate(parse_log(text.splitlines()), load_manifest())
        self.assertEqual(results[0].verdict, "NONE: no lamp frame received")
        self.assertIn("# noise trains ignored in step 1: 2", text)


class LearningTests(unittest.TestCase):
    """Buttons with no captured code learn it from the press."""

    def manifest_without(self, *ids):
        manifest = load_manifest()
        for cmd in manifest:
            if cmd["id"] in ids:
                cmd.update({"source": None, "pattern": None})
        return manifest

    def test_uncaptured_button_learns_a_new_code(self):
        manifest = self.manifest_without("brightness_up")
        manifest = [c for c in manifest if c["pattern"] != "7B50030D"]
        results = evaluate(parse_log(fixture_lines()), manifest, ["Brightness up"])
        self.assertEqual(results[0].verdict, "LEARNED 7B50030D")
        self.assertIn("1 learned a new button code", format_report(results))

    def test_code_of_an_unassigned_capture_is_named(self):
        manifest = self.manifest_without("brightness_up")
        manifest.append({"id": "bup_capture", "position": None, "label": "x", "pattern": "7B50030D"})
        results = evaluate(parse_log(fixture_lines()), manifest, ["Brightness up"])
        self.assertEqual(results[0].verdict, "LEARNED 7B50030D (same as bup_capture)")

    def test_code_already_owned_by_another_button_is_a_conflict(self):
        manifest = self.manifest_without("color_warmer")
        results = evaluate(parse_log(fixture_lines()), manifest, ["Color warmer"])
        self.assertEqual(results[0].verdict, "CONFLICT: 7B50030D is listed as Brightness up")

    def test_remote_buttons_are_in_physical_order(self):
        from tools.press_log import remote_buttons
        labels = [c["label"] for c in remote_buttons(load_manifest())]
        self.assertEqual(labels[:3], ["Night mode", "Power", "Color warmer"])
        self.assertEqual(len(labels), 13)


class LookupAndCliTests(unittest.TestCase):
    def test_find_command_by_id_or_label(self):
        manifest = load_manifest()
        self.assertEqual(find_command("Brightness up", manifest)["id"], "brightness_up")
        self.assertEqual(find_command("night_mode", manifest)["label"], "Night mode")
        self.assertEqual(find_command("NEUTRAL 100%", manifest)["id"], "neutral_100")
        self.assertEqual(find_command("warm 50", manifest)["id"], "warm_50")
        self.assertEqual(find_command("POWER", manifest)["id"], "power")
        self.assertIsNone(find_command("mystery", manifest))

    def test_cli_prints_a_table(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(main([str(FIXTURE), "--order", "Brightness up,Power,Power"]), 0)
        self.assertIn("3 of 3 steps passed.", buffer.getvalue())

    def test_report_lists_effects(self):
        results = evaluate(parse_log(fixture_lines()), load_manifest(), ["Brightness up"])
        results[0].effect = "got brighter"
        self.assertIn("| got brighter |", format_report(results))


if __name__ == "__main__":
    unittest.main()
