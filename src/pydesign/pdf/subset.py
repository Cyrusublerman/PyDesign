"""FontTools subset embedding helpers for searchable glyph_run PDF export."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as RLTTFont


def register_subset_face(
    font_path: str | Path,
    *,
    text: str,
    face_name: str,
) -> str:
    """Subset *font_path* to glyphs needed by *text* and register with ReportLab.

    Returns the registered PostScript font name. ReportLab embeds a ToUnicode CMap
    for TrueType faces registered this way, enabling extractable text.
    """
    source = Path(font_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"font not found: {source}")
    if face_name in pdfmetrics.getRegisteredFontNames():
        return face_name
    options = Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.recommended_glyphs = True
    font = TTFont(str(source))
    subsetter = Subsetter(options=options)
    subsetter.populate(text=text or " ")
    subsetter.subset(font)
    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        font.save(temporary)
        pdfmetrics.registerFont(RLTTFont(face_name, str(temporary)))
    finally:
        temporary.unlink(missing_ok=True)
    return face_name
