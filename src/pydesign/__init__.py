"""Public authoring API for PyDesign projects."""

from pydesign.context import BuildContext
from pydesign.layout import LayoutSnapshot, layout_document
from pydesign.model import Document, Layer, Page, Rect, Rectangle, Size, TextFrame
from pydesign.units import Length, cm, inch, mm, pc, pt, px
from pydesign.validation import DocumentValidationError, validate_document

__all__ = [
    "BuildContext",
    "Document",
    "DocumentValidationError",
    "Layer",
    "LayoutSnapshot",
    "Length",
    "Page",
    "Rect",
    "Rectangle",
    "Size",
    "TextFrame",
    "cm",
    "inch",
    "layout_document",
    "mm",
    "pc",
    "pt",
    "px",
    "validate_document",
]

__version__ = "0.1.0.dev0"
