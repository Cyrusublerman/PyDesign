"""Offline preflight checks before PDF publication."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PreflightIssue:
    code: str
    severity: str
    message: str


def preflight_layout(
    layout: Mapping[str, Any],
    *,
    profile: str = "vector",
    asset_root: str | Path | None = None,
    waivers: Sequence[str] = (),
) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    pages = layout.get("pages")
    if not isinstance(pages, list) or not pages:
        issues.append(PreflightIssue("PD-PRE-001", "error", "layout has no pages"))
        return issues
    root = None if asset_root is None else Path(asset_root).expanduser().resolve()
    for page in pages:
        if not isinstance(page, dict):
            continue
        for operation in page.get("operations", []):
            if not isinstance(operation, dict):
                continue
            kind = operation.get("op")
            if kind == "text_placeholder":
                issues.append(
                    PreflightIssue(
                        "PD-PRE-002",
                        "error",
                        f"unshaped text {operation.get('object_id')!r} blocks publication",
                    )
                )
            if kind == "image":
                issues.extend(_image_issues(operation, root))
            if kind == "glyph_run" and operation.get("overset") is True:
                issues.append(
                    PreflightIssue(
                        "PD-PRE-004",
                        "warning",
                        f"overset text in {operation.get('object_id')!r}",
                    )
                )
    if profile == "pdfx4":
        profile_path = None if root is None else root / "assets" / "colour_profiles"
        if profile_path is None or not any(profile_path.glob("*")):
            issues.append(
                PreflightIssue(
                    "PD-PRE-010",
                    "warning",
                    "PDF/X-4 profile selected without colour profiles under assets/colour_profiles",
                )
            )
    try:
        from pydesign.extensions import REGISTRY

        for message in REGISTRY.run_preflight(dict(layout)):
            issues.append(PreflightIssue("PD-PRE-EXT", "warning", message))
    except ImportError:
        pass
    waived = set(waivers)
    return [issue for issue in issues if issue.code not in waived]


def load_waivers(project_root: str | Path) -> tuple[str, ...]:
    path = Path(project_root).expanduser().resolve() / ".pydesign" / "waivers.txt"
    if not path.is_file():
        return ()
    codes: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text and not text.startswith("#"):
            codes.append(text.split()[0])
    return tuple(codes)


def _image_issues(operation: Mapping[str, Any], root: Path | None) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    path_value = operation.get("path")
    object_id = operation.get("object_id")
    if not path_value:
        issues.append(
            PreflightIssue("PD-PRE-003", "error", f"image {object_id!r} is missing a path")
        )
        return issues
    resolved = Path(str(path_value))
    if not resolved.is_file() and root is not None:
        resolved = root / str(path_value)
    if not resolved.is_file():
        issues.append(
            PreflightIssue("PD-PRE-003", "error", f"image {object_id!r} path missing: {path_value}")
        )
        return issues
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    expected = operation.get("content_sha256")
    if isinstance(expected, str) and expected and expected != digest:
        issues.append(
            PreflightIssue(
                "PD-PRE-005",
                "error",
                f"image {object_id!r} content changed; refuse stale export",
            )
        )
    width = float(operation.get("width") or 0)
    if 0 < width < 8:
        issues.append(
            PreflightIssue(
                "PD-PRE-006",
                "warning",
                f"image {object_id!r} frame is very small; check effective DPI",
            )
        )
    return issues
