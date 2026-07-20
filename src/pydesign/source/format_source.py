"""Project Python formatting via Ruff (design 02 formatter)."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from pydesign.source.edits import SourceEditPlan


def format_python_source(source: str, *, path: str | Path | None = None) -> str:
    """Return Ruff-formatted source, or the original text if formatting is unavailable."""
    if not source:
        return source
    filename = str(path) if path is not None else "document.py"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--stdin-filename",
                filename,
                "-",
            ],
            input=source,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return source
    if completed.returncode != 0:
        return source
    formatted = completed.stdout
    return formatted if formatted else source


def finalize_edit_plan(plan: SourceEditPlan) -> SourceEditPlan:
    """Format the planned file body so GUI commits land as project-formatted Python."""
    if not plan.changed:
        return plan
    formatted = format_python_source(plan.after, path=plan.path)
    if formatted == plan.after:
        return plan
    return replace(plan, after=formatted)
