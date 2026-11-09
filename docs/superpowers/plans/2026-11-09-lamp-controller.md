# Sub-GHz Lamp Controller Implementation Plan

Date: November 9, 2026

**Goal:** Control the existing lamp from Home Assistant using the wired ESP32-S3 and CC1101, starting with one proven power command.

**Architecture:** ESPHome handles Wi-Fi, the Home Assistant API, and the CC1101 radio. Replay isolated, verified command frames rather than entire Flipper recordings. Expose remote-style buttons initially; do not claim knowledge of the lamp's actual state.

**Tech stack:** ESP32-S3 N16R8, CC1101, ESPHome, Home Assistant, and a small standard-library Python capture analyzer if needed.

**Design basis:** `../../../CC1101-ESP32-S3-wiring.md` and the capture analysis and user confirmations from this chat. ESPHome is the proposed implementation route; firmware has not been installed or tested.

## Current locations and status

- Active project root: `/Users/sasha/Documents/lumos`
- Existing hardware notes: `CC1101-ESP32-S3-wiring.md` in that root.
- Original captures: `/Users/sasha/Downloads/` — eight named captures and four timestamped captures listed below.
- The existing Lumos Git repository is on `main`, with an established `origin` at `https://github.com/sasha351/lumos.git`. It had no local commits or advertised remote branches before this migration. Preserve its `.git` and remote; do not create another remote.
- The named old path ending in `2` was already absent. Original notes and this plan were recovered from its sibling folder; exact recovered copies are in `docs/archive/`. The sibling old project and its Git metadata were removed after preservation checks, leaving Lumos as the active project. See [migration provenance](../../migration.md).
- The user reports the hardware is wired according to the diagram and Flipper replay has controlled the lamp successfully.
- `/dev/cu.usbmodem21101` was previously observed; re-enumerate ports before use. Board identity and electrical operation have not yet been verified.
- ESPHome was not found on the shell command path; Python 3 and `uv` were found. Wi-Fi and Home Assistant are not configured.

## Constraints and known radio data

- Remote FCC ID: `2A3SL-DY010050001`, confirmed by the user.
- Frequency: **433.92 MHz**. Captures use `FuriHalSubGhzPresetOok650Async` and `Protocol: RAW`.
- Retain wiring: SCK GPIO12, MOSI GPIO11, MISO GPIO13, CS GPIO10, transmit GDO0 GPIO4, receive GDO2 GPIO5; radio power is 3.3 V.
- Preserve original recordings. Several contain multiple command patterns and must not be replayed wholesale.
- Keep Wi-Fi credentials, API encryption keys, build products, and device backups out of Git.
- Do not assume power is a discrete on/off command or that brightness commands set absolute levels.

## Proposed repository contents

```text
README.md
.gitignore
CC1101-ESP32-S3-wiring.md
docs/superpowers/plans/2026-11-09-lamp-controller.md
docs/radio-captures.md
captures/original/*.sub
esphome/lamp-controller.yaml
esphome/secrets.example.yaml
tools/analyze_captures.py       # only if needed for repeatable extraction
tests/test_capture_analysis.py # accompanies nontrivial extraction logic
```

The README, ignore rules, wiring notes, plan, capture evidence, migration record, recovered originals, and twelve captures now exist. Firmware, secrets examples, analyzer, and tests remain proposed.

## Milestone 1 — Preserve evidence and prepare the repository

- [x] Copy the twelve supplied captures into `captures/original/`, retaining their filenames and leaving Downloads untouched.
- [x] Verify copied files match their originals byte for byte and by SHA-256.
- [x] Write `README.md` with the goal, hardware, current status, setup path, and links to wiring and this plan.
- [x] Add `.gitignore` entries for local secrets, ESPHome build/storage directories, Python caches, and firmware backups.
- [x] Document capture provenance, duplicates, mixed recordings, and uncertain button labels in `docs/radio-captures.md`.
- [x] Preserve the established Lumos repository and remote; archive the recovered source notes unchanged.
- The user authorized committing and pushing the migration after local preservation checks. Review staged files for secrets and unintended files, then publish to the existing `origin/main`.

**Pass condition:** A fresh checkout contains the original evidence and setup documentation, with no credentials or generated firmware artifacts.

## Milestone 2 — Extract commands reproducibly

- [ ] Parse all `RAW_Data` lines in each file as one continuous pulse stream; line boundaries are not frame boundaries.
- [ ] Separate frames using long negative gaps, reject malformed or partial frames, and report every repeated pattern rather than only the most frequent one.
- [ ] If implementing an analyzer, first add checks for multiline input, incomplete frames, malformed pulses, mixed commands, and the known power recording.
- [ ] Extract a clean power frame and its measured timing, trailing gap, and repetition behavior. Preserve measured timing until hardware testing supports normalization.
- [ ] Confirm each button's meaning with the user or a lamp test before assigning final labels.

