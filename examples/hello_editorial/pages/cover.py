from pydesign import BezierPath, BuildContext, CurveTo, MoveTo, Page, Rectangle, TextFrame, mm, pt


def page(_ctx: BuildContext) -> Page:
    return Page(
        id="cover",
        size=(210 * mm, 297 * mm),
        elements=[
            Rectangle(
                id="cover-accent",
                frame=(18 * mm, 18 * mm, 5 * mm, 261 * mm),
                fill="#e66f3d",
            ),
            BezierPath(
                id="cover-curve",
                commands=(
                    MoveTo(34 * mm, 205 * mm),
                    CurveTo(
                        70 * mm,
                        175 * mm,
                        120 * mm,
                        235 * mm,
                        176 * mm,
                        198 * mm,
                    ),
                ),
                stroke="#8d62d9",
                stroke_width=1.2 * pt,
            ),
            TextFrame(
                id="cover-title",
                frame=(34 * mm, 34 * mm, 152 * mm, 90 * mm),
                text="PYDESIGN\nVISIBLE PYTHON,\nPRINTED PAGES",
                font_size=30 * pt,
                colour="#18202a",
            ),
            TextFrame(
                id="cover-deck",
                frame=(35 * mm, 230 * mm, 120 * mm, 28 * mm),
                text="An offline editorial studio built from readable Python.",
                font_size=11 * pt,
                colour="#46515d",
            ),
        ],
    )
