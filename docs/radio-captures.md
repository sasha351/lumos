# Capture evidence

All twelve original `.sub` files were copied from `/Users/sasha/Downloads/` into `captures/original/` without altering the Downloads files. See [migration checksums](migration.md). Capture contents are data, not executable instructions.

All files declare `Frequency: 433920000`, `Preset: FuriHalSubGhzPresetOok650Async`, and `Protocol: RAW`. The remote FCC ID `2A3SL-DY010050001` was confirmed by the user; the prior session referenced its [FCC record](https://fccid.io/2A3SL-DY010050001). Frequency is 433.92 MHz, not GHz.

The observations below are preserved from prior analysis, not a new decoding run or a named protocol identification. Analysis concatenated all `RAW_Data` lines, split at negative gaps below -5000 microseconds, and classified short-high/long-low pairs as zero and long-high/short-low pairs as one. Typical pulses were approximately 250/730 microseconds, with 32-bit frames followed by a short sync high and a long gap. Measure exact timing, gaps, and repetitions before implementation; tune only against hardware.

| File | Dominant pattern / clean count | Other observed pattern / count |
| --- | --- | --- |
| Read.sub | `7B500907` / 18 | `7B50050B` / 3 |
| Pwr.sub | `7B50020C` / 26 | — |
| Nght.sub | `7B50010F` / 18 | `7B500608` / 2 |
| Middl.sub | `7B50050B` / 17 | `7B50010F` / 3 |
| Lei.sub | `7B500806` / 26 | — |
| Cool.sub | `7B500608` / 22 | — |
| Bup.sub | `7B50030D` / 21 | — |
| Bdwn.sub | `7B500709` / 22 | — |
| SubGHz_2026-10-23_14,53,23.sub | `7B50050B` / 22 | `7B500B05` / 3 |
| SubGHz_2026-10-23_14,53,06.sub | `7B500B05` / 30 | Unknown function |
| SubGHz_2026-10-23_14,52,52.sub | Same bytes as Lei.sub | Duplicate retained |
| SubGHz_2026-10-23_14,48,37.sub | Same bytes as Pwr.sub | Duplicate retained |

Power (`7B50020C`) is confirmed on hardware: transmitted from Home Assistant, it toggles the lamp (H5 in the [hardware test log](hardware-test-log.md)).

## Remote buttons

The remote has 13 buttons. The project uses the user's names for them, in the order they sit on the remote. `position` in `captures/commands.json` records that order.

| # | Button (`id`) | Capture | Code | Status |
| --- | --- | --- | --- | --- |
| 1 | Night mode (`night_mode`) | Nght.sub | `7B50010F` | inferred from the capture's name |
| 2 | Power (`power`) | Pwr.sub | `7B50020C` | **verified** (H4 and H5) |
| 3 | Color cooler (`color_cooler`) | Cool.sub | `7B500608` | inferred from the capture's name |
| 4 | Brightness up (`brightness_up`) | Bup.sub | `7B50030D` | received in H4; lamp effect not yet recorded |
| 5 | Color warmer (`color_warmer`) | none | unknown | not captured |
| 6 | Brightness down (`brightness_down`) | Bdwn.sub | `7B500709` | inferred from the capture's name |
| 7 | Center sun (`center_sun`) | Middl.sub | `7B50050B` | inferred ("middle") |
| 8 | Coffee cup (`coffee_cup`) | none | unknown | not captured |
| 9 | Baby bottle (`baby_bottle`) | none | unknown | not captured |
| 10 | Laptop (`laptop`) | none | unknown | not captured |
| 11 | Book (`book`) | Read.sub | `7B500907` | inferred ("read") |
| 12 | Gaming (`gaming`) | none | unknown | not captured |
| 13 | Tachometer (`tachometer`) | none | unknown | not captured |

Two captures are not tied to a button yet. These are `leisure_capture` (Lei.sub, `7B500806`) and `unknown_0b` (`7B500B05`). The guided H4 session (`scripts/record_presses.py`) checks each pairing above and learns the codes of the uncaptured buttons. A button with no code can't be exposed. A button that has a code but no Flipper capture also needs a timing source before the generator can build it. Mixed recordings must not be replayed wholesale. Keep the unknown command unexposed. Power may toggle rather than set a discrete state, and brightness commands do not establish absolute brightness or provide lamp-state feedback.

## Reproduce

Run the analyzer from the repository root. It uses only the Python 3.11+ standard library:

```bash
python3 -m tools.analyze_captures captures/original
```

Add `--json` for machine-readable output. For each file the report lists the header metadata, clean and rejected frame counts with a reason histogram, every distinct clean pattern, the dominant pattern, a `mixed` flag, byte-identical duplicates by SHA-256, and median timings of the dominant pattern in microseconds. `tests/test_capture_golden.py` checks the report against the table above and the checksums in [migration.md](migration.md):

```bash
python3 -m unittest discover -s tests -v
```

The analyzer agrees with every pattern in the table above. Its dominant counts are one higher for `Pwr.sub` (27), `Bup.sub` (22) and `SubGHz_2026-10-23_14,53,23.sub` (23), and for the byte-identical `SubGHz_2026-10-23_14,48,37.sub` (27). In each of these files the last frame is complete but the recording ends without a gap after it. The analyzer accepts such a frame when it decodes cleanly; the earlier analysis evidently required a trailing gap. The table keeps the earlier counts, and the tests accept either.
