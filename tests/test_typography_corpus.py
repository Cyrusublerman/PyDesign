"""Stage 3 corpus stability: golden shape-text + project layout overset."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "examples" / "typography_corpus"
FONT = CORPUS / "assets" / "fonts" / "DejaVuSans.ttf"
GOLDENS = CORPUS / "goldens"

try:
    import uharfbuzz

    from pydesign.text import load_font_face, shape_text
except ImportError:
    uharfbuzz = None  # type: ignore[assignment]


@unittest.skipUnless(uharfbuzz is not None and FONT.is_file(), "typography corpus unavailable")
class TypographyCorpusTests(unittest.TestCase):
    def test_golden_glyph_ids_stable(self) -> None:
        cases = (
            ("ltr_hello.json", "Hello office", "en", None),
            ("mixed_hello_arabic.json", "Hello سلام", "und", None),
            ("rtl_arabic.json", "سلام", "ar", "rtl"),
        )
        face = load_font_face(FONT)
        for name, text, language, direction in cases:
            with self.subTest(name=name):
                golden = json.loads((GOLDENS / name).read_text(encoding="utf-8"))
                run = shape_text(
                    face,
                    text,
                    font_size=12.0 if "ltr" in name else 14.0,
                    language=language,
                    direction=direction,  # type: ignore[arg-type]
                )
                self.assertEqual(
                    [glyph["glyph_id"] for glyph in golden["glyphs"]],
                    [glyph.glyph_id for glyph in run.glyphs],
                )
                self.assertEqual(golden["direction"], run.direction)

    def test_corpus_project_shapes_and_reports_overset(self) -> None:
        from pydesign.runtime import WorkerClient

        result = WorkerClient().evaluate(CORPUS, timeout=60.0)
        self.assertTrue(result.ok, result.response)
        assert result.layout is not None
        ops = result.layout["pages"][0]["operations"]
        kinds = {item["op"] for item in ops}
        self.assertIn("glyph_run", kinds)
        self.assertIn("guide", kinds)
        self.assertTrue(any(item.get("op") == "glyph_run" and item.get("overset") for item in ops))
        diagnostics = result.response.get("diagnostics", [])
        self.assertTrue(any(item.get("code") == "PD-TEXT-003" for item in diagnostics))
