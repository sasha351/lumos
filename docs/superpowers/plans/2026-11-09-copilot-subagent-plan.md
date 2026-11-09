# Lumos — Subagent Execution Plan (for GitHub Copilot)

Date: November 9, 2026

This plan breaks the remaining software work from [the lamp-controller plan](2026-11-09-lamp-controller.md) into self-contained tasks. Each task gets its own fresh agent session and its own PR, followed by a review pass before the next task starts. Tasks marked **HUMAN** need the physical board, lamp, or Home Assistant, so no agent can do them.

Read [`.github/copilot-instructions.md`](../../../.github/copilot-instructions.md) first. Its guardrails apply to every task.

## How to run this plan

1. **One task = one fresh agent session = one PR.** Don't carry one session across tasks. Give each session only its task section plus the guardrails.
2. **Strict order.** Respect `Depends on`. Tasks T5 and T6 may run in parallel once T4 is merged.
3. **Review gate after every task** (see [Reviewer prompt](#reviewer-prompt)). Merge only when the review finds no blocking issues.
4. **Stop at HUMAN gates.** Don't start T7 until the user has filled in the results table in `docs/hardware-test-log.md`.

| ID | Task | Depends on | Who |
| --- | --- | --- | --- |
| T1 | Capture parser + frame decoder (synthetic TDD) | — | Agent |
| T2 | Analyzer CLI + golden tests on real captures | T1 | Agent |
| T3 | Command manifest + ESPHome command generator | T2 | Agent |
| T4 | ESPHome firmware config + secrets example | T3 | Agent |
| T5 | CI workflow + Copilot setup steps | T4 | Agent |
| T6 | Hardware runbook + test log template + README | T4 | Agent |
| H1–H5 | Board ID, backup, flash, receive test, power test | T4, T6 | **HUMAN** |
| T7 | Enable verified commands, tune repeats | H5 | Agent |
| T8 | Final documentation pass | T7 | Agent |

## Verified facts (checked against the repo on 2026-11-09)

These were reproduced from `captures/original/*.sub`, not just copied from older notes. Treat them as test oracles.

- **File format:** Flipper `.sub`. Several `RAW_Data:` lines per file, each a space-separated list of signed integers in µs (positive = carrier on, negative = off). **Line breaks are not frame boundaries.** Concatenate all `RAW_Data` values first.
- **Frame delimiter:** a negative value below −5000 µs. Real gaps are about −7570 to −8480 µs and vary per file.
- **Clean frame = exactly 65 values:** 32 bit pairs `(high, −low)` plus one trailing sync high, then the gap.
  - bit `0` = short high (~250 µs) + long low (~730 µs)
  - bit `1` = long high (~740 µs) + short low (~240 µs)
  - sync high ~250 µs
  - Classify with windows 150–400 µs (short) and 550–950 µs (long). Anything else rejects the frame.
- **Bit order:** MSB first. `Pwr.sub` decodes to `0x7B50020C`.
- **Checksum invariant (observed in every clean frame of every file; not a confirmed protocol property):** `byte3 XOR 0x0E == byte4`, where byte3 is bits 15..8 and byte4 is bits 7..0. Example: `0x02 ^ 0x0E = 0x0C`. Prefix `0x7B50` is constant.
- **Measured median timings for `Pwr.sub` clean frames:** short-high 249, long-high 737, short-low 240, long-low 726, sync-high 249, gap −7578.
- **Patterns per file.** Clean counts vary by ±1 with the exact rejection rule, so tests assert the patterns and `count >= documented − 1`, never exact counts.

| File | Dominant | Docs count | Other patterns |
| --- | --- | ---: | --- |
| Pwr.sub | `7B50020C` | 26 | — |
| Bup.sub | `7B50030D` | 21 | — |
| Bdwn.sub | `7B500709` | 22 | — |
| Cool.sub | `7B500608` | 22 | — |
| Read.sub | `7B500907` | 18 | `7B50050B` |
| Nght.sub | `7B50010F` | 18 | `7B500608` |
| Middl.sub | `7B50050B` | 17 | `7B50010F` |
| Lei.sub | `7B500806` | 26 | — |
| SubGHz_2026-10-23_14,53,23.sub | `7B50050B` | 22 | `7B500B05` |
| SubGHz_2026-10-23_14,53,06.sub | `7B500B05` | 30 | — (function unknown, never expose) |
| SubGHz_2026-10-23_14,52,52.sub | byte-identical to Lei.sub | | |
| SubGHz_2026-10-23_14,48,37.sub | byte-identical to Pwr.sub | | |

- **ESPHome 2026.10.2** (current on PyPI) has a native `cc1101` component with `cc1101.begin_tx` / `cc1101.begin_rx` actions. The YAML skeleton in T4 passes `esphome config` on 2026.10.2 with zero warnings.
- **ESPHome quirks found while validating:**
  - An all-zeros `api_encryption_key` is rejected, so the placeholder in `secrets.example.yaml` must be non-zero.
  - An `ota` password triggers a warning; use `encryption: {}`, which reuses the API key.
  - `remote_transmitter` warns unless `non_blocking` is set explicitly.

## Key design decisions (pros/cons)

| Decision | Chosen | Pros | Cons |
| --- | --- | --- | --- |
| Analyzer stack | Python ≥3.11 stdlib only, `unittest` | No deps; runs on any laptop/CI; matches original plan | More verbose than pytest |
| Transmit encoding | `transmit_raw` from per-file **measured** median timings | Matches capture byte order exactly (data → sync → gap); respects "preserve measured timing" rule | Long arrays in YAML (mitigated by generation) |
| Alternative: `transmit_rc_switch_raw` (pulse 245, sync [1,31], zero [1,3], one [3,1]) | Not used yet | Readable one-line codes | ESPHome sends sync **before** data, so the last repeat lacks its trailing sync; timing is quantized. Revisit only after hardware proves raw works |
| Command definitions | `captures/commands.json` manifest → generated `esphome/lamp-commands.generated.yaml` | Single source of truth; `--check` catches drift; human flips `expose` after verification | One extra file + generator to maintain |
| Repeat count | One substitution `tx_repeat` (start at 8), per-command override later in T7 | Tunable in HA-free way without regenerating | Initial value is a guess; captures (17–30 frames) reflect button-hold length, not one press |
| CI | `unittest` + `esphome config` on every push; `esphome compile` only when `esphome/**` changes | Fast feedback; compile catches build errors | Compile job ~5–10 min, needs PlatformIO downloads (cached) |

---

## T1 — Capture parser and frame decoder (synthetic TDD)

**Depends on:** nothing.
**Creates:** `tools/__init__.py` (empty), `tools/lumos_captures.py`, `tests/__init__.py` (empty), `tests/test_lumos_captures.py`.
**Must not touch:** `captures/`, `docs/archive/`.

**Goal:** a pure, importable library (no CLI yet) that parses `.sub` files and decodes clean frames, with explicit rejection reasons.

**API (implement exactly these names):**

```python
@dataclass(frozen=True)
class SubFile:
    path: str
    frequency: int          # from "Frequency:" header
    preset: str             # from "Preset:" header
    protocol: str           # from "Protocol:" header
    pulses: list[int]       # all RAW_Data values concatenated, in order

@dataclass(frozen=True)
class Frame:
    index: int              # position in file (0-based, counting all frames incl. rejected)
    pulses: list[int]       # values between gaps (gap excluded)
    gap: int | None         # the negative delimiter that followed it, or None at EOF
    value: int | None       # decoded 32-bit int, or None if rejected
    reject_reason: str | None   # e.g. "length 63 != 65", "pulse 1612 at 12 out of window", "checksum"

def parse_sub(path: str) -> SubFile: ...
def parse_sub_text(text: str, path: str = "<memory>") -> SubFile: ...
def split_frames(pulses: list[int], gap_threshold: int = -5000) -> list[tuple[list[int], int | None]]: ...
def decode_frame(pulses: list[int]) -> tuple[int | None, str | None]: ...
def checksum_ok(value: int) -> bool: ...            # ((value >> 8) & 0xFF) ^ 0x0E == value & 0xFF
def frames(sub: SubFile) -> list[Frame]: ...
```

**Rules:**
- Raise `ValueError` with a clear message on: a missing `Filetype: Flipper SubGhz RAW File` header, `Protocol` other than `RAW`, or a non-integer token in `RAW_Data`.
- Classification windows: short 150–400 µs, long 550–950 µs (inclusive). The sync high must be short. Signs must alternate, starting positive.
- Reject frames whose decoded value fails `checksum_ok` with reason `"checksum"`.

**Steps (TDD — write each test, watch it fail, then implement):**
1. Tests for `parse_sub_text`:
   - header fields
   - multi-line `RAW_Data` concatenation, where a frame spans a line break
   - malformed token → `ValueError`
   - wrong protocol → `ValueError`
2. Tests for `split_frames`:
   - gap threshold
   - trailing frame without a gap
   - leading gap produces an empty first chunk (it must be kept and later rejected, not dropped silently)
3. Tests for `decode_frame`, using a helper that synthesizes a frame from a 32-bit int with nominal timings 250/730:
   - round-trip for `0x7B50020C`
   - length 63 → rejected
   - out-of-window pulse → rejected with its index in the reason
   - non-alternating signs → rejected
   - long sync → rejected
4. Tests for `checksum_ok`:
   - true for all 10 known patterns
   - false for `0x7B50020D`
5. Implement until green.

**Acceptance:**
- `python3 -m unittest discover -s tests -v` passes.
- No third-party imports anywhere in `tools/` or `tests/`.
- Every public function has a docstring stating units (µs) and sign convention.

---

## T2 — Analyzer CLI and golden tests on real captures

**Depends on:** T1.
**Creates:** `tools/analyze_captures.py`, `tests/test_capture_golden.py`.
**Modifies:** `docs/radio-captures.md` (add a "Reproduce" section; update counts only if your analyzer's counts differ, and say why).

**Goal:** a repeatable report over all captures that flags mixed recordings and duplicates.

**CLI:**

```bash
python3 -m tools.analyze_captures captures/original            # human-readable table
python3 -m tools.analyze_captures captures/original --json     # machine-readable
```

**Per file, report:**
- frequency
- preset
- total frames, clean frames, rejected frames, plus a histogram of rejection reasons
- every distinct clean pattern with its count, sorted by count descending
- the dominant pattern
- `mixed: true` if there is more than one distinct clean pattern
- the SHA-256 of the file, plus which other files are byte-identical
- median timings of clean frames for the dominant pattern: `short_high`, `long_high`, `short_low`, `long_low`, `sync_high`, `gap`

**Golden tests** (load the real files from `captures/original/`, resolved relative to the test file, not the CWD):
- For each row of the table in "Verified facts": the dominant pattern matches exactly, the set of other patterns matches exactly, and `dominant_count >= docs_count - 1`.
- `mixed` is true for Read, Nght, Middl, and SubGHz_…14,53,23. It is false for the others.
- The duplicate pairs are detected: 14,52,52 ↔ Lei, and 14,48,37 ↔ Pwr.
- Pwr.sub median timings are within ±15 µs of 249/737/240/726/249, and the gap is within ±50 µs of −7578.
- Every clean frame in every file passes `checksum_ok`.
- SHA-256 of each capture equals the value in `docs/migration.md`. Parse that table in the test; don't hard-code the values. This proves the evidence is untouched.

**Acceptance:**
- All tests pass.
- The CLI runs in under 2 s.
- `docs/radio-captures.md` gains a short "Reproduce" section with the exact command.
- No file under `captures/` is modified (`git diff --stat captures/` is empty).

---

## T3 — Command manifest and ESPHome command generator

**Depends on:** T2.
**Creates:** `captures/commands.json`, `tests/test_generator.py`, `esphome/lamp-commands.generated.yaml`.
**Modifies:** `tools/analyze_captures.py` (add `--emit-esphome` and `--check`).

**Manifest `captures/commands.json`** (initial content — only Power exposed):

```json
{
  "commands": [
    {"id": "power",       "source": "Pwr.sub",   "pattern": "7B50020C", "label": "Power",            "icon": "mdi:power",            "expose": true,  "verified": false},
    {"id": "bright_up",   "source": "Bup.sub",   "pattern": "7B50030D", "label": "Brightness up",    "icon": "mdi:brightness-7",     "expose": false, "verified": false},
    {"id": "bright_down", "source": "Bdwn.sub",  "pattern": "7B500709", "label": "Brightness down",  "icon": "mdi:brightness-5",     "expose": false, "verified": false},
    {"id": "cool",        "source": "Cool.sub",  "pattern": "7B500608", "label": "Cool",             "icon": "mdi:snowflake",        "expose": false, "verified": false},
    {"id": "read",        "source": "Read.sub",  "pattern": "7B500907", "label": "Read",             "icon": "mdi:book-open-variant","expose": false, "verified": false},
    {"id": "night",       "source": "Nght.sub",  "pattern": "7B50010F", "label": "Night",            "icon": "mdi:weather-night",    "expose": false, "verified": false},
    {"id": "middle",      "source": "Middl.sub", "pattern": "7B50050B", "label": "Middle",           "icon": "mdi:circle-half-full", "expose": false, "verified": false},
    {"id": "leisure",     "source": "Lei.sub",   "pattern": "7B500806", "label": "Leisure",          "icon": "mdi:sofa",             "expose": false, "verified": false},
    {"id": "unknown_0b",  "source": "SubGHz_2026-10-23_14,53,06.sub", "pattern": "7B500B05", "label": "Unknown 0x0B", "icon": "mdi:help", "expose": false, "verified": false}
  ]
}
```

Optional per-command fields that T7 may add: `"repeat"` (int) and `"wait_time_ms"` (int).

**Generator rules (`--emit-esphome PATH` writes the file; `--check` exits 1 if the file on disk differs from what would be generated):**
- Emit a `button:` list with one `platform: template` entry for each manifest entry where `expose` is true.
  - id: `cmd_<id>`
  - name: the label
  - icon: the icon
  - `on_press` → `remote_transmitter.transmit_raw` with `transmitter_id: tx`
  - `repeat: times:` set to `${tx_repeat}`, or the command's own `repeat` if present
- **Refuse to generate**, with a non-zero exit and a clear error, if any of these holds:
  - the pattern is not the **dominant** clean pattern of its source file
  - the pattern fails `checksum_ok`
  - the source has fewer than 10 clean frames of the pattern
  - an entry has `expose: true` and its `id` starts with `unknown`
- **Raw code = one frame only:**
  - 32 bit pairs built from the pattern bits, using that file's **measured median** timings for the dominant pattern (from T2)
  - then `sync_high`
  - then `gap`
  - All values are integers. Never copy pulses verbatim from a recording, so never a whole recording.
- First line of the output: `# GENERATED by tools/analyze_captures.py --emit-esphome from captures/commands.json. Do not edit by hand.`
- Output must be deterministic: same input gives a byte-identical file.

**Tests:**
- Generated Power code has exactly 66 integers, alternates signs, and decodes back to `0x7B50020C` through `decode_frame` (strip the trailing gap first).
- Exposing `unknown_0b` → error.
- Pointing `power` at `Read.sub` with pattern `7B50050B` → error (not dominant).
- `--check` passes on the committed file.
- Run twice → identical output.

**Acceptance:**
- `python3 -m tools.analyze_captures captures/original --emit-esphome esphome/lamp-commands.generated.yaml` produces the committed file.
- `--check` exits 0.
- All tests pass.

---

## T4 — ESPHome firmware configuration

**Depends on:** T3.
**Creates:** `esphome/lamp-controller.yaml`, `esphome/secrets.example.yaml`.
**Must not create:** `esphome/secrets.yaml` (it is git-ignored and holds real credentials).

**Start from this skeleton.** It was validated with `esphome config` on ESPHome 2026.10.2 with zero warnings. Keep the GPIO numbers; they match the soldered hardware in `CC1101-ESP32-S3-wiring.md`.

```yaml
substitutions:
  tx_repeat: "8"

esphome:
  name: lumos-lamp
  friendly_name: Lumos Lamp
  min_version: 2026.10.2

esp32:
  board: esp32-s3-devkitc-1
  variant: esp32s3
  flash_size: 16MB
  framework:
    type: esp-idf

logger:

api:
  encryption:
    key: !secret api_encryption_key

ota:
  - platform: esphome
    encryption: {}          # reuses the API key

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

spi:
  clk_pin: GPIO12
  mosi_pin: GPIO11
  miso_pin: GPIO13

cc1101:
  id: radio
  cs_pin: GPIO10
  frequency: 433.92MHz
  modulation_type: ASK/OOK

remote_transmitter:
  id: tx
  pin: GPIO4                 # CC1101 GDO0
  carrier_duty_percent: 100%
  non_blocking: true
  on_transmit:
    then:
      - cc1101.begin_tx: radio
  on_complete:
    then:
      - cc1101.begin_rx: radio

remote_receiver:
  id: rx
  pin: GPIO5                 # CC1101 GDO2
  dump: [raw, rc_switch]
  tolerance: 25%
  filter: 100us
  idle: 5ms

packages:
  commands: !include lamp-commands.generated.yaml
```

**`esphome/secrets.example.yaml`:**

```yaml
# Copy to secrets.yaml (git-ignored) and replace every value.
# Generate a real key with: openssl rand -base64 32
wifi_ssid: "your-wifi-ssid"
wifi_password: "your-wifi-password"
api_encryption_key: "bHVtb3MtcGxhY2Vob2xkZXIta2V5LW5vdC1zZWNyZXQ="   # placeholder, NOT secret, must be replaced
```

**Safety requirements (each needs a comment in the YAML or a test):**
- Nothing transmits on boot, Wi-Fi reconnect, API reconnect, or OTA. There is no `on_boot`/`on_connect` transmit, no `interval` transmit, and no `switch`/`light` with restore.
- No entity pretends to know lamp state. Use buttons only, with no `switch`, `light`, or `number`.
- PSRAM is deliberately not configured. It isn't needed, and a wrong PSRAM mode can stop the board booting. Note this in a comment.

**Verification:**

```bash
cp esphome/secrets.example.yaml esphome/secrets.yaml
uvx --from esphome==2026.10.2 esphome config esphome/lamp-controller.yaml
rm esphome/secrets.yaml
```

(Or `pip install esphome==2026.10.2`.) Must print `Configuration is valid!` with no `WARNING` lines. Try `esphome compile` too. If the sandbox blocks PlatformIO/toolchain downloads, say so in the PR and rely on T5's CI job; don't work around the firewall.

**Acceptance:**
- Config is valid with zero warnings.
- `git status` shows no `secrets.yaml`.
- `tests/test_generator.py` still passes.
- Add a test `tests/test_esphome_config_static.py` (stdlib only, plain text checks) asserting:
  - `on_boot`, `interval:`, `switch:` and `light:` are absent from `esphome/*.yaml`
  - the GPIO numbers 12, 11, 13, 10, 4 and 5 are present

---

## T5 — CI workflow and Copilot setup steps

**Depends on:** T4. Can run in parallel with T6.
**Creates:** `.github/workflows/ci.yml`, `.github/workflows/copilot-setup-steps.yml`.

**`ci.yml`:**
- Triggers: `push` and `pull_request`.
- Job `tests` (ubuntu-latest, Python 3.12):
  - `python -m unittest discover -s tests -v`
  - `python -m tools.analyze_captures captures/original --emit-esphome esphome/lamp-commands.generated.yaml --check`
- Job `esphome-config`:
  - install `esphome==2026.10.2`
  - copy `secrets.example.yaml` → `secrets.yaml`
  - run `esphome config esphome/lamp-controller.yaml`
  - fail if the output contains `WARNING`
- Job `esphome-compile`:
  - runs only when files under `esphome/**` changed (use `dorny/paths-filter` pinned to a commit SHA, or `on.push.paths`)
  - same setup as `esphome-config`, then `esphome compile`
  - cache `~/.platformio` and `esphome/.esphome`
- Pin every third-party action to a full commit SHA, with a version comment.
- Set `permissions: contents: read`.

**`copilot-setup-steps.yml`** (GitHub's convention for preparing the Copilot coding agent's environment; the job **must** be named `copilot-setup-steps`):
- Set up Python 3.12 and `pip install esphome==2026.10.2`.
- Trigger: `workflow_dispatch`, plus `push`/`pull_request` on that file only, so it can be tested.

**Acceptance:**
- `actionlint` passes, if available.
- The PR's own CI run is green, or the PR states which job couldn't run and why.

---

## T6 — Hardware runbook, test log template, README update

**Depends on:** T4. Can run in parallel with T5.
**Creates:** `docs/hardware-runbook.md`, `docs/hardware-test-log.md`.
**Modifies:** `README.md` (Status, Start here links, Setup section).

**`docs/hardware-runbook.md`** — step-by-step commands for the HUMAN gates below, written for macOS. The user's previous port was `/dev/cu.usbmodem21101`; tell them to re-enumerate with `ls /dev/cu.usb*`. Cover:
- **H1 — Identify the board:**
  - `uvx --from esptool esptool --port <PORT> chip-id`
  - `uvx --from esptool esptool --port <PORT> flash-id`
  - Expected: ESP32-S3, 16 MB flash, and PSRAM reported as 8 MB if the tool shows it.
- **H2 — Back up the factory firmware before the first flash:**
  - `uvx --from esptool esptool --port <PORT> read-flash 0 ALL backups/factory-<date>.bin`
  - `backups/` and `*.bin` are git-ignored. Say so explicitly.
- **H3 — First flash and boot log:**
  - `secrets.yaml` setup
  - `esphome run esphome/lamp-controller.yaml --device <PORT>`
  - What success looks like: CC1101 initialized, Wi-Fi connected, API ready
  - Confirm no transmission happened at boot (no `remote_transmitter` log lines).
- **H4 — Receive test:**
  - Press each physical remote button near the board.
  - Copy the `remote_receiver` raw/rc_switch log lines into the test log.
  - Compare against the "Verified facts" table: same 32-bit value, timing within ~15%.
- **H5 — First transmit test (Power only):**
  - Attach the antenna first.
  - Add the device in Home Assistant (Settings → Devices & services → ESPHome).
  - Press Power once.
  - Record whether it toggled, whether there was a double toggle, and the distance.
  - Then repeat with `tx_repeat` set to 3, 5, 8 and 12.
  - Restart the board and reconnect Wi-Fi; confirm there is no spontaneous lamp action.
- **Recovery:** how to reflash from `backups/factory-*.bin` with `esptool write-flash 0 ...`.

**`docs/hardware-test-log.md`** — fill-in tables (the user fills them, agents only read them):

| Gate | Date | Result (pass/fail) | Notes / log excerpt |
| --- | --- | --- | --- |
| H1 chip / flash / PSRAM | | | |
| H2 backup file + SHA-256 | | | |
| H3 boot log OK, no TX at boot | | | |
| H4 receive per button (one row each) | | | |
| H5 power: best `tx_repeat`, double-toggle? | | | |

Plus a "Button meaning confirmation" table: manifest id → observed lamp effect → keep the label? (y/n) → new label.

**README:** keep the existing tone. Update Status to reflect the analyzer, generator, config and CI now existing, and say that firmware has still not been flashed. Link the runbook and test log.

**Acceptance:**
- Every command in the runbook uses the real file paths from T4.
- The runbook contains no real credentials.
- All Markdown links resolve. A quick script or manual check is fine; list them in the PR.

---

## HUMAN gates H1–H5 (no agent)

Follow `docs/hardware-runbook.md` and fill in `docs/hardware-test-log.md`. Commit the log. **Don't start T7 until H5 has a recorded pass for Power.**

---

## T7 — Enable verified commands and tune repeats

**Depends on:** H5 recorded in `docs/hardware-test-log.md`.
**Modifies:** `captures/commands.json`, `esphome/lamp-commands.generated.yaml` (regenerated), `docs/radio-captures.md`.

**Steps:**
1. Read the test log.
2. For each command the user marked as verified:
   - set `"verified": true` and `"expose": true`
   - apply the user's label if they gave a new one
   - set a per-command `"repeat"` if the log names a different best value
3. Leave `unknown_*` unexposed.
4. Leave any command without a recorded pass unexposed.
5. Regenerate the YAML.
6. Update `docs/radio-captures.md` with the confirmed meanings.

**Acceptance:**
- Every `expose: true` entry has `verified: true` and is backed by a log row with "pass".
- The generator's `--check` passes.
- CI is green.
- Add a test that fails if any `expose: true` entry has `verified: false`.

---

## T8 — Final documentation pass

**Depends on:** T7.
**Modifies:** `README.md`, `docs/superpowers/plans/2026-11-09-lamp-controller.md` (tick completed milestone boxes; add no new claims).

**Record in the README:**
- the tested ESPHome version
- the board identity from H1
- working range and the best repeat counts from the log
- known limitations: no lamp-state feedback, Power is probably a toggle, brightness steps are relative
- recovery/reflash steps, linking to the runbook

**Acceptance:**
- Every statement traces to the test log or to code. Nothing claims verification that the log doesn't show.

---

## Reviewer prompt

Run this after each task, in a **fresh** session or as a Copilot PR review:

> Review this PR against task `<ID>` in `docs/superpowers/plans/2026-11-09-copilot-subagent-plan.md` and the guardrails in `.github/copilot-instructions.md`.
>
> 1. **Spec compliance:** check every bullet under the task's "Acceptance" and every rule in its body. Report each as met / not met, with file:line.
> 2. **Correctness bugs:** look for off-by-one errors in frame splitting, sign handling, bit order, checksum, and non-deterministic output.
> 3. **Guardrail violations:** files changed under `captures/original/` or `docs/archive/`, secrets, third-party Python deps, exposed unknown commands, or anything that could transmit without a button press.
>
> List blocking issues first. Don't restate the diff. If there are no blocking issues, say "APPROVE".

If the review finds blocking issues, send them back to the implementing session (or a new one) with: "Fix these review findings for task `<ID>`: …". Re-review after the fix.
