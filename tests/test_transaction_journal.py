from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydesign.source import (
    PendingSourceTransaction,
    SourceEditPlan,
    SourceTransaction,
    apply_source_transaction,
    recover_source_transactions,
)


class TransactionJournalTests(unittest.TestCase):
    def test_partial_crash_is_rolled_back_from_persistent_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.py"
            second = root / "second.py"
            first.write_text("first\n", encoding="utf-8")
            second.write_text("second\n", encoding="utf-8")
            plans = (
                SourceEditPlan(first, "first\n", "changed first\n", "first", "a", "x", "test"),
                SourceEditPlan(second, "second\n", "changed second\n", "second", "b", "x", "test"),
            )
            pending = PendingSourceTransaction.prepare(
                root, "Crash fixture", plans, transaction_id="fixture"
            )
            pending.write()
            first.write_text("changed first\n", encoding="utf-8")

            report = recover_source_transactions(root)

            self.assertEqual(report.recovered, ("fixture",))
            self.assertTrue(report.clean)
            self.assertEqual(first.read_text(encoding="utf-8"), "first\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "second\n")
            self.assertFalse(pending.path.exists())

    def test_divergent_source_is_never_overwritten_by_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "page.py"
            source.write_text("before\n", encoding="utf-8")
            plan = SourceEditPlan(source, "before\n", "after\n", "change", "object", "x", "test")
            pending = PendingSourceTransaction.prepare(
                root, "Conflict fixture", (plan,), transaction_id="conflict"
            )
            pending.write()
            source.write_text("author changed this\n", encoding="utf-8")

            report = recover_source_transactions(root)

            self.assertFalse(report.clean)
            self.assertIn("source diverged", report.conflicts[0])
            self.assertEqual(source.read_text(encoding="utf-8"), "author changed this\n")
            self.assertTrue(pending.path.exists())

    def test_successful_transaction_removes_write_ahead_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "page.py"
            source.write_text("before\n", encoding="utf-8")
            plan = SourceEditPlan(source, "before\n", "after\n", "change", "object", "x", "test")
            apply_source_transaction(SourceTransaction.create((plan,)), project_root=root)

            journals = root / ".pydesign" / "recovery" / "transactions"
            self.assertFalse(any(journals.glob("*.json")))
            self.assertEqual(source.read_text(encoding="utf-8"), "after\n")


if __name__ == "__main__":
    unittest.main()
