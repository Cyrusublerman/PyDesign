"""Immutable Stage 1 layout and renderer-neutral display list."""

from __future__ import annotations

from dataclasses import dataclass

from pydesign.diagnostics import Diagnostic
from pydesign.model import Document, Rectangle, TextFrame
from pydesign.validation import validate_document

type JsonScalar = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class DisplayOperation:
    kind: str
    object_id: str
    parameters: tuple[tuple[str, JsonScalar], ...]

    def to_dict(self) -> dict[str, JsonScalar]:
        return {"op": self.kind, "object_id": self.object_id, **dict(self.parameters)}


@dataclass(frozen=True, slots=True)
class DisplayPage:
    id: str
    width: float
    height: float
    operations: tuple[DisplayOperation, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "operations": [operation.to_dict() for operation in self.operations],
        }


@dataclass(frozen=True, slots=True)
class LayoutSnapshot:
    revision: str
    document_id: str
    title: str
    pages: tuple[DisplayPage, ...]
    diagnostics: tuple[Diagnostic, ...]
    schema_version: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "revision": self.revision,
            "document": {"id": self.document_id, "title": self.title},
            "pages": [page.to_dict() for page in self.pages],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


def layout_document(document: Document, *, revision: str = "unversioned") -> LayoutSnapshot:
    diagnostics = list(validate_document(document))
    pages: list[DisplayPage] = []

    for page in document.pages:
        operations: list[DisplayOperation] = []
        for element in page.iter_elements():
            if not element.visible or not element.printable:
                continue
            if isinstance(element, Rectangle):
                x, y, width, height = element.frame.to_points()
                operations.append(
                    DisplayOperation(
                        "rectangle",
                        element.id,
                        (
                            ("x", x),
                            ("y", y),
                            ("width", width),
                            ("height", height),
                            ("fill", element.fill),
                            ("stroke", element.stroke),
                            ("stroke_width", element.stroke_width.points),
                        ),
                    )
                )
            elif isinstance(element, TextFrame):
                x, y, width, height = element.frame.to_points()
                operations.append(
                    DisplayOperation(
                        "text_placeholder",
                        element.id,
                        (
                            ("x", x),
                            ("y", y),
                            ("width", width),
                            ("height", height),
                            ("text", element.text),
                            ("font_size", element.font_size.points),
                            ("colour", element.colour),
                        ),
                    )
                )
                diagnostics.append(
                    Diagnostic(
                        code="PD-TEXT-001",
                        severity="warning",
                        message=(
                            "Stage 1 displays this text as a labelled placeholder; professional "
                            "shaping and composition arrive in Stage 3"
                        ),
                        object_id=element.id,
                        page_id=page.id,
                    )
                )

        width, height = page.size.to_points()
        pages.append(DisplayPage(page.id, width, height, tuple(operations)))

    return LayoutSnapshot(
        revision=revision,
        document_id=document.id,
        title=document.title,
        pages=tuple(pages),
        diagnostics=tuple(diagnostics),
    )
