from pydesign import BuildContext, Layer, Page, Rectangle, TextFrame, mm, pt


def page(_ctx: BuildContext) -> Page:
    return Page(
        id="principles",
        size=(210 * mm, 297 * mm),
        layers=[
            Layer(
                id="principles-content",
                elements=[
                    TextFrame(
                        id="principles-title",
                        frame=(18 * mm, 20 * mm, 174 * mm, 30 * mm),
                        text="Three principles",
                        font_size=26 * pt,
                    ),
                    Rectangle(
                        id="principles-rule",
                        frame=(18 * mm, 56 * mm, 174 * mm, 0.7 * mm),
                        fill="#e66f3d",
                    ),
                    TextFrame(
                        id="principles-copy",
                        frame=(18 * mm, 70 * mm, 174 * mm, 180 * mm),
                        text=(
                            "1  Python remains visible.\n\n"
                            "2  Canvas and output share one layout.\n\n"
                            "3  Authoring and proofing work offline."
                        ),
                        font_size=15 * pt,
                        colour="#18202a",
                    ),
                ],
            )
        ],
    )
