"""Deterministic font identity and OpenType shaping contracts."""

from pydesign.text.breaks import (
    BreakKind,
    BreakOpportunity,
    UnicodeAuthorityUnavailable,
    hyphenation_opportunities,
    line_break_opportunities,
)
from pydesign.text.font import (
    EmbeddingPermissions,
    FontAxis,
    FontChangedError,
    FontFace,
    FontFingerprint,
    FontMetadata,
    FontValidationError,
    load_font_face,
)
from pydesign.text.glyphrun import Glyph, GlyphBounds, GlyphRun
from pydesign.text.paragraph import ComposedLine, ParagraphLayout, compose_greedy
from pydesign.text.shaping import ShapingError, shape_text

__all__ = [
    "BreakKind",
    "BreakOpportunity",
    "ComposedLine",
    "EmbeddingPermissions",
    "FontAxis",
    "FontChangedError",
    "FontFace",
    "FontFingerprint",
    "FontMetadata",
    "FontValidationError",
    "Glyph",
    "GlyphBounds",
    "GlyphRun",
    "ParagraphLayout",
    "ShapingError",
    "UnicodeAuthorityUnavailable",
    "compose_greedy",
    "hyphenation_opportunities",
    "line_break_opportunities",
    "load_font_face",
    "shape_text",
]
