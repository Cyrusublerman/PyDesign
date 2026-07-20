"""Deterministic single-line paragraph composer over shaped candidates."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace

from pydesign.text.breaks import (
    BreakKind,
    BreakOpportunity,
    hyphenation_opportunities,
    line_break_opportunities,
)
from pydesign.text.font import FontFace
from pydesign.text.glyphrun import GlyphRun
from pydesign.text.shaping import shape_text


@dataclass(frozen=True, slots=True)
class ComposedLine:
    source_start: int
    source_end: int
    run: GlyphRun
    hard_break: bool
    hyphenated: bool
    overset: bool


@dataclass(frozen=True, slots=True)
class ParagraphLayout:
    text: str
    maximum_width: float
    lines: tuple[ComposedLine, ...]

    @property
    def overset(self) -> bool:
        return any(line.overset for line in self.lines)


def compose_greedy(
    face: FontFace,
    text: str,
    *,
    font_size: float,
    maximum_width: float,
    language: str = "und",
    features: Mapping[str, int | bool] | None = None,
    hyphenate: bool = True,
) -> ParagraphLayout:
    """Compose legal ICU/Pyphen candidates using boundary-sensitive re-shaping."""

    if not math.isfinite(maximum_width) or maximum_width <= 0:
        raise ValueError("maximum_width must be finite and greater than zero")
    opportunities = list(line_break_opportunities(text, language=language))
    if hyphenate and language != "und":
        opportunities.extend(hyphenation_opportunities(text, language=language))
    opportunities = list(_merged_breaks(opportunities))

    lines: list[ComposedLine] = []
    start = 0
    while start < len(text):
        candidates = [item for item in opportunities if item.index > start]
        if not candidates:
            candidates = [BreakOpportunity(len(text), BreakKind.HARD)]
        first_hard = next((item.index for item in candidates if item.kind == BreakKind.HARD), None)
        if first_hard is not None:
            candidates = [item for item in candidates if item.index <= first_hard]

        chosen: tuple[BreakOpportunity, GlyphRun] | None = None
        first: tuple[BreakOpportunity, GlyphRun] | None = None
        for opportunity in candidates:
            run = _shape_candidate(
                face,
                text,
                start,
                opportunity,
                font_size=font_size,
                language=language,
                features=features,
            )
            first = first or (opportunity, run)
            if run.x_advance <= maximum_width + 1e-9:
                chosen = (opportunity, run)
                if opportunity.kind == BreakKind.HARD:
                    break
                continue
            break
        chosen = chosen or first
        if chosen is None:
            break
        opportunity, run = chosen
        lines.append(
            ComposedLine(
                source_start=start,
                source_end=opportunity.index,
                run=run,
                hard_break=opportunity.kind == BreakKind.HARD,
                hyphenated=opportunity.kind == BreakKind.HYPHEN,
                overset=run.x_advance > maximum_width + 1e-9,
            )
        )
        start = opportunity.index

    if not text:
        run = shape_text(face, "", font_size=font_size, language=language, features=features)
        lines.append(ComposedLine(0, 0, run, True, False, False))
    return ParagraphLayout(text, maximum_width, tuple(lines))


def _shape_candidate(
    face: FontFace,
    text: str,
    start: int,
    opportunity: BreakOpportunity,
    *,
    font_size: float,
    language: str,
    features: Mapping[str, int | bool] | None,
) -> GlyphRun:
    from pydesign.text.bidi import itemise_bidi

    segment = text[start : opportunity.index].rstrip(" \t\r\n")
    if opportunity.kind == BreakKind.HYPHEN:
        segment += "\u2010"
    if not segment:
        run = shape_text(
            face,
            "",
            font_size=font_size,
            language=language,
            features=features,
            source_start=start,
        )
        return replace(run, source_end=opportunity.index)
    runs = itemise_bidi(segment)
    if len(runs) == 1:
        run = shape_text(
            face,
            runs[0].text,
            font_size=font_size,
            language=language,
            features=features,
            direction=runs[0].direction,
            source_start=start,
        )
        return replace(run, source_end=opportunity.index)
    glyphs: list[object] = []
    first: GlyphRun | None = None
    cursor = start
    for bidi_run in runs:
        shaped = shape_text(
            face,
            bidi_run.text,
            font_size=font_size,
            language=language,
            features=features,
            direction=bidi_run.direction,
            source_start=cursor,
        )
        first = first or shaped
        glyphs.extend(shaped.glyphs)
        cursor += len(bidi_run.text)
    assert first is not None
    return replace(
        first,
        text=segment,
        glyphs=tuple(glyphs),  # type: ignore[arg-type]
        source_start=start,
        source_end=opportunity.index,
    )


def _merged_breaks(opportunities: list[BreakOpportunity]) -> tuple[BreakOpportunity, ...]:
    priority = {BreakKind.SOFT: 0, BreakKind.HYPHEN: 1, BreakKind.HARD: 2}
    merged: dict[int, BreakOpportunity] = {}
    for opportunity in opportunities:
        previous = merged.get(opportunity.index)
        if previous is None or priority[opportunity.kind] > priority[previous.kind]:
            merged[opportunity.index] = opportunity
    return tuple(merged[index] for index in sorted(merged))
