"""Populate the inspector from a selected stable ID."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydesign.gui.inspector import GeometryInspector
from pydesign.source import Frame, build_source_index


def sync_inspector_selection(
    inspector: GeometryInspector,
    *,
    project_root: Path,
    object_id: str,
    frame: Frame | None,
) -> None:
    try:
        declaration = build_source_index(project_root).require(object_id)
        ownership = declaration.property("frame")
        source = f"{declaration.path.relative_to(project_root)}:{declaration.span.start_line}"
        ownership_text = ownership.kind.value if ownership is not None else "derived/missing"
        if ownership is not None and ownership.components:
            ownership_text += " · " + ", ".join(item.value for item in ownership.components)
        style_prop = declaration.property("style")
        style_text = (
            f"style={style_prop.code} ({style_prop.kind.value})"
            if style_prop is not None
            else "No style= reference"
        )
        appearance: dict[str, Any] = {}
        for name in ("fill", "stroke", "colour", "text"):
            prop = declaration.property(name)
            if prop is None:
                continue
            appearance[name] = prop.code.strip("'\"") if prop.kind.value == "literal" else prop.code
        stroke_w = declaration.property("stroke_width")
        if stroke_w is not None:
            appearance["stroke_width"] = stroke_w.code
    except (OSError, ValueError, KeyError) as error:
        source = str(error)
        ownership_text = "unresolved"
        style_text = "unresolved"
        appearance = {}
    inspector.set_selection(
        object_id,
        frame,
        source=source,
        ownership=ownership_text,
        style=style_text,
        appearance=appearance,
    )
