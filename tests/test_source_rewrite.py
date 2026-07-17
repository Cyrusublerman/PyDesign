from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import libcst as cst

from pydesign import mm
from pydesign.source import (
    DuplicateSourceIdError,
    SourceRewriteError,
    SourceTransaction,
    SourceTransactionError,
    apply_source_edit,
    apply_source_transaction,
    build_source_index,
    frame_edit_options,
    new_gui_id,
    plan_bezier_insertion,
    plan_frame_update,
    plan_rectangle_insertion,
)


def write_source(root: Path, source: str, *, relative: str = "page.py") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


class SourceIndexTests(unittest.TestCase):
    def test_indexes_multi_file_declarations_and_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_source(
                root,
                "from pydesign import Page, Rectangle, mm\n"
                "page = Page(id='page-1', size=(100, 100), elements=[\n"
                "    Rectangle(id='box', frame=(10 * mm, 20 * mm, 30, width), fill='#f60'),\n"
                "])\n",
                relative="pages/one.py",
            )
            index = build_source_index(root)
            box = index.require("box")
            self.assertEqual(box.path.relative_to(root).as_posix(), "pages/one.py")
            frame = box.property("frame")
            assert frame is not None
            self.assertEqual(frame.kind, "tuple")
            self.assertEqual(
                tuple(item.value for item in frame.components),
                ("quantity", "quantity", "literal", "name"),
            )
            self.assertEqual(frame_edit_options(box), ("edit_shared", "adjust", "detach"))

    def test_duplicate_ids_across_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_source(
                root, "from pydesign import Page\nPage(id='same', size=(1, 1))\n", relative="a.py"
            )
            write_source(
                root, "from pydesign import Page\nPage(id='same', size=(1, 1))\n", relative="b.py"
            )
            with self.assertRaises(DuplicateSourceIdError):
                build_source_index(root)


