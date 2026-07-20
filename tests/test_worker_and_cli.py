from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from pydesign.cli import main
from pydesign.runtime import WorkerClient


def write_project(root: Path, *, valid: bool = True) -> None:
    (root / "project.toml").write_text(
        "[project]\nformat=1\nname='Worker Test'\nentrypoint='document:build'\n",
        encoding="utf-8",
    )
    source = (
        "from pydesign import BuildContext, Document, Page, Rectangle\n"
        "def build(ctx: BuildContext):\n"
        "    return Document(id='doc', pages=[Page(id='page', size=(100, 200), "
        "elements=[Rectangle(id='box', frame=(10, 20, 30, 40))])])\n"
        if valid
        else "raise RuntimeError('deliberate failure')\n"
    )
    (root / "document.py").write_text(source, encoding="utf-8")


class WorkerAndCliTests(unittest.TestCase):
    def test_cli_new_duplicate_and_package_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "Publication"
            duplicate = root / "Publication Copy"
            package = root / "publication.zip"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                new_code = main(["new", str(project), "--name", "Publication"])
                duplicate_code = main(["duplicate", str(project), str(duplicate)])
                package_code = main(["package", str(duplicate), "--output", str(package)])
            self.assertEqual(new_code, 0, stdout.getvalue())
            self.assertEqual(duplicate_code, 0, stdout.getvalue())
            self.assertEqual(package_code, 0, stdout.getvalue())
            self.assertTrue((project / "project.toml").is_file())
            self.assertTrue((duplicate / "project.toml").is_file())
            self.assertTrue(package.is_file())

    def test_worker_returns_layout_from_disposable_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(root)
            result = WorkerClient().evaluate(root)
            self.assertTrue(result.ok, result.error_message)
            assert result.layout is not None
            self.assertEqual(result.layout["pages"][0]["operations"][0]["object_id"], "box")

    def test_worker_returns_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(root, valid=False)
            result = WorkerClient().evaluate(root)
            self.assertFalse(result.ok)
            self.assertIn("deliberate failure", result.error_message or "")
            self.assertEqual(result.response["diagnostics"][0]["code"], "PD-RUN-001")

    def test_cli_check_and_render_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(root)
            output = root / "layout.json"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                check_code = main(["check", str(root), "--json"])
                render_code = main(["render-json", str(root), "--output", str(output)])
            self.assertEqual(check_code, 0)
            self.assertEqual(render_code, 0)
            self.assertTrue(output.is_file())
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 1)

    @unittest.skipUnless(
        importlib.util.find_spec("reportlab") is not None
        and importlib.util.find_spec("pikepdf") is not None,
        "PDF export dependencies unavailable",
    )
    def test_cli_build_pdf_writes_verified_output_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(root)
            output = root / "publication.pdf"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["build-pdf", str(root), "--output", str(output)])
            self.assertEqual(code, 0, stdout.getvalue())
            self.assertTrue(output.is_file())
            self.assertTrue((root / "publication.pdf.manifest.json").is_file())

    def test_core_import_does_not_load_qt(self) -> None:
        process = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; import pydesign; "
                    "assert pydesign.__version__; "
                    "assert not any(name == 'PySide6' or name.startswith('PySide6.') "
                    "for name in sys.modules)"
                ),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)


if __name__ == "__main__":
    unittest.main()
