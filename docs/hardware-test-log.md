# Hardware test log

Results of the HUMAN gates H1–H5 from the [subagent execution plan](superpowers/plans/2026-11-09-copilot-subagent-plan.md#human-gates-h1h5-no-agent). The user runs each gate on the physical hardware. Agents only read this file.

H1 and H2 were run by the user on November 9, 2026, on macOS with `esptool v5.6.0` (via `uvx esptool`). The results below were transcribed from the user's terminal output. The board enumerated as `/dev/cu.usbmodem101`, not the previously noted `/dev/cu.usbmodem21101`. Re-enumerate with `ls /dev/cu.usb*` before each session.

| Gate | Date | Result (pass/fail) | Notes / log excerpt |
| --- | --- | --- | --- |
| H1 chip / flash / PSRAM | 2026-11-09 | pass | `ESP32-S3 (QFN56) (revision v0.2)`; features `Wi-Fi, BT 5 (LE), Dual Core + LP Core, 240MHz, Embedded PSRAM 8MB (AP_3v3)`; crystal 40 MHz; USB mode `USB-Serial/JTAG`; flash manufacturer `68`, device `4018`, detected size `16MB`, eFuse flash type quad, flash voltage 3.3 V. |
| H2 backup file + SHA-256 | 2026-11-09 | pass | `read-flash 0 ALL` read 16,777,216 bytes in 72.8 s to `lumos-factory-backup.bin`. `verify-flash 0` reported `Verification successful (digest matched)`. SHA-256 `5399f1416b3f6e64969f353d6d0189c2d40497b6ed249af6748604b9d3c9c147`. The file is git-ignored (`*.bin`) and is kept only on the user's laptop. |
| H3 boot log OK, no TX at boot | 2026-11-09 | **pass** (after jumper fix; first run failed) | First run: flashed over USB (866 KB, hash verified). Boots `ESP-IDF v5.5.6`, `SPI_FAST_FLASH_BOOT`, ESPHome 2026.10.2. Wi-Fi connected on 2.4 GHz (`192.168.29.140`), API and OTA (encrypted) up, no `remote_transmitter` activity at boot. **CC1101 failed:** `CC1101 found! Chip ID: 0xF77F` then `cc1101 is marked FAILED`. A real CC1101 reports PARTNUM `0x00` and VERSION `0x14` (some clones `0x04`/`0x07`), so SPI reads return garbage: check VCC/GND, CS (GPIO10), SCK (GPIO12), MOSI (GPIO11) and MISO (GPIO13). Earlier silence was the chip sitting in ROM download mode (`rst:0x15`, `boot:0x3`, `waiting for download`) after `esphome logs` opened the port with DTR/RTS asserted; fixed with `logger: deassert_rts_dtr: true`. **Photo inspection afterwards:** power, SCK and MISO match the plan, but the CS and MOSI jumpers are crossed (GPIO10 goes to radio pin 6 MOSI and GPIO11 to pin 4 CSN). The two jumpers are being swapped at the ESP end; the firmware keeps the planned pins. See "As built" in the wiring doc. **Re-run after the swap (same firmware, no reflash):** the config dump over the Wi-Fi API shows `CC1101: Chip ID: 0x0014`, `Frequency: 433919840 Hz`, `Modulation: ASK/OOK`, `CS Pin: GPIO10`, SPI `SDO GPIO11`/`SDI GPIO13`/`CLK GPIO12` on `SPI2_HOST`, and no component marked FAILED. The receiver on GPIO5 logs short noise bursts (100–375 µs), so the radio is in RX. No transmitter activity. |
| H4 receive: Power (`7B50020C`) | 2026-11-09 | pass | Original remote, two presses (17:09:58, 17:09:59). Received 12 of 12 frames clean, 65 values each, checksum OK, all decoding to `7B50020C`. Median timings: short high 242 µs, long high 734 µs, short low 243 µs, long low 730 µs, sync high 245 µs. The Flipper `Pwr.sub` medians are 249/737/240/726/249, so every value is within 7 µs. The trailing −7.5 ms gap ends each frame, so the receiver logs it as idle and not as a value. |
| H4 receive: Brightness up (`7B50030D`) | 2026-11-09 | pass | Original remote, one press (17:09:55). Received 7 of 7 frames clean, all decoding to `7B50030D` (matches `Bup.sub`). |
| H4 guided session, all 13 buttons | 2026-11-09 | pass | Run with `scripts/record_presses.py`, Power first, one press per button on the original remote. Session file: `captures/sessions/h4-20261109-174852.log` (on the user's laptop). Every button gave 5–6 clean frames with valid checksums. Third byte by button: 01 Night mode, 02 Power, 03 Brightness up, 04 Color cooler, 05 Center sun, 06 Color warmer, 07 Brightness down, 08 Coffee cup, 09 Book, 0A Laptop, 0B Baby bottle, 0C Gaming, 0D Tachometer. That is 01–0D with no gaps. |
| H4 receive: Power (`7B50020C`) | 2026-11-09 | pass | Session step 1: 7B50020C x5, 1 rejected; median timings (µs, short high, long high, short low, long low, sync) 242 734 242 730 243. Lamp: success. Matches `Pwr.sub`. One long train was rejected; it did not decode cleanly. |
| H4 receive: Night mode (`7B50010F`) | 2026-11-09 | pass | Session step 2: 7B50010F x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 242 736 241 730 240. Lamp: success. Matches `Nght.sub`. |
| H4 receive: Color cooler (`7B50040A`) | 2026-11-09 | pass | Session step 3: 7B50040A x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 242 734 241 730 242. Lamp: the lamp was already at its coolest, and the user reports it behaved as expected. **New code, never captured with the Flipper.** Re-check from Home Assistant when the lamp is not already at its coolest. |
| H4 receive: Brightness up (`7B50030D`) | 2026-11-09 | pass | Session step 4: 7B50030D x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 244 734 242 728 230. Lamp: success. Matches `Bup.sub`. |
| H4 receive: Color warmer (`7B500608`) | 2026-11-09 | pass | Session step 5: 7B500608 x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 243 735 243 729 244. Lamp: success. Matches `Cool.sub`. Recorded here under the session prompt's name, which was wrong; see the correction row below. |
| H4 receive: Brightness down (`7B500709`) | 2026-11-09 | pass | Session step 6: 7B500709 x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 244 735 243 726 244. Lamp: success. Matches `Bdwn.sub`. |
| H4 receive: Center sun (`7B50050B`) | 2026-11-09 | pass | Session step 7: 7B50050B x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 242 734 243 729 240. Lamp: success. Matches `Middl.sub`. |
| H4 receive: Coffee cup (`7B500806`) | 2026-11-09 | pass | Session step 8: 7B500806 x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 242 734 243 730 244. Lamp: success. Same code as `Lei.sub` ("leisure"). |
| H4 receive: Baby bottle (`7B500B05`) | 2026-11-09 | pass | Session step 9: 7B500B05 x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 243 734 243 729 249. Lamp: success. Same code as the formerly unknown capture `SubGHz_2026-10-23_14,53,06.sub` (`unknown_0b`). |
| H4 receive: Laptop (`7B500A04`) | 2026-11-09 | pass | Session step 10: 7B500A04 x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 242 738 242 729 244. Lamp: success. **New code, never captured with the Flipper.** |
| H4 receive: Book (`7B500907`) | 2026-11-09 | pass | Session step 11: 7B500907 x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 242 734 243 730 248. Lamp: success. Matches `Read.sub`. |
| H4 receive: Gaming (`7B500C02`) | 2026-11-09 | pass | Session step 12: 7B500C02 x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 242 735 240 730 258. Lamp: success. **New code, never captured with the Flipper.** |
| H4 receive: Tachometer (`7B500D03`) | 2026-11-09 | pass | Session step 13: 7B500D03 x6, 0 rejected; median timings (µs, short high, long high, short low, long low, sync) 244 738 241 728 256. Lamp: success. **New code, never captured with the Flipper.** |
| H4 correction: color temperature | 2026-11-09 | corrected | After the session, the user reported that Color warmer and Color cooler were reversed. `7B50040A` (step 3, the left button of the ring, "Color Temperature +" on the product diagram) is **Color warmer**. `7B500608` (step 5, the right button, "Color Temperature −") is **Color cooler**. That is the code in `Cool.sub`, so the Flipper file name was right all along. Both codes and their H4 passes stand; only the names swapped. |
| H4 rename: mode buttons | 2026-11-09 | renamed | At the user's request, the mode buttons are named for the color and brightness the product diagram lists, not their icons or the diagram's mode names. Center sun (`7B50050B`, 5500K, 100%) is Cool 100%. Coffee cup / Leisure (`7B500806`, 3000K, 100%) is Warm 100%. Baby bottle / Breastfeeding (`7B500B05`, 3000K) is Warm 50%. Laptop / Office (`7B500A04`, 5500K, 50%) is Cool 50%. Book / Reading (`7B500907`, 4000K, 100%) is Neutral 100%. Gaming / Entertainment (`7B500C02`, 4000K, 50%) is Neutral 50%. The diagram lists Breastfeeding as "50% warm light & 100% brightness". That would be the same as Leisure, so it is taken to mean 50% brightness, which fits the 3 × 2 pattern; this is **not yet confirmed by eye**. Tachometer (`7B500D03`) is the 10/40-minute auto-off **timer**. The user never uses it, so it stays recorded but is not exposed. |
| H4 note: GDO0/GDO2 yellow wires | 2026-11-09 | found crossed | ESPHome sets both GDO0 and GDO2 to serial data out in RX (`IOCFG0 = IOCFG2 = 0x0D`), so receiving on GPIO5 does not show which yellow wire reaches GDO0. Only GDO0 is the TX data input. Traced by hand: radio pin 3 (GDO0) went to ESP 5 and pin 8 (GDO2) to ESP 4, so they were crossed. The fix is to turn the 2-pin housing on ESP 4–5 end-for-end. The firmware keeps GPIO4 for TX and GPIO5 for RX. Re-check receive after the fix, before H5. |
| H5 power: best `tx_repeat`, double-toggle? | 2026-11-09 | **pass** (Power `7B50020C`, `tx_repeat` 8) | Device added to Home Assistant over the encrypted API. Pressing Power in HA toggled the lamp once, with no double toggle, from about 1.5 m (5 ft), with the antenna attached. For comparison, H4 logged 6–7 frames about 40 ms apart for one short press of the original remote, so 8 repeats (about 0.3 s on air) is close to what the remote sends. **Restart check: pass.** After a USB power cycle and 1 minute of waiting, the lamp did not change. **Minimum `tx_repeat`: 3.** The user swept counts upward from 1 at the same distance and reports 3 as the lowest reliable count. 8 also toggled the lamp once, so 3 and 8 bracket the usable range with no double toggle seen. **Chosen: `tx_repeat` 8,** nearly 3× the minimum and close to the 6–7 frames the real remote sends. |

## Running H4 (receive) per button

`scripts/record_presses.py` guides the test. It prompts for one button at a time, records the frames the board receives and the lamp effect you type, and prints a pass/fail table. It only listens. Run it from the repository root, with the board on Wi-Fi:

```bash
python3 scripts/record_presses.py
```

With no options it walks every exposed button in remote order: Night mode, Power, Color warmer, Brightness up, Color cooler, Brightness down, Cool 100%, Warm 100%, Warm 50%, Cool 50%, Neutral 100%, Neutral 50%. The hidden Timer is skipped. `--order "Laptop,Gaming"` picks a subset, and `--ask` prompts for each name. The verdicts are:

- `PASS`: the button sent its expected code.
- `WRONG`: it sent another button's code.
- `LEARNED`: a button with no capture sent a new code.
- `CONFLICT`: it sent a code already assigned to a different button.
- `NONE`: nothing was received.

Session files go to `captures/sessions/`. They hold only frames, step names and notes, with no Wi-Fi details or keys. Re-print a session's table with `python3 -m tools.press_log captures/sessions/<file>.log`.

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
| `night_mode` | as named (user: "success") | y | |
| `power` | as named (user: "success") | y | |
| `color_warmer` (`7B50040A`) | warmer; recorded in H4 as "Color cooler", corrected by the user | n | Color warmer |
| `brightness_up` | as named (user: "success") | y | |
| `color_cooler` (`7B500608`) | cooler; recorded in H4 as "Color warmer", corrected by the user | n | Color cooler |
| `brightness_down` | as named (user: "success") | y | |
| `cool_100` (`7B50050B`) | user: "success"; diagram 5500K, 100% | n | Cool 100% (was Center sun) |
| `warm_100` (`7B500806`) | user: "success"; diagram 3000K, 100% | n | Warm 100% (was Coffee cup) |
| `warm_50` (`7B500B05`) | user: "success"; diagram 3000K, brightness unclear | n | Warm 50% (was Baby bottle) |
| `cool_50` (`7B500A04`) | user: "success"; diagram 5500K, 50% | n | Cool 50% (was Laptop) |
| `neutral_100` (`7B500907`) | user: "success"; diagram 4000K, 100% | n | Neutral 100% (was Book) |
| `neutral_50` (`7B500C02`) | user: "success"; diagram 4000K, 50% | n | Neutral 50% (was Gaming) |
| `timer` (`7B500D03`) | 10/40-minute auto-off timer (diagram) | n | Timer, not exposed (was Tachometer) |