class SourceRewriteTests(unittest.TestCase):
    def test_safe_quantity_rewrite_preserves_units_and_comments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = (
                "from pydesign import Rectangle, mm\n\n"
                "box = Rectangle(\n"
                "    id='box',\n"
                "    frame=(10 * mm, 20 * mm, 30 * mm, 40 * mm),  # keep this comment\n"
                ")\n"
            )
            path = write_source(root, source)
            previous = tuple(value * mm.points for value in (10, 20, 30, 40))
            desired = tuple(value * mm.points for value in (15, 24, 30, 40))
            plan = plan_frame_update(root, "box", previous=previous, desired=desired)
            self.assertIn("15 * mm", plan.after)
            self.assertIn("24 * mm", plan.after)
            self.assertIn("# keep this comment", plan.after)
            cst.parse_module(plan.after)
            applied = apply_source_edit(plan)
            self.assertEqual(path.read_text(encoding="utf-8"), plan.after)
            apply_source_edit(applied.undo_plan())
            self.assertEqual(path.read_text(encoding="utf-8"), source)

    def test_expression_requires_explicit_adjust_or_detach(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = (
                "from pydesign import Rectangle, mm\n"
                "base = 10 * mm\n"
                "Rectangle(id='box', frame=(base + 2 * mm, 20 * mm, 30 * mm, 40 * mm))\n"
            )
            write_source(root, source)
            previous = tuple(value * mm.points for value in (12, 20, 30, 40))
            desired = tuple(value * mm.points for value in (15, 20, 30, 40))
            with self.assertRaises(SourceRewriteError):
                plan_frame_update(root, "box", previous=previous, desired=desired, strategy="safe")
            plan = plan_frame_update(
                root, "box", previous=previous, desired=desired, strategy="adjust"
            )
            self.assertIn("base + 2 * mm", plan.after)
            self.assertIn("pt", plan.after)
            self.assertNotEqual(plan.before, plan.after)
            cst.parse_module(plan.after)

    def test_shared_name_edit_updates_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = (
                "from pydesign import Rectangle, mm\n"
                "shared_x = 10 * mm\n"
                "Rectangle(id='box', frame=(shared_x, 20 * mm, 30 * mm, 40 * mm))\n"
            )
            write_source(root, source)
            previous = tuple(value * mm.points for value in (10, 20, 30, 40))
            desired = tuple(value * mm.points for value in (16, 20, 30, 40))
            plan = plan_frame_update(
                root, "box", previous=previous, desired=desired, strategy="edit_shared"
            )
            self.assertIn("shared_x = 16 * mm", plan.after)
            self.assertIn("frame=(shared_x,", plan.after)

    def test_rectangle_insertion_adds_imports_and_readable_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_source(
                root,
                "from pydesign import Page, mm\n\n"
                "page = Page(id='page', size=(210 * mm, 297 * mm), elements=[])\n",
            )
            plan = plan_rectangle_insertion(
                root,
                "page",
                object_id="new-box",
                frame=(10.0, 20.0, 30.0, 40.0),
                fill="#123456",
            )
            self.assertIn("Rectangle", plan.after)
            self.assertIn("new-box", plan.after)
            self.assertIn("10 * pt", plan.after)
            cst.parse_module(plan.after)
            write_source(root, plan.after)
            self.assertIsNotNone(build_source_index(root).get("new-box"))

    def test_bezier_insertion_is_visible_python_and_indexable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_source(
                root,
                "from pydesign import Page\n\n"
                "page = Page(id='page', size=(500, 500), elements=[])\n",
            )
            plan = plan_bezier_insertion(
                root,
                "page",
                object_id="pd_curve",
                start=(10, 20),
                control_1=(30, 0),
                control_2=(60, 80),
                end=(90, 20),
            )
            self.assertIn("BezierPath", plan.after)
            self.assertIn("MoveTo(10 * pt, 20 * pt)", plan.after)
            self.assertIn("CurveTo(30 * pt, 0 * pt", plan.after)
            cst.parse_module(plan.after)
            write_source(root, plan.after)
            self.assertEqual(build_source_index(root).require("pd_curve").constructor, "BezierPath")

    def test_transaction_rejects_external_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = write_source(
                root,
                "from pydesign import Rectangle\nRectangle(id='box', frame=(1, 2, 3, 4))\n",
            )
            plan = plan_frame_update(root, "box", previous=(1, 2, 3, 4), desired=(2, 2, 3, 4))
            path.write_text(plan.before + "# external\n", encoding="utf-8")
            with self.assertRaises(SourceTransactionError):
                apply_source_edit(plan)

    def test_multi_file_transaction_preflights_every_file_and_undoes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_source(root, "first\n", relative="first.py")
            second = write_source(root, "second\n", relative="second.py")
            from pydesign.source import SourceEditPlan

            plans = (
                SourceEditPlan(first, "first\n", "changed first\n", "first", "a", "x", "test"),
                SourceEditPlan(second, "second\n", "changed second\n", "second", "b", "x", "test"),
            )
            transaction = SourceTransaction.create(plans, description="Change two files")
            undo = apply_source_transaction(transaction)
            self.assertEqual(first.read_text(encoding="utf-8"), "changed first\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "changed second\n")
            apply_source_transaction(undo)
            self.assertEqual(first.read_text(encoding="utf-8"), "first\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "second\n")

    def test_multi_file_transaction_does_not_partially_apply_on_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_source(root, "first\n", relative="first.py")
            second = write_source(root, "second external\n", relative="second.py")
            from pydesign.source import SourceEditPlan

            transaction = SourceTransaction.create(
                (
                    SourceEditPlan(first, "first\n", "changed\n", "first", "a", "x", "test"),
                    SourceEditPlan(second, "second\n", "changed\n", "second", "b", "x", "test"),
                )
            )
            with self.assertRaises(SourceTransactionError):
                apply_source_transaction(transaction)
            self.assertEqual(first.read_text(encoding="utf-8"), "first\n")

    def test_multi_file_transaction_rolls_back_a_late_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_source(root, "first\n", relative="first.py")
            second = write_source(root, "second\n", relative="second.py")
            from pydesign.source import SourceEditPlan
            from pydesign.source import transaction as transaction_module

            transaction = SourceTransaction.create(
                (
                    SourceEditPlan(first, "first\n", "changed\n", "first", "a", "x", "test"),
                    SourceEditPlan(second, "second\n", "changed\n", "second", "b", "x", "test"),
                )
            )
            atomic_write = transaction_module._atomic_write_text
            calls = 0

            def fail_second(path: Path, content: str) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected late failure")
                atomic_write(path, content)

            with (
                patch.object(transaction_module, "_atomic_write_text", side_effect=fail_second),
                self.assertRaises(SourceTransactionError),
            ):
                apply_source_transaction(transaction)
            self.assertEqual(first.read_text(encoding="utf-8"), "first\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "second\n")

    def test_gui_ids_are_opaque_base32_and_collision_checked(self) -> None:
        identifier = new_gui_id(set(), random_bytes=b"abcde")
        self.assertRegex(identifier, r"^pd_[a-z2-7]{8}$")
        with self.assertRaises(SourceRewriteError):
            new_gui_id({identifier}, random_bytes=b"abcde")


if __name__ == "__main__":
    unittest.main()
