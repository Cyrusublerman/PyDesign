"""Validate the machine-readable PyDesign delivery backlog."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "docs" / "roadmap" / "backlog.toml"
TRACEABILITY = ROOT / "docs" / "design" / "requirements_traceability.md"
REQUIREMENT_PATTERN = re.compile(r"\| (R-[A-Z]+-\d{3}) \|")
REQUIRED_FIELDS = {
    "id",
    "title",
    "description",
    "workstream",
    "stage",
    "milestone",
    "status",
    "priority",
    "depends_on",
    "requirements",
    "specifications",
    "acceptance",
}


def _string_set(data: dict[str, Any], key: str, errors: list[str]) -> set[str]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"top-level {key!r} must be a list of strings")
        return set()
    return set(value)


def _task_strings(task: dict[str, Any], key: str, task_id: str, errors: list[str]) -> list[str]:
    value = task.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{task_id}: {key} must be a list of strings")
        return []
    return value


def _known_specifications() -> set[str]:
    return {
        path.name.split("_", maxsplit=1)[0]
        for path in (ROOT / "docs" / "design").glob("[0-9][0-9]_*.md")
    }


def _find_cycles(dependencies: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            start = visiting.index(task_id)
            cycle = [*visiting[start:], task_id]
            errors.append(f"dependency cycle: {' -> '.join(cycle)}")
            return
        visiting.append(task_id)
        for dependency in dependencies.get(task_id, []):
            visit(dependency)
        visiting.pop()
        visited.add(task_id)

    for task_id in dependencies:
        visit(task_id)
    return errors


def validate_backlog() -> list[str]:
    errors: list[str] = []
    with BACKLOG.open("rb") as stream:
        data: dict[str, Any] = tomllib.load(stream)

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    statuses = _string_set(data, "statuses", errors)
    priorities = _string_set(data, "priorities", errors)
    milestones = _string_set(data, "milestones", errors)
    workstreams = _string_set(data, "workstreams", errors)
    known_requirements = set(REQUIREMENT_PATTERN.findall(TRACEABILITY.read_text(encoding="utf-8")))
    known_specifications = _known_specifications()

    raw_tasks = data.get("task")
    if not isinstance(raw_tasks, list):
        return [*errors, "top-level [[task]] entries are required"]

    tasks: dict[str, dict[str, Any]] = {}
    dependencies: dict[str, list[str]] = {}
    for index, raw_task in enumerate(raw_tasks, start=1):
        if not isinstance(raw_task, dict):
            errors.append(f"task entry {index} must be a table")
            continue
        task: dict[str, Any] = raw_task
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id:
            errors.append(f"task entry {index} has no valid id")
            continue
        if task_id in tasks:
            errors.append(f"duplicate task id: {task_id}")
            continue
        tasks[task_id] = task
        missing = sorted(REQUIRED_FIELDS - task.keys())
        if missing:
            errors.append(f"{task_id}: missing fields {', '.join(missing)}")

        if task.get("status") not in statuses:
            errors.append(f"{task_id}: unknown status {task.get('status')!r}")
        if task.get("priority") not in priorities:
            errors.append(f"{task_id}: unknown priority {task.get('priority')!r}")
        if task.get("milestone") not in milestones:
            errors.append(f"{task_id}: unknown milestone {task.get('milestone')!r}")
        if task.get("workstream") not in workstreams:
            errors.append(f"{task_id}: unknown workstream {task.get('workstream')!r}")

        task_dependencies = _task_strings(task, "depends_on", task_id, errors)
        dependencies[task_id] = task_dependencies
        requirements = _task_strings(task, "requirements", task_id, errors)
        specifications = _task_strings(task, "specifications", task_id, errors)
        acceptance = _task_strings(task, "acceptance", task_id, errors)

        for requirement in requirements:
            if requirement not in known_requirements:
                errors.append(f"{task_id}: unknown requirement {requirement}")
        for specification in specifications:
            if specification not in known_specifications:
                errors.append(f"{task_id}: unknown specification {specification}")
        if len(acceptance) < 2:
            errors.append(f"{task_id}: at least two acceptance statements are required")
        if task.get("status") == "blocked" and not task.get("blocked_by"):
            errors.append(f"{task_id}: blocked tasks require blocked_by")

    for task_id, task_dependencies in dependencies.items():
        for dependency in task_dependencies:
            if dependency not in tasks:
                errors.append(f"{task_id}: unknown dependency {dependency}")
            if dependency == task_id:
                errors.append(f"{task_id}: task cannot depend on itself")

    errors.extend(_find_cycles(dependencies))

    current_focus = _task_strings(data, "current_focus", "top-level", errors)
    for task_id in current_focus:
        task = tasks.get(task_id)
        if task is None:
            errors.append(f"current_focus references unknown task {task_id}")
        elif task.get("status") not in {"ready", "in_progress"}:
            errors.append(f"current_focus task {task_id} must be ready or in_progress")

    return errors


def main() -> int:
    errors = validate_backlog()
    if errors:
        for error in errors:
            print(f"roadmap error: {error}", file=sys.stderr)
        return 1
    print("roadmap: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
