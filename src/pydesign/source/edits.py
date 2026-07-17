"""Shared value contracts for visible-Python edit plans."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

type Frame = tuple[float, float, float, float]
type Point = tuple[float, float]
type FrameStrategy = Literal["safe", "adjust", "detach", "edit_shared"]


class SourceRewriteError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourceEditPlan:
    path: Path
    before: str
    after: str
    description: str
    object_id: str
    property_name: str
    strategy: str

    @property
    def changed(self) -> bool:
        return self.before != self.after

    def unified_diff(self) -> str:
        return "".join(
            difflib.unified_diff(
                self.before.splitlines(keepends=True),
                self.after.splitlines(keepends=True),
                fromfile=str(self.path),
                tofile=str(self.path),
            )
        )
