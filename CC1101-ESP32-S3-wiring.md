# Sub-GHz lamp controller for Home Assistant

Exported November 9, 2026. Wiring and source review completed during the November 2, 2026 planning session.

Recovered from the sibling project folder on November 9, 2026 and updated for `/Users/sasha/Documents/lumos`. The [unaltered recovered export](docs/archive/CC1101-ESP32-S3-wiring.md) is preserved for provenance.

## Current goals and status

**Overall goal:** Use an ESP32-S3 and CC1101 radio to control the lamp through Home Assistant.

**Immediate goal:** Preserve the evidence, isolate a clean command, then verify the connected board and radio before firmware bring-up.

- [x] Identify the supplied radio and ESP32-S3 board from their product listings.
- [x] Select GPIO assignments and prepare a pinout diagram.
- [x] User reports soldering the connections per the diagram and connecting the board to the laptop.
- [ ] Independently inspect wiring and verify electrical operation.
- [x] Record remote FCC ID `2A3SL-DY010050001` and capture frequency 433.92 MHz with OOK RAW recordings.
- [ ] Verify command encoding and timings; a named protocol has not been identified.
- [ ] Configure and flash firmware using the GPIO assignments below. ESPHome is the proposed route.
- [ ] Verify communication with the CC1101, then capture and reproduce the remote commands as the protocol permits.
- [ ] Add the controller to Home Assistant and test lamp control.

The user reports successful lamp control by Flipper replay. Physical wiring, ESP chip identity, and CC1101 operation have not been independently verified. No firmware has been created or flashed and no Home Assistant integration has been configured. The lamp model and named remote protocol remain unknown. See [capture evidence](docs/radio-captures.md).

## Hardware

