# CC1101 on the 38-pin ESP32 perfboard

This replaces the ESP32-S3 build in [CC1101-ESP32-S3-wiring.md](CC1101-ESP32-S3-wiring.md), which is kept as history.

## Board

`esptool flash-id` on November 17, 2026 read: ESP32-D0WD-V3 (revision v3.1), 4 MB flash, no PSRAM, Silicon Labs CP2102 USB bridge (`/dev/cu.usbserial-0001`), 38-pin NodeMCU-32S-style header. `esphome compile` passes: RAM 55.9%, flash 67.4% of the 1.8 MB app slot, with the Bluetooth proxy enabled.

## Wiring

Find pins by their printed label, not by position.

| CC1101 pin | Signal | ESP32 label | Purpose |
| --- | --- | --- | --- |
| 1 | GND | GND (right header, below 21) | Ground |
| 2 | VCC | 3V3 (left header, top) | 3.3 V. **Never 5V.** |
| 3 | GDO0 | 5 | Transmit data (open drain) |
| 4 | CSN | 4 | SPI chip select |
| 5 | SCK | 18 | SPI clock |
| 6 | MOSI | 23 | SPI data, ESP to radio |
| 7 | MISO | 19 | SPI data, radio to ESP |
| 8 | GDO2 | 22 | Receive data |

GPIO 18, 19 and 23 are the ESP32's standard VSPI pins. The perfboard was soldered with CSN on GPIO4 and GDO0 on GPIO5, and the firmware follows the board. GPIO5 is a strapping pin, and ESPHome warns about it. At reset it only sets SDIO slave timing, which this board doesn't use, so GDO0 driving it during boot is harmless. The design avoids GPIO 0, 2, 12 and 15 (strapping), 1 and 3 (CP2102 UART) and 6–11 (flash).

## Perfboard

As built (November 17, 2026), on a 7 × 9 cm perfboard. The ESP32 sits in two 1 × 19 female headers spaced 9 holes apart. The CC1101 lies flat north of the ESP32 with its antenna off the board edge; seen from above, pin 2 is top left. Five wires run on top (brown 3V3, green GND, orange MOSI, gray GDO2, yellow SCK) and three orange wires underneath (GDO0, CSN, MISO), with solder bridges from each pin to its wire's hole. Both sides are drawn in the [Lumos perfboard](https://claude.ai/artifact/GWUDQ5J36ki9oE1WzCYRso) artifact (private).

Every connection was checked with a meter. Over 23 resets the radio read chip ID `0x0014` 22 times; the one bad read came straight after flashing. The radio enters receive mode and the receiver on GPIO22 picks up 433 MHz noise. Wi-Fi, Home Assistant and transmitting to the lamp are not tested yet.
