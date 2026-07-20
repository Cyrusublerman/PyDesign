"""LibCST plans for TextFrame insertion."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from pydesign.source.analysis import build_source_index
from pydesign.source.cst_helpers import ensure_pydesign_imports, point_code
from pydesign.source.edits import Frame, SourceEditPlan, SourceRewriteError
from pydesign.source.rewrite import _ElementInsertionTransformer


def plan_text_frame_insertion(
    project_root: str | Path,
    page_id: str,
    *,
    object_id: str,
    frame: Frame,
    text: str = "Text",
    font: str | None = None,
    font_size: float = 12.0,
    colour: str = "#000000",
) -> SourceEditPlan:
    index = build_source_index(project_root)
    if index.get(object_id) is not None:
        raise SourceRewriteError(f"stable ID {object_id!r} already exists")
    page = index.require(page_id)
    if page.constructor != "Page":
        raise SourceRewriteError(f"{page_id!r} does not identify a Page declaration")
    source = page.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    font_arg = f", font={font!r}" if font else ""
    expression = cst.parse_expression(
        "TextFrame("
        f"id={object_id!r}, "
        f"frame=({point_code(frame[0])}, {point_code(frame[1])}, "
        f"{point_code(frame[2])}, {point_code(frame[3])}), "
        f"text={text!r}, font_size={font_size:g} * pt, colour={colour!r}{font_arg})"
    )
    transformer = _ElementInsertionTransformer(page_id, expression)
    updated = module.visit(transformer)
    if not transformer.changed:
        raise SourceRewriteError(f"could not insert into Page {page_id!r}")
    updated = ensure_pydesign_imports(updated, {"TextFrame", "pt"})
    return SourceEditPlan(
        path=page.path,
        before=source,
        after=updated.code,
        description=f"Create text frame {object_id}",
        object_id=object_id,
        property_name="elements",
        strategy="insert",
    )
