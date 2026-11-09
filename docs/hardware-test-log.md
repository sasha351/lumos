# Hardware test log

Results of the HUMAN gates H1–H5 from the [subagent execution plan](superpowers/plans/2026-11-09-copilot-subagent-plan.md#human-gates-h1h5-no-agent). The user runs each gate on the physical hardware. Agents only read this file.

H1 and H2 were run by the user on November 9, 2026, on macOS with `esptool v5.6.0` (via `uvx esptool`). The results below were transcribed from the user's terminal output. The board enumerated as `/dev/cu.usbmodem101`, not the previously noted `/dev/cu.usbmodem21101`. Re-enumerate with `ls /dev/cu.usb*` before each session.

| Gate | Date | Result (pass/fail) | Notes / log excerpt |
| --- | --- | --- | --- |
| H1 chip / flash / PSRAM | 2026-11-09 | pass | `ESP32-S3 (QFN56) (revision v0.2)`; features `Wi-Fi, BT 5 (LE), Dual Core + LP Core, 240MHz, Embedded PSRAM 8MB (AP_3v3)`; crystal 40 MHz; USB mode `USB-Serial/JTAG`; flash manufacturer `68`, device `4018`, detected size `16MB`, eFuse flash type quad, flash voltage 3.3 V. |
| H2 backup file + SHA-256 | 2026-11-09 | pass | `read-flash 0 ALL` read 16,777,216 bytes in 72.8 s to `lumos-factory-backup.bin`. `verify-flash 0` reported `Verification successful (digest matched)`. SHA-256 `5399f1416b3f6e64969f353d6d0189c2d40497b6ed249af6748604b9d3c9c147`. The file is git-ignored (`*.bin`) and is kept only on the user's laptop. |
| H3 boot log OK, no TX at boot | 2026-11-09 | **pass** (after jumper fix; first run failed) | First run: flashed over USB (866 KB, hash verified). Boots `ESP-IDF v5.5.6`, `SPI_FAST_FLASH_BOOT`, ESPHome 2026.10.2. Wi-Fi connected on 2.4 GHz (`192.168.29.140`), API and OTA (encrypted) up, no `remote_transmitter` activity at boot. **CC1101 failed:** `CC1101 found! Chip ID: 0xF77F` then `cc1101 is marked FAILED`. A real CC1101 reports PARTNUM `0x00` and VERSION `0x14` (some clones `0x04`/`0x07`), so SPI reads return garbage: check VCC/GND, CS (GPIO10), SCK (GPIO12), MOSI (GPIO11) and MISO (GPIO13). Earlier silence was the chip sitting in ROM download mode (`rst:0x15`, `boot:0x3`, `waiting for download`) after `esphome logs` opened the port with DTR/RTS asserted; fixed with `logger: deassert_rts_dtr: true`. **Photo inspection afterwards:** power, SCK and MISO match the plan, but the CS and MOSI jumpers are crossed (GPIO10 goes to radio pin 6 MOSI and GPIO11 to pin 4 CSN). The two jumpers are being swapped at the ESP end; the firmware keeps the planned pins. See "As built" in the wiring doc. **Re-run after the swap (same firmware, no reflash):** the config dump over the Wi-Fi API shows `CC1101: Chip ID: 0x0014`, `Frequency: 433919840 Hz`, `Modulation: ASK/OOK`, `CS Pin: GPIO10`, SPI `SDO GPIO11`/`SDI GPIO13`/`CLK GPIO12` on `SPI2_HOST`, and no component marked FAILED. The receiver on GPIO5 logs short noise bursts (100–375 µs), so the radio is in RX. No transmitter activity. |
| H4 receive per button (one row each) | | | |
| H5 power: best `tx_repeat`, double-toggle? | | | |

## Firmware settings implied by H1

- **PSRAM:** 8 MB embedded PSRAM is the ESP32-S3R8 die variant, which is octal. The firmware leaves PSRAM unconfigured because it does not need it; if it is ever enabled, use `psram: mode: octal`.
- **Flash:** `flash_size: 16MB`.
- **Logging:** the board uses the native USB-Serial/JTAG peripheral, so set `logger: hardware_uart: USB_SERIAL_JTAG` to see boot logs on the USB port.
- **Pins:** the selected radio pins (GPIO 4, 5, 10, 11, 12 and 13) do not collide with octal PSRAM (GPIO 33–37), native USB (GPIO 19–20) or strapping pins (GPIO 0, 3, 45, 46).

## Recovery

To restore the original firmware, write the backup back to address 0 and check the SHA-256 above first:

```bash
uvx esptool --port /dev/cu.usbmodem101 write-flash 0 lumos-factory-backup.bin
```

## Button meaning confirmation

| Manifest id | Observed lamp effect | Keep label? (y/n) | New label |
| --- | --- | --- | --- |
| | | | |
