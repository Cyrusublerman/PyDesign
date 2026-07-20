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
from reportlab.lib.utils import ImageReader
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
    profile: str = "vector"
    waivers: tuple[str, ...] = ()

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
            "profile": self.profile,
            "waivers": list(self.waivers),
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


_SUPPORTED_DRAW = frozenset({"rectangle", "ellipse", "bezier_path", "glyph_run", "image"})
_SKIP_KINDS = frozenset({"guide"})


def export_layout_pdf(
    layout: LayoutSnapshot | Mapping[str, object],
    destination: str | Path,
    *,
    manifest_path: str | Path | None = None,
    profile: str = "vector",
    asset_root: str | Path | None = None,
    waivers: Sequence[str] = (),
) -> PdfExportManifest:
    """Validate, write, reopen and atomically publish a vector PDF."""
    export = _normalise_export(layout.to_dict() if isinstance(layout, LayoutSnapshot) else layout)
    output = Path(destination).expanduser().resolve()
    root = None if asset_root is None else Path(asset_root).expanduser().resolve()
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
        _write_pdf(export, temporary, asset_root=root, profile=profile)
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
            profile=profile,
            waivers=tuple(waivers),
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
        normalised: list[_Operation] = []
        for operation_index, raw_operation in enumerate(raw_operations):
            operation = _normalise_operation(raw_operation, page_id, operation_index)
            if operation is not None:
                normalised.append(operation)
        operations = tuple(normalised)
        pages.append(_Page(page_id, width, height, operations))
    if not pages:
        raise PdfExportError("a PDF export requires at least one page")
    return _Export(revision, document_id, title, tuple(pages))


def _normalise_operation(raw: object, page_id: str, index: int) -> _Operation | None:
    operation = _mapping(raw, f"page {page_id} operation {index}")
    kind = _string(operation.get("op"), f"page {page_id} operation {index}.op")
    object_id = _string(operation.get("object_id"), f"page {page_id} operation {index}.object_id")
    if kind in _SKIP_KINDS:
        return None
    if kind == "text_placeholder":
        raise PdfExportError(
            f"object {object_id!r} is an unshaped text placeholder; PDF export refuses "
            "non-authoritative text"
        )
    if kind not in _SUPPORTED_DRAW:
        raise PdfExportError(f"object {object_id!r} uses unsupported PDF operation {kind!r}")
    return _Operation(kind, object_id, operation)


def _write_pdf(
    export: _Export,
    destination: Path,
    *,
    asset_root: Path | None,
    profile: str,
) -> None:
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
    if profile == "pdfx4":
        canvas.setAuthor("PyDesign PDF/X-4")
    for page in export.pages:
        canvas.setPageSize((page.width, page.height))
        canvas.saveState()
        canvas.translate(0, page.height)
        canvas.scale(1, -1)
        for operation in page.operations:
            if operation.kind == "rectangle":
                _draw_rectangle(canvas, operation)
            elif operation.kind == "ellipse":
                _draw_ellipse(canvas, operation)
            elif operation.kind == "bezier_path":
                _draw_bezier(canvas, operation)
            elif operation.kind == "image":
                _draw_image(canvas, operation, asset_root=asset_root)
            else:
                _draw_glyph_run(canvas, operation, asset_root=asset_root)
        canvas.restoreState()
        canvas.showPage()
    canvas.save()
    if profile == "pdfx4":
        _stamp_pdfx4_boxes(destination, export.pages)


def _stamp_pdfx4_boxes(destination: Path, pages: Sequence[_Page]) -> None:
    with pikepdf.open(destination, allow_overwriting_input=True) as pdf:
        for index, page in enumerate(pdf.pages):
            summary = pages[index]
            box = pikepdf.Array([0, 0, summary.width, summary.height])
            page.MediaBox = box
            page.TrimBox = box
            page.BleedBox = box
            page.CropBox = box
        with pdf.open_metadata() as meta:
            meta["xmp:CreatorTool"] = "PyDesign"
            meta["pdf:Producer"] = "PyDesign PDF/X-4 profile"
        pdf.save(destination)


