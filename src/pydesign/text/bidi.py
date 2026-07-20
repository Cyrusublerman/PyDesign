"""Bidirectional itemisation before shaping."""

from __future__ import annotations

from dataclasses import dataclass

from pydesign.text.glyphrun import TextDirection


@dataclass(frozen=True, slots=True)
class BidiRun:
    text: str
    start: int
    end: int
    direction: TextDirection
    level: int


def itemise_bidi(text: str, *, base_direction: TextDirection | None = None) -> tuple[BidiRun, ...]:
    """Split text into directional runs. Uses ICU when available; else one base-direction run."""
    if not text:
        return ()
    try:
        return _itemise_icu(text, base_direction=base_direction)
    except Exception:
        direction: TextDirection = base_direction or "ltr"
        return (BidiRun(text, 0, len(text), direction, 0 if direction == "ltr" else 1),)


def _itemise_icu(text: str, *, base_direction: TextDirection | None) -> tuple[BidiRun, ...]:
    from icu import BiDi, UBiDiLevel

    bidi = BiDi()
    level = UBiDiLevel.UBIDI_DEFAULT_LTR
    if base_direction == "rtl":
        level = UBiDiLevel.UBIDI_DEFAULT_RTL
    bidi.setPara(text, level)
    count = bidi.countRuns()
    runs: list[BidiRun] = []
    offset = 0
    for _index in range(count):
        start, length, run_level = bidi.getLogicalRun(offset)
        direction: TextDirection = "rtl" if int(run_level) % 2 else "ltr"
        end = int(start) + int(length)
        runs.append(BidiRun(text[int(start) : end], int(start), end, direction, int(run_level)))
        offset = end
        if offset >= len(text):
            break
    if not runs:
        direction = base_direction or "ltr"
        return (BidiRun(text, 0, len(text), direction, 0 if direction == "ltr" else 1),)
    return tuple(runs)
