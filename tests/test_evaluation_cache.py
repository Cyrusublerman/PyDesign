from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydesign.runtime import WorkerClient
from pydesign.runtime.build_cache import BuildCache


def write_counting_project(root: Path, *, deterministic: bool = True) -> None:
    (root / "project.toml").write_text(
        (
            "[project]\n"
            "format = 1\n"
            "name = 'Evaluation Cache Test'\n"
            "entrypoint = 'document:build'\n"
            "\n"
            "[build]\n"
            f"deterministic = {'true' if deterministic else 'false'}\n"
        ),
        encoding="utf-8",
    )
    (root / "document.py").write_text(
        (
            "from pydesign import BuildContext, Document, Page, Rectangle\n"
            "\n"
            "def build(ctx: BuildContext):\n"
            "    marker = ctx.root / '.pydesign' / 'execution-count.txt'\n"
            "    marker.parent.mkdir(parents=True, exist_ok=True)\n"
            "    count = int(marker.read_text(encoding='utf-8')) if marker.exists() else 0\n"
            "    marker.write_text(str(count + 1), encoding='utf-8')\n"
            "    return Document(\n"
            "        id='doc',\n"
            "        pages=[Page(\n"
            "            id='page',\n"
            "            size=(100, 200),\n"
            "            elements=[Rectangle(id='box', frame=(10, 20, 30, 40))],\n"
            "        )],\n"
            "    )\n"
        ),
        encoding="utf-8",
    )


class EvaluationCacheTests(unittest.TestCase):
    def test_deterministic_cache_hit_skips_user_code_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_counting_project(root)
            client = WorkerClient()

            first = client.evaluate(root)
            second = client.evaluate(root)

            self.assertTrue(first.ok, first.error_message)
            self.assertTrue(second.ok, second.error_message)
            self.assertIs(first.response.get("cache_hit"), False)
            self.assertIs(second.response.get("cache_hit"), True)
            self.assertEqual(
                (root / ".pydesign" / "execution-count.txt").read_text(encoding="utf-8"),
                "1",
            )
            self.assertEqual(list((root / ".pydesign" / "cache").glob("*.tmp")), [])

    def test_non_deterministic_project_bypasses_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_counting_project(root, deterministic=False)
            client = WorkerClient()

            first = client.evaluate(root)
            second = client.evaluate(root)

            self.assertTrue(first.ok, first.error_message)
            self.assertTrue(second.ok, second.error_message)
            self.assertIs(first.response.get("cache_hit"), False)
            self.assertIs(second.response.get("cache_hit"), False)
            self.assertEqual(
                (root / ".pydesign" / "execution-count.txt").read_text(encoding="utf-8"),
                "2",
            )
            self.assertFalse((root / ".pydesign" / "cache").exists())

    def test_corrupt_cache_entry_is_discarded_and_rebuilt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_counting_project(root)
            client = WorkerClient()

            first = client.evaluate(root)
            self.assertTrue(first.ok, first.error_message)
            cache_files = list((root / ".pydesign" / "cache").glob("*.json"))
            self.assertEqual(len(cache_files), 1)
            cache_files[0].write_text("{not-json", encoding="utf-8")

            rebuilt = client.evaluate(root)
            cached = client.evaluate(root)

            self.assertTrue(rebuilt.ok, rebuilt.error_message)
            self.assertTrue(cached.ok, cached.error_message)
            self.assertIs(rebuilt.response.get("cache_hit"), False)
            self.assertIs(cached.response.get("cache_hit"), True)
            self.assertEqual(
                (root / ".pydesign" / "execution-count.txt").read_text(encoding="utf-8"),
                "2",
            )

    def test_cache_dependency_must_remain_inside_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = BuildCache(directory)
            with self.assertRaisesRegex(ValueError, "escapes project root"):
                cache.key_for(relative_paths=("../outside.py",))


if __name__ == "__main__":
    unittest.main()