| Item | Identified hardware | Link |
| --- | --- | --- |
| Radio | AOICRIE CC1101 module with SMA antenna; 8-pin, E07-M1101D-style connector | [Amazon — B0D2TMTV5Z](https://www.amazon.com/dp/B0D2TMTV5Z) |
| Controller | DORHEA ESP32-S3 N16R8 development board; 44 pins and two USB-C ports, as pictured in the listing | [Amazon — B0CKXJLP4B](https://www.amazon.com/dp/B0CKXJLP4B) |

The radio listing advertises multiple bands, but its description and board photo identify a 433 MHz module. Compatibility with the lamp's frequency and protocol remains to be checked; the listing title alone does not establish performance across every advertised band.

## Wiring — all eight connections

These GPIO assignments are the selected wiring plan. Configure firmware to match them; they are not universal defaults for every CC1101 example.

| CC1101 connector pin | Radio signal | ESP32-S3 printed label | Purpose |
| --- | --- | --- | --- |
| 1 | GND | **GND** | Common ground |
| 2 | VCC | **3V3** | 3.3 V power |
| 3 | GDO0 | **4** / GPIO4 | Transmit data in the proposed ESPHome configuration |
| 4 | CSN / CS | **10** / GPIO10 | SPI chip select |
| 5 | SCK / CLK | **12** / GPIO12 | SPI clock |
| 6 | MOSI / SI | **11** / GPIO11 | SPI data from ESP to radio |
| 7 | MISO / GDO1 | **13** / GPIO13 | SPI data from radio to ESP |
| 8 | GDO2 | **5** / GPIO5 | Receive data in the proposed ESPHome configuration |

**ESP numbers are GPIO numbers, not positions counted along the header.** The radio numbers identify its module connector pins, not pins on the CC1101 chip itself.

### As built (November 9, 2026)

The connections use DuPont jumpers, not solder. The radio has a right-angle 2×4 header on its underside. Its edge-row pins (1, 3, 5, 7) are in the connector layer nearer the board. Its inner-row pins (2, 4, 6, 8) are in the outer layer.

Photos taken after H3 failed showed the purple and gray jumpers crossed: GPIO10 went to pin 6 (MOSI) and GPIO11 to pin 4 (CSN). The fix is to swap the two wires at the ESP end. The firmware keeps the planned pins, so after the swap:

| CC1101 pin | Wire colour | ESP32-S3 label |
| --- | --- | --- |
| 1 GND | white | GND (last pin) |
| 2 VCC | red | 3V3 |
| 3 GDO0 | yellow | 4 or 5 (two yellow wires; H4 will confirm) |
| 4 CSN | gray | 10 |
| 5 SCK | green | 12 |
| 6 MOSI | purple | 11 |
| 7 MISO | blue | 13 |
| 8 GDO2 | yellow | 5 or 4 |

A re-run of H3 confirms the fix if the CC1101 Chip ID reads `0x0014` (clones `0x0004` or `0x0007`). Both data wires are yellow, so if the receiver sees nothing in H4, swap them at one end.

### ESP32-S3 physical pinout

View the component side with the Wi-Fi antenna at the top and both USB ports at the bottom. All eight wires use the left header. The arrows show electrical connections, not cable routing.

```text
                            Wi-Fi antenna
                         +-----------------+
  CC1101 pin 2 (VCC) <----| 3V3         GND |
                         | 3V3          TX |
                         | RST          RX |
  CC1101 pin 3 (GDO0)<----| 4             1 |
  CC1101 pin 8 (GDO2)<----| 5             2 |
                         | 6            42 |
                         | 7            41 |
                         | 15           40 |
                         | 16           39 |
                         | 17           38 |
                         | 18           37 |
                         | 8            36 |
                         | 3            35 |
                         | 46            0 |
                         | 9            45 |
  CC1101 pin 4 (CSN) <----| 10           48 |
  CC1101 pin 6 (MOSI)<----| 11           47 |
  CC1101 pin 5 (SCK) <----| 12           21 |
  CC1101 pin 7 (MISO)<----| 13           20 |
                         | 14           19 |
                         | 5V          GND |
  CC1101 pin 1 (GND) <----| GND         GND |
                         +-----------------+
                           [COM]     [USB]
                             USB-C ports
```

### CC1101 connector orientation

View the component side with the chip facing you and the SMA antenna connector at the top.

```text
                         SMA antenna
                              |
                    +-------------------+
                    |                   |
                    |    CC1101 chip    |
                    |                   |
  Row near chip:    |    2   4   6   8  |
  Row near edge:    |    1   3   5   7  |
                    +-------------------+
                         ^
                    Square pad: pin 1
```

The bottom-left square pad is pin 1 in this view. Looking at the underside mirrors left and right. Match the board's printed numbers before soldering.

## Soldering and power notes

- Disconnect USB and all power before soldering.
- **Connect CC1101 VCC to 3V3. Never connect it to the ESP's 5V pin.**
- Keep the interconnect wires short.
- Inspect for solder bridges before applying power.
- Attach the radio antenna before transmitting.
- Use GPIO4 and GPIO5 for the radio data signals as shown; the ESP pins printed TX and RX are different pins.

## Firmware direction

The proposed ESPHome arrangement uses GDO0 for transmit data and GDO2 for receive data. This follows ESPHome's documented [dual-pin wiring](https://esphome.io/components/cc1101/#1-dual-pin-wiring-recommended).

Firmware should use SCK = GPIO12, MOSI = GPIO11, MISO = GPIO13, CS = GPIO10, transmit data = GPIO4, and receive data = GPIO5. The recordings declare 433.92 MHz and the OOK asynchronous preset. Command encoding and measured timing still need verification. No firmware or complete Home Assistant configuration has been produced yet.

## Sources and what they establish

1. [AOICRIE CC1101 product listing](https://www.amazon.com/dp/B0D2TMTV5Z) — the supplied radio, voltage specification, 433 MHz marking, and connector numbering visible in the product photos.
2. [DORHEA ESP32-S3 product listing](https://www.amazon.com/dp/B0CKXJLP4B) — the supplied development board. Its [component-side and underside photo](https://m.media-amazon.com/images/I/71fkajVvHtL._AC_SL1500_.jpg) shows the N16R8 marking, header labels, and USB orientation used in the diagram.
3. [EBYTE E07-M1101D-SMA pin definitions](https://www.ebyte.com/product/57.html) — reference signal assignments for the matching E07-style connector: GND, VCC, GDO0, CSN, SCK, MOSI, MISO/GDO1, and GDO2 on pins 1–8. This is a connector reference, not a claim that AOICRIE is the same manufacturer.
4. [Texas Instruments CC1101 product information](https://www.ti.com/product/CC1101) and [CC1101 datasheet](https://www.ti.com/lit/ds/symlink/cc1101.pdf) — chip supply limits, SPI interface, and radio data-pin functions. Chip package pin numbers differ from module connector numbers.
5. [ESPHome CC1101 documentation](https://esphome.io/components/cc1101/) — the proposed firmware component and separate transmit/receive wiring arrangement.
6. [Espressif ESP32-S3-DevKitC-1 reference guide](https://documentation.espressif.com/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html) — reference GPIO and header information for the DevKitC-style layout; the DORHEA listing photo was used to check the actual board labels.

Sources were consulted during the November 2 planning session and were not rechecked live for this Markdown export. The wiring has not been tested on physical hardware, and lamp compatibility is not yet established.
