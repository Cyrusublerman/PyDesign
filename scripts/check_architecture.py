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

MAX_MODULE_LINES = 600

FORBIDDEN_LAYER_IMPORTS = {
    "pdf": ("pydesign.gui", "pydesign.runtime", "pydesign.source"),
    "runtime": ("pydesign.gui",),
    "source": ("pydesign.gui", "pydesign.runtime", "pydesign.text"),
    "text": ("pydesign.gui", "pydesign.runtime", "pydesign.source"),
}


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
    source_paths = tuple(core_root.rglob("*.py"))
    module_paths = {_module_name(core_root, path): path for path in source_paths}
    dependency_graph: dict[str, set[str]] = {module: set() for module in module_paths}
    for source_path in source_paths:
        relative_source = source_path.relative_to(core_root)
        source_module = _module_name(core_root, source_path)
        line_count = len(source_path.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_MODULE_LINES:
            failures.append(
                f"module exceeds {MAX_MODULE_LINES}-line cohesion budget: "
                f"{source_path.relative_to(ROOT)} ({line_count} lines)"
            )
        if (
            source_path.is_relative_to(gui_root)
            and source_path.name == "app.py"
            and line_count > 100
        ):
            failures.append("pydesign.gui.app must remain a small stable entrypoint facade")
        if (
            source_path.is_relative_to(gui_root)
            and source_path.name == "window.py"
            and line_count > 575
        ):
            failures.append("pydesign.gui.window exceeds its orchestration budget; extract a seam")
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        layer = relative_source.parts[0] if len(relative_source.parts) > 1 else None
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            module = next(
                (name for name in names if name == "PySide6" or name.startswith("PySide6.")), None
            )
            if module and not source_path.is_relative_to(gui_root):
                failures.append(
                    f"core/headless module imports GUI dependency {module}: "
                    f"{source_path.relative_to(ROOT)}:{node.lineno}"
                )
            if layer in FORBIDDEN_LAYER_IMPORTS:
                forbidden = next(
                    (
                        name
                        for name in names
                        if any(
                            name == prefix or name.startswith(f"{prefix}.")
                            for prefix in FORBIDDEN_LAYER_IMPORTS[layer]
                        )
                    ),
                    None,
                )
                if forbidden:
                    failures.append(
                        f"{layer} layer imports forbidden dependency {forbidden}: "
                        f"{source_path.relative_to(ROOT)}:{node.lineno}"
                    )
            for name in names:
                dependency = _local_dependency(name, module_paths)
                if dependency is not None and dependency != source_module:
                    dependency_graph[source_module].add(dependency)

    for cycle in _dependency_cycles(dependency_graph):
        failures.append(f"internal module dependency cycle: {' -> '.join((*cycle, cycle[0]))}")

    canvas_path = gui_root / "canvas.py"
    if canvas_path.is_file() and "pydesign.gui.window" in canvas_path.read_text(encoding="utf-8"):
        failures.append("canvas must emit intents and must not depend on the main window")

    if failures:
        for failure in failures:
            print(f"ARCHITECTURE ERROR: {failure}", file=sys.stderr)
        return 1
    print("architecture guardrails passed")
    return 0


def _module_name(core_root: Path, path: Path) -> str:
    relative = path.relative_to(core_root).with_suffix("")
    parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
    return ".".join(("pydesign", *parts))


def _local_dependency(name: str, modules: dict[str, Path]) -> str | None:
    candidate = name
    while candidate.startswith("pydesign"):
        if candidate in modules:
            return candidate
        candidate, separator, _leaf = candidate.rpartition(".")
        if not separator:
            break
    return None


def _dependency_cycles(graph: dict[str, set[str]]) -> tuple[tuple[str, ...], ...]:
    """Return one canonical representation for each directed DFS cycle."""

    visited: set[str] = set()
    active: list[str] = []
    active_set: set[str] = set()
    cycles: set[tuple[str, ...]] = set()

    def visit(module: str) -> None:
        visited.add(module)
        active.append(module)
        active_set.add(module)
        for dependency in sorted(graph[module]):
            if dependency not in visited:
                visit(dependency)
            elif dependency in active_set:
                start = active.index(dependency)
                raw = tuple(active[start:])
                rotations = tuple(raw[index:] + raw[:index] for index in range(len(raw)))
                cycles.add(min(rotations))
        active.pop()
        active_set.remove(module)

    for module in sorted(graph):
        if module not in visited:
            visit(module)
    return tuple(sorted(cycles))


if __name__ == "__main__":
    raise SystemExit(main())
