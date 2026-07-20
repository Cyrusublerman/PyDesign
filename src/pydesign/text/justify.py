"""Simple justification adjustments for composed lines."""

from __future__ import annotations

from dataclasses import dataclass, replace

from pydesign.text.glyphrun import Glyph, GlyphRun
from pydesign.text.paragraph import ComposedLine


@dataclass(frozen=True, slots=True)
class JustificationReport:
    target_width: float
    natural_width: float
    underfull: bool
    overfull: bool
    delta: float


def justify_line(
    line: ComposedLine, target_width: float
) -> tuple[ComposedLine, JustificationReport]:
    """Distribute leftover width across glyph advances (space-like clusters only)."""
    natural = line.run.x_advance
    delta = target_width - natural
    report = JustificationReport(
        target_width=target_width,
        natural_width=natural,
        underfull=delta > 0.5,
        overfull=delta < -0.5,
        delta=delta,
    )
    if abs(delta) < 0.01 or not line.run.glyphs:
        return line, report
    space_indices = [
        index for index, glyph in enumerate(line.run.glyphs) if _is_space_cluster(line.run, glyph)
    ]
    if not space_indices:
        return line, report
    each = delta / len(space_indices)
    glyphs: list[Glyph] = []
    for index, glyph in enumerate(line.run.glyphs):
        if index in space_indices:
            glyphs.append(replace(glyph, x_advance=glyph.x_advance + each))
        else:
            glyphs.append(glyph)
    run = replace(line.run, glyphs=tuple(glyphs))
    return replace(line, run=run), report


def _is_space_cluster(run: GlyphRun, glyph: Glyph) -> bool:
    if glyph.cluster < 0 or glyph.cluster >= len(run.text):
        return False
    return run.text[glyph.cluster].isspace()
