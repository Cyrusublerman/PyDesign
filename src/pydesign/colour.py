"""Colour objects for Stage 6 soft-proof and resource diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RGBColour:
    r: float
    g: float
    b: float

    def to_hex(self) -> str:
        red = max(0, min(255, round(self.r * 255)))
        green = max(0, min(255, round(self.g * 255)))
        blue = max(0, min(255, round(self.b * 255)))
        return f"#{red:02x}{green:02x}{blue:02x}"


@dataclass(frozen=True, slots=True)
class CMYKColour:
    c: float
    m: float
    y: float
    k: float


@dataclass(frozen=True, slots=True)
class SpotColour:
    name: str
    alt: RGBColour | CMYKColour


def parse_hex_rgb(value: str) -> RGBColour:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"expected #RRGGBB colour, got {value!r}")
    return RGBColour(
        int(text[0:2], 16) / 255.0,
        int(text[2:4], 16) / 255.0,
        int(text[4:6], 16) / 255.0,
    )
