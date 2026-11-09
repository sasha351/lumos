"""Golden tests that run the analyzer over the real captures in captures/original."""

import re
import unittest
from pathlib import Path

from tools.analyze_captures import analyze_dir
from tools.lumos_captures import checksum_ok, frames, parse_sub

REPO = Path(__file__).resolve().parents[1]
CAPTURES = REPO / "captures" / "original"
MIGRATION_DOC = REPO / "docs" / "migration.md"

# (file, dominant, documented count, other patterns) from the plan's "Verified facts".
EXPECTED = [
    ("Pwr.sub", "7B50020C", 26, set()),
    ("Bup.sub", "7B50030D", 21, set()),
    ("Bdwn.sub", "7B500709", 22, set()),
    ("Cool.sub", "7B500608", 22, set()),
    ("Read.sub", "7B500907", 18, {"7B50050B"}),
    ("Nght.sub", "7B50010F", 18, {"7B500608"}),
    ("Middl.sub", "7B50050B", 17, {"7B50010F"}),
    ("Lei.sub", "7B500806", 26, set()),
    ("SubGHz_2026-10-23_14,53,23.sub", "7B50050B", 22, {"7B500B05"}),
    ("SubGHz_2026-10-23_14,53,06.sub", "7B500B05", 30, set()),
    # Byte-identical duplicates inherit their twin's expectations.
    ("SubGHz_2026-10-23_14,52,52.sub", "7B500806", 26, set()),
    ("SubGHz_2026-10-23_14,48,37.sub", "7B50020C", 26, set()),
]

MIXED = {"Read.sub", "Nght.sub", "Middl.sub", "SubGHz_2026-10-23_14,53,23.sub"}


class CaptureGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = {r["file"]: r for r in analyze_dir(CAPTURES)}

    def test_all_twelve_files_present(self):
        self.assertEqual(len(self.reports), 12)
        self.assertEqual(set(self.reports), {row[0] for row in EXPECTED})

    def test_dominant_and_other_patterns(self):
        for name, dominant, docs_count, others in EXPECTED:
            with self.subTest(file=name):
                report = self.reports[name]
                self.assertEqual(report["dominant"], dominant)
                self.assertEqual({p["pattern"] for p in report["patterns"][1:]}, others)
                self.assertGreaterEqual(report["dominant_count"], docs_count - 1)

    def test_mixed_flag(self):
        for name, report in self.reports.items():
            with self.subTest(file=name):
                self.assertEqual(report["mixed"], name in MIXED)

    def test_duplicates_detected(self):
        self.assertEqual(self.reports["SubGHz_2026-10-23_14,52,52.sub"]["duplicates"], ["Lei.sub"])
        self.assertEqual(self.reports["Lei.sub"]["duplicates"], ["SubGHz_2026-10-23_14,52,52.sub"])
        self.assertEqual(self.reports["SubGHz_2026-10-23_14,48,37.sub"]["duplicates"], ["Pwr.sub"])
        self.assertEqual(self.reports["Pwr.sub"]["duplicates"], ["SubGHz_2026-10-23_14,48,37.sub"])
        for name in {"Bup.sub", "Bdwn.sub", "Cool.sub", "Read.sub", "Nght.sub", "Middl.sub"}:
            self.assertEqual(self.reports[name]["duplicates"], [])

    def test_header_metadata(self):
        for name, report in self.reports.items():
            with self.subTest(file=name):
                self.assertEqual(report["frequency"], 433920000)
                self.assertEqual(report["preset"], "FuriHalSubGhzPresetOok650Async")

    def test_power_median_timings(self):
        t = self.reports["Pwr.sub"]["timings"]
        for key, expected in [
            ("short_high", 249),
            ("long_high", 737),
            ("short_low", 240),
            ("long_low", 726),
            ("sync_high", 249),
        ]:
            with self.subTest(key=key):
                self.assertAlmostEqual(t[key], expected, delta=15)
        self.assertAlmostEqual(t["gap"], -7578, delta=50)

    def test_every_clean_frame_passes_checksum_and_none_fail_it(self):
        for path in sorted(CAPTURES.glob("*.sub")):
            with self.subTest(file=path.name):
                all_frames = frames(parse_sub(str(path)))
                for frame in all_frames:
                    if frame.value is not None:
                        self.assertTrue(checksum_ok(frame.value))
                # The checksum rule is an observation: no otherwise-valid frame breaks it.
                self.assertNotIn("checksum", [f.reject_reason for f in all_frames])

    def test_capture_sha256_matches_migration_record(self):
        rows = re.findall(
            r"^\|\s*`captures/original/([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|",
            MIGRATION_DOC.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
        recorded = dict(rows)
        self.assertEqual(len(recorded), 12, "migration.md should list all 12 captures")
        for name, report in self.reports.items():
            with self.subTest(file=name):
                self.assertEqual(report["sha256"], recorded[name])


if __name__ == "__main__":
    unittest.main()
