"""Atomic vector PDF adapter for the renderer-neutral display list."""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pikepdf
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas

from pydesign.layout import LayoutSnapshot


class PdfExportError(ValueError):
    """Raised before a prior output is replaced when parity cannot be guaranteed."""


@dataclass(frozen=True, slots=True)
class PdfPageSummary:
    id: str
    width: float
    height: float
    operation_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "operation_count": self.operation_count,
        }


@dataclass(frozen=True, slots=True)
class PdfExportManifest:
    source_revision: str
    document_id: str
    document_title: str
    pdf_sha256: str
    pages: tuple[PdfPageSummary, ...]
    writer: str = "reportlab"
    inspector: str = "pikepdf"
    schema_version: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_revision": self.source_revision,
            "document": {"id": self.document_id, "title": self.document_title},
            "pdf_sha256": self.pdf_sha256,
            "page_count": len(self.pages),
            "pages": [page.to_dict() for page in self.pages],
            "writer": self.writer,
            "inspector": self.inspector,
        }


@dataclass(frozen=True, slots=True)
class _Operation:
    kind: str
    object_id: str
    values: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class _Page:
    id: str
    width: float
    height: float
    operations: tuple[_Operation, ...]


@dataclass(frozen=True, slots=True)
class _Export:
    revision: str
    document_id: str
    title: str
    pages: tuple[_Page, ...]


