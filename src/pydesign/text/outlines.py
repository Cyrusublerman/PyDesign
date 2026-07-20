"""FreeType glyph outlines for renderer-neutral display-list painting."""

from __future__ import annotations

from typing import Any

from pydesign.text.font import FontFace
from pydesign.text.glyphrun import GlyphRun


def glyph_outlines(face: FontFace, run: GlyphRun) -> list[dict[str, Any]]:
    """Return point-space path commands for each glyph in reading order."""
    try:
        import freetype
    except ImportError as error:
        raise ImportError("freetype-py is required for glyph outlines") from error

    ft_face = freetype.Face(str(face.path))
    ft_face.set_char_size(int(run.font_size * 64))
    scale = run.font_size / float(run.units_per_em) if run.units_per_em else 0.0
    pen_x = 0.0
    pen_y = 0.0
    result: list[dict[str, Any]] = []
    for glyph in run.glyphs:
        ft_face.load_glyph(glyph.glyph_id, freetype.FT_LOAD_NO_BITMAP | freetype.FT_LOAD_NO_HINTING)
        outline = ft_face.glyph.outline
        points = outline.points
        tags = outline.tags
        contours = outline.contours
        commands: list[dict[str, float | str]] = []
        start = 0
        for contour_end in contours:
            contour_points = points[start : contour_end + 1]
            contour_tags = tags[start : contour_end + 1]
            if not contour_points:
                start = contour_end + 1
                continue
            first = contour_points[0]
            origin_x = pen_x + glyph.x_offset + first[0] * scale
            # FreeType Y is up; display list Y is down.
            origin_y = pen_y - glyph.y_offset - first[1] * scale
            commands.append({"command": "move", "x": origin_x, "y": origin_y})
            for point, _tag in zip(contour_points[1:], contour_tags[1:], strict=False):
                commands.append(
                    {
                        "command": "line",
                        "x": pen_x + glyph.x_offset + point[0] * scale,
                        "y": pen_y - glyph.y_offset - point[1] * scale,
                    }
                )
            commands.append({"command": "close"})
            start = contour_end + 1
        result.append(
            {
                "glyph_id": glyph.glyph_id,
                "x": pen_x + glyph.x_offset,
                "y": pen_y - glyph.y_offset,
                "commands": commands,
            }
        )
        pen_x += glyph.x_advance
        pen_y += glyph.y_advance
    return result