**Pass condition:** Analysis reproduces the repeated power pattern below, flags mixed captures, and never emits an entire noisy recording as a command.

| Original file | Dominant 32-bit pattern | Clean repetitions observed |
| --- | --- | ---: |
| Pwr.sub | `7B50020C` | 26 |
| Bup.sub | `7B50030D` | 21 |
| Bdwn.sub | `7B500709` | 22 |
| Cool.sub | `7B500608` | 22 |
| Read.sub | `7B500907` | 18 |
| Nght.sub | `7B50010F` | 18 |
| Middl.sub | `7B50050B` | 17 |
| Lei.sub | `7B500806` | 26 |

These are provisional pulse-decoding results, using short-high/long-low as zero and long-high/short-low as one, not a named protocol identification. Typical pulse lengths are approximately 250 and 730 microseconds.

`Read.sub`, `Nght.sub`, and `Middl.sub` include additional command patterns. The timestamped captures are:

- `SubGHz_2026-10-23_14,53,23.sub`: mostly `7B50050B`, also `7B500B05`.
- `SubGHz_2026-10-23_14,53,06.sub`: repeated `7B500B05`; function unknown.
- `SubGHz_2026-10-23_14,52,52.sub`: byte-identical to `Lei.sub`.
- `SubGHz_2026-10-23_14,48,37.sub`: byte-identical to `Pwr.sub`.

## Milestone 3 — Bring up ESPHome and verify the radio

- [ ] Identify the actual USB-connected chip and flash capacity; confirm whether existing firmware needs preserving before replacement.
- [ ] Install a compatible ESPHome release in an isolated environment and record the tested version.
- [ ] Create `esphome/lamp-controller.yaml` using the existing GPIO assignments and current official CC1101 dual-pin configuration.
- [ ] Confirm the Home Assistant instance/network and configure Wi-Fi and API credentials locally through an ignored secrets file. Commit only placeholders in `secrets.example.yaml`.
- [ ] Validate configuration and compile successfully before flashing.
- [ ] Flash and inspect boot logs for successful radio initialization and network connection.
- [ ] Compare received remote pulses with the supplied captures before enabling the first user-triggered transmission.

**Pass condition:** The board boots, communicates with the radio, and receives recognizable remote frames. Booting, reconnecting, or restarting must not transmit a lamp command.

## Milestone 4 — Prove one power button end to end

- [ ] Add one Home Assistant button that sends the isolated power frame through ESPHome's remote transmitter and CC1101 transmit/receive mode switching.
- [ ] Confirm the antenna is attached before transmitting.
- [ ] Add the ESPHome device to Home Assistant and test the button against the physical lamp.
- [ ] Establish whether the command toggles power and choose repetitions/gaps that yield one intended action per press.
- [ ] Test repeated presses and controller restart/reconnection for duplicate or unsolicited actions.

**Pass condition:** Each requested press produces the expected lamp action reliably, without a second toggle or unrelated mode change.

## Milestone 5 — Add remaining verified controls

- [ ] Add individually verified brightness and mode commands using the same transmission path.
- [ ] Test each control independently, including repeated brightness presses and normal remote use alongside Home Assistant.
- [ ] Leave unknown commands unexposed until identified.
- [ ] Record working range, limitations, tested firmware version, and recovery/reflash steps in the README.

**Pass condition:** Every exposed button has a verified effect. Home Assistant does not present an assumed lamp state as measured feedback.

## Main verification risks

- Mixed recordings: extraction must isolate commands rather than transmit all recorded pulses.
- Repeated power frames: tune against the lamp to avoid multiple toggles.
- Wiring/USB mismatch: detect the actual board and verify radio initialization rather than relying on the serial-port name.
- Lost network or reboot: no automatic command replay or fabricated state.
- Secrets in Git: inspect staged files before commits and publishing.

## References

- [ESPHome CC1101 documentation](https://esphome.io/components/cc1101/)
- [Remote FCC filing record](https://fccid.io/2A3SL-DY010050001)

## Not done yet

All twelve captures and the recovered source documents have been preserved in Lumos. No firmware has been written or flashed, and no physical radio tests have been performed. The existing GitHub remote was preserved; publication of the migration was subsequently authorized. Next is clean-frame extraction, followed by board identification and firmware bring-up under the later milestones.
