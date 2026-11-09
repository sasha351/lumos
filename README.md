# Lumos

Control an existing 433.92 MHz lamp from Home Assistant with a DORHEA ESP32-S3 N16R8 and an AOICRIE CC1101 radio.

## Status

Evidence and planning only. The user reports that the boards are soldered according to the wiring diagram, connected to the laptop, and that Flipper replay controls the lamp. Board identity, physical wiring, and radio operation have not been independently verified. No firmware has been created or flashed, and no Home Assistant integration has been configured.

The active project is `/Users/sasha/Documents/lumos`. Its existing Git remote is `https://github.com/sasha351/lumos.git`. Both old project paths have been cleared after preserving the source files. The remote was preserved; the user subsequently authorized committing and pushing the migration to `main`.

## Start here

- [Wiring and hardware](CC1101-ESP32-S3-wiring.md)
- [Implementation plan](docs/superpowers/plans/2026-11-09-lamp-controller.md)
- [Capture observations and uncertain labels](docs/radio-captures.md)
- [Original captures](captures/original/) — all 12 files, verified against Downloads with SHA-256
- [Migration provenance and checksums](docs/migration.md)

The proposed implementation uses ESPHome with separate CC1101 transmit and receive pins. Next, isolate and measure a clean power frame, then identify the actual ESP chip and flash before configuring firmware. Start with Home Assistant buttons; lamp state and absolute brightness are not established. Mixed recordings must not be replayed wholesale.

Supply Wi-Fi and Home Assistant credentials locally through ignored secrets files. ESPHome was not on the shell PATH in the prior session; Python 3 and `uv` were found. The previously observed `/dev/cu.usbmodem21101` must be re-enumerated before use. Firmware setup, compilation, flashing, and hardware tests belong to later plan phases.
