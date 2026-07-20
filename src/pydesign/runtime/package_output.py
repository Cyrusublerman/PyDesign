"""Package-for-output: collect authored inputs plus published PDF artifacts."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from pydesign.runtime.project_files import package_project


@dataclass(frozen=True, slots=True)
class OutputPackageResult:
    output: Path
    file_count: int
    included_pdf: bool


def package_for_output(
    project: str | Path,
    destination: str | Path,
    *,
    pdf_path: str | Path | None = None,
) -> OutputPackageResult:
    """Create an authoring package, then optionally inject a published PDF."""
    base = package_project(project, destination)
    included_pdf = False
    if pdf_path is not None:
        pdf = Path(pdf_path).expanduser().resolve()
        if pdf.is_file():
            with zipfile.ZipFile(base.output, "a", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(pdf, arcname=f"exports/{pdf.name}")
            included_pdf = True
    return OutputPackageResult(base.output, base.file_count + int(included_pdf), included_pdf)
