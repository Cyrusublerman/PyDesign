from __future__ import annotations

import unittest

from pydesign import (
    BezierPath,
    CurveTo,
    Document,
    DocumentValidationError,
    MoveTo,
    Page,
    Rectangle,
    TextFrame,
    layout_document,
    mm,
    pt,
    validate_document,
)


def sample_document() -> Document:
    return Document(
        id="test-document",
        title="Test",
        pages=[
            Page(
                id="page-1",
                size=(210 * mm, 297 * mm),
                elements=[
                    Rectangle(
                        id="accent",
                        frame=(10 * mm, 12 * mm, 40 * mm, 4 * mm),
                        fill="#ff6600",
                    ),
                    BezierPath(
                        id="curve",
                        commands=(
                            MoveTo(10 * mm, 60 * mm),
                            CurveTo(
                                40 * mm,
                                30 * mm,
                                80 * mm,
                                90 * mm,
                                120 * mm,
                                60 * mm,
                            ),
                        ),
                        stroke="#5b32a3",
                    ),
                    TextFrame(
                        id="title",
                        frame=(10 * mm, 20 * mm, 150 * mm, 30 * mm),
                        text="Visible Python",
                        font_size=24 * pt,
                    ),
                ],
            )
        ],
    )


class ModelAndLayoutTests(unittest.TestCase):
    def test_model_normalises_lists_and_units(self) -> None:
        document = sample_document()
        self.assertIsInstance(document.pages, tuple)
        self.assertIsInstance(document.pages[0].elements, tuple)
        self.assertAlmostEqual(document.pages[0].size.width.to(mm), 210.0)

    def test_layout_is_renderer_neutral_and_serialisable(self) -> None:
        snapshot = layout_document(sample_document(), revision="abc123")
        data = snapshot.to_dict()
        self.assertEqual(data["revision"], "abc123")
        page = data["pages"][0]
        operations = page["operations"]
        self.assertEqual(
            [item["op"] for item in operations],
            ["rectangle", "bezier_path", "text_placeholder"],
        )
        self.assertEqual(operations[0]["object_id"], "accent")
        self.assertEqual(operations[1]["commands"][1]["command"], "curve")
        self.assertTrue(any(item.code == "PD-TEXT-001" for item in snapshot.diagnostics))

    def test_duplicate_ids_are_rejected(self) -> None:
        document = Document(
            id="duplicate",
            pages=[Page(id="duplicate", size=(100, 100))],
        )
        with self.assertRaises(DocumentValidationError) as caught:
            validate_document(document)
        self.assertIn("Duplicate stable ID", str(caught.exception))

    def test_negative_frame_is_rejected(self) -> None:
        document = Document(
            id="document",
            pages=[
                Page(
                    id="page",
                    size=(100, 100),
                    elements=[Rectangle(id="bad", frame=(0, 0, -1, 10))],
                )
            ],
        )
        with self.assertRaises(DocumentValidationError):
            validate_document(document)

    def test_path_must_begin_with_move(self) -> None:
        document = Document(
            id="document",
            pages=[
                Page(
                    id="page",
                    size=(100, 100),
                    elements=[BezierPath(id="bad-path", commands=[CurveTo(0, 0, 1, 1, 2, 2)])],
                )
            ],
        )
        with self.assertRaises(DocumentValidationError) as caught:
            validate_document(document)
        self.assertIn("must begin with MoveTo", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
