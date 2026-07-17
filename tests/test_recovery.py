from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydesign.runtime import RecoveryStore


class RecoveryTests(unittest.TestCase):
    def test_snapshot_is_derived_and_clearable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "document.py"
            source.write_text("value = 1\n", encoding="utf-8")
            store = RecoveryStore(root)
            store.save(source, "value = 2\n", base_content="value = 1\n")
            snapshot = store.load(source)
            assert snapshot is not None
            self.assertEqual(snapshot.content, "value = 2\n")
            self.assertEqual(source.read_text(encoding="utf-8"), "value = 1\n")
            store.clear(source)
            self.assertIsNone(store.load(source))

    def test_source_cannot_leave_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            store = RecoveryStore(directory)
            with self.assertRaises(ValueError):
                store.save(Path(outside) / "bad.py", "", base_content="")


if __name__ == "__main__":
    unittest.main()