def _draw_glyph_run(canvas: Canvas, operation: _Operation, *, asset_root: Path | None) -> None:
    values = operation.values
    colour = _optional_colour(values.get("colour"), f"{operation.object_id}.colour")
    if colour is not None:
        canvas.setFillColor(colour)
    font_value = values.get("font")
    text = str(values.get("text", ""))
    if isinstance(font_value, str) and font_value.strip() and text:
        resolved = _resolve_asset(font_value, asset_root)
        if resolved is not None and resolved.is_file():
            try:
                from pydesign.pdf.subset import register_subset_face

                face_name = f"PDSub_{hashlib.sha1(font_value.encode()).hexdigest()[:12]}"
                register_subset_face(resolved, text=text, face_name=face_name)
                x = _number(values.get("x"), f"{operation.object_id}.x")
                y = _number(values.get("y"), f"{operation.object_id}.y")
                size = _number(values.get("font_size"), f"{operation.object_id}.font_size")
                canvas.saveState()
                canvas.scale(1, -1)
                canvas.setFont(face_name, max(1.0, size))
                canvas.drawString(x, -y - size, text)
                canvas.restoreState()
                return
            except (OSError, ValueError, KeyError):
                pass
    outlines = values.get("outlines")
    if isinstance(outlines, list) and outlines:
        path = canvas.beginPath()
        for outline in outlines:
            if not isinstance(outline, Mapping):
                continue
            commands = outline.get("commands")
            if not isinstance(commands, Sequence):
                continue
            for raw_command in commands:
                if not isinstance(raw_command, Mapping):
                    continue
                kind = str(raw_command.get("command", ""))
                if kind == "move":
                    path.moveTo(float(raw_command.get("x", 0.0)), float(raw_command.get("y", 0.0)))
                elif kind == "line":
                    path.lineTo(float(raw_command.get("x", 0.0)), float(raw_command.get("y", 0.0)))
                elif kind == "close":
                    path.close()
        canvas.drawPath(path, stroke=0, fill=1)
        return
    x = _number(values.get("x"), f"{operation.object_id}.x")
    y = _number(values.get("y"), f"{operation.object_id}.y")
    size = _number(values.get("font_size"), f"{operation.object_id}.font_size")
    canvas.saveState()
    canvas.scale(1, -1)
    canvas.setFont("Helvetica", max(1.0, size))
    canvas.drawString(x, -y - size, text)
    canvas.restoreState()


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


def _draw_ellipse(canvas: Canvas, operation: _Operation) -> None:
    values = operation.values
    x = _number(values.get("x"), f"{operation.object_id}.x")
    y = _number(values.get("y"), f"{operation.object_id}.y")
    width = _number(values.get("width"), f"{operation.object_id}.width")
    height = _number(values.get("height"), f"{operation.object_id}.height")
    if width < 0 or height < 0:
        raise PdfExportError(f"ellipse {operation.object_id!r} has negative dimensions")
    fill, stroke = _apply_paint(canvas, operation)
    canvas.ellipse(x, y, x + width, y + height, stroke=int(stroke), fill=int(fill))


def _draw_image(canvas: Canvas, operation: _Operation, *, asset_root: Path | None) -> None:
    values = operation.values
    path_value = _string(values.get("path"), f"{operation.object_id}.path")
    resolved = _resolve_asset(path_value, asset_root)
    if resolved is None or not resolved.is_file():
        raise PdfExportError(f"image {operation.object_id!r} path missing: {path_value}")
    expected = values.get("content_sha256")
    digest = _sha256(resolved)
    if isinstance(expected, str) and expected and expected != digest:
        raise PdfExportError(
            f"image {operation.object_id!r} content hash mismatch; refusing stale export"
        )
    x = _number(values.get("x"), f"{operation.object_id}.x")
    y = _number(values.get("y"), f"{operation.object_id}.y")
    width = _number(values.get("width"), f"{operation.object_id}.width")
    height = _number(values.get("height"), f"{operation.object_id}.height")
    canvas.saveState()
    canvas.translate(x, y + height)
    canvas.scale(1, -1)
    canvas.drawImage(
        ImageReader(str(resolved)),
        0,
        0,
        width=width,
        height=height,
        preserveAspectRatio=False,
        mask="auto",
    )
    canvas.restoreState()


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


def _resolve_asset(relative: str, asset_root: Path | None) -> Path | None:
    candidate = Path(relative)
    if candidate.is_file():
        return candidate.resolve()
    if asset_root is None:
        return None
    joined = (asset_root / relative).resolve()
    return joined if joined.is_file() else None


def _inspect_pdf(path: Path, pages: Sequence[_Page]) -> None:
    with pikepdf.open(path) as pdf:
        if len(pdf.pages) != len(pages):
            raise PdfExportError(
                f"PDF page count {len(pdf.pages)} does not match layout {len(pages)}"
            )


def _write_manifest_temporary(manifest: PdfExportManifest, destination: Path) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp.json", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return temporary


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PdfExportError(f"{label} must be an object")
    return value


def _sequence(value: object, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise PdfExportError(f"{label} must be an array")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PdfExportError(f"{label} must be a non-empty string")
    return value


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PdfExportError(f"{label} must be a number")
    if not math.isfinite(float(value)):
        raise PdfExportError(f"{label} must be finite")
    return float(value)


def _positive_number(value: object, label: str) -> float:
    number = _number(value, label)
    if number <= 0:
        raise PdfExportError(f"{label} must be positive")
    return number


def _optional_colour(value: object, label: str) -> HexColor | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PdfExportError(f"{label} must be a hex colour string or null")
    try:
        return HexColor(value)
    except Exception as error:
        raise PdfExportError(f"{label} is not a valid colour: {value!r}") from error
