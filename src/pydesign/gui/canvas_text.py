"""Glyph-run outline painting helpers for PageCanvas."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem

from pydesign.gui.canvas_items import EditableFrameItem


def paint_glyph_run(operation: dict[str, Any], parent: EditableFrameItem) -> None:
    colour = QColor(str(operation.get("colour", "#111827")))
    parent.setBrush(QColor(Qt.GlobalColor.transparent))
    parent.set_authored_pen(QPen(QColor("#94a3b8"), 0.5, Qt.PenStyle.DotLine))
    path = QPainterPath()
    flow = operation.get("flow_outlines")
    if isinstance(flow, list):
        for entry in flow:
            if not isinstance(entry, dict):
                continue
            append_outline_commands(
                path,
                entry.get("outlines"),
                float(entry.get("x", 0.0)),
                float(entry.get("y", 0.0)),
            )
    else:
        append_outline_commands(path, operation.get("outlines"), 0.0, 0.0)
    glyph_item = QGraphicsPathItem(path, parent)
    glyph_item.setBrush(colour)
    glyph_item.setPen(QPen(Qt.PenStyle.NoPen))
    glyph_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)


def append_outline_commands(
    path: QPainterPath, outlines: object, origin_x: float, origin_y: float
) -> None:
    if not isinstance(outlines, list):
        return
    for outline in outlines:
        if not isinstance(outline, dict):
            continue
        commands = outline.get("commands")
        if not isinstance(commands, list):
            continue
        for command in commands:
            if not isinstance(command, dict):
                continue
            kind = command.get("command")
            if kind == "move":
                path.moveTo(
                    origin_x + float(command.get("x", 0.0)),
                    origin_y + float(command.get("y", 0.0)),
                )
            elif kind == "line":
                path.lineTo(
                    origin_x + float(command.get("x", 0.0)),
                    origin_y + float(command.get("y", 0.0)),
                )
            elif kind == "close":
                path.closeSubpath()
