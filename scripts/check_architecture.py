#!/usr/bin/env python3
"""Fast repository guardrails derived from the locked design baseline."""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DESIGN_FILES = (
    "docs/design/00_decision_register.md",
    "docs/design/02_project_format_and_python_authoring.md",
    "docs/design/04_typography_and_text_layout.md",
    "docs/design/07_rendering_pdf_export_and_proofing.md",
    "docs/design/requirements_traceability.md",
)


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED_DESIGN_FILES:
        if not (ROOT / relative).is_file():
            failures.append(f"missing normative design file: {relative}")

    licence = ROOT / "LICENSE"
    if not licence.is_file() or "Mozilla Public License Version 2.0" not in licence.read_text(
        encoding="utf-8"
    ):
        failures.append("LICENSE must contain the MPL-2.0 text")

    with (ROOT / "pyproject.toml").open("rb") as stream:
        metadata = tomllib.load(stream)
    if metadata.get("project", {}).get("license", {}).get("text") != "MPL-2.0":
        failures.append("pyproject.toml must declare MPL-2.0")

    core_root = ROOT / "src" / "pydesign"
    gui_root = core_root / "gui"
    for source_path in core_root.rglob("*.py"):
        if source_path.is_relative_to(gui_root):
            continue
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            module: str | None = None
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            module = next(
                (name for name in names if name == "PySide6" or name.startswith("PySide6.")), None
            )
            if module:
                failures.append(
                    f"core/headless module imports GUI dependency {module}: "
                    f"{source_path.relative_to(ROOT)}:{node.lineno}"
                )

    if failures:
        for failure in failures:
            print(f"ARCHITECTURE ERROR: {failure}", file=sys.stderr)
        return 1
    print("architecture guardrails passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
