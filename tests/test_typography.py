from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

try:
    import uharfbuzz

    from pydesign.text import (
        FontChangedError,
        ShapingError,
        compose_greedy,
        hyphenation_opportunities,
        line_break_opportunities,
        load_font_face,
        shape_text,
    )
except ImportError:
    uharfbuzz = None  # type: ignore[assignment]

try:
    import icu
except ImportError:
    icu = None  # type: ignore[assignment]


FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


@unittest.skipUnless(uharfbuzz is not None and FONT.is_file(), "typography stack/font unavailable")
class TypographyTests(unittest.TestCase):
    def test_font_face_has_exact_identity_and_embedding_metadata(self) -> None:
        face = load_font_face(FONT)
        self.assertRegex(face.fingerprint.file_sha256, r"^[0-9a-f]{64}$")
        self.assertRegex(face.fingerprint.instance_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(face.metadata.family, "DejaVu Sans")
        self.assertGreater(face.metadata.units_per_em, 0)
        self.assertGreater(face.metadata.glyph_count, 1000)
        self.assertTrue(face.metadata.embedding.installable)

    def test_ligature_shaping_emits_positioned_cluster_safe_glyphs(self) -> None:
        face = load_font_face(FONT)
        run = shape_text(face, "office", font_size=12, language="en")
        self.assertEqual(run.direction, "ltr")
        self.assertEqual(run.script, "Latn")
        self.assertLess(len(run.glyphs), len(run.text))
        self.assertGreater(run.x_advance, 0)
        self.assertEqual(run.source_end, 6)
        self.assertTrue(all(glyph.bounds is not None for glyph in run.glyphs))

        no_ligature = shape_text(face, "office", font_size=12, features={"liga": False})
        self.assertGreater(len(no_ligature.glyphs), len(run.glyphs))

    def test_arabic_run_resolves_rtl_and_retains_logical_clusters(self) -> None:
        face = load_font_face(FONT)
        run = shape_text(face, "سلام", font_size=14, language="ar", source_start=20)
        self.assertEqual(run.direction, "rtl")
        self.assertEqual(run.script, "Arab")
        self.assertTrue(all(20 <= cluster < 24 for cluster in run.clusters))
        self.assertGreater(run.x_advance, 0)

    def test_changed_font_file_is_rejected_before_shaping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "font.ttf"
            shutil.copyfile(FONT, copied)
            face = load_font_face(copied)
            with copied.open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaises(FontChangedError):
                shape_text(face, "text", font_size=12)

    def test_invalid_feature_is_visible_error(self) -> None:
        face = load_font_face(FONT)
        with self.assertRaisesRegex(ShapingError, re.escape("four ASCII")):
            shape_text(face, "text", font_size=12, features={"long-feature": True})

    def test_dictionary_hyphenation_maps_candidates_to_source(self) -> None:
        opportunities = hyphenation_opportunities("typography", language="en_US")
        positions = {item.index for item in opportunities}
        self.assertTrue(positions)
        self.assertTrue(all(0 < position < len("typography") for position in positions))

    def test_shape_text_cli_emits_auditable_json(self) -> None:
        from pydesign.cli import main

        output = StringIO()
        with redirect_stdout(output):
            status = main(["shape-text", str(FONT), "office", "--size", "11"])
        self.assertEqual(status, 0)
        self.assertIn('"glyphs"', output.getvalue())
        self.assertIn('"instance_sha256"', output.getvalue())


@unittest.skipUnless(
    uharfbuzz is not None and icu is not None and FONT.is_file(),
    "ICU typography stack/font unavailable",
)
class UnicodeCompositionTests(unittest.TestCase):
    def test_icu_boundaries_map_utf16_to_python_indices(self) -> None:
        text = "A😀 line\nNext"
        opportunities = line_break_opportunities(text, language="en")
        self.assertEqual(opportunities[-1].index, len(text))
        self.assertTrue(all(0 < item.index <= len(text) for item in opportunities))
        self.assertTrue(any(item.kind == "hard" for item in opportunities))

    def test_greedy_composer_reshapes_legal_line_candidates(self) -> None:
        face = load_font_face(FONT)
        one_word = shape_text(face, "Typography", font_size=12, language="en_US")
        layout = compose_greedy(
            face,
            "Typography makes magazines",
            font_size=12,
            maximum_width=one_word.x_advance + 2,
            language="en_US",
            hyphenate=False,
        )
        self.assertGreaterEqual(len(layout.lines), 3)
        self.assertEqual(layout.lines[0].source_start, 0)
        self.assertEqual(layout.lines[-1].source_end, len(layout.text))
        self.assertFalse(layout.overset)


if __name__ == "__main__":
    unittest.main()
