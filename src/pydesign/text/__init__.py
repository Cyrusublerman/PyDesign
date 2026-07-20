"""Deterministic font identity and OpenType shaping contracts."""

from pydesign.text.bidi import BidiRun, itemise_bidi
from pydesign.text.breaks import (
    BreakKind,
    BreakOpportunity,
    UnicodeAuthorityUnavailable,
    hyphenation_opportunities,
    line_break_opportunities,
)
from pydesign.text.flow import (
    ColumnFlow,
    FrameFlow,
    PositionedLine,
    StoryFlow,
    TextFrameSpec,
    flow_story,
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
from pydesign.text.justify import JustificationReport, justify_line
from pydesign.text.outlines import glyph_outlines
from pydesign.text.paragraph import ComposedLine, ParagraphLayout, compose_greedy
from pydesign.text.registry import (
    FontRegistry,
    FontRegistryError,
    MissingGlyphError,
    RegisteredFont,
    grapheme_clusters,
    shape_with_fallback,
)
from pydesign.text.shaping import ShapingError, shape_text

__all__ = [
    "BidiRun",
    "BreakKind",
    "BreakOpportunity",
    "ColumnFlow",
    "ComposedLine",
    "EmbeddingPermissions",
    "FontAxis",
    "FontChangedError",
    "FontFace",
    "FontFingerprint",
    "FontMetadata",
    "FontRegistry",
    "FontRegistryError",
    "FontValidationError",
    "FrameFlow",
    "Glyph",
    "GlyphBounds",
    "GlyphRun",
    "JustificationReport",
    "MissingGlyphError",
    "ParagraphLayout",
    "PositionedLine",
    "RegisteredFont",
    "ShapingError",
    "StoryFlow",
    "TextFrameSpec",
    "UnicodeAuthorityUnavailable",
    "compose_greedy",
    "flow_story",
    "glyph_outlines",
    "grapheme_clusters",
    "hyphenation_opportunities",
    "itemise_bidi",
    "justify_line",
    "line_break_opportunities",
    "load_font_face",
    "shape_text",
    "shape_with_fallback",
]
