"""Unit tests for tools.lumos_captures using synthetic data only."""

import unittest

from tools.lumos_captures import (
    Frame,
    SubFile,
    checksum_ok,
    decode_frame,
    frames,
    parse_sub_text,
    split_frames,
)

KNOWN_PATTERNS = [
    0x7B50020C,
    0x7B50030D,
    0x7B500709,
    0x7B500608,
    0x7B500907,
    0x7B50050B,
    0x7B50010F,
    0x7B500806,
    0x7B500B05,
]

HEADER = (
    "Filetype: Flipper SubGhz RAW File\n"
    "Version: 1\n"
    "Frequency: 433920000\n"
    "Preset: FuriHalSubGhzPresetOok650Async\n"
    "Protocol: RAW\n"
)


def synth_frame(value, short=250, long=730, sync=250):
    """Build a 65-value frame (32 bit pairs + sync high), MSB first, in µs."""
    out = []
    for bit in range(31, -1, -1):
        if (value >> bit) & 1:
            out += [long, -short]
        else:
            out += [short, -long]
    out.append(sync)
    return out


class ParseSubTextTests(unittest.TestCase):
    def test_header_fields(self):
        sub = parse_sub_text(HEADER + "RAW_Data: 250 -730 740 -240\n", path="x.sub")
        self.assertIsInstance(sub, SubFile)
        self.assertEqual(sub.path, "x.sub")
        self.assertEqual(sub.frequency, 433920000)
        self.assertEqual(sub.preset, "FuriHalSubGhzPresetOok650Async")
        self.assertEqual(sub.protocol, "RAW")
        self.assertEqual(sub.pulses, [250, -730, 740, -240])

    def test_raw_data_lines_are_concatenated_across_frame_boundary(self):
        frame = synth_frame(0x7B50020C)
        first, second = frame[:20], frame[20:] + [-7578]
        text = (
            HEADER
            + "RAW_Data: " + " ".join(map(str, first)) + "\n"
            + "RAW_Data: " + " ".join(map(str, second)) + "\n"
        )
        sub = parse_sub_text(text)
        self.assertEqual(sub.pulses, frame + [-7578])
        decoded = frames(sub)
        self.assertEqual(len(decoded), 1)
        self.assertEqual(decoded[0].value, 0x7B50020C)

    def test_malformed_token_raises(self):
        with self.assertRaisesRegex(ValueError, "RAW_Data"):
            parse_sub_text(HEADER + "RAW_Data: 250 -730 abc\n")

    def test_wrong_protocol_raises(self):
        text = HEADER.replace("Protocol: RAW", "Protocol: Princeton")
        with self.assertRaisesRegex(ValueError, "Protocol"):
            parse_sub_text(text + "RAW_Data: 250 -730\n")

    def test_missing_filetype_raises(self):
        text = HEADER.replace("Filetype: Flipper SubGhz RAW File\n", "")
        with self.assertRaisesRegex(ValueError, "Filetype"):
            parse_sub_text(text + "RAW_Data: 250 -730\n")


class SplitFramesTests(unittest.TestCase):
    def test_gap_threshold(self):
        chunks = split_frames([1, -2, 3, -5000, 4, -5001, 5, -6000])
        # -5000 is not below the threshold, so it stays inside the first chunk.
        self.assertEqual(chunks, [([1, -2, 3, -5000, 4], -5001), ([5], -6000)])

    def test_trailing_frame_without_gap(self):
        chunks = split_frames([1, -2, -7000, 3, -4])
        self.assertEqual(chunks, [([1, -2], -7000), ([3, -4], None)])

    def test_leading_gap_keeps_empty_first_chunk(self):
        chunks = split_frames([-8000, 1, -2, -7000])
        self.assertEqual(chunks, [([], -8000), ([1, -2], -7000)])

    def test_empty_chunk_is_rejected_not_dropped(self):
        sub = SubFile("m", 433920000, "p", "RAW", [-8000] + synth_frame(0x7B50020C) + [-7578])
        result = frames(sub)
        self.assertEqual(len(result), 2)
        self.assertIsNone(result[0].value)
        self.assertEqual(result[0].reject_reason, "length 0 != 65")
        self.assertEqual(result[1].index, 1)
        self.assertEqual(result[1].value, 0x7B50020C)
        self.assertEqual(result[1].gap, -7578)


