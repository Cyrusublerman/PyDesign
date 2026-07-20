from __future__ import annotations

import json
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

from pydesign.runtime import WorkerClient
from pydesign.runtime.project_files import (
    ProjectOperationError,
    UnsafeProjectLocationError,
    create_project,
    duplicate_project,
    find_pydesign_source_checkout,
    is_bundled_example,
    package_project,
)


class ProjectFileTests(unittest.TestCase):
    def test_bundled_example_copies_to_an_external_independent_project(self) -> None:
        checkout = find_pydesign_source_checkout()
        if checkout is None:
            self.skipTest("not running from an editable source checkout")
        example = checkout / "examples" / "hello_editorial"
        self.assertTrue(is_bundled_example(example))
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "Hello Editorial Copy"
            config = duplicate_project(example, destination)
            result = WorkerClient().evaluate(config.root)
            self.assertTrue(result.ok, result.error_message)
            self.assertFalse((destination / ".git").exists())

    def test_external_project_creates_and_builds_without_touching_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkout = root / "PyDesign"
            checkout.mkdir()
            sentinel = checkout / "repository-sentinel.txt"
            sentinel.write_text("unchanged\n", encoding="utf-8")
            before = _tree_snapshot(checkout)

            project = root / "Documents" / "PyDesign Projects" / "Magazine"
            config = create_project(project, name="Magazine", source_checkout=checkout)
            result = WorkerClient().evaluate(config.root)

            self.assertTrue(result.ok, result.error_message)
            self.assertEqual(_tree_snapshot(checkout), before)
            self.assertTrue((project / "project.toml").is_file())
            self.assertTrue((project / "pages" / "page_001.py").is_file())

    def test_creation_inside_source_checkout_requires_explicit_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "PyDesign"
            checkout.mkdir()
            destination = checkout / "user-projects" / "Local Test"
            with self.assertRaises(UnsafeProjectLocationError):
                create_project(destination, source_checkout=checkout)
            config = create_project(
                destination,
                source_checkout=checkout,
                allow_in_source_checkout=True,
            )
            self.assertEqual(config.root, destination.resolve())

    def test_duplicate_is_independent_and_excludes_internal_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Source"
            destination = root / "Copy"
            create_project(source, name="Source", source_checkout=root / "checkout")
            (source / "assets" / "images" / "picture.txt").write_text("asset", encoding="utf-8")
            for relative in (".pydesign/cache/data", "exports/out.pdf", "build/temp.bin"):
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("derived", encoding="utf-8")

            duplicate_project(
                source,
                destination,
                name="Independent Copy",
                source_checkout=root / "checkout",
            )

            self.assertEqual(
                (destination / "assets" / "images" / "picture.txt").read_text(encoding="utf-8"),
                "asset",
            )
            self.assertFalse((destination / ".pydesign").exists())
            self.assertFalse((destination / "exports").exists())
            self.assertFalse((destination / "build").exists())
            self.assertTrue((destination / "assets" / "fonts").is_dir())
            source_manifest = _manifest(source)
            copy_manifest = _manifest(destination)
            self.assertNotEqual(source_manifest["project"]["id"], copy_manifest["project"]["id"])
            self.assertEqual(copy_manifest["project"]["name"], "Independent Copy")

    def test_package_is_deterministic_and_contains_only_portable_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "Project"
            create_project(project, source_checkout=root / "checkout")
            (project / "assets" / "images" / "cover.dat").write_bytes(b"cover")
            (project / ".pydesign" / "cache").mkdir(parents=True)
            (project / ".pydesign" / "cache" / "preview.bin").write_bytes(b"cache")
            first = root / "first.zip"
            second = root / "second.zip"
            folder_package = root / "folder-package"

            first_result = package_project(project, first)
            second_result = package_project(project, second)
            package_project(project, folder_package)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first_result.manifest_sha256, second_result.manifest_sha256)
            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())
                self.assertIn("project.toml", names)
                self.assertIn("assets/images/cover.dat", names)
                self.assertIn("package-manifest.json", names)
                self.assertNotIn(".pydesign/cache/preview.bin", names)
                manifest = json.loads(archive.read("package-manifest.json"))
            self.assertEqual(manifest["schema_version"], 1)
            self.assertTrue((folder_package / "package-manifest.json").is_file())
            self.assertTrue((folder_package / "assets" / "fonts").is_dir())

    def test_package_refuses_symbolic_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "Project"
            create_project(project, source_checkout=root / "checkout")
            target = project / "assets" / "images" / "original.dat"
            target.write_bytes(b"asset")
            link = project / "assets" / "images" / "alias.dat"
            try:
                link.symlink_to(target.name)
            except OSError as error:
                self.skipTest(f"symbolic links unavailable: {error}")
            with self.assertRaises(ProjectOperationError):
                package_project(project, root / "package.zip")

    def test_package_output_cannot_pollute_authored_project_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "Project"
            create_project(project, source_checkout=root / "checkout")
            with self.assertRaises(ProjectOperationError):
                package_project(project, project / "package.zip")
            result = package_project(project, project / "exports" / "package.zip")
            self.assertTrue(result.output.is_file())


def _manifest(root: Path) -> dict[str, object]:
    with (root / "project.toml").open("rb") as stream:
        return tomllib.load(stream)


def _tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


if __name__ == "__main__":
    unittest.main()
