"""Character and paragraph style value objects (Stage 5)."""

from __future__ import annotations

from dataclasses import dataclass

from pydesign.units import Length, LengthLike, as_length


class StyleError(ValueError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CharacterStyle:
    id: str
    font_size: Length | None = None
    colour: str | None = None
    font: str | None = None
    based_on: str | None = None

    def __init__(
        self,
        *,
        id: str,
        font_size: LengthLike | None = None,
        colour: str | None = None,
        font: str | None = None,
        based_on: str | None = None,
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "font_size", None if font_size is None else as_length(font_size))
        object.__setattr__(self, "colour", colour)
        object.__setattr__(self, "font", font)
        object.__setattr__(self, "based_on", based_on)


@dataclass(frozen=True, slots=True, kw_only=True)
class ParagraphStyle:
    id: str
    character_style: str | None = None
    leading: Length | None = None
    based_on: str | None = None

    def __init__(
        self,
        *,
        id: str,
        character_style: str | None = None,
        leading: LengthLike | None = None,
        based_on: str | None = None,
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "character_style", character_style)
        object.__setattr__(self, "leading", None if leading is None else as_length(leading))
        object.__setattr__(self, "based_on", based_on)


def detect_style_cycle(styles: dict[str, CharacterStyle | ParagraphStyle], start_id: str) -> None:
    seen: set[str] = set()
    current: str | None = start_id
    while current is not None:
        if current in seen:
            raise StyleError(f"style inheritance cycle involving {start_id!r}")
        seen.add(current)
        style = styles.get(current)
        current = None if style is None else style.based_on


@dataclass(frozen=True, slots=True)
class ResolvedCharacter:
    font_size: Length | None
    colour: str | None
    font: str | None
    provenance: tuple[str, ...]


def resolve_character_style(
    styles: dict[str, CharacterStyle],
    style_id: str,
) -> ResolvedCharacter:
    detect_style_cycle(styles, style_id)  # type: ignore[arg-type]
    chain: list[str] = []
    font_size: Length | None = None
    colour: str | None = None
    font: str | None = None
    current: str | None = style_id
    while current is not None:
        style = styles.get(current)
        if style is None:
            raise StyleError(f"unknown character style {current!r}")
        chain.append(current)
        if font_size is None and style.font_size is not None:
            font_size = style.font_size
        if colour is None and style.colour is not None:
            colour = style.colour
        if font is None and style.font is not None:
            font = style.font
        current = style.based_on
    return ResolvedCharacter(font_size, colour, font, tuple(chain))
