# Lumos

Control an existing 433.92 MHz lamp from Home Assistant with a DORHEA ESP32-S3 N16R8 and an AOICRIE CC1101 radio.

## Status

The ESPHome firmware runs on the board and is added to Home Assistant. The CC1101 answers over SPI (Chip ID `0x0014`), and frames received from the original remote decode cleanly. Pressing Power in Home Assistant toggles the lamp. Two pairs of jumpers were crossed and have been fixed; see the as-built table in the [wiring doc](CC1101-ESP32-S3-wiring.md). The remote has 13 buttons, listed in [Remote buttons](docs/radio-captures.md#remote-buttons) under the user's names. Power is the only exposed command, and it is verified. The other buttons stay hidden until each is confirmed on hardware with the guided session `scripts/record_presses.py`. Results are in the [hardware test log](docs/hardware-test-log.md). The capture analyzer, command generator and configuration pass `python3 -m unittest discover -s tests`.

The active project is `/Users/sasha/Documents/lumos`. Its existing Git remote is `https://github.com/sasha351/lumos.git`. Both old project paths have been cleared after preserving the source files. The remote was preserved; the user subsequently authorized committing and pushing the migration to `main`.

## Start here

- [Wiring and hardware](CC1101-ESP32-S3-wiring.md)
- [Implementation plan](docs/superpowers/plans/2026-11-09-lamp-controller.md)
- [Subagent execution plan (Copilot)](docs/superpowers/plans/2026-11-09-copilot-subagent-plan.md) and [agent guardrails](.github/copilot-instructions.md)
- [Hardware test log](docs/hardware-test-log.md)
- [Capture observations and uncertain labels](docs/radio-captures.md)
- [Original captures](captures/original/) — all 12 files, verified against Downloads with SHA-256
- [Migration provenance and checksums](docs/migration.md)

The proposed implementation uses ESPHome with separate CC1101 transmit and receive pins. Next, isolate and measure a clean power frame, then identify the actual ESP chip and flash before configuring firmware. Start with Home Assistant buttons; lamp state and absolute brightness are not established. Mixed recordings must not be replayed wholesale.

Supply Wi-Fi and Home Assistant credentials locally through ignored secrets files. ESPHome was not on the shell PATH in the prior session; Python 3 and `uv` were found. The previously observed `/dev/cu.usbmodem21101` must be re-enumerated before use. Firmware setup, compilation, flashing, and hardware tests belong to later plan phases.
