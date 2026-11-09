"""Report on Flipper captures: patterns, mixed recordings, duplicates, timings.

Usage::

    python3 -m tools.analyze_captures captures/original
    python3 -m tools.analyze_captures captures/original --json

All timings are in µs. Highs and lows are reported as positive magnitudes;
``gap`` keeps its negative sign, matching the capture convention.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

from tools.lumos_captures import FRAME_BITS, Frame, frames, parse_sub

TIMING_KEYS = ("short_high", "long_high", "short_low", "long_low", "sync_high", "gap")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _median(values: list[int]) -> int:
    return int(round(statistics.median(values)))


def median_timings(clean: list[Frame]) -> dict[str, int]:
    """Median µs timings over clean frames that share one pattern.

    Highs/lows are positive magnitudes; ``gap`` is negative. Frames at end of
    file (no gap) are skipped for the gap median only.
    """
    buckets: dict[str, list[int]] = {key: [] for key in TIMING_KEYS}
    for frame in clean:
        for bit_index in range(FRAME_BITS):
            high = frame.pulses[2 * bit_index]
            low = -frame.pulses[2 * bit_index + 1]
            bit = (frame.value >> (FRAME_BITS - 1 - bit_index)) & 1
            if bit:
                buckets["long_high"].append(high)
                buckets["short_low"].append(low)
            else:
                buckets["short_high"].append(high)
                buckets["long_low"].append(low)
        buckets["sync_high"].append(frame.pulses[-1])
        if frame.gap is not None:
            buckets["gap"].append(frame.gap)
    return {key: _median(values) for key, values in buckets.items() if values}


def analyze_file(path: Path) -> dict:
    """Analyze one ``.sub`` file and return a JSON-serialisable report."""
    sub = parse_sub(str(path))
    all_frames = frames(sub)
    clean = [f for f in all_frames if f.value is not None]
    rejected = [f for f in all_frames if f.value is None]

    counts = Counter(f.value for f in clean)
    # Sort by count descending, then by value so ties are deterministic.
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    patterns = [{"pattern": f"{value:08X}", "count": count} for value, count in ordered]
    dominant = ordered[0][0] if ordered else None

    reasons = Counter(_reason_kind(f.reject_reason) for f in rejected)

    return {
        "file": path.name,
        "sha256": _sha256(path),
        "duplicates": [],
        "frequency": sub.frequency,
        "preset": sub.preset,
        "total_frames": len(all_frames),
        "clean_frames": len(clean),
        "rejected_frames": len(rejected),
        "reject_reasons": dict(sorted(reasons.items())),
        "patterns": patterns,
        "dominant": f"{dominant:08X}" if dominant is not None else None,
        "dominant_count": counts[dominant] if dominant is not None else 0,
        "mixed": len(counts) > 1,
        "timings": median_timings([f for f in clean if f.value == dominant]),
    }


def _reason_kind(reason: str) -> str:
    """Collapse a reject reason to its category so the histogram stays short."""
    for kind in ("length", "sign", "pulse", "pair", "sync", "checksum"):
        if reason.startswith(kind):
            return kind
    return reason


def analyze_dir(directory: Path) -> list[dict]:
    """Analyze every ``*.sub`` in ``directory``, sorted by file name."""
    reports = [analyze_file(p) for p in sorted(directory.glob("*.sub"))]
    by_hash: dict[str, list[str]] = {}
    for report in reports:
        by_hash.setdefault(report["sha256"], []).append(report["file"])
    for report in reports:
        report["duplicates"] = [n for n in by_hash[report["sha256"]] if n != report["file"]]
    return reports


def format_table(reports: list[dict]) -> str:
    """Render reports as a human-readable text table."""
    lines = []
    header = f"{'File':34} {'Clean':>5} {'Rej':>4} {'Dominant':9} {'Mixed':5}  Other patterns / duplicates"
    lines.append(header)
    lines.append("-" * len(header))
    for r in reports:
        others = ", ".join(f"{p['pattern']}×{p['count']}" for p in r["patterns"][1:]) or "—"
        dup = f"  (same bytes as {', '.join(r['duplicates'])})" if r["duplicates"] else ""
        lines.append(
            f"{r['file']:34} {r['clean_frames']:>5} {r['rejected_frames']:>4} "
            f"{(r['dominant'] or '—'):9} {('yes' if r['mixed'] else 'no'):5}  {others}{dup}"
        )
    lines.append("")
    lines.append("Median timings of dominant pattern (µs): short_high long_high short_low long_low sync_high gap")
    for r in reports:
        t = r["timings"]
        values = " ".join(f"{t.get(k, '—'):>6}" for k in TIMING_KEYS)
        lines.append(f"  {r['file']:34} {values}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("capture_dir", type=Path, help="directory containing .sub files")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)

    if not args.capture_dir.is_dir():
        parser.error(f"{args.capture_dir} is not a directory")

    reports = analyze_dir(args.capture_dir)
    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
    else:
        print(format_table(reports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
