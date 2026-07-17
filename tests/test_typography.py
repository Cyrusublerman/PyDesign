from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from itertools import pairwise
from pathlib import Path

try:
    import uharfbuzz

    from pydesign.text import (
        FontChangedError,
        FontRegistry,
        FontRegistryError,
        MissingGlyphError,
        ShapingError,
        TextFrameSpec,
        compose_greedy,
        flow_story,
        grapheme_clusters,
        hyphenation_opportunities,
        line_break_opportunities,
        load_font_face,
        shape_text,
        shape_with_fallback,
    )
except ImportError:
    uharfbuzz = None  # type: ignore[assignment]

try:
    import icu
except ImportError:
    icu = None  # type: ignore[assignment]


FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
LATIN_FONT = Path("/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf")


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

    def test_project_registry_is_explicit_and_cannot_escape_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_font = root / "font.ttf"
            shutil.copyfile(FONT, project_font)
            registry = FontRegistry(root)
            registered = registry.register_project("body", "font.ttf")
            self.assertEqual(registered.origin, "project")
            self.assertEqual(registry.aliases, ("body",))
            with self.assertRaises(FontRegistryError):
                registry.register_project("outside", "../outside.ttf")

    def test_system_registry_requires_the_exact_file_hash(self) -> None:
        face = load_font_face(FONT)
        registry = FontRegistry(FONT.parent)
        with self.assertRaisesRegex(FontRegistryError, "fingerprint mismatch"):
            registry.register_system("wrong", FONT, expected_sha256="0" * 64)
        registered = registry.register_system(
            "exact", FONT, expected_sha256=face.fingerprint.file_sha256
        )
        self.assertEqual(registered.face.fingerprint, face.fingerprint)

    @unittest.skipUnless(LATIN_FONT.is_file(), "Lato fallback test font unavailable")
    def test_fallback_selects_one_exact_font_per_grapheme_cluster(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(LATIN_FONT, root / "latin.ttf")
            shutil.copyfile(FONT, root / "fallback.ttf")
            registry = FontRegistry(root)
            latin = registry.register_project("latin", "latin.ttf")
            fallback = registry.register_project("fallback", "fallback.ttf")
            text = "abc سَلام"
            runs = shape_with_fallback(
                registry,
                text,
                preferred="latin",
                fallback=("fallback",),
                font_size=12,
                language="ar",
                source_start=10,
            )
            fingerprints = {run.font.instance_sha256 for run in runs}
            self.assertIn(latin.face.fingerprint.instance_sha256, fingerprints)
            self.assertIn(fallback.face.fingerprint.instance_sha256, fingerprints)
            self.assertEqual(runs[0].source_start, 10)
            self.assertEqual(runs[-1].source_end, 10 + len(text))

    def test_missing_cluster_reports_the_original_source_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(FONT, root / "font.ttf")
            registry = FontRegistry(root)
            registry.register_project("body", "font.ttf")
            with self.assertRaises(MissingGlyphError) as caught:
                shape_with_fallback(
                    registry,
                    "a\U0010ffff",
                    preferred="body",
                    font_size=12,
                    source_start=20,
                )
            self.assertEqual(caught.exception.source_index, 21)

    def test_grapheme_clusters_keep_combining_marks_with_their_base(self) -> None:
        self.assertEqual(grapheme_clusters("a\u0301b"), ((0, 2), (2, 3)))


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

    def test_story_flows_across_columns_and_frames_with_global_source_ranges(self) -> None:
        face = load_font_face(FONT)
        text = "One two three four five six seven eight nine ten eleven twelve."
        flow = flow_story(
            face,
            text,
            (
                TextFrameSpec("first", width=150, height=24, columns=2, gutter=10),
                TextFrameSpec("second", width=70, height=48),
            ),
            font_size=12,
            leading=12,
            language="en_US",
            hyphenate=False,
        )
        lines = [
            positioned.line
            for frame in flow.frames
            for column in frame.columns
            for positioned in column.lines
        ]
        self.assertGreater(len(lines), 2)
        self.assertEqual(lines[0].source_start, 0)
        self.assertTrue(
            all(
                previous.source_end == current.source_start for previous, current in pairwise(lines)
            )
        )
        self.assertEqual(flow.overset_text, text[flow.source_end :])

    def test_story_exposes_unplaced_overset_text(self) -> None:
        face = load_font_face(FONT)
        text = "This deliberately contains more copy than one short line can hold."
        flow = flow_story(
            face,
            text,
            (TextFrameSpec("only", width=90, height=12),),
            font_size=12,
            leading=12,
            language="en_US",
            hyphenate=False,
        )
        self.assertTrue(flow.overset)
        self.assertGreater(len(flow.overset_text), 0)


class FlowValidationTests(unittest.TestCase):
    def test_flow_rejects_duplicate_ids_and_impossible_gutters(self) -> None:
        duplicate = (
            TextFrameSpec("same", 100, 100),
            TextFrameSpec("same", 100, 100),
        )
        with self.assertRaisesRegex(ValueError, "unique"):
            flow_story(None, "", duplicate, font_size=12, leading=14)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "no column width"):
            flow_story(
                None,  # type: ignore[arg-type]
                "",
                (TextFrameSpec("bad", 10, 100, columns=2, gutter=10),),
                font_size=12,
                leading=14,
            )


if __name__ == "__main__":
    unittest.main()