def export_layout_pdf(
    layout: LayoutSnapshot | Mapping[str, object],
    destination: str | Path,
    *,
    manifest_path: str | Path | None = None,
) -> PdfExportManifest:
    """Validate, write, reopen and atomically publish a vector-only PDF.

    Text placeholders and unknown operations are rejected. This prevents a Stage 1
    preview representation from being mistaken for typography-authoritative output.
    """

    export = _normalise_export(layout.to_dict() if isinstance(layout, LayoutSnapshot) else layout)
    output = Path(destination).expanduser().resolve()
    manifest_output = (
        Path(manifest_path).expanduser().resolve()
        if manifest_path is not None
        else output.with_name(f"{output.name}.manifest.json")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp.pdf", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    manifest_temporary: Path | None = None
    try:
        _write_pdf(export, temporary)
        _inspect_pdf(temporary, export.pages)
        digest = _sha256(temporary)
        manifest = PdfExportManifest(
            source_revision=export.revision,
            document_id=export.document_id,
            document_title=export.title,
            pdf_sha256=digest,
            pages=tuple(
                PdfPageSummary(page.id, page.width, page.height, len(page.operations))
                for page in export.pages
            ),
        )
        manifest_temporary = _write_manifest_temporary(manifest, manifest_output)
        os.replace(temporary, output)
        os.replace(manifest_temporary, manifest_output)
        return manifest
    except PdfExportError:
        raise
    except Exception as error:
        raise PdfExportError(f"PDF export failed: {error}") from error
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()
        if manifest_temporary is not None:
            with contextlib.suppress(FileNotFoundError):
                manifest_temporary.unlink()


def _normalise_export(layout: Mapping[str, object]) -> _Export:
    schema_version = layout.get("schema_version")
    if schema_version != 1:
        raise PdfExportError(f"unsupported display-list schema: {schema_version!r}")
    revision = _string(layout.get("revision"), "revision")
    document = _mapping(layout.get("document"), "document")
    document_id = _string(document.get("id"), "document.id")
    title = _string(document.get("title"), "document.title")
    raw_pages = _sequence(layout.get("pages"), "pages")
    pages: list[_Page] = []
    for page_index, raw_page in enumerate(raw_pages):
        page = _mapping(raw_page, f"pages[{page_index}]")
        page_id = _string(page.get("id"), f"pages[{page_index}].id")
        width = _positive_number(page.get("width"), f"page {page_id} width")
        height = _positive_number(page.get("height"), f"page {page_id} height")
        raw_operations = _sequence(page.get("operations"), f"page {page_id} operations")
        operations = tuple(
            _normalise_operation(raw_operation, page_id, operation_index)
            for operation_index, raw_operation in enumerate(raw_operations)
        )
        pages.append(_Page(page_id, width, height, operations))
    if not pages:
        raise PdfExportError("a PDF export requires at least one page")
    return _Export(revision, document_id, title, tuple(pages))


def _normalise_operation(raw: object, page_id: str, index: int) -> _Operation:
    operation = _mapping(raw, f"page {page_id} operation {index}")
    kind = _string(operation.get("op"), f"page {page_id} operation {index}.op")
    object_id = _string(operation.get("object_id"), f"page {page_id} operation {index}.object_id")
    if kind == "text_placeholder":
        raise PdfExportError(
            f"object {object_id!r} is an unshaped text placeholder; PDF export refuses "
            "non-authoritative text"
        )
    if kind not in {"rectangle", "bezier_path"}:
        raise PdfExportError(f"object {object_id!r} uses unsupported PDF operation {kind!r}")
    return _Operation(kind, object_id, operation)


def _write_pdf(export: _Export, destination: Path) -> None:
    first = export.pages[0]
    canvas = Canvas(
        str(destination),
        pagesize=(first.width, first.height),
        pageCompression=1,
        invariant=1,
    )
    canvas.setCreator("PyDesign")
    canvas.setProducer("PyDesign ReportLab adapter")
    canvas.setTitle(export.title)
    for page in export.pages:
        canvas.setPageSize((page.width, page.height))
        canvas.saveState()
        canvas.translate(0, page.height)
        canvas.scale(1, -1)
        for operation in page.operations:
            if operation.kind == "rectangle":
                _draw_rectangle(canvas, operation)
            else:
                _draw_bezier(canvas, operation)
        canvas.restoreState()
        canvas.showPage()
    canvas.save()


def _draw_rectangle(canvas: Canvas, operation: _Operation) -> None:
    values = operation.values
    x = _number(values.get("x"), f"{operation.object_id}.x")
    y = _number(values.get("y"), f"{operation.object_id}.y")
    width = _number(values.get("width"), f"{operation.object_id}.width")
    height = _number(values.get("height"), f"{operation.object_id}.height")
    if width < 0 or height < 0:
        raise PdfExportError(f"rectangle {operation.object_id!r} has negative dimensions")
    fill, stroke = _apply_paint(canvas, operation)
    canvas.rect(x, y, width, height, stroke=int(stroke), fill=int(fill))


def _draw_bezier(canvas: Canvas, operation: _Operation) -> None:
    values = operation.values
    commands = _sequence(values.get("commands"), f"{operation.object_id}.commands")
    path = canvas.beginPath()
    for index, raw_command in enumerate(commands):
        command = _mapping(raw_command, f"{operation.object_id}.commands[{index}]")
        kind = _string(command.get("command"), f"{operation.object_id}.commands[{index}]")
        prefix = f"{operation.object_id}.commands[{index}]"
        if kind == "move":
            path.moveTo(
                _number(command.get("x"), f"{prefix}.x"), _number(command.get("y"), f"{prefix}.y")
            )
        elif kind == "line":
            path.lineTo(
                _number(command.get("x"), f"{prefix}.x"), _number(command.get("y"), f"{prefix}.y")
            )
        elif kind == "curve":
            path.curveTo(
                _number(command.get("control_1_x"), f"{prefix}.control_1_x"),
                _number(command.get("control_1_y"), f"{prefix}.control_1_y"),
                _number(command.get("control_2_x"), f"{prefix}.control_2_x"),
                _number(command.get("control_2_y"), f"{prefix}.control_2_y"),
                _number(command.get("x"), f"{prefix}.x"),
                _number(command.get("y"), f"{prefix}.y"),
            )
        elif kind == "close":
            path.close()
        else:
            raise PdfExportError(f"{prefix} has unsupported path command {kind!r}")
    fill, stroke = _apply_paint(canvas, operation)
    canvas.drawPath(path, stroke=int(stroke), fill=int(fill))


def _apply_paint(canvas: Canvas, operation: _Operation) -> tuple[bool, bool]:
    fill = _optional_colour(operation.values.get("fill"), f"{operation.object_id}.fill")
    stroke = _optional_colour(operation.values.get("stroke"), f"{operation.object_id}.stroke")
    stroke_width = _number(
        operation.values.get("stroke_width"), f"{operation.object_id}.stroke_width"
    )
    if stroke_width < 0:
        raise PdfExportError(f"object {operation.object_id!r} has negative stroke width")
    if fill is not None:
        canvas.setFillColor(fill)
    if stroke is not None:
        canvas.setStrokeColor(stroke)
        canvas.setLineWidth(stroke_width)
    return fill is not None, stroke is not None


def _inspect_pdf(path: Path, pages: tuple[_Page, ...]) -> None:
    try:
        with pikepdf.open(path) as document:
            if len(document.pages) != len(pages):
                raise PdfExportError(
                    f"writer produced {len(document.pages)} pages; expected {len(pages)}"
                )
            for expected, actual in zip(pages, document.pages, strict=True):
                media_box = tuple(float(value) for value in actual.MediaBox)
                width = media_box[2] - media_box[0]
                height = media_box[3] - media_box[1]
                if not math.isclose(width, expected.width, abs_tol=0.01) or not math.isclose(
                    height, expected.height, abs_tol=0.01
                ):
                    raise PdfExportError(
                        f"page {expected.id!r} MediaBox is {width:g} x {height:g}; "
                        f"expected {expected.width:g} x {expected.height:g}"
                    )
    except pikepdf.PdfError as error:
        raise PdfExportError(f"pikepdf could not reopen writer output: {error}") from error


def _write_manifest_temporary(manifest: PdfExportManifest, destination: Path) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    path = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(manifest.to_dict(), stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        return path
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PdfExportError(f"{label} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise PdfExportError(f"{label} keys must be strings")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise PdfExportError(f"{label} must be an array")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise PdfExportError(f"{label} must be a string")
    return value


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PdfExportError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise PdfExportError(f"{label} must be finite")
    return number


def _positive_number(value: object, label: str) -> float:
    number = _number(value, label)
    if number <= 0:
        raise PdfExportError(f"{label} must be positive")
    return number


def _optional_colour(value: object, label: str) -> Any | None:
    if value is None:
        return None
    colour = _string(value, label)
    try:
        return HexColor(colour)
    except ValueError as error:
        raise PdfExportError(f"{label} is not a supported hex colour: {colour!r}") from error
