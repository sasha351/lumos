"""Guided receive test (H4): press remote buttons, record what the board hears.

This script runs `esphome logs` against the board and prompts for one button
at a time. For each press it writes the frames the board received, plus the
lamp effect you type, to a session file in captures/sessions/. At the end it
prints a pass/fail table. It only listens; the board does not transmit.

Run it from the repository root, with the board powered and on Wi-Fi:

    python3 scripts/record_presses.py                    # every button, top to bottom
    python3 scripts/record_presses.py --order "Color warmer,Cool 50%,Neutral 50%"
    python3 scripts/record_presses.py --ask              # type each name as you go

With no options it walks every exposed button in the order they sit on the
remote: Night mode, Power, Color warmer, Brightness up, Color cooler,
Brightness down, Cool 100%, Warm 100%, Warm 50%, Cool 50%, Neutral 100%,
Neutral 50%. The hidden Timer button is skipped; name it in --order to test
it. Names are matched ignoring case and spaces. A name that matches
nothing is still recorded, for example "mystery 1".

Re-print the table for a saved session at any time:

    python3 -m tools.press_log captures/sessions/<file>.log

The session file holds only received frames, step names and your notes.
Wi-Fi details, addresses and keys from the log are not written.
"""

from __future__ import annotations

import argparse
import datetime
import shlex
import subprocess
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.press_log import (  # noqa: E402  (needs the repo on sys.path)
    Session,
    evaluate,
    find_command,
    format_report,
    load_manifest,
    parse_log,
    remote_buttons,
)

CONNECT_MARKERS = ("Successfully connected", "Successful handshake", "remote.raw")
CONNECT_TIMEOUT_S = 45


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Guided H4 receive test.")
    parser.add_argument("--order", help="comma-separated buttons to press, in order (default: the whole remote)")
    parser.add_argument("--ask", action="store_true", help="type each button name as you go instead")
    parser.add_argument("--device", default="192.168.29.140", help="board address (default: %(default)s)")
    parser.add_argument("--config", default="esphome/lamp-controller.yaml")
    parser.add_argument("--out", type=Path, help="session file (default: captures/sessions/h4-<time>.log)")
    parser.add_argument("--log-command", help=argparse.SUPPRESS)  # testing: replaces `esphome logs`
    args = parser.parse_args(argv)

    manifest = load_manifest()
    if args.ask:
        order = None
    elif args.order:
        order = [name.strip() for name in args.order.split(",") if name.strip()]
    else:
        order = [cmd["label"] for cmd in remote_buttons(manifest) if cmd["expose"]]
    if order:
        unknown = [name for name in order if find_command(name, manifest) is None]
        if unknown:
            print(f"Not in captures/commands.json (recorded anyway): {', '.join(unknown)}")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.out or REPO / "captures" / "sessions" / f"h4-{stamp}.log"
    out.parent.mkdir(parents=True, exist_ok=True)

    command = shlex.split(args.log_command) if args.log_command else ["esphome", "logs", args.config, "--device", args.device]
    try:
        proc = subprocess.Popen(
            command, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, errors="replace",
        )
    except FileNotFoundError:
        print(f"Cannot run {command[0]!r}. Is ESPHome installed and on your PATH?")
        return 1

    connected = threading.Event()
    lock = threading.Lock()
    early_lines: list[str] = []

    with out.open("w", encoding="utf-8") as fh:
        fh.write(f"# H4 receive session {stamp}. Written by scripts/record_presses.py.\n")
        session = Session(fh)

        def reader() -> None:
            for line in proc.stdout:
                if not connected.is_set():
                    early_lines.append(line.rstrip())
                    if any(marker in line for marker in CONNECT_MARKERS):
                        connected.set()
                with lock:
                    session.on_log_line(line)
            connected.set()  # also wakes the main thread if esphome exits

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()

        print(f"Connecting to the board at {args.device} ...")
        if not connected.wait(CONNECT_TIMEOUT_S) or proc.poll() is not None:
            print("Could not connect. Last output from esphome logs:")
            print("\n".join(early_lines[-15:]) or "(none)")
            proc.terminate()
            return 1
        print("Connected and listening. Nothing will be transmitted.")
        print("For each step: press the button ONCE on the original remote, watch the lamp,")
        print("then type what it did and press Enter. Ctrl+C stops early; the file is kept.\n")

        index = 0
        try:
            while True:
                if order:
                    if index >= len(order):
                        break
                    name = order[index]
                else:
                    name = input("Button you will press next (Enter on an empty line to finish): ").strip()
                    if not name:
                        break
                cmd = find_command(name, manifest)
                shown = f"{cmd['label']} ({cmd['id']})" if cmd else name
                with lock:
                    number = session.start_step(name)
                total = f"/{len(order)}" if order else ""
                effect = input(f"Step {number}{total}: press {shown} now. What did the lamp do? ")
                with lock:
                    session.set_effect(effect)
                index += 1
        except (KeyboardInterrupt, EOFError):
            print("\nStopped early.")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            thread.join(timeout=2)
            with lock:
                session.finish()

    report = format_report(evaluate(parse_log(out.read_text(encoding="utf-8").splitlines()), manifest))
    with out.open("a", encoding="utf-8") as fh:
        fh.write("\n# Report\n" + "\n".join(f"# {line}" for line in report.splitlines()) + "\n")
    print("\n" + report)
    print(f"\nSaved to {out.relative_to(REPO) if out.is_relative_to(REPO) else out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
