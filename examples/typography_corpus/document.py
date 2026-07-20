"""Multilingual typography corpus: project fonts, LTR / mixed / RTL frames."""

from __future__ import annotations

from pydesign import BuildContext, Document, Guide, Layer, Page, TextFrame, mm, pt


def build(ctx: BuildContext) -> Document:
    font = str((ctx.root / "assets/fonts/DejaVuSans.ttf").resolve())
    return Document(
        id="typography-corpus",
        title="Typography Corpus",
        pages=[
            Page(
                id="corpus-1",
                size=(210 * mm, 297 * mm),
                guides=(Guide("vertical", 18 * mm), Guide("horizontal", 20 * mm)),
                page_label="i",
                section_id="corpus",
                layers=[
                    Layer(
                        id="corpus-1-text",
                        elements=[
                            TextFrame(
                                id="ltr-hello",
                                frame=(18 * mm, 20 * mm, 174 * mm, 14 * mm),
                                text="Hello office",
                                font_size=12 * pt,
                                font=font,
                            ),
                            TextFrame(
                                id="mixed-hello",
                                frame=(18 * mm, 40 * mm, 174 * mm, 14 * mm),
                                text="Hello سلام",
                                font_size=14 * pt,
                                font=font,
                            ),
                            TextFrame(
                                id="rtl-arabic",
                                frame=(18 * mm, 60 * mm, 174 * mm, 14 * mm),
                                text="سلام",
                                font_size=14 * pt,
                                font=font,
                            ),
                            TextFrame(
                                id="flow-overset",
                                frame=(18 * mm, 90 * mm, 35 * mm, 16 * mm),
                                text=(
                                    "Linked flow overset probe: this paragraph is deliberately "
                                    "longer than the narrow short frame so layout records overset "
                                    "and emits PD-TEXT-003 for unplaced story text."
                                ),
                                font_size=11 * pt,
                                font=font,
                            ),
                        ],
                    )
                ],
            )
        ],
    )
