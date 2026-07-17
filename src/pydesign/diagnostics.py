"""Structured diagnostics shared by the core, worker, CLI and GUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    object_id: str | None = None
    page_id: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "object_id": self.object_id,
            "page_id": self.page_id,
            "source": self.source,
        }
