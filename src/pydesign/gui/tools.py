"""Canvas tool registry for the desktop toolbox.

Layout model (design 06):
- Left toolbox holds persistent tools only.
- Shape variants live behind one Shape tool, not as permanent clutter.
- View/fit/zoom controls belong on a View bar, not in tool options.
- Tool options show only the active tool's context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ToolId = Literal[
    "select",
    "direct_select",
    "frame",
    "shape",
    "pen",
    "line",
    "text",
    "eyedropper",
    "hand",
    "zoom",
]
ShapeVariant = Literal["rectangle", "ellipse", "polygon"]
ToolAvailability = Literal["live", "stub"]
ToolGroup = Literal["select", "create", "navigate"]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    tool_id: ToolId
    label: str
    shortcut: str
    availability: ToolAvailability
    stage_hint: str
    status_hint: str
    group: ToolGroup


@dataclass(frozen=True, slots=True)
class ShapeVariantSpec:
    variant_id: ShapeVariant
    label: str
    shortcut: str
    availability: ToolAvailability
    stage_hint: str


# Persistent toolbox tools — Shape covers rectangle/ellipse/polygon.
TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "select",
        "Select",
        "V",
        "live",
        "",
        "Click to select · drag empty pasteboard to pan",
        "select",
    ),
    ToolSpec(
        "direct_select",
        "Direct Select",
        "A",
        "live",
        "",
        "Select paths to edit Bézier nodes and handles · Esc clears selection",
        "select",
    ),
    ToolSpec("frame", "Frame", "F", "stub", "Stage 5", "Create a text or content frame", "create"),
    ToolSpec(
        "shape",
        "Shape",
        "R",
        "live",
        "",
        "Drag on a page to create the active shape variant · Esc cancels",
        "create",
    ),
    ToolSpec(
        "pen",
        "Pen",
        "B",
        "live",
        "",
        "Click four points for a cubic Bézier · full Pen arrives later · Esc cancels",
        "create",
    ),
    ToolSpec("line", "Line", "L", "live", "", "Draw a straight line segment", "create"),
    ToolSpec(
        "text",
        "Text",
        "T",
        "live",
        "",
        "Drag on a page to create a text frame · Esc cancels",
        "create",
    ),
    ToolSpec(
        "eyedropper",
        "Eyedropper",
        "I",
        "stub",
        "Stage 6",
        "Sample appearance from an object",
        "create",
    ),
    ToolSpec("hand", "Hand", "H", "live", "", "Drag to pan the pasteboard", "navigate"),
    ToolSpec(
        "zoom",
        "Zoom",
        "Z",
        "live",
        "",
        "Click to zoom in · Alt-click to zoom out · double-click fits page",
        "navigate",
    ),
)

SHAPE_VARIANTS: tuple[ShapeVariantSpec, ...] = (
    ShapeVariantSpec("rectangle", "Rectangle", "R", "live", ""),
    ShapeVariantSpec("ellipse", "Ellipse", "E", "live", ""),
    ShapeVariantSpec("polygon", "Polygon", "N", "stub", "Stage 6"),
)

TOOL_BY_ID: dict[str, ToolSpec] = {tool.tool_id: tool for tool in TOOLS}
SHAPE_BY_ID: dict[str, ShapeVariantSpec] = {item.variant_id: item for item in SHAPE_VARIANTS}

# Map legacy canvas create modes / shortcuts onto toolbox tools.
CANVAS_CREATE_MODES = {
    "rectangle": "shape",
    "bezier": "pen",
    "pen": "pen",
}


def live_tools() -> tuple[ToolSpec, ...]:
    return tuple(tool for tool in TOOLS if tool.availability == "live")
