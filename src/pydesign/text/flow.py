"""Linked text-frame and column flow over the paragraph authority."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from pydesign.text.font import FontFace
from pydesign.text.glyphrun import GlyphRun
from pydesign.text.paragraph import ComposedLine, compose_greedy


@dataclass(frozen=True, slots=True)
class TextFrameSpec:
    id: str
    width: float
    height: float
    columns: int = 1
    gutter: float = 0.0

    @property
    def column_width(self) -> float:
        return (self.width - self.gutter * (self.columns - 1)) / self.columns


@dataclass(frozen=True, slots=True)
class PositionedLine:
    x: float
    baseline_y: float
    line: ComposedLine


@dataclass(frozen=True, slots=True)
class ColumnFlow:
    index: int
    x: float
    width: float
    lines: tuple[PositionedLine, ...]


@dataclass(frozen=True, slots=True)
class FrameFlow:
    id: str
    width: float
    height: float
    columns: tuple[ColumnFlow, ...]


@dataclass(frozen=True, slots=True)
class StoryFlow:
    text: str
    frames: tuple[FrameFlow, ...]
    source_end: int
    width_overflow: bool

    @property
    def overset(self) -> bool:
        return self.source_end < len(self.text)

    @property
    def overset_text(self) -> str:
        return self.text[self.source_end :]


def flow_story(
    face: FontFace,
    text: str,
    frames: Sequence[TextFrameSpec],
    *,
    font_size: float,
    leading: float,
    language: str = "und",
    features: Mapping[str, int | bool] | None = None,
    hyphenate: bool = True,
) -> StoryFlow:
    """Compose a story through ordered frames and columns with exact source ranges."""

    _validate_flow(frames, font_size=font_size, leading=leading)
    source_end = 0
    width_overflow = False
    empty_pending = not text
    flowed_frames: list[FrameFlow] = []
    for frame in frames:
        columns: list[ColumnFlow] = []
        capacity = math.floor((frame.height + 1e-9) / leading)
        for column_index in range(frame.columns):
            column_x = column_index * (frame.column_width + frame.gutter)
            positioned: list[PositionedLine] = []
            if capacity > 0 and (source_end < len(text) or empty_pending):
                base_source = source_end
                paragraph = compose_greedy(
                    face,
                    text[base_source:],
                    font_size=font_size,
                    maximum_width=frame.column_width,
                    language=language,
                    features=features,
                    hyphenate=hyphenate,
                )
                for slot, raw_line in enumerate(paragraph.lines[:capacity]):
                    line = _offset_line(raw_line, base_source)
                    positioned.append(PositionedLine(column_x, (slot + 1) * leading, line))
                    source_end = line.source_end
                    width_overflow = width_overflow or line.overset
                empty_pending = False
            columns.append(
                ColumnFlow(column_index, column_x, frame.column_width, tuple(positioned))
            )
        flowed_frames.append(FrameFlow(frame.id, frame.width, frame.height, tuple(columns)))
    return StoryFlow(text, tuple(flowed_frames), source_end, width_overflow)


def _validate_flow(frames: Sequence[TextFrameSpec], *, font_size: float, leading: float) -> None:
    if not math.isfinite(font_size) or font_size <= 0:
        raise ValueError("font_size must be finite and greater than zero")
    if not math.isfinite(leading) or leading <= 0:
        raise ValueError("leading must be finite and greater than zero")
    seen: set[str] = set()
    for frame in frames:
        if not frame.id or frame.id in seen:
            raise ValueError(f"text frame IDs must be non-empty and unique: {frame.id!r}")
        seen.add(frame.id)
        if not math.isfinite(frame.width) or frame.width <= 0:
            raise ValueError(f"text frame {frame.id!r} width must be finite and positive")
        if not math.isfinite(frame.height) or frame.height < 0:
            raise ValueError(f"text frame {frame.id!r} height must be finite and non-negative")
        if (
            isinstance(frame.columns, bool)
            or not isinstance(frame.columns, int)
            or frame.columns < 1
        ):
            raise ValueError(f"text frame {frame.id!r} columns must be a positive integer")
        if not math.isfinite(frame.gutter) or frame.gutter < 0:
            raise ValueError(f"text frame {frame.id!r} gutter must be finite and non-negative")
        if frame.column_width <= 0:
            raise ValueError(f"text frame {frame.id!r} gutters leave no column width")


def _offset_line(line: ComposedLine, offset: int) -> ComposedLine:
    run = _offset_run(line.run, offset)
    return replace(
        line,
        source_start=line.source_start + offset,
        source_end=line.source_end + offset,
        run=run,
    )


def _offset_run(run: GlyphRun, offset: int) -> GlyphRun:
    return replace(
        run,
        source_start=run.source_start + offset,
        source_end=run.source_end + offset,
        glyphs=tuple(replace(glyph, cluster=glyph.cluster + offset) for glyph in run.glyphs),
    )
