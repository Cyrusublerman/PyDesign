"""Deterministic context passed to project build functions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BuildContext:
    root: Path
    profile: str = "screen"
    deterministic: bool = True
    seed: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())

    def path(self, relative: str | Path) -> Path:
        """Resolve a project-relative path without requiring it to exist."""

        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise ValueError(f"path leaves project root: {relative}") from error
        return candidate

    def read_text(self, relative: str | Path, *, encoding: str = "utf-8") -> str:
        return self.path(relative).read_text(encoding=encoding)
