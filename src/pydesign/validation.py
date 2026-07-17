"""Semantic document validation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydesign.diagnostics import Diagnostic
from pydesign.model import Document, Page, Rectangle, TextFrame

_ID_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")


@dataclass(frozen=True, slots=True)
class DocumentValidationError(ValueError):
    diagnostics: tuple[Diagnostic, ...]

    def __str__(self) -> str:
        return "; ".join(item.message for item in self.diagnostics)


def validate_document(document: Document) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    seen: dict[str, str] = {}

    def register(object_id: str, kind: str) -> None:
        if not _ID_PATTERN.fullmatch(object_id):
            diagnostics.append(
                Diagnostic(
                    code="PD-MODEL-001",
                    severity="error",
                    message=f"Invalid stable ID {object_id!r} on {kind}",
                    object_id=object_id,
                )
            )
        previous = seen.get(object_id)
        if previous is not None:
            diagnostics.append(
                Diagnostic(
                    code="PD-MODEL-002",
                    severity="error",
                    message=f"Duplicate stable ID {object_id!r} on {previous} and {kind}",
                    object_id=object_id,
                )
            )
        else:
            seen[object_id] = kind

    register(document.id, "Document")
    if not document.pages:
        diagnostics.append(
            Diagnostic(
                "PD-MODEL-003", "error", "Document must contain at least one page", document.id
            )
        )

    for page in document.pages:
        _validate_page(page, register, diagnostics)

    errors = tuple(item for item in diagnostics if item.severity == "error")
    if errors:
        raise DocumentValidationError(errors)
    return tuple(diagnostics)


def _validate_page(
    page: Page,
    register: object,
    diagnostics: list[Diagnostic],
) -> None:
    # ``register`` is locally closed over with a precise two-string signature.
    register(page.id, "Page")  # type: ignore[operator]
    width, height = page.size.to_points()
    if width <= 0 or height <= 0:
        diagnostics.append(
            Diagnostic("PD-MODEL-004", "error", "Page size must be positive", page.id, page.id)
        )

    for layer in page.layers:
        register(layer.id, "Layer")  # type: ignore[operator]
    for element in page.iter_elements():
        register(element.id, type(element).__name__)  # type: ignore[operator]
        if isinstance(element, (Rectangle, TextFrame)):
            _, _, element_width, element_height = element.frame.to_points()
            if element_width < 0 or element_height < 0:
                diagnostics.append(
                    Diagnostic(
                        "PD-MODEL-005",
                        "error",
                        "Element frame width and height cannot be negative",
                        element.id,
                        page.id,
                    )
                )
        if isinstance(element, TextFrame) and element.font_size.points <= 0:
            diagnostics.append(
                Diagnostic(
                    "PD-TEXT-002",
                    "error",
                    "Text font size must be positive",
                    element.id,
                    page.id,
                )
            )
