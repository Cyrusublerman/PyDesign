"""HarfBuzz shaping that emits the shared renderer-neutral GlyphRun."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import cast

import uharfbuzz as hb

from pydesign.text.font import FontFace
from pydesign.text.glyphrun import Glyph, GlyphBounds, GlyphRun, TextDirection


class ShapingError(ValueError):
    pass


def shape_text(
    face: FontFace,
    text: str,
    *,
    font_size: float,
    direction: TextDirection | None = None,
    script: str | None = None,
    language: str | None = None,
    features: Mapping[str, int | bool] | None = None,
    source_start: int = 0,
) -> GlyphRun:
    """Shape one already-itemised run into unhinted page-point positions."""

    if not math.isfinite(font_size) or font_size <= 0:
        raise ShapingError("font_size must be finite and greater than zero")
    if source_start < 0:
        raise ShapingError("source_start must be non-negative")
    normalized_features = _features(features or {})
    if not text:
        direction = direction or "ltr"
        script = script or "Zyyy"
        language = language or "und"
    face.verify_unchanged()
    try:
        blob = hb.Blob.from_file_path(str(face.path))
        hb_face = hb.Face(blob, face.fingerprint.face_index)
        hb_font = hb.Font(hb_face)
        hb.ot_font_set_funcs(hb_font)
        units_per_em = int(hb_face.upem)
        hb_font.scale = (units_per_em, units_per_em)
        if face.fingerprint.variations:
            hb_font.set_variations(dict(face.fingerprint.variations))
        if face.fingerprint.synthetic_bold:
            hb_font.synthetic_bold = (
                face.fingerprint.synthetic_bold,
                face.fingerprint.synthetic_bold,
                False,
            )
        if face.fingerprint.synthetic_slant:
            hb_font.synthetic_slant = face.fingerprint.synthetic_slant

        buffer = hb.Buffer()
        buffer.cluster_level = hb.BufferClusterLevel.MONOTONE_GRAPHEMES
        buffer.add_codepoints([ord(character) for character in text])
        if direction is not None:
            buffer.direction = direction
        if script is not None:
            buffer.script = script
        if language is not None:
            buffer.language = language
        buffer.guess_segment_properties()
        hb.shape(hb_font, buffer, dict(normalized_features))
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise ShapingError(f"HarfBuzz could not shape the run: {error}") from error

    resolved_direction = cast(TextDirection, str(buffer.direction))
    resolved_script = str(buffer.script)
    resolved_language = str(buffer.language)
    point_scale = font_size / units_per_em
    glyphs: list[Glyph] = []
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions, strict=True):
        extents = hb_font.get_glyph_extents(info.codepoint)
        bounds = (
            GlyphBounds(
                x_bearing=extents.x_bearing * point_scale,
                y_bearing=extents.y_bearing * point_scale,
                width=extents.width * point_scale,
                height=extents.height * point_scale,
            )
            if extents is not None
            else None
        )
        glyphs.append(
            Glyph(
                glyph_id=int(info.codepoint),
                glyph_name=hb_font.get_glyph_name(info.codepoint),
                cluster=source_start + int(info.cluster),
                x_advance=position.x_advance * point_scale,
                y_advance=position.y_advance * point_scale,
                x_offset=position.x_offset * point_scale,
                y_offset=position.y_offset * point_scale,
                unsafe_to_break=bool(info.flags & hb.GlyphFlags.UNSAFE_TO_BREAK),
                bounds=bounds,
            )
        )

    return GlyphRun(
        text=text,
        source_start=source_start,
        source_end=source_start + len(text),
        font=face.fingerprint,
        font_size=float(font_size),
        units_per_em=units_per_em,
        direction=resolved_direction,
        script=resolved_script,
        language=resolved_language,
        features=normalized_features,
        glyphs=tuple(glyphs),
    )


def _features(features: Mapping[str, int | bool]) -> tuple[tuple[str, int | bool], ...]:
    normalized: list[tuple[str, int | bool]] = []
    for tag, value in sorted(features.items()):
        if len(tag) != 4 or not tag.isascii():
            raise ShapingError(f"OpenType feature tag must be four ASCII characters: {tag!r}")
        normalized.append((tag, value))
    return tuple(normalized)
