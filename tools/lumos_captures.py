"""Parse Flipper Sub-GHz RAW captures and decode the lamp remote's frames.

Units and sign convention used throughout this module:

* Every pulse value is a duration in microseconds (µs).
* Positive values are carrier on (high); negative values are carrier off (low).
* A frame is 32 bit pairs ``(high, -low)`` sent MSB first, then one short sync
  high, then a long negative gap that separates it from the next frame.

The checksum rule (``byte3 ^ 0x0E == byte4``) was observed in every clean frame
of every capture. It is an observation, not a confirmed protocol property.
"""

from __future__ import annotations

from dataclasses import dataclass

FRAME_BITS = 32
FRAME_LENGTH = FRAME_BITS * 2 + 1  # 32 bit pairs + trailing sync high
DEFAULT_GAP_THRESHOLD = -5000  # µs; a value strictly below this ends a frame

SHORT_MIN, SHORT_MAX = 150, 400  # µs, inclusive
LONG_MIN, LONG_MAX = 550, 950  # µs, inclusive

_REQUIRED_FILETYPE = "Flipper SubGhz RAW File"


@dataclass(frozen=True)
class SubFile:
    """A parsed Flipper ``.sub`` RAW capture.

    ``pulses`` holds every ``RAW_Data`` value in file order, concatenated
    across lines, in µs (positive = carrier on, negative = carrier off).
    ``frequency`` is in Hz.
    """

    path: str
    frequency: int
    preset: str
    protocol: str
    pulses: list[int]


@dataclass(frozen=True)
class Frame:
    """One chunk of a capture between gaps, decoded or rejected.

    ``pulses`` excludes the gap. ``gap`` is the negative delimiter in µs that
    followed the chunk, or ``None`` at end of file. ``value`` is the decoded
    32-bit integer, or ``None`` when ``reject_reason`` explains the rejection.
    """

    index: int
    pulses: list[int]
    gap: int | None
    value: int | None
    reject_reason: str | None


def parse_sub_text(text: str, path: str = "<memory>") -> SubFile:
    """Parse the text of a Flipper ``.sub`` RAW file.

    Returns a :class:`SubFile` whose ``pulses`` are µs durations
    (positive = carrier on, negative = carrier off).

    Raises ``ValueError`` if the ``Filetype`` header is missing or wrong, if
    ``Protocol`` is not ``RAW``, or if a ``RAW_Data`` token is not an integer.
    """
    headers: dict[str, str] = {}
    pulses: list[int] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        key, sep, rest = line.partition(":")
        if not sep:
            raise ValueError(f"{path}:{lineno}: expected 'Key: value', got {line!r}")
        key, rest = key.strip(), rest.strip()
        if key == "RAW_Data":
            for token in rest.split():
                try:
                    pulses.append(int(token))
                except ValueError:
                    raise ValueError(
                        f"{path}:{lineno}: RAW_Data token {token!r} is not an integer"
                    ) from None
        else:
            headers[key] = rest

    if headers.get("Filetype") != _REQUIRED_FILETYPE:
        raise ValueError(
            f"{path}: Filetype header must be {_REQUIRED_FILETYPE!r}, "
            f"got {headers.get('Filetype')!r}"
        )
    if headers.get("Protocol") != "RAW":
        raise ValueError(f"{path}: Protocol must be 'RAW', got {headers.get('Protocol')!r}")
    try:
        frequency = int(headers["Frequency"])
    except (KeyError, ValueError):
        raise ValueError(
            f"{path}: Frequency header missing or not an integer: {headers.get('Frequency')!r}"
        ) from None

    return SubFile(
        path=path,
        frequency=frequency,
        preset=headers.get("Preset", ""),
        protocol=headers["Protocol"],
        pulses=pulses,
    )


def parse_sub(path: str) -> SubFile:
    """Read and parse a Flipper ``.sub`` RAW file from disk.

    See :func:`parse_sub_text` for units (µs), sign convention and errors.
    """
    with open(path, encoding="utf-8") as fh:
        return parse_sub_text(fh.read(), path=str(path))


def split_frames(
    pulses: list[int], gap_threshold: int = DEFAULT_GAP_THRESHOLD
) -> list[tuple[list[int], int | None]]:
    """Split a pulse list (µs, positive = on, negative = off) at gaps.

    A gap is any value strictly below ``gap_threshold`` (default -5000 µs).
    Returns ``(chunk, gap)`` pairs where ``chunk`` excludes the gap. A leading
    gap yields an empty first chunk, which is kept so it can be rejected
    explicitly. A trailing chunk with no gap after it gets ``gap=None``.
    """
    chunks: list[tuple[list[int], int | None]] = []
    current: list[int] = []
    for value in pulses:
        if value < gap_threshold:
            chunks.append((current, value))
            current = []
        else:
            current.append(value)
    if current:
        chunks.append((current, None))
    return chunks


def _classify(value: int) -> str | None:
    magnitude = abs(value)
    if SHORT_MIN <= magnitude <= SHORT_MAX:
        return "short"
    if LONG_MIN <= magnitude <= LONG_MAX:
        return "long"
    return None


def checksum_ok(value: int) -> bool:
    """Return True if ``byte3 ^ 0x0E == byte4`` for a 32-bit frame value.

    byte3 is bits 15..8 and byte4 is bits 7..0. This rule is observed in every
    clean capture frame; it is not a confirmed protocol property.
    """
    return ((value >> 8) & 0xFF) ^ 0x0E == value & 0xFF


def decode_frame(pulses: list[int]) -> tuple[int | None, str | None]:
    """Decode one frame of µs pulses (positive = on, negative = off).

    The frame must be exactly 65 values: 32 ``(high, -low)`` bit pairs, MSB
    first, then a short sync high. Bit 0 is short high + long low; bit 1 is
    long high + short low. Short is 150–400 µs and long is 550–950 µs,
    both inclusive.

    Returns ``(value, None)`` on success or ``(None, reason)`` on rejection.
    """
    if len(pulses) != FRAME_LENGTH:
        return None, f"length {len(pulses)} != {FRAME_LENGTH}"

    for i, p in enumerate(pulses):
        expected_positive = i % 2 == 0
        if (p > 0) != expected_positive:
            want = "positive" if expected_positive else "negative"
            return None, f"sign of pulse {p} at {i}, expected {want}"

    kinds = []
    for i, p in enumerate(pulses):
        kind = _classify(p)
        if kind is None:
            return None, f"pulse {p} at {i} out of window"
        kinds.append(kind)

    value = 0
    for bit_index in range(FRAME_BITS):
        high, low = kinds[2 * bit_index], kinds[2 * bit_index + 1]
        if (high, low) == ("short", "long"):
            bit = 0
        elif (high, low) == ("long", "short"):
            bit = 1
        else:
            return None, f"pair at {2 * bit_index} is {high} high + {low} low"
        value = (value << 1) | bit

    if kinds[-1] != "short":
        return None, f"sync high {pulses[-1]} at {FRAME_LENGTH - 1} is not short"

    if not checksum_ok(value):
        return None, "checksum"

    return value, None


def frames(sub: SubFile) -> list[Frame]:
    """Split a capture at gaps and decode every chunk.

    Every chunk becomes a :class:`Frame`, including rejected ones, so ``index``
    is the 0-based position among all chunks. Pulses and gaps are in µs.
    """
    result = []
    for index, (chunk, gap) in enumerate(split_frames(sub.pulses)):
        value, reason = decode_frame(chunk)
        result.append(Frame(index=index, pulses=chunk, gap=gap, value=value, reject_reason=reason))
    return result
