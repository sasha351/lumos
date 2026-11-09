"""Turn ESPHome receiver logs into a per-button-press report (gate H4).

``remote_receiver`` with ``dump: raw`` logs every received pulse train as
``Received Raw: ...``. ESPHome splits long trains across several log lines, so
:class:`RawJoiner` stitches them back together. Each train is then decoded
with the lamp frame decoder.

Input can be either of two formats:

* a session file written by ``scripts/record_presses.py``, with step markers,
  the lamp effect the user typed for each step, and one ``RAW`` line per frame;
* a plain ``esphome logs ... | tee file`` capture. Here the presses are
  grouped into bursts by time, and ``--order`` names the bursts in order.

Run it on a file with::

    python3 -m tools.press_log captures/sessions/h4-YYYYMMDD-HHMMSS.log
    python3 -m tools.press_log plain.log --order "Night mode,Power,Color cooler"

The script only reads logs. It never talks to the board and never transmits.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from tools.analyze_captures import DEFAULT_MANIFEST, median_timings
from tools.lumos_captures import FRAME_LENGTH, Frame, decode_frame

RAW_START = "Received Raw:"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
TIMESTAMP = re.compile(r"\[(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)\]")
NUMBER = re.compile(r"-?\d+")
STEP_LINE = re.compile(r"^=== STEP (\d+): (.+?) ===$")
EFFECT_LINE = re.compile(r"^=== EFFECT (\d+): ?(.*)$")
FRAME_LINE = re.compile(r"^(\S+) RAW (.+)$")

# Pulse trains shorter than this are background noise. A lamp frame has 65.
MIN_CANDIDATE_VALUES = 20
# Frames of one press arrive about 40 ms apart. A longer silence starts a new
# burst when a plain log has no step markers.
BURST_GAP_S = 0.5
# A press needs this many matching frames to count as a pass.
MIN_PASS_FRAMES = 2


def _seconds(stamp: str | None) -> float | None:
    """``"17:09:55.258"`` -> seconds since midnight, or None."""
    if not stamp:
        return None
    hours, minutes, seconds = stamp.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


class RawJoiner:
    """Rebuild ``Received Raw`` dumps that ESPHome splits across lines.

    :meth:`feed` takes one log line and returns the dumps it completed, each
    as ``(timestamp, values)``. A dump is complete when the next one starts,
    so call :meth:`flush` at the end, or before a step marker.
    """

    def __init__(self) -> None:
        self._stamp: str | None = None
        self._values: list[int] | None = None

    def feed(self, line: str) -> list[tuple[str | None, list[int]]]:
        line = ANSI.sub("", line).rstrip("\n")
        if "remote.raw" not in line:
            return []
        if RAW_START in line:
            done = self.flush()
            match = TIMESTAMP.search(line)
            self._stamp = ":".join(match.groups()) if match else None
            self._values = [int(v) for v in NUMBER.findall(line.split(RAW_START, 1)[1])]
            return done
        if self._values is not None and "]:" in line:
            self._values.extend(int(v) for v in NUMBER.findall(line.rsplit("]:", 1)[1]))
        return []

    def flush(self) -> list[tuple[str | None, list[int]]]:
        if self._values is None:
            return []
        done = [(self._stamp, self._values)]
        self._stamp, self._values = None, None
        return done


@dataclass
class Step:
    """One labelled press, or one unlabelled burst from a plain log."""

    number: int
    name: str | None
    effect: str = ""
    frames: list[tuple[str | None, list[int]]] = field(default_factory=list)
    noise: int = 0


def format_frame_line(stamp: str | None, values: list[int]) -> str:
    return f"{stamp or '-'} RAW {','.join(str(v) for v in values)}"


class Session:
    """Write a press-by-press session file while logs stream in.

    ``scripts/record_presses.py`` drives this from the live ``esphome logs``
    output. Only frame candidates are written; noise is only counted. The
    file holds no Wi-Fi details, addresses or keys.
    """

    def __init__(self, out: TextIO) -> None:
        self.out = out
        self.joiner = RawJoiner()
        self.step = 0
        self.noise = Counter()

    def on_log_line(self, line: str) -> None:
        for stamp, values in self.joiner.feed(line):
            self._record(stamp, values)

    def _record(self, stamp: str | None, values: list[int]) -> None:
        if len(values) < MIN_CANDIDATE_VALUES:
            self.noise[self.step] += 1
            return
        self.out.write(format_frame_line(stamp, values) + "\n")
        self.out.flush()

    def _flush_pending(self) -> None:
        for stamp, values in self.joiner.flush():
            self._record(stamp, values)

    def start_step(self, name: str) -> int:
        self._flush_pending()
        self.step += 1
        self.out.write(f"=== STEP {self.step}: {name} ===\n")
        self.out.flush()
        return self.step

    def set_effect(self, effect: str) -> None:
        self._flush_pending()
        self.out.write(f"=== EFFECT {self.step}: {effect.strip()}\n")
        self.out.flush()

    def finish(self) -> None:
        self._flush_pending()
        for step, count in sorted(self.noise.items()):
            where = f"in step {step}" if step else "before step 1"
            self.out.write(f"# noise trains ignored {where}: {count}\n")
        self.out.flush()


def parse_log(lines: list[str]) -> list[Step]:
    """Group the frames in a session file or plain log into steps."""
    joiner = RawJoiner()
    steps: list[Step] = []
    loose: list[tuple[str | None, list[int]]] = []  # frames before any marker
    current: Step | None = None

    def add(stamp: str | None, values: list[int]) -> None:
        if current is None:
            loose.append((stamp, values))
        elif len(values) < MIN_CANDIDATE_VALUES:
            current.noise += 1
        else:
            current.frames.append((stamp, values))

    for raw_line in lines:
        line = ANSI.sub("", raw_line).rstrip("\n")
        if match := STEP_LINE.match(line):
            for stamp, values in joiner.flush():
                add(stamp, values)
            current = Step(int(match.group(1)), match.group(2).strip())
            steps.append(current)
            continue
        if match := EFFECT_LINE.match(line):
            for stamp, values in joiner.flush():
                add(stamp, values)
            if current is not None and int(match.group(1)) == current.number:
                current.effect = match.group(2).strip()
            continue
        if match := FRAME_LINE.match(line):
            stamp = None if match.group(1) == "-" else match.group(1)
            add(stamp, [int(v) for v in NUMBER.findall(match.group(2))])
            continue
        for stamp, values in joiner.feed(line):
            add(stamp, values)
    for stamp, values in joiner.flush():
        add(stamp, values)

    if steps:
        return steps
    return _bursts(loose)


def _bursts(frames: list[tuple[str | None, list[int]]]) -> list[Step]:
    """Split unlabelled frames into bursts separated by silence."""
    steps: list[Step] = []
    last: float | None = None
    for stamp, values in frames:
        if len(values) < MIN_CANDIDATE_VALUES:
            if steps:
                steps[-1].noise += 1
            continue
        if _decode(values)[0] is None:
            # Only decodable frames start or extend a burst; keep rejects with
            # the burst they fall in.
            if steps:
                steps[-1].frames.append((stamp, values))
            continue
        now = _seconds(stamp)
        if not steps or (now is not None and last is not None and now - last > BURST_GAP_S):
            steps.append(Step(len(steps) + 1, None))
        steps[-1].frames.append((stamp, values))
        if now is not None:
            last = now
    return steps


def _decode(values: list[int]) -> tuple[int | None, str | None]:
    """Decode a received train. The receiver drops the trailing gap."""
    if len(values) == FRAME_LENGTH + 1 and values[-1] < 0:
        values = values[:-1]
    return decode_frame(values)


def load_manifest(path: Path = DEFAULT_MANIFEST) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["commands"]


def remote_buttons(manifest: list[dict]) -> list[dict]:
    """The physical remote buttons, in the order they sit on the remote."""
    return sorted((c for c in manifest if c.get("position")), key=lambda c: c["position"])


def find_command(name: str | None, manifest: list[dict]) -> dict | None:
    """Match a typed step name to a manifest entry by id or label.

    Case, spaces and punctuation are ignored, so "Night mode", "night_mode"
    and "NIGHT MODE" all find the same button.
    """
    if not name:
        return None
    wanted = re.sub(r"[^a-z0-9]", "", name.lower())
    for cmd in manifest:
        if wanted in (re.sub(r"[^a-z0-9]", "", cmd["id"].lower()), re.sub(r"[^a-z0-9]", "", cmd["label"].lower())):
            return cmd
    return None


@dataclass
class StepResult:
    number: int
    name: str
    expected: str | None
    effect: str
    counts: Counter
    rejected: int
    noise: int
    verdict: str
    timings: dict[str, int]


def evaluate(steps: list[Step], manifest: list[dict], order: list[str] | None = None) -> list[StepResult]:
    by_pattern = {cmd["pattern"]: cmd for cmd in manifest}
    results = []
    for index, step in enumerate(steps):
        name = step.name or (order[index] if order and index < len(order) else None)
        expected_cmd = find_command(name, manifest)
        counts: Counter = Counter()
        clean: list[Frame] = []
        rejected = 0
        for _, values in step.frames:
            value, _reason = _decode(values)
            if value is None:
                rejected += 1
                continue
            pattern = f"{value:08X}"
            counts[pattern] += 1
            clean.append(Frame(index=len(clean), pulses=values[:FRAME_LENGTH], gap=None, value=value, reject_reason=None))

        dominant, dominant_count = counts.most_common(1)[0] if counts else (None, 0)
        owner = by_pattern.get(dominant) if dominant else None
        if dominant is None:
            verdict = "NONE: no lamp frame received"
        elif dominant_count < MIN_PASS_FRAMES:
            verdict = f"WEAK: only {dominant_count} frame of {dominant}"
        elif expected_cmd is None:
            verdict = f"GOT {owner['label']}" if owner else f"NEW CODE {dominant}"
        elif expected_cmd["pattern"] is None:
            # The button's code was never captured: this press teaches it.
            if owner is None:
                verdict = f"LEARNED {dominant}"
            elif owner.get("position") is None:
                verdict = f"LEARNED {dominant} (same as {owner['id']})"
            else:
                verdict = f"CONFLICT: {dominant} is listed as {owner['label']}"
        elif dominant != expected_cmd["pattern"]:
            verdict = f"WRONG: got {owner['label'] if owner else 'new code ' + dominant}"
        else:
            verdict = "PASS"
        if len(counts) > 1:
            verdict += " (mixed codes)"

        dominant_frames = [f for f in clean if dominant and f"{f.value:08X}" == dominant]
        timings = median_timings(dominant_frames) if dominant_frames else {}
        results.append(
            StepResult(
                number=step.number,
                name=name or f"burst {step.number}",
                expected=expected_cmd["pattern"] if expected_cmd else None,
                effect=step.effect,
                counts=counts,
                rejected=rejected,
                noise=step.noise,
                verdict=verdict,
                timings=timings,
            )
        )
    return results


def format_report(results: list[StepResult]) -> str:
    lines = [
        "| Step | Button | Verdict | Frames (code x count) | Rejected | Timings us (sH lH sL lL sync) | Lamp did |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        frames = ", ".join(f"{p} x{n}" for p, n in r.counts.most_common()) or "-"
        t = r.timings
        timing = " ".join(str(t.get(k, "-")) for k in ("short_high", "long_high", "short_low", "long_low", "sync_high")) if t else "-"
        lines.append(f"| {r.number} | {r.name} | {r.verdict} | {frames} | {r.rejected} | {timing} | {r.effect or '-'} |")
    passed = sum(r.verdict.startswith("PASS") for r in results)
    learned = sum(r.verdict.startswith("LEARNED") for r in results)
    lines.append("")
    summary = f"{passed} of {len(results)} steps passed"
    if learned:
        summary += f", {learned} learned a new button code"
    lines.append(summary + ".")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("log", type=Path, help="session file or plain esphome logs capture")
    parser.add_argument("--order", help="comma-separated button names for unlabelled bursts, in press order")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    order = [o.strip() for o in args.order.split(",")] if args.order else None
    results = evaluate(parse_log(lines), load_manifest(args.manifest), order)
    print(format_report(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
