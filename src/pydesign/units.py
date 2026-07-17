"""Typed physical units used by author source and layout."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class Length:
    """A physical length stored as PostScript points (1/72 inch)."""

    points: float

    def __post_init__(self) -> None:
        value = float(self.points)
        if not isfinite(value):
            raise ValueError("length must be finite")
        object.__setattr__(self, "points", value)

    def __add__(self, other: LengthLike) -> Length:
        return Length(self.points + as_points(other))

    def __radd__(self, other: LengthLike) -> Length:
        return self + other

    def __sub__(self, other: LengthLike) -> Length:
        return Length(self.points - as_points(other))

    def __rsub__(self, other: LengthLike) -> Length:
        return Length(as_points(other) - self.points)

    def __mul__(self, scalar: float) -> Length:
        return Length(self.points * float(scalar))

    def __rmul__(self, scalar: float) -> Length:
        return self * scalar

    def __truediv__(self, divisor: float | Length) -> Length | float:
        if isinstance(divisor, Length):
            return self.points / divisor.points
        return Length(self.points / float(divisor))

    def __neg__(self) -> Length:
        return Length(-self.points)

    def __float__(self) -> float:
        return self.points

    def to(self, unit: Length) -> float:
        """Return the numeric value expressed in ``unit``."""

        return self.points / unit.points


type LengthLike = Length | int | float


def as_points(value: LengthLike) -> float:
    """Normalize a public length value to points; bare numbers mean points."""

    if isinstance(value, Length):
        return value.points
    result = float(value)
    if not isfinite(result):
        raise ValueError("length must be finite")
    return result


def as_length(value: LengthLike) -> Length:
    return value if isinstance(value, Length) else Length(value)


pt = Length(1.0)
inch = Length(72.0)
pc = Length(12.0)
mm = Length(72.0 / 25.4)
cm = Length(10.0 * mm.points)

# CSS pixel convenience. Print projects should prefer physical units.
px = Length(72.0 / 96.0)
