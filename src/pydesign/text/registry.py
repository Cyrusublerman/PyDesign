"""Deterministic explicit font registry and cluster-safe fallback shaping."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from importlib import import_module
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

from fontTools.ttLib import TTFont, TTLibError

from pydesign.text.font import FontFace, FontValidationError, load_font_face
from pydesign.text.glyphrun import GlyphRun, TextDirection
from pydesign.text.shaping import shape_text

type FontOrigin = Literal["project", "system"]


class FontRegistryError(ValueError):
    pass


class MissingGlyphError(FontRegistryError):
    def __init__(self, cluster: str, source_index: int, aliases: tuple[str, ...]) -> None:
        self.cluster = cluster
        self.source_index = source_index
        self.aliases = aliases
        codepoints = " ".join(f"U+{ord(character):04X}" for character in cluster)
        super().__init__(
            f"no registered font covers cluster {cluster!r} ({codepoints}) at "
            f"source index {source_index}; tried {', '.join(aliases)}"
        )


@dataclass(frozen=True, slots=True)
class RegisteredFont:
    alias: str
    origin: FontOrigin
    face: FontFace
    coverage: frozenset[int]

    def covers(self, cluster: str) -> bool:
        required = {
            ord(character)
            for character in cluster
            if unicodedata.category(character) not in {"Cc", "Cf"}
        }
        return required.issubset(self.coverage)


class FontRegistry:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self._fonts: dict[str, RegisteredFont] = {}

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(self._fonts)

    def register_project(
        self,
        alias: str,
        path: str | Path,
        *,
        face_index: int = 0,
        variations: dict[str, float] | None = None,
    ) -> RegisteredFont:
        candidate = (self.project_root / path).resolve()
        try:
            candidate.relative_to(self.project_root)
        except ValueError as error:
            raise FontRegistryError(f"project font leaves project root: {candidate}") from error
        return self._register(
            alias,
            "project",
            load_font_face(candidate, face_index=face_index, variations=variations),
        )

    def register_system(
        self,
        alias: str,
        path: str | Path,
        *,
        expected_sha256: str,
        face_index: int = 0,
        variations: dict[str, float] | None = None,
    ) -> RegisteredFont:
        face = load_font_face(path, face_index=face_index, variations=variations)
        if face.fingerprint.file_sha256 != expected_sha256:
            raise FontRegistryError(
                f"system font fingerprint mismatch for {alias!r}: expected {expected_sha256}, "
                f"found {face.fingerprint.file_sha256}"
            )
        return self._register(alias, "system", face)

    def require(self, alias: str) -> RegisteredFont:
        try:
            return self._fonts[alias]
        except KeyError as error:
            raise FontRegistryError(f"font alias is not registered: {alias!r}") from error

    def resolve_cluster(
        self, cluster: str, *, preferred: str, fallback: tuple[str, ...] = ()
    ) -> RegisteredFont:
        aliases = (preferred, *fallback)
        for alias in aliases:
            font = self.require(alias)
            if font.covers(cluster):
                return font
        raise MissingGlyphError(cluster, 0, aliases)

    def _register(self, alias: str, origin: FontOrigin, face: FontFace) -> RegisteredFont:
        if not alias or alias in self._fonts:
            raise FontRegistryError(f"font alias must be non-empty and unique: {alias!r}")
        registered = RegisteredFont(alias, origin, face, _coverage(face))
        self._fonts[alias] = registered
        return registered


def shape_with_fallback(
    registry: FontRegistry,
    text: str,
    *,
    preferred: str,
    fallback: tuple[str, ...] = (),
    font_size: float,
    direction: TextDirection | None = None,
    script: str | None = None,
    language: str | None = None,
    features: dict[str, int | bool] | None = None,
    source_start: int = 0,
) -> tuple[GlyphRun, ...]:
    """Choose one exact face per grapheme cluster, then shape adjacent face runs."""

    clusters = grapheme_clusters(text)
    if not clusters:
        font = registry.require(preferred)
        return (
            shape_text(
                font.face,
                "",
                font_size=font_size,
                direction=direction,
                script=script,
                language=language,
                features=features,
                source_start=source_start,
            ),
        )
    resolved: list[tuple[int, int, RegisteredFont]] = []
    aliases = (preferred, *fallback)
    for start, end in clusters:
        cluster = text[start:end]
        try:
            font = registry.resolve_cluster(cluster, preferred=preferred, fallback=fallback)
        except MissingGlyphError as error:
            raise MissingGlyphError(cluster, source_start + start, aliases) from error
        resolved.append((start, end, font))

    runs: list[GlyphRun] = []
    run_start, run_end, run_font = resolved[0]
    for cluster_start, cluster_end, font in resolved[1:]:
        if font.alias == run_font.alias:
            run_end = cluster_end
            continue
        runs.append(
            _shape_registry_run(
                run_font,
                text[run_start:run_end],
                source_start + run_start,
                font_size,
                direction,
                script,
                language,
                features,
            )
        )
        run_start, run_end, run_font = cluster_start, cluster_end, font
    runs.append(
        _shape_registry_run(
            run_font,
            text[run_start:run_end],
            source_start + run_start,
            font_size,
            direction,
            script,
            language,
            features,
        )
    )
    return tuple(runs)


def grapheme_clusters(text: str) -> tuple[tuple[int, int], ...]:
    """Return ICU extended graphemes when available, with a conservative fallback."""

    try:
        icu: Any = import_module("icu")
    except ImportError:
        return _conservative_clusters(text)
    iterator = icu.BreakIterator.createCharacterInstance(icu.Locale.getRoot())
    iterator.setText(text)
    utf16_map = _utf16_map(text)
    boundaries = [0]
    iterator.first()
    while True:
        raw = int(iterator.nextBoundary())
        if raw == int(icu.BreakIterator.DONE):
            break
        mapped = utf16_map.get(raw)
        if mapped is None:
            raise FontRegistryError(f"ICU returned an invalid grapheme offset: {raw}")
        boundaries.append(mapped)
    return tuple(pairwise(boundaries))


def _shape_registry_run(
    font: RegisteredFont,
    text: str,
    source_start: int,
    font_size: float,
    direction: TextDirection | None,
    script: str | None,
    language: str | None,
    features: dict[str, int | bool] | None,
) -> GlyphRun:
    return shape_text(
        font.face,
        text,
        font_size=font_size,
        direction=direction,
        script=script,
        language=language,
        features=features,
        source_start=source_start,
    )


def _coverage(face: FontFace) -> frozenset[int]:
    try:
        with TTFont(face.path, fontNumber=face.fingerprint.face_index, lazy=True) as font:
            cmap = font.getBestCmap() or {}
            return frozenset(int(codepoint) for codepoint in cmap)
    except (OSError, KeyError, TTLibError, TypeError, ValueError) as error:
        raise FontValidationError(f"cannot read font coverage for {face.path}: {error}") from error


def _conservative_clusters(text: str) -> tuple[tuple[int, int], ...]:
    if not text:
        return ()
    result: list[tuple[int, int]] = []
    start = 0
    join_next = False
    for index in range(1, len(text)):
        current = text[index]
        previous = text[index - 1]
        if (
            unicodedata.combining(current)
            or current in {"\ufe0e", "\ufe0f"}
            or previous == "\u200d"
            or current == "\u200d"
            or join_next
        ):
            join_next = current == "\u200d"
            continue
        result.append((start, index))
        start = index
        join_next = False
    result.append((start, len(text)))
    return tuple(result)


def _utf16_map(text: str) -> dict[int, int]:
    result = {0: 0}
    units = 0
    for index, character in enumerate(text, start=1):
        units += len(character.encode("utf-16-le")) // 2
        result[units] = index
    return result
