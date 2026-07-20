"""Immutable Stage 1 layout and renderer-neutral display list."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from pydesign.diagnostics import Diagnostic
from pydesign.model import (
    BezierPath,
    ClosePath,
    CurveTo,
    Document,
    Ellipse,
    ImageFrame,
    Layer,
    LineTo,
    MoveTo,
    Page,
    Rectangle,
    TextFrame,
)
from pydesign.validation import validate_document

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class DisplayOperation:
    kind: str
    object_id: str
    parameters: tuple[tuple[str, JsonValue], ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {"op": self.kind, "object_id": self.object_id, **dict(self.parameters)}


@dataclass(frozen=True, slots=True)
class DisplayPage:
    id: str
    width: float
    height: float
    operations: tuple[DisplayOperation, ...]
    layers: tuple[dict[str, JsonValue], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "layers": list(self.layers),
            "operations": [operation.to_dict() for operation in self.operations],
        }


@dataclass(frozen=True, slots=True)
class LayoutSnapshot:
    revision: str
    document_id: str
    title: str
    pages: tuple[DisplayPage, ...]
    diagnostics: tuple[Diagnostic, ...]
    layers: tuple[dict[str, JsonValue], ...] = ()
    schema_version: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "revision": self.revision,
            "document": {"id": self.document_id, "title": self.title},
            "layers": list(self.layers),
            "pages": [page.to_dict() for page in self.pages],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


def layout_document(document: Document, *, revision: str = "unversioned") -> LayoutSnapshot:
    diagnostics = list(validate_document(document))
    pages: list[DisplayPage] = []
    all_layers: list[dict[str, JsonValue]] = []

    for page in document.pages:
        operations: list[DisplayOperation] = []
        page_layers = tuple(_layer_row(layer, page.id) for layer in page.layers)
        all_layers.extend(page_layers)
        for guide in page.guides:
            operations.append(
                DisplayOperation(
                    "guide",
                    f"{page.id}:guide:{guide.orientation}:{guide.position.points}",
                    (
                        ("orientation", guide.orientation),
                        ("position", guide.position.points),
                    ),
                )
            )
        for layer_id, element in _iter_canvas_elements(page):
            if isinstance(element, (Rectangle, Ellipse)):
                x, y, width, height = element.frame.to_points()
                kind = "ellipse" if isinstance(element, Ellipse) else "rectangle"
                params: list[tuple[str, JsonValue]] = [
                    ("x", x),
                    ("y", y),
                    ("width", width),
                    ("height", height),
                    ("fill", element.fill),
                    ("stroke", element.stroke),
                    ("stroke_width", element.stroke_width.points),
                ]
                if layer_id is not None:
                    params.append(("layer", layer_id))
                operations.append(DisplayOperation(kind, element.id, tuple(params)))
            elif isinstance(element, ImageFrame):
                x, y, width, height = element.frame.to_points()
                params = [
                    ("x", x),
                    ("y", y),
                    ("width", width),
                    ("height", height),
                    ("path", element.path),
                ]
                digest = _image_digest(element.path)
                if digest is not None:
                    params.append(("content_sha256", digest))
                if layer_id is not None:
                    params.append(("layer", layer_id))
                operations.append(DisplayOperation("image", element.id, tuple(params)))
            elif isinstance(element, BezierPath):
                params = [
                    ("commands", [_path_command(command) for command in element.commands]),
                    ("fill", element.fill),
                    ("stroke", element.stroke),
                    ("stroke_width", element.stroke_width.points),
                ]
                if layer_id is not None:
                    params.append(("layer", layer_id))
                operations.append(DisplayOperation("bezier_path", element.id, tuple(params)))
            elif isinstance(element, TextFrame):
                operations.append(_text_operation(element, page, layer_id, diagnostics))

        width, height = page.size.to_points()
        pages.append(
            DisplayPage(
                page.id,
                width,
                height,
                tuple(operations),
                page_layers,
            )
        )

    return LayoutSnapshot(
        revision=revision,
        document_id=document.id,
        title=document.title,
        pages=tuple(pages),
        diagnostics=tuple(diagnostics),
        layers=tuple(all_layers),
    )


def _layer_row(layer: Layer, page_id: str) -> dict[str, JsonValue]:
    return {
        "id": layer.id,
        "label": layer.label or layer.id,
        "visible": layer.visible,
        "printable": layer.printable,
        "page_id": page_id,
    }


type CanvasLeaf = Rectangle | Ellipse | ImageFrame | BezierPath | TextFrame


def _iter_canvas_elements(page: Page) -> list[tuple[str | None, CanvasLeaf]]:
    """Visible elements for canvas preview; printable is export-only (design 03/06)."""
    items: list[tuple[str | None, CanvasLeaf]] = []
    for element in page.elements:
        if element.visible:
            items.append((None, element))
    for layer in page.layers:
        if not layer.visible:
            continue
        for element in layer.elements:
            if element.visible:
                items.append((layer.id, element))
    return items


def _text_operation(
    element: TextFrame,
    page: Page,
    layer_id: str | None,
    diagnostics: list[Diagnostic],
) -> DisplayOperation:
    x, y, width, height = element.frame.to_points()
    params: list[tuple[str, JsonValue]] = [
        ("x", x),
        ("y", y),
        ("width", width),
        ("height", height),
        ("text", element.text),
        ("font_size", element.font_size.points),
        ("colour", element.colour),
    ]
    if layer_id is not None:
        params.append(("layer", layer_id))
    if element.font and element.font.strip():
        shaped = _try_shape_text(element, element.font.strip())
        if shaped is not None and "shape_error" not in dict(shaped):
            params.extend(shaped)
            shaped_map = dict(shaped)
            if shaped_map.get("overset") is True:
                diagnostics.append(
                    Diagnostic(
                        code="PD-TEXT-003",
                        severity="warning",
                        message="TextFrame has overset text that did not fit the frame",
                        object_id=element.id,
                        page_id=page.id,
                    )
                )
            return DisplayOperation("glyph_run", element.id, tuple(params))
        if shaped is not None:
            params.extend(shaped)
    diagnostics.append(
        Diagnostic(
            code="PD-TEXT-001",
            severity="warning",
            message=(
                "TextFrame has no shaped glyph run yet; set an explicit font path for Stage 3 "
                "outline painting, or keep this labelled placeholder"
            ),
            object_id=element.id,
            page_id=page.id,
        )
    )
    return DisplayOperation("text_placeholder", element.id, tuple(params))


def _try_shape_text(element: TextFrame, font_path: str) -> list[tuple[str, JsonValue]] | None:
    try:
        from pydesign.text import load_font_face, shape_text
        from pydesign.text.bidi import itemise_bidi
        from pydesign.text.flow import TextFrameSpec, flow_story
        from pydesign.text.justify import justify_line
        from pydesign.text.outlines import glyph_outlines
    except ImportError:
        return None
    try:
        face = load_font_face(font_path)
        font_size = element.font_size.points
        x, y, width, height = element.frame.to_points()
        leading = font_size * 1.2
        if "\n" in element.text or height > font_size * 2.5:
            story = flow_story(
                face,
                element.text.replace("\n", " "),
                (TextFrameSpec(element.id, width, height),),
                font_size=font_size,
                leading=leading,
            )
            lines_payload: list[JsonValue] = []
            outline_payload: list[JsonValue] = []
            for frame in story.frames:
                for column in frame.columns:
                    for positioned in column.lines:
                        line, report = justify_line(positioned.line, column.width)
                        run = line.run
                        outlines = glyph_outlines(face, run)
                        lines_payload.append(
                            cast(
                                JsonValue,
                                {
                                    "x": x + positioned.x,
                                    "baseline_y": y + positioned.baseline_y,
                                    "underfull": report.underfull,
                                    "overfull": report.overfull,
                                    "glyphs": [glyph.to_dict() for glyph in run.glyphs],
                                },
                            )
                        )
                        outline_payload.append(
                            cast(
                                JsonValue,
                                {
                                    "x": x + positioned.x,
                                    "y": y + positioned.baseline_y,
                                    "outlines": outlines,
                                },
                            )
                        )
            result: list[tuple[str, JsonValue]] = [
                ("font", font_path),
                ("lines", cast(JsonValue, lines_payload)),
                ("flow_outlines", cast(JsonValue, outline_payload)),
                ("overset", story.overset),
            ]
            if story.overset:
                result.append(("overset_text", story.overset_text))
            return result
        runs = itemise_bidi(element.text)
        all_glyphs: list[JsonValue] = []
        all_outlines: list[JsonValue] = []
        direction = "ltr"
        for bidi_run in runs:
            shaped = shape_text(
                face,
                bidi_run.text,
                font_size=font_size,
                direction=bidi_run.direction,
            )
            direction = shaped.direction
            all_glyphs.extend(cast(list[JsonValue], [glyph.to_dict() for glyph in shaped.glyphs]))
            all_outlines.extend(cast(list[JsonValue], glyph_outlines(face, shaped)))
        return [
            ("font", font_path),
            ("glyphs", cast(JsonValue, all_glyphs)),
            ("direction", direction),
            ("outlines", cast(JsonValue, all_outlines)),
        ]
    except (OSError, ValueError) as error:
        return [("shape_error", str(error))]


def _image_digest(path_value: str) -> str | None:
    from hashlib import sha256
    from pathlib import Path

    path = Path(path_value)
    if not path.is_file():
        return None
    return sha256(path.read_bytes()).hexdigest()


def _path_command(command: MoveTo | LineTo | CurveTo | ClosePath) -> dict[str, JsonValue]:
    if isinstance(command, MoveTo):
        return {"command": "move", "x": command.x.points, "y": command.y.points}
    if isinstance(command, LineTo):
        return {"command": "line", "x": command.x.points, "y": command.y.points}
    if isinstance(command, CurveTo):
        return {
            "command": "curve",
            "control_1_x": command.control_1_x.points,
            "control_1_y": command.control_1_y.points,
            "control_2_x": command.control_2_x.points,
            "control_2_y": command.control_2_y.points,
            "x": command.x.points,
            "y": command.y.points,
        }
    return {"command": "close"}
