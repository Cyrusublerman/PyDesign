"""Renderer-neutral positioned glyph-run value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydesign.text.font import FontFingerprint

type TextDirection = Literal["ltr", "rtl", "ttb", "btt"]


@dataclass(frozen=True, slots=True)
class GlyphBounds:
    x_bearing: float
    y_bearing: float
    width: float
    height: float

    def to_dict(self) -> dict[str, float]:
        return {
            "x_bearing": self.x_bearing,
            "y_bearing": self.y_bearing,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True, slots=True)
class Glyph:
    glyph_id: int
    glyph_name: str | None
    cluster: int
    x_advance: float
    y_advance: float
    x_offset: float
    y_offset: float
    unsafe_to_break: bool
    bounds: GlyphBounds | None

    def to_dict(self) -> dict[str, object]:
        return {
            "glyph_id": self.glyph_id,
            "glyph_name": self.glyph_name,
            "cluster": self.cluster,
            "x_advance": self.x_advance,
            "y_advance": self.y_advance,
            "x_offset": self.x_offset,
            "y_offset": self.y_offset,
            "unsafe_to_break": self.unsafe_to_break,
            "bounds": self.bounds.to_dict() if self.bounds is not None else None,
        }


@dataclass(frozen=True, slots=True)
class GlyphRun:
    text: str
    source_start: int
    source_end: int
    font: FontFingerprint
    font_size: float
    units_per_em: int
    direction: TextDirection
    script: str
    language: str
    features: tuple[tuple[str, int | bool], ...]
    glyphs: tuple[Glyph, ...]

    @property
    def x_advance(self) -> float:
        return sum(glyph.x_advance for glyph in self.glyphs)

    @property
    def y_advance(self) -> float:
        return sum(glyph.y_advance for glyph in self.glyphs)

    @property
    def clusters(self) -> tuple[int, ...]:
        return tuple(glyph.cluster for glyph in self.glyphs)

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "source_start": self.source_start,
            "source_end": self.source_end,
            "font": self.font.to_dict(),
            "font_size": self.font_size,
            "units_per_em": self.units_per_em,
            "direction": self.direction,
            "script": self.script,
            "language": self.language,
            "features": dict(self.features),
            "x_advance": self.x_advance,
            "y_advance": self.y_advance,
            "glyphs": [glyph.to_dict() for glyph in self.glyphs],
        }
