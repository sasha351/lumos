# Copilot instructions for Lumos

Lumos controls a 433.92 MHz lamp from Home Assistant using an ESP32-S3 and a CC1101 radio running ESPHome. The work is driven by `docs/superpowers/plans/2026-11-09-copilot-subagent-plan.md`: do only the task you were assigned, and stop at HUMAN gates.

## Hard rules

- **Never modify, rename, re-encode, or delete anything in `captures/original/` or `docs/archive/`.** These are preserved evidence. Their SHA-256 values are listed in `docs/migration.md`.
- **Never commit secrets.** `esphome/secrets.yaml`, `.env*`, `backups/`, `*.bin`, `.esphome/`, and `build/` are git-ignored, and must stay that way. Commit only placeholders in `esphome/secrets.example.yaml`.
- **Never transmit except on an explicit button press.** Don't add `on_boot`, `interval`, `on_connect`, or restore-mode transmissions, and don't add `switch`, `light`, or `number` entities that imply known lamp state.
- **Never expose a command that is not `verified: true` in `captures/commands.json`**, and never expose an `unknown_*` command.
- **Never replay a whole recording.** Transmit codes must be generated from one decoded frame plus measured timings, by `tools/analyze_captures.py`.
- **Don't hand-edit `esphome/lamp-commands.generated.yaml`.** Edit `captures/commands.json` and regenerate.
- **Never claim hardware verification.** Agents can't flash, transmit, or observe the lamp. Only `docs/hardware-test-log.md`, filled in by the user, establishes hardware facts.

## Conventions

- Python ≥ 3.11, **standard library only**. Tests use `unittest`: `python3 -m unittest discover -s tests -v`.
- Write tests first (TDD) for parser, decoder, and generator logic.
- ESPHome is pinned to `2026.10.2`. Validate with `esphome config esphome/lamp-controller.yaml` after copying `secrets.example.yaml` to `secrets.yaml`. The output must contain zero `WARNING` lines. Delete the copied `secrets.yaml` before committing.
- Pulse units are microseconds. Positive values mean carrier on, negative values mean off. Bits are MSB first.
- Keep each PR to one plan task. In the PR description, list every acceptance criterion with its status.
- If the sandbox blocks a download (for example PlatformIO toolchains), say so in the PR. Don't work around the firewall.
