"""Shared GUI value contracts and runtime narrowing helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TypeGuard

from PySide6.QtCore import QPointF

from pydesign.source import Frame
from pydesign.source.path_rewrite import BezierPoints as SourceBezierPoints

type BezierPoints = SourceBezierPoints


@dataclass(frozen=True, slots=True)
class PageRegion:
    page_id: str
    x: float
    y: float
    width: float
    height: float

    def contains(self, point: QPointF) -> bool:
        return (
            self.x <= point.x() <= self.x + self.width
            and self.y <= point.y() <= self.y + self.height
        )


def _is_frame(value: object) -> TypeGuard[Frame]:
    return (
        isinstance(value, tuple)
        and len(value) == 4
        and all(isinstance(item, (int, float)) and math.isfinite(item) for item in value)
    )


def _is_bezier_points(value: object) -> TypeGuard[BezierPoints]:
    return (
        isinstance(value, tuple)
        and len(value) == 4
        and all(
            isinstance(point, tuple)
            and len(point) == 2
            and all(
                isinstance(coordinate, (int, float)) and math.isfinite(coordinate)
                for coordinate in point
            )
            for point in value
        )
    )
