"""Create-mode helpers for PageCanvas (keeps canvas.py under budget)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsView


def begin_rectangle(canvas: Any, *, variant: str = "rectangle") -> None:
    canvas.cancel_create()
    canvas._create_mode = "ellipse" if variant == "ellipse" else "rectangle"
    canvas._active_tool = "shape"
    canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
    canvas.setCursor(Qt.CursorShape.CrossCursor)
    canvas.tool_changed.emit(canvas._active_tool)


def begin_line(canvas: Any) -> None:
    canvas.cancel_create()
    canvas._create_mode = "line"
    canvas._active_tool = "line"
    canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
    canvas.setCursor(Qt.CursorShape.CrossCursor)
    canvas.tool_changed.emit(canvas._active_tool)


def begin_bezier(canvas: Any) -> None:
    canvas.cancel_create()
    canvas._create_mode = "bezier"
    canvas._active_tool = "pen"
    canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
    canvas.setCursor(Qt.CursorShape.CrossCursor)
    canvas.tool_changed.emit(canvas._active_tool)


def begin_text(canvas: Any) -> None:
    canvas.cancel_create()
    canvas._create_mode = "text"
    canvas._active_tool = "text"
    canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
    canvas.setCursor(Qt.CursorShape.IBeamCursor)
    canvas.tool_changed.emit(canvas._active_tool)
