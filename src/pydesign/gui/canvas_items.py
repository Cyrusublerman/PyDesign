"""Selectable canvas scene items and handles."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
)

from pydesign.gui.types import BezierPoints
from pydesign.source import Frame

SELECTION_PEN = QPen(QColor("#5b32a3"), 2.0)
SELECTION_PEN.setCosmetic(True)


class EditableFrameItem(QGraphicsRectItem):
    """Movable/resizable scene proxy that commits on interaction release."""

    def __init__(
        self,
        *,
        object_id: str,
        page_id: str,
        page_y: float,
        frame: Frame,
        commit: Callable[[str, Frame, Frame], None],
    ) -> None:
        x, y, width, height = frame
        super().__init__(0.0, 0.0, width, height)
        self.object_id = object_id
        self.page_id = page_id
        self.page_y = page_y
        self.source_frame = frame
        self._press_position = QPointF(x, page_y + y)
        self._commit = commit
        self._authored_pen = QPen(Qt.PenStyle.NoPen)
        self.setPos(x, page_y + y)
        self.setData(0, object_id)
        self.setToolTip(object_id)
        self.resize_handle = FrameResizeHandle(self)
        self.resize_handle.setVisible(False)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def set_authored_pen(self, pen: QPen) -> None:
        self._authored_pen = QPen(pen)
        if not self.isSelected():
            self.setPen(self._authored_pen)

    def frame_points(self) -> Frame:
        return (
            self.pos().x(),
            self.pos().y() - self.page_y,
            self.rect().width(),
            self.rect().height(),
        )

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self._press_position = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if self.pos() == self._press_position:
            return
        self._commit(self.object_id, self.source_frame, self.frame_points())

    def set_frame_size(self, width: float, height: float) -> None:
        self.setRect(0.0, 0.0, max(1.0, width), max(1.0, height))
        self.resize_handle.setPos(self.rect().width(), self.rect().height())

    def commit_resize(self, previous: Frame) -> None:
        desired = self.frame_points()
        if desired != previous:
            self._commit(self.object_id, previous, desired)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            selected = bool(value)
            self.resize_handle.setVisible(selected)
            self.setPen(SELECTION_PEN if selected else self._authored_pen)
        return super().itemChange(change, value)


class FrameResizeHandle(QGraphicsRectItem):
    """Bottom-right direct-manipulation handle for an editable frame."""

    def __init__(self, owner: EditableFrameItem) -> None:
        super().__init__(-5.0, -5.0, 10.0, 10.0, owner)
        self.owner = owner
        self.previous = owner.frame_points()
        self.setToolTip("Resize frame")
        self.setBrush(QColor("#ffffff"))
        self.setPen(QPen(QColor("#5b32a3"), 1.0))
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setZValue(1000.0)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setPos(owner.rect().width(), owner.rect().height())

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.previous = self.owner.frame_points()
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        local = self.owner.mapFromScene(event.scenePos())
        self.owner.set_frame_size(local.x(), local.y())
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.owner.commit_resize(self.previous)
        event.accept()


class EditableBezierItem(QGraphicsPathItem):
    """One cubic segment with four directly editable source-backed points."""

    def __init__(
        self,
        *,
        object_id: str,
        page_y: float,
        points: BezierPoints,
        commit: Callable[[str, BezierPoints, BezierPoints], None],
    ) -> None:
        super().__init__()
        self.object_id = object_id
        self.page_y = page_y
        self.source_points = points
        self._commit = commit
        self._scene_points = [QPointF(x, page_y + y) for x, y in points]
        self._authored_pen = QPen(Qt.PenStyle.NoPen)
        self.control_lines = [QGraphicsLineItem(self), QGraphicsLineItem(self)]
        for line in self.control_lines:
            line.setPen(QPen(QColor("#8d62d9"), 0.75, Qt.PenStyle.DashLine))
            line.setVisible(False)
        self.handles = [BezierControlHandle(self, index) for index in range(4)]
        self.setData(0, object_id)
        self.setToolTip(object_id)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self._update_geometry()

    def set_authored_pen(self, pen: QPen) -> None:
        self._authored_pen = QPen(pen)
        if not self.isSelected():
            self.setPen(self._authored_pen)

    def points_local(self) -> BezierPoints:
        return tuple((point.x(), point.y() - self.page_y) for point in self._scene_points)  # type: ignore[return-value]

    def set_control_point(self, index: int, point: QPointF) -> None:
        self._scene_points[index] = point
        self._update_geometry()

    def commit_points(self, previous: BezierPoints) -> None:
        desired = self.points_local()
        if desired != previous:
            self._commit(self.object_id, previous, desired)

    def _update_geometry(self) -> None:
        start, control_1, control_2, end = self._scene_points
        path = QPainterPath(start)
        path.cubicTo(control_1, control_2, end)
        self.setPath(path)
        self.control_lines[0].setLine(start.x(), start.y(), control_1.x(), control_1.y())
        self.control_lines[1].setLine(control_2.x(), control_2.y(), end.x(), end.y())
        for handle, point in zip(self.handles, self._scene_points, strict=True):
            handle.setPos(point)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            visible = bool(value)
            for handle in self.handles:
                handle.setVisible(visible)
            for line in self.control_lines:
                line.setVisible(visible)
            self.setPen(SELECTION_PEN if visible else self._authored_pen)
        return super().itemChange(change, value)


class BezierControlHandle(QGraphicsRectItem):
    def __init__(self, owner: EditableBezierItem, index: int) -> None:
        super().__init__(-5.0, -5.0, 10.0, 10.0, owner)
        self.owner = owner
        self.index = index
        self.previous = owner.source_points
        self.setBrush(QColor("#ffffff") if index in {0, 3} else QColor("#8d62d9"))
        self.setPen(QPen(QColor("#5b32a3"), 1.0))
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setZValue(1000.0)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setVisible(False)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.previous = self.owner.points_local()
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.owner.set_control_point(self.index, event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.owner.commit_points(self.previous)
        event.accept()
