"""Public authoring API for PyDesign projects."""

from pydesign.context import BuildContext
from pydesign.layout import LayoutSnapshot, layout_document
from pydesign.model import (
    BezierPath,
    ClosePath,
    CurveTo,
    Document,
    Ellipse,
    Guide,
    ImageFrame,
    Layer,
    LineTo,
    MoveTo,
    Page,
    Rect,
    Rectangle,
    Size,
    TextFrame,
)
from pydesign.styles import (
    CharacterStyle,
    ParagraphStyle,
    ResolvedCharacter,
    StyleError,
    detect_style_cycle,
    resolve_character_style,
)
from pydesign.units import Length, cm, inch, mm, pc, pt, px
from pydesign.validation import DocumentValidationError, validate_document

__all__ = [
    "BezierPath",
    "BuildContext",
    "CharacterStyle",
    "ClosePath",
    "CurveTo",
    "Document",
    "DocumentValidationError",
    "Ellipse",
    "Guide",
    "ImageFrame",
    "Layer",
    "LayoutSnapshot",
    "Length",
    "LineTo",
    "MoveTo",
    "Page",
    "ParagraphStyle",
    "Rect",
    "Rectangle",
    "ResolvedCharacter",
    "Size",
    "StyleError",
    "TextFrame",
    "cm",
    "detect_style_cycle",
    "inch",
    "layout_document",
    "mm",
    "pc",
    "pt",
    "px",
    "resolve_character_style",
    "validate_document",
]

__version__ = "0.1.0.dev0"
