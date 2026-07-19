from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydesign.runtime.project import (
    ProjectConfigError,
    compute_project_revision,
    load_project_config,
)


class ProjectTests(unittest.TestCase):
    def test_manifest_and_revision_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "project.toml").write_text(
                "[project]\nformat=1\nid='project-test'\n"
                "name='Test'\nentrypoint='document:build'\n",
                encoding="utf-8",
            )
            (root / "document.py").write_text("value = 1\n", encoding="utf-8")
            config = load_project_config(root)
            first = compute_project_revision(config)
            second = compute_project_revision(config)
            self.assertEqual(first, second)
            self.assertEqual(config.module_name, "document")
            self.assertEqual(config.function_name, "build")
            self.assertEqual(config.project_id, "project-test")
            (root / "document.py").write_text("value = 2\n", encoding="utf-8")
            self.assertNotEqual(first, compute_project_revision(config))

    def test_missing_manifest_is_clear(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ProjectConfigError):
            load_project_config(directory)


if __name__ == "__main__":
    unittest.main()
