from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import pikepdf
    import reportlab

    from pydesign.pdf import PdfExportError, export_layout_pdf
except ImportError:
    pikepdf = None  # type: ignore[assignment]
    reportlab = None  # type: ignore[assignment]


def vector_layout() -> dict[str, object]:
    return {
        "schema_version": 1,
        "revision": "revision-123",
        "document": {"id": "document", "title": "Vector proof"},
        "diagnostics": [],
        "pages": [
            {
                "id": "page-1",
                "width": 200.0,
                "height": 300.0,
                "operations": [
                    {
                        "op": "rectangle",
                        "object_id": "accent",
                        "x": 10.0,
                        "y": 15.0,
                        "width": 80.0,
                        "height": 20.0,
                        "fill": "#ff6600",
                        "stroke": "#222222",
                        "stroke_width": 1.0,
                    },
                    {
                        "op": "bezier_path",
                        "object_id": "curve",
                        "commands": [
                            {"command": "move", "x": 15.0, "y": 100.0},
                            {
                                "command": "curve",
                                "control_1_x": 45.0,
                                "control_1_y": 60.0,
                                "control_2_x": 100.0,
                                "control_2_y": 140.0,
                                "x": 160.0,
                                "y": 100.0,
                            },
                        ],
                        "fill": None,
                        "stroke": "#5b32a3",
                        "stroke_width": 2.0,
                    },
                ],
            }
        ],
    }


@unittest.skipUnless(
    pikepdf is not None and reportlab is not None, "PDF export dependencies unavailable"
)
class PdfExportTests(unittest.TestCase):
    def test_export_reopens_with_exact_page_geometry_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "proof.pdf"
            manifest = export_layout_pdf(vector_layout(), output)
            self.assertTrue(output.is_file())
            with pikepdf.open(output) as document:
                self.assertEqual(len(document.pages), 1)
                self.assertEqual(
                    tuple(float(value) for value in document.pages[0].MediaBox),
                    (0.0, 0.0, 200.0, 300.0),
                )
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            self.assertEqual(manifest.pdf_sha256, digest)
            manifest_data = json.loads(
                (Path(directory) / "proof.pdf.manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest_data["source_revision"], "revision-123")
            self.assertEqual(manifest_data["pages"][0]["operation_count"], 2)

    def test_export_is_byte_deterministic_for_the_same_display_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.pdf"
            second = Path(directory) / "second.pdf"
            export_layout_pdf(vector_layout(), first)
            export_layout_pdf(vector_layout(), second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_text_placeholder_is_rejected_without_replacing_prior_output(self) -> None:
        layout = vector_layout()
        pages = layout["pages"]
        assert isinstance(pages, list)
        page = pages[0]
        assert isinstance(page, dict)
        operations = page["operations"]
        assert isinstance(operations, list)
        operations.append({"op": "text_placeholder", "object_id": "title", "text": "not shaped"})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "proof.pdf"
            output.write_bytes(b"prior output")
            with self.assertRaisesRegex(PdfExportError, "unshaped text placeholder"):
                export_layout_pdf(layout, output)
            self.assertEqual(output.read_bytes(), b"prior output")

    def test_inspection_failure_does_not_replace_prior_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "proof.pdf"
            output.write_bytes(b"prior output")
            with (
                mock.patch(
                    "pydesign.pdf.adapter._inspect_pdf", side_effect=PdfExportError("injected")
                ),
                self.assertRaisesRegex(PdfExportError, "injected"),
            ):
                export_layout_pdf(vector_layout(), output)
            self.assertEqual(output.read_bytes(), b"prior output")


if __name__ == "__main__":
    unittest.main()
