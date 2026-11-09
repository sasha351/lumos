# Hardware test log

Results of the HUMAN gates H1–H5 from the [subagent execution plan](superpowers/plans/2026-11-09-copilot-subagent-plan.md#human-gates-h1h5-no-agent). The user runs each gate on the physical hardware. Agents only read this file.

H1 and H2 were run by the user on November 9, 2026, on macOS with `esptool v5.6.0` (via `uvx esptool`). The results below were transcribed from the user's terminal output. The board enumerated as `/dev/cu.usbmodem101`, not the previously noted `/dev/cu.usbmodem21101`. Re-enumerate with `ls /dev/cu.usb*` before each session.

| Gate | Date | Result (pass/fail) | Notes / log excerpt |
| --- | --- | --- | --- |
| H1 chip / flash / PSRAM | 2026-11-09 | pass | `ESP32-S3 (QFN56) (revision v0.2)`; features `Wi-Fi, BT 5 (LE), Dual Core + LP Core, 240MHz, Embedded PSRAM 8MB (AP_3v3)`; crystal 40 MHz; USB mode `USB-Serial/JTAG`; flash manufacturer `68`, device `4018`, detected size `16MB`, eFuse flash type quad, flash voltage 3.3 V. |
| H2 backup file + SHA-256 | 2026-11-09 | pass | `read-flash 0 ALL` read 16,777,216 bytes in 72.8 s to `lumos-factory-backup.bin`. `verify-flash 0` reported `Verification successful (digest matched)`. SHA-256 `5399f1416b3f6e64969f353d6d0189c2d40497b6ed249af6748604b9d3c9c147`. The file is git-ignored (`*.bin`) and is kept only on the user's laptop. |
| H3 boot log OK, no TX at boot | | | |
| H4 receive per button (one row each) | | | |
| H5 power: best `tx_repeat`, double-toggle? | | | |

## Firmware settings implied by H1

- **PSRAM:** 8 MB embedded PSRAM is the ESP32-S3R8 die variant, which is octal. Configure `psram: mode: octal`.
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
