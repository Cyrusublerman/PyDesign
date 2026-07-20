"""Lightweight offline PDF/X-4 structural checks (Stage 7)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pikepdf


@dataclass(frozen=True, slots=True)
class Pdfx4Issue:
    code: str
    message: str


def validate_pdfx4(path: str | Path) -> list[Pdfx4Issue]:
    """Require MediaBox/TrimBox/BleedBox on every page after pdfx4 export."""
    pdf_path = Path(path).expanduser().resolve()
    issues: list[Pdfx4Issue] = []
    with pikepdf.open(pdf_path) as pdf:
        if not pdf.pages:
            return [Pdfx4Issue("PD-X4-001", "PDF has no pages")]
        for index, page in enumerate(pdf.pages):
            for box_name in ("/MediaBox", "/TrimBox", "/BleedBox"):
                if box_name not in page:
                    issues.append(
                        Pdfx4Issue(
                            "PD-X4-002",
                            f"page {index + 1} missing {box_name.lstrip('/')}",
                        )
                    )
    return issues
