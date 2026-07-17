"""Retained semantic document model for the first vertical slice."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from pydesign.units import Length, LengthLike, as_length


@dataclass(frozen=True, slots=True)
class Size:
    width: Length
    height: Length

    def __init__(self, width: LengthLike, height: LengthLike) -> None:
        object.__setattr__(self, "width", as_length(width))
        object.__setattr__(self, "height", as_length(height))

    def to_points(self) -> tuple[float, float]:
        return self.width.points, self.height.points


type SizeLike = Size | tuple[LengthLike, LengthLike]


@dataclass(frozen=True, slots=True)
class Rect:
    x: Length
    y: Length
    width: Length
    height: Length

    def __init__(
        self,
        x: LengthLike,
        y: LengthLike,
        width: LengthLike,
        height: LengthLike,
    ) -> None:
        object.__setattr__(self, "x", as_length(x))
        object.__setattr__(self, "y", as_length(y))
        object.__setattr__(self, "width", as_length(width))
        object.__setattr__(self, "height", as_length(height))

    def to_points(self) -> tuple[float, float, float, float]:
        return self.x.points, self.y.points, self.width.points, self.height.points


type RectLike = Rect | tuple[LengthLike, LengthLike, LengthLike, LengthLike]


def _size(value: SizeLike) -> Size:
    return value if isinstance(value, Size) else Size(*value)


def _rect(value: RectLike) -> Rect:
    return value if isinstance(value, Rect) else Rect(*value)


@dataclass(frozen=True, slots=True, kw_only=True)
class Element:
    id: str
    label: str | None = None
    visible: bool = True
    printable: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class Rectangle(Element):
    frame: Rect
    fill: str | None = "#000000"
    stroke: str | None = None
    stroke_width: Length = field(default_factory=lambda: Length(1.0))

    def __init__(
        self,
        *,
        id: str,
        frame: RectLike,
        label: str | None = None,
        visible: bool = True,
        printable: bool = True,
        fill: str | None = "#000000",
        stroke: str | None = None,
        stroke_width: LengthLike = 1.0,
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "visible", visible)
        object.__setattr__(self, "printable", printable)
        object.__setattr__(self, "frame", _rect(frame))
        object.__setattr__(self, "fill", fill)
        object.__setattr__(self, "stroke", stroke)
        object.__setattr__(self, "stroke_width", as_length(stroke_width))


@dataclass(frozen=True, slots=True)
class MoveTo:
    x: Length
    y: Length

    def __init__(self, x: LengthLike, y: LengthLike) -> None:
        object.__setattr__(self, "x", as_length(x))
        object.__setattr__(self, "y", as_length(y))


@dataclass(frozen=True, slots=True)
class LineTo:
    x: Length
    y: Length

    def __init__(self, x: LengthLike, y: LengthLike) -> None:
        object.__setattr__(self, "x", as_length(x))
        object.__setattr__(self, "y", as_length(y))


@dataclass(frozen=True, slots=True)
class CurveTo:
    control_1_x: Length
    control_1_y: Length
    control_2_x: Length
    control_2_y: Length
    x: Length
    y: Length

    def __init__(
        self,
        control_1_x: LengthLike,
        control_1_y: LengthLike,
        control_2_x: LengthLike,
        control_2_y: LengthLike,
        x: LengthLike,
        y: LengthLike,
    ) -> None:
        object.__setattr__(self, "control_1_x", as_length(control_1_x))
        object.__setattr__(self, "control_1_y", as_length(control_1_y))
        object.__setattr__(self, "control_2_x", as_length(control_2_x))
        object.__setattr__(self, "control_2_y", as_length(control_2_y))
        object.__setattr__(self, "x", as_length(x))
        object.__setattr__(self, "y", as_length(y))


@dataclass(frozen=True, slots=True)
class ClosePath:
    pass


type PathCommand = MoveTo | LineTo | CurveTo | ClosePath


@dataclass(frozen=True, slots=True, kw_only=True)
class BezierPath(Element):
    commands: tuple[PathCommand, ...]
    fill: str | None = None
    stroke: str | None = "#000000"
    stroke_width: Length = field(default_factory=lambda: Length(1.0))

    def __init__(
        self,
        *,
        id: str,
        commands: Iterable[PathCommand],
        label: str | None = None,
        visible: bool = True,
        printable: bool = True,
        fill: str | None = None,
        stroke: str | None = "#000000",
        stroke_width: LengthLike = 1.0,
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "visible", visible)
        object.__setattr__(self, "printable", printable)
        object.__setattr__(self, "commands", tuple(commands))
        object.__setattr__(self, "fill", fill)
        object.__setattr__(self, "stroke", stroke)
        object.__setattr__(self, "stroke_width", as_length(stroke_width))


@dataclass(frozen=True, slots=True, kw_only=True)
class TextFrame(Element):
    frame: Rect
    text: str
    font_size: Length = field(default_factory=lambda: Length(12.0))
    colour: str = "#000000"

    def __init__(
        self,
        *,
        id: str,
        frame: RectLike,
        text: str,
        label: str | None = None,
        visible: bool = True,
        printable: bool = True,
        font_size: LengthLike = 12.0,
        colour: str = "#000000",
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "visible", visible)
        object.__setattr__(self, "printable", printable)
        object.__setattr__(self, "frame", _rect(frame))
        object.__setattr__(self, "text", str(text))
        object.__setattr__(self, "font_size", as_length(font_size))
        object.__setattr__(self, "colour", colour)


type LeafElement = BezierPath | Rectangle | TextFrame


@dataclass(frozen=True, slots=True, kw_only=True)
class Layer(Element):
    elements: tuple[LeafElement, ...] = ()

    def __init__(
        self,
        *,
        id: str,
        elements: Iterable[LeafElement] = (),
        label: str | None = None,
        visible: bool = True,
        printable: bool = True,
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "visible", visible)
        object.__setattr__(self, "printable", printable)
        object.__setattr__(self, "elements", tuple(elements))


@dataclass(frozen=True, slots=True, kw_only=True)
class Page(Element):
    size: Size
    elements: tuple[LeafElement, ...] = ()
    layers: tuple[Layer, ...] = ()

    def __init__(
        self,
        *,
        id: str,
        size: SizeLike,
        elements: Iterable[LeafElement] = (),
        layers: Iterable[Layer] = (),
        label: str | None = None,
        visible: bool = True,
        printable: bool = True,
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "visible", visible)
        object.__setattr__(self, "printable", printable)
        object.__setattr__(self, "size", _size(size))
        object.__setattr__(self, "elements", tuple(elements))
        object.__setattr__(self, "layers", tuple(layers))

    def iter_elements(self) -> Iterable[LeafElement]:
        yield from self.elements
        for layer in self.layers:
            if layer.visible and layer.printable:
                yield from layer.elements


@dataclass(frozen=True, slots=True, kw_only=True)
class Document(Element):
    pages: tuple[Page, ...]
    title: str = "Untitled"

    def __init__(
        self,
        *,
        id: str,
        pages: Iterable[Page],
        title: str = "Untitled",
        label: str | None = None,
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "visible", True)
        object.__setattr__(self, "printable", True)
        object.__setattr__(self, "pages", tuple(pages))
        object.__setattr__(self, "title", title)
