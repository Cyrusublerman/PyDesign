from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydesign.source import (
    apply_source_edit,
    plan_frame_update,
    plan_quantity_property_update,
    plan_rectangle_insertion,
    plan_string_property_update,
    style_edit_options,
)


def write_source(root: Path, source: str, *, relative: str = "page.py") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


class PropertyRewriteTests(unittest.TestCase):
    def test_safe_fill_rewrite_and_undo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = (
                "from pydesign import Rectangle\n"
                "box = Rectangle(id='box', frame=(1, 2, 3, 4), fill='#ff0000')\n"
            )
            path = write_source(root, source)
            plan = plan_string_property_update(root, "box", "fill", desired="#00ff00")
            self.assertIn("fill='#00ff00'", plan.after)
            applied = apply_source_edit(plan)
            self.assertEqual(path.read_text(encoding="utf-8"), plan.after)
            apply_source_edit(applied.undo_plan())
            self.assertEqual(path.read_text(encoding="utf-8"), source)

    def test_stroke_width_quantity_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_source(
                root,
                "from pydesign import Rectangle, pt\n"
                "box = Rectangle(id='box', frame=(1, 2, 3, 4), stroke_width=2 * pt)\n",
            )
            plan = plan_quantity_property_update(root, "box", "stroke_width", desired_points=3.0)
            self.assertIn("3", plan.after)
            apply_source_edit(plan)

    def test_style_name_ownership_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_source(
                root,
                "from pydesign import Rectangle\n"
                "accent = 'body'\n"
                "box = Rectangle(id='box', frame=(1, 2, 3, 4), style=accent)\n",
            )
            self.assertEqual(style_edit_options(root, "box"), ("edit_shared", "detach"))

    def test_create_move_undo_fuzz_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_source(
                root,
                "from pydesign import Page, Rectangle\n"
                "page = Page(id='page-1', size=(100, 100), elements=[\n"
                "    Rectangle(id='seed', frame=(10, 10, 20, 20), fill='#111111'),\n"
                "])\n",
            )
            for index in range(5):
                previous = (float(index), float(index), 10.0, 10.0)
                desired = (float(index + 1), float(index + 1), 10.0, 10.0)
                plan = plan_rectangle_insertion(
                    root,
                    "page-1",
                    object_id=f"gui-{index}",
                    frame=previous,
                )
                apply_source_edit(plan)
                move = plan_frame_update(
                    root,
                    f"gui-{index}",
                    previous=previous,
                    desired=desired,
                )
                moved = apply_source_edit(move)
                apply_source_edit(moved.undo_plan())
            text = (root / "page.py").read_text(encoding="utf-8")
            self.assertIn("id='seed'", text)
            self.assertIn("gui-4", text)


if __name__ == "__main__":
    unittest.main()
