"""Exact font-file identity and OpenType metadata inspection."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

from fontTools.ttLib import TTFont, TTLibError


class FontValidationError(ValueError):
    pass


class FontChangedError(FontValidationError):
    pass


@dataclass(frozen=True, slots=True)
class FontFingerprint:
    file_sha256: str
    face_index: int
    variations: tuple[tuple[str, float], ...] = ()
    synthetic_bold: float = 0.0
    synthetic_slant: float = 0.0

    @property
    def instance_sha256(self) -> str:
        payload = json.dumps(
            {
                "file_sha256": self.file_sha256,
                "face_index": self.face_index,
                "variations": self.variations,
                "synthetic_bold": self.synthetic_bold,
                "synthetic_slant": self.synthetic_slant,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("ascii")).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "file_sha256": self.file_sha256,
            "instance_sha256": self.instance_sha256,
            "face_index": self.face_index,
            "variations": dict(self.variations),
            "synthetic_bold": self.synthetic_bold,
            "synthetic_slant": self.synthetic_slant,
        }


@dataclass(frozen=True, slots=True)
class FontAxis:
    tag: str
    minimum: float
    default: float
    maximum: float
    name: str | None
    hidden: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "tag": self.tag,
            "minimum": self.minimum,
            "default": self.default,
            "maximum": self.maximum,
            "name": self.name,
            "hidden": self.hidden,
        }


@dataclass(frozen=True, slots=True)
class EmbeddingPermissions:
    fs_type: int
    restricted: bool
    preview_and_print: bool
    editable: bool
    no_subsetting: bool
    bitmap_only: bool

    @property
    def installable(self) -> bool:
        return not (self.restricted or self.preview_and_print or self.editable)

    @property
    def may_embed_outlines(self) -> bool:
        return not self.restricted and not self.bitmap_only

    def to_dict(self) -> dict[str, object]:
        return {
            "fs_type": self.fs_type,
            "installable": self.installable,
            "restricted": self.restricted,
            "preview_and_print": self.preview_and_print,
            "editable": self.editable,
            "no_subsetting": self.no_subsetting,
            "bitmap_only": self.bitmap_only,
            "may_embed_outlines": self.may_embed_outlines,
        }


@dataclass(frozen=True, slots=True)
class FontMetadata:
    family: str | None
    subfamily: str | None
    full_name: str | None
    postscript_name: str | None
    units_per_em: int
    glyph_count: int
    axes: tuple[FontAxis, ...]
    embedding: EmbeddingPermissions
    table_tags: tuple[str, ...]

    def axis(self, tag: str) -> FontAxis | None:
        return next((axis for axis in self.axes if axis.tag == tag), None)

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "subfamily": self.subfamily,
            "full_name": self.full_name,
            "postscript_name": self.postscript_name,
            "units_per_em": self.units_per_em,
            "glyph_count": self.glyph_count,
            "axes": [axis.to_dict() for axis in self.axes],
            "embedding": self.embedding.to_dict(),
            "table_tags": list(self.table_tags),
        }


@dataclass(frozen=True, slots=True)
class FontFace:
    path: Path
    fingerprint: FontFingerprint
    metadata: FontMetadata

    def verify_unchanged(self) -> None:
        current = _sha256_file(self.path)
        if current != self.fingerprint.file_sha256:
            raise FontChangedError(
                f"font file changed since it was resolved: {self.path}; expected "
                f"{self.fingerprint.file_sha256}, found {current}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "fingerprint": self.fingerprint.to_dict(),
            "metadata": self.metadata.to_dict(),
        }


def load_font_face(
    path: str | Path,
    *,
    face_index: int = 0,
    variations: dict[str, float] | None = None,
    synthetic_bold: float = 0.0,
    synthetic_slant: float = 0.0,
) -> FontFace:
    font_path = Path(path).expanduser().resolve()
    if face_index < 0:
        raise FontValidationError("face_index must be non-negative")
    if not font_path.is_file():
        raise FontValidationError(f"font file does not exist: {font_path}")
    if not math.isfinite(synthetic_bold) or synthetic_bold < 0:
        raise FontValidationError("synthetic_bold must be a finite non-negative value")
    if not math.isfinite(synthetic_slant):
        raise FontValidationError("synthetic_slant must be finite")

    try:
        with _open_ttfont(font_path, face_index) as font:
            axes = _read_axes(font)
            normalized_variations = _validate_variations(variations or {}, axes)
            metadata = FontMetadata(
                family=_debug_name(font, 1),
                subfamily=_debug_name(font, 2),
                full_name=_debug_name(font, 4),
                postscript_name=_debug_name(font, 6),
                units_per_em=int(font["head"].unitsPerEm),
                glyph_count=len(font.getGlyphOrder()),
                axes=axes,
                embedding=_embedding_permissions(font),
                table_tags=_table_tags(font),
            )
    except (OSError, TTLibError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, FontValidationError):
            raise
        raise FontValidationError(f"cannot inspect font {font_path}: {error}") from error

    fingerprint = FontFingerprint(
        file_sha256=_sha256_file(font_path),
        face_index=face_index,
        variations=normalized_variations,
        synthetic_bold=float(synthetic_bold),
        synthetic_slant=float(synthetic_slant),
    )
    return FontFace(font_path, fingerprint, metadata)


class _TTFontContext:
    def __init__(self, font: TTFont) -> None:
        self.font = font

    def __enter__(self) -> TTFont:
        return self.font

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.font.close()


def _open_ttfont(path: Path, face_index: int) -> _TTFontContext:
    return _TTFontContext(TTFont(path, fontNumber=face_index, lazy=True))


def _debug_name(font: TTFont, name_id: int) -> str | None:
    name = font["name"].getDebugName(name_id)
    return str(name) if name is not None else None


def _table_tags(font: TTFont) -> tuple[str, ...]:
    tags = font.keys()
    return tuple(sorted(str(tag) for tag in tags if tag != "GlyphOrder"))


def _read_axes(font: TTFont) -> tuple[FontAxis, ...]:
    if "fvar" not in font:
        return ()
    axes: list[FontAxis] = []
    for raw_axis in font["fvar"].axes:
        tag = str(raw_axis.axisTag)
        axes.append(
            FontAxis(
                tag=tag,
                minimum=float(raw_axis.minValue),
                default=float(raw_axis.defaultValue),
                maximum=float(raw_axis.maxValue),
                name=_debug_name(font, int(raw_axis.axisNameID)),
                hidden=bool(int(raw_axis.flags) & 0x0001),
            )
        )
    return tuple(axes)


def _validate_variations(
    variations: dict[str, float], axes: tuple[FontAxis, ...]
) -> tuple[tuple[str, float], ...]:
    available = {axis.tag: axis for axis in axes}
    normalized: list[tuple[str, float]] = []
    for tag, raw_value in sorted(variations.items()):
        if len(tag) != 4 or not tag.isascii():
            raise FontValidationError(f"variation axis tag must be four ASCII characters: {tag!r}")
        axis = available.get(tag)
        if axis is None:
            raise FontValidationError(f"font does not provide variation axis {tag!r}")
        value = float(raw_value)
        if not math.isfinite(value) or not axis.minimum <= value <= axis.maximum:
            raise FontValidationError(
                f"variation {tag!r} must be between {axis.minimum:g} and {axis.maximum:g}"
            )
        normalized.append((tag, value))
    return tuple(normalized)


def _embedding_permissions(font: TTFont) -> EmbeddingPermissions:
    os2: Any = font.get("OS/2")
    fs_type = int(getattr(os2, "fsType", 0))
    return EmbeddingPermissions(
        fs_type=fs_type,
        restricted=bool(fs_type & 0x0002),
        preview_and_print=bool(fs_type & 0x0004),
        editable=bool(fs_type & 0x0008),
        no_subsetting=bool(fs_type & 0x0100),
        bitmap_only=bool(fs_type & 0x0200),
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
