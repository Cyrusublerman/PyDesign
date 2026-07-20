"""32-page magazine fixture for Stage 5 editorial exit checks."""

from __future__ import annotations

from pydesign import (
    BuildContext,
    CharacterStyle,
    Document,
    Guide,
    Layer,
    Page,
    Rectangle,
    TextFrame,
    mm,
    pt,
)
from pydesign.components import ComponentDefinition, ComponentInstance, instantiate
from pydesign.model import LeafElement
from pydesign.styles import resolve_character_style


def _folio_component(overrides: dict[str, object]) -> tuple[LeafElement, ...]:
    number = int(overrides["number"])  # type: ignore[arg-type]
    font = str(overrides["font"])
    return (
        TextFrame(
            id=f"mag-{number:02d}-folio",
            frame=(18 * mm, 280 * mm, 40 * mm, 10 * mm),
            text=str(number),
            font_size=10 * pt,
            font=font,
        ),
    )


FOLIO = ComponentDefinition(id="folio", generator=_folio_component)


def _page(index: int, font: str, styles: dict[str, CharacterStyle]) -> Page:
    number = index + 1
    title = resolve_character_style(styles, "title")
    body = resolve_character_style(styles, "body")
    folio = instantiate(
        FOLIO,
        ComponentInstance(
            id=f"mag-{number:02d}-folio-instance",
            definition_id="folio",
            overrides={"number": number, "font": font},
        ),
    )
    story = (
        f"Section {number} lead. Reusable styles and a folio component keep the "
        f"32-page magazine fixture authorable without hidden document state. "
        * (3 if number == 1 else 1)
    )
    return Page(
        id=f"mag-{number:02d}",
        size=(210 * mm, 297 * mm),
        page_label=str(number),
        section_id="features" if number <= 16 else "backmatter",
        guides=(Guide("vertical", 18 * mm), Guide("vertical", 192 * mm)),
        layers=[
            Layer(
                id=f"mag-{number:02d}-content",
                elements=[
                    *folio,
                    TextFrame(
                        id=f"mag-{number:02d}-title",
                        frame=(18 * mm, 20 * mm, 174 * mm, 24 * mm),
                        text=f"Section {number}",
                        font_size=title.font_size or 22 * pt,
                        colour=title.colour or "#111111",
                        font=font,
                    ),
                    Rectangle(
                        id=f"mag-{number:02d}-rule",
                        frame=(18 * mm, 48 * mm, 174 * mm, 0.5 * mm),
                        fill="#e66f3d",
                    ),
                    TextFrame(
                        id=f"mag-{number:02d}-body",
                        frame=(18 * mm, 56 * mm, 174 * mm, 200 * mm if number > 1 else 40 * mm),
                        text=story,
                        font_size=body.font_size or 11 * pt,
                        colour=body.colour or "#222222",
                        font=font,
                    ),
                ],
            )
        ],
    )


def build(ctx: BuildContext) -> Document:
    packaged = ctx.root / "assets" / "fonts" / "DejaVuSans.ttf"
    corpus = (
        ctx.root.parent / "typography_corpus" / "assets" / "fonts" / "DejaVuSans.ttf"
    ).resolve()
    font_path = packaged if packaged.is_file() else corpus
    font = str(font_path.resolve())
    styles = {
        "body": CharacterStyle(id="body", font_size=11 * pt, colour="#222222", font=font),
        "title": CharacterStyle(
            id="title",
            font_size=22 * pt,
            colour="#111111",
            font=font,
            based_on="body",
        ),
    }
    return Document(
        id="magazine-32",
        title="Magazine 32",
        pages=[_page(index, font, styles) for index in range(32)],
    )