class DecodeFrameTests(unittest.TestCase):
    def test_round_trip_power(self):
        self.assertEqual(decode_frame(synth_frame(0x7B50020C)), (0x7B50020C, None))

    def test_round_trip_all_known_patterns(self):
        for value in KNOWN_PATTERNS:
            with self.subTest(value=hex(value)):
                self.assertEqual(decode_frame(synth_frame(value)), (value, None))

    def test_length_63_rejected(self):
        value, reason = decode_frame(synth_frame(0x7B50020C)[:63])
        self.assertIsNone(value)
        self.assertEqual(reason, "length 63 != 65")

    def test_out_of_window_pulse_reports_index(self):
        pulses = synth_frame(0x7B50020C)
        pulses[12] = 1612
        value, reason = decode_frame(pulses)
        self.assertIsNone(value)
        self.assertEqual(reason, "pulse 1612 at 12 out of window")

    def test_gap_between_windows_rejected(self):
        pulses = synth_frame(0x7B50020C)
        pulses[3] = -470  # between short (<=400) and long (>=550)
        value, reason = decode_frame(pulses)
        self.assertIsNone(value)
        self.assertEqual(reason, "pulse -470 at 3 out of window")

    def test_non_alternating_signs_rejected(self):
        pulses = synth_frame(0x7B50020C)
        pulses[5] = -pulses[5]
        value, reason = decode_frame(pulses)
        self.assertIsNone(value)
        self.assertIn("sign", reason)
        self.assertIn("5", reason)

    def test_must_start_positive(self):
        pulses = [-p for p in synth_frame(0x7B50020C)]
        value, reason = decode_frame(pulses)
        self.assertIsNone(value)
        self.assertIn("sign", reason)

    def test_long_sync_rejected(self):
        pulses = synth_frame(0x7B50020C, sync=730)
        value, reason = decode_frame(pulses)
        self.assertIsNone(value)
        self.assertIn("sync", reason)

    def test_invalid_pair_rejected(self):
        pulses = synth_frame(0x7B50020C)
        pulses[0], pulses[1] = 250, -240  # short high + short low is neither 0 nor 1
        value, reason = decode_frame(pulses)
        self.assertIsNone(value)
        self.assertIn("pair", reason)

    def test_window_bounds_inclusive(self):
        pulses = synth_frame(0x7B50020C, short=150, long=950, sync=400)
        self.assertEqual(decode_frame(pulses), (0x7B50020C, None))
        pulses = synth_frame(0x7B50020C, short=400, long=550, sync=150)
        self.assertEqual(decode_frame(pulses), (0x7B50020C, None))

    def test_checksum_failure_rejected(self):
        value, reason = decode_frame(synth_frame(0x7B50020D))
        self.assertIsNone(value)
        self.assertEqual(reason, "checksum")


class ChecksumTests(unittest.TestCase):
    def test_known_patterns_pass(self):
        for value in KNOWN_PATTERNS:
            with self.subTest(value=hex(value)):
                self.assertTrue(checksum_ok(value))

    def test_corrupted_value_fails(self):
        self.assertFalse(checksum_ok(0x7B50020D))


class FramesTests(unittest.TestCase):
    def test_frames_indexes_and_rejections(self):
        pulses = (
            [533, -3944, 67]  # preamble noise, rejected
            + [-7600]
            + synth_frame(0x7B50020C)
            + [-7578]
            + synth_frame(0x7B50020C)[:40]  # truncated tail at EOF
        )
        result = frames(SubFile("m", 433920000, "p", "RAW", pulses))
        self.assertEqual([f.index for f in result], [0, 1, 2])
        self.assertIsInstance(result[0], Frame)
        self.assertEqual(result[0].reject_reason, "length 3 != 65")
        self.assertEqual(result[1].value, 0x7B50020C)
        self.assertIsNone(result[1].reject_reason)
        self.assertEqual(result[1].gap, -7578)
        self.assertIsNone(result[2].gap)
        self.assertEqual(result[2].reject_reason, "length 40 != 65")


if __name__ == "__main__":
    unittest.main()
