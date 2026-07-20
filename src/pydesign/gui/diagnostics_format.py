"""Format and group structured evaluation diagnostics for the drawer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def format_diagnostics_text(diagnostics: Sequence[object], stderr: str = "") -> str:
    lines: list[str] = []
    counts: dict[tuple[str, str, str], int] = {}
    order: list[tuple[str, str, str]] = []
    for item in diagnostics:
        if not isinstance(item, Mapping):
            continue
        severity = str(item.get("severity", "info")).upper()
        code = str(item.get("code", "PD-UNKNOWN"))
        message = str(item.get("message", ""))
        key = (severity, code, message)
        if key not in counts:
            order.append(key)
            counts[key] = 0
        counts[key] += 1
    for severity, code, message in order:
        count = counts[(severity, code, message)]
        suffix = f" (x{count})" if count > 1 else ""
        lines.append(f"{severity} {code}{suffix}: {message}")
    if stderr.strip():
        if lines:
            lines.append("")
        lines.extend(["Worker output:", stderr.rstrip()])
    return "\n".join(lines) or "No diagnostics"


def diagnostic_targets(diagnostics: Sequence[object]) -> list[dict[str, Any]]:
    """Return first occurrence of each grouped diagnostic with optional navigation ids."""
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, Any]] = []
    for item in diagnostics:
        if not isinstance(item, Mapping):
            continue
        severity = str(item.get("severity", "info")).upper()
        code = str(item.get("code", "PD-UNKNOWN"))
        message = str(item.get("message", ""))
        key = (severity, code, message)
        if key in seen:
            continue
        seen.add(key)
        entry: dict[str, Any] = {"severity": severity, "code": code, "message": message}
        for field in ("object_id", "path", "page_id", "line"):
            if field in item:
                entry[field] = item[field]
        result.append(entry)
    return result
