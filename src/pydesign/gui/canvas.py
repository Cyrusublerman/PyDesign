"""Interactive page canvas and direct-manipulation tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
)

from pydesign.gui.types import BezierPoints, PageRegion
from pydesign.source import Frame


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
            self.resize_handle.setVisible(bool(value))
        return super().itemChange(change, value)


class FrameResizeHandle(QGraphicsRectItem):
    """Bottom-right direct-manipulation handle for an editable frame."""

    def __init__(self, owner: EditableFrameItem) -> None:
        super().__init__(-4.0, -4.0, 8.0, 8.0, owner)
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
        self.control_lines = [QGraphicsLineItem(self), QGraphicsLineItem(self)]
        for line in self.control_lines:
            line.setPen(QPen(QColor("#8d62d9"), 0.75, Qt.PenStyle.DashLine))
            line.setVisible(False)
        self.handles = [BezierControlHandle(self, index) for index in range(4)]
        self.setData(0, object_id)
        self.setToolTip(object_id)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self._update_geometry()

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
        return super().itemChange(change, value)


class BezierControlHandle(QGraphicsRectItem):
    def __init__(self, owner: EditableBezierItem, index: int) -> None:
        super().__init__(-4.0, -4.0, 8.0, 8.0, owner)
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


class PageCanvas(QGraphicsView):
    object_selected = Signal(str, object)
    frame_committed = Signal(str, object, object)
    rectangle_created = Signal(str, object)
    bezier_created = Signal(str, object)
    bezier_committed = Signal(str, object, object)

    def __init__(self) -> None:
        self.canvas_scene = QGraphicsScene()
        super().__init__(self.canvas_scene)
        self.setAccessibleName("Document canvas")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setBackgroundBrush(QColor("#35383d"))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.canvas_scene.selectionChanged.connect(self._selection_changed)
        self._page_regions: list[PageRegion] = []
        self._object_items: dict[str, QGraphicsItem] = {}
        self._create_mode: str | None = None
        self._create_origin: QPointF | None = None
        self._create_page: PageRegion | None = None
        self._create_preview: QGraphicsRectItem | None = None
        self._bezier_points: list[QPointF] = []
        self._bezier_preview: QGraphicsPathItem | None = None

    def set_layout(self, layout: dict[str, Any]) -> None:
        self.canvas_scene.clear()
        self._page_regions.clear()
        self._object_items.clear()
        y_offset = 24.0
        pages = layout.get("pages", [])
        if not isinstance(pages, list):
            return
        for page_number, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                continue
            page_id = str(page.get("id", f"page-{page_number}"))
            width = float(page.get("width", 0.0))
            height = float(page.get("height", 0.0))
            self._page_regions.append(PageRegion(page_id, 0.0, y_offset, width, height))
            paper = self.canvas_scene.addRect(
                0.0,
                y_offset,
                width,
                height,
                QPen(QColor("#b8bcc2"), 0.75),
                QColor("#ffffff"),
            )
            paper.setZValue(-1000)
            paper.setData(0, page_id)
            operations = page.get("operations", [])
            if isinstance(operations, list):
                for operation in operations:
                    if isinstance(operation, dict):
                        self._draw_operation(operation, page_id, y_offset)
            label = self.canvas_scene.addSimpleText(
                f"{page_number} · {page_id}", QFont("Sans Serif", 7)
            )
            label.setBrush(QColor("#d8dbe0"))
            label.setPos(0.0, y_offset + height + 4.0)
            y_offset += height + 54.0
        if pages:
            self.fitInView(
                self.canvas_scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio
            )

    def _draw_operation(self, operation: dict[str, Any], page_id: str, page_y: float) -> None:
        kind = operation.get("op")
        if kind == "bezier_path":
            self._draw_bezier_operation(operation, page_y)
            return
        if kind not in {"rectangle", "text_placeholder"}:
            return
        object_id = str(operation.get("object_id", ""))
        frame: Frame = (
            float(operation.get("x", 0.0)),
            float(operation.get("y", 0.0)),
            float(operation.get("width", 0.0)),
            float(operation.get("height", 0.0)),
        )
        item = EditableFrameItem(
            object_id=object_id,
            page_id=page_id,
            page_y=page_y,
            frame=frame,
            commit=self._frame_commit,
        )
        self._object_items[object_id] = item
        self.canvas_scene.addItem(item)

        if kind == "rectangle":
            fill_value = operation.get("fill")
            stroke_value = operation.get("stroke")
            item.setBrush(
                QColor(str(fill_value)) if fill_value else QColor(Qt.GlobalColor.transparent)
            )
            item.setPen(
                QPen(QColor(str(stroke_value)), float(operation.get("stroke_width", 1.0)))
                if stroke_value
                else QPen(Qt.PenStyle.NoPen)
            )
            return

        item.setPen(QPen(QColor("#87909c"), 0.5, Qt.PenStyle.DashLine))
        text = self.canvas_scene.addText(str(operation.get("text", "")))
        text.setParentItem(item)
        font = text.font()
        font.setPointSizeF(max(1.0, float(operation.get("font_size", 12.0))))
        text.setFont(font)
        text.setDefaultTextColor(QColor(str(operation.get("colour", "#000000"))))
        text.setTextWidth(frame[2])
        text.setPos(0.0, 0.0)
        text.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def _draw_bezier_operation(self, operation: dict[str, Any], page_y: float) -> None:
        commands = operation.get("commands")
        if not isinstance(commands, list):
            return
        path = QPainterPath()
        for command in commands:
            if not isinstance(command, dict):
                continue
            kind = command.get("command")
            if kind == "move":
                path.moveTo(float(command.get("x", 0.0)), page_y + float(command.get("y", 0.0)))
            elif kind == "line":
                path.lineTo(float(command.get("x", 0.0)), page_y + float(command.get("y", 0.0)))
            elif kind == "curve":
                path.cubicTo(
                    float(command.get("control_1_x", 0.0)),
                    page_y + float(command.get("control_1_y", 0.0)),
                    float(command.get("control_2_x", 0.0)),
                    page_y + float(command.get("control_2_y", 0.0)),
                    float(command.get("x", 0.0)),
                    page_y + float(command.get("y", 0.0)),
                )
            elif kind == "close":
                path.closeSubpath()
        object_id = str(operation.get("object_id", ""))
        editable_points = _editable_bezier_points(commands)
        item: QGraphicsPathItem
        if editable_points is not None:
            item = EditableBezierItem(
                object_id=object_id,
                page_y=page_y,
                points=editable_points,
                commit=self._bezier_commit,
            )
        else:
            item = QGraphicsPathItem(path)
        item.setData(0, object_id)
        item.setToolTip(object_id)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        fill = operation.get("fill")
        stroke = operation.get("stroke")
        item.setBrush(QColor(str(fill)) if fill else QColor(Qt.GlobalColor.transparent))
        item.setPen(
            QPen(QColor(str(stroke)), float(operation.get("stroke_width", 1.0)))
            if stroke
            else QPen(Qt.PenStyle.NoPen)
        )
        self._object_items[object_id] = item
        self.canvas_scene.addItem(item)

    def _bezier_commit(self, object_id: str, previous: BezierPoints, desired: BezierPoints) -> None:
        self.bezier_committed.emit(object_id, previous, desired)

    def _frame_commit(self, object_id: str, previous: Frame, desired: Frame) -> None:
        self.frame_committed.emit(object_id, previous, desired)

    def _selection_changed(self) -> None:
        selected = self.canvas_scene.selectedItems()
        if not selected:
            self.object_selected.emit("", None)
            return
        item = selected[0]
        object_id = str(item.data(0))
        frame = item.frame_points() if isinstance(item, EditableFrameItem) else None
        self.object_selected.emit(object_id, frame)

    def select_object(self, object_id: str) -> None:
        self.canvas_scene.clearSelection()
        item = self._object_items.get(object_id)
        if item is not None:
            item.setSelected(True)
            self.centerOn(item)

    def begin_rectangle(self) -> None:
        self.cancel_tool()
        self._create_mode = "rectangle"
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def begin_bezier(self) -> None:
        self.cancel_tool()
        self._create_mode = "bezier"
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def cancel_tool(self) -> None:
        self._create_mode = None
        self._create_origin = None
        self._create_page = None
        if self._create_preview is not None:
            self.canvas_scene.removeItem(self._create_preview)
            self._create_preview = None
        self._bezier_points.clear()
        if self._bezier_preview is not None:
            self.canvas_scene.removeItem(self._bezier_preview)
            self._bezier_preview = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.unsetCursor()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._create_mode == "bezier" and event.button() == Qt.MouseButton.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            page = self._create_page or next(
                (region for region in self._page_regions if region.contains(point)), None
            )
            if page is not None and page.contains(point):
                self._create_page = page
                self._bezier_points.append(point)
                if len(self._bezier_points) == 4:
                    points: BezierPoints = tuple(
                        (item.x() - page.x, item.y() - page.y) for item in self._bezier_points
                    )  # type: ignore[assignment]
                    page_id = page.page_id
                    self.cancel_tool()
                    self.bezier_created.emit(page_id, points)
                event.accept()
                return
        if self._create_mode == "rectangle" and event.button() == Qt.MouseButton.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            page = next((region for region in self._page_regions if region.contains(point)), None)
            if page is not None:
                self._create_origin = point
                self._create_page = page
                self._create_preview = self.canvas_scene.addRect(
                    point.x(),
                    point.y(),
                    0.0,
                    0.0,
                    QPen(QColor("#8d62d9"), 1.0, Qt.PenStyle.DashLine),
                    QColor(141, 98, 217, 40),
                )
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._create_mode == "bezier" and self._bezier_points:
            self._update_bezier_preview(self.mapToScene(event.position().toPoint()))
            event.accept()
            return
        if self._create_origin is not None and self._create_preview is not None:
            point = self.mapToScene(event.position().toPoint())
            self._create_preview.setRect(_normal_rect(self._create_origin, point))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _update_bezier_preview(self, current: QPointF) -> None:
        points = [*self._bezier_points, current]
        path = QPainterPath(points[0])
        if len(points) == 2:
            path.lineTo(points[1])
        elif len(points) == 3:
            path.cubicTo(points[1], points[2], points[2])
        else:
            path.cubicTo(points[1], points[2], points[3])
        if self._bezier_preview is None:
            self._bezier_preview = self.canvas_scene.addPath(
                path, QPen(QColor("#5b32a3"), 1.0, Qt.PenStyle.DashLine)
            )
        else:
            self._bezier_preview.setPath(path)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            self._create_origin is not None
            and self._create_preview is not None
            and self._create_page is not None
            and self._create_mode == "rectangle"
        ):
            rectangle = self._create_preview.rect()
            page = self._create_page
            frame: Frame = (
                rectangle.x() - page.x,
                rectangle.y() - page.y,
                rectangle.width(),
                rectangle.height(),
            )
            self.cancel_tool()
            if frame[2] >= 1.0 and frame[3] >= 1.0:
                self.rectangle_created.emit(page.page_id, frame)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: Any) -> None:
        if event.key() == Qt.Key.Key_Escape and self._create_mode is not None:
            self.cancel_tool()
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event: Any) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)


def _normal_rect(first: QPointF, second: QPointF) -> Any:
    from PySide6.QtCore import QRectF

    return QRectF(first, second).normalized()


def _editable_bezier_points(commands: list[object]) -> BezierPoints | None:
    if len(commands) != 2 or not all(isinstance(command, dict) for command in commands):
        return None
    move = commands[0]
    curve = commands[1]
    if not isinstance(move, dict) or not isinstance(curve, dict):
        return None
    if move.get("command") != "move" or curve.get("command") != "curve":
        return None
    try:
        return (
            (float(move["x"]), float(move["y"])),
            (float(curve["control_1_x"]), float(curve["control_1_y"])),
            (float(curve["control_2_x"]), float(curve["control_2_y"])),
            (float(curve["x"]), float(curve["y"])),
        )
    except (KeyError, TypeError, ValueError):
        return None
