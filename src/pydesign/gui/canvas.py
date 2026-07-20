"""Interactive page canvas, tools and touchpad-friendly view navigation."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt, Signal  # QRectF used by helpers
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from pydesign.gui.canvas_items import EditableBezierItem, EditableFrameItem
from pydesign.gui.canvas_text import paint_glyph_run
from pydesign.gui.canvas_view import CanvasNavigationMixin, ViewMode
from pydesign.gui.types import BezierPoints, PageRegion
from pydesign.source import Frame

# Compatibility export for smoke tests and external imports.
__all__ = ["EditableBezierItem", "PageCanvas"]


class PageCanvas(CanvasNavigationMixin, QGraphicsView):
    object_selected = Signal(str, object)
    frame_committed = Signal(str, object, object)
    rectangle_created = Signal(str, object, str)
    text_created = Signal(str, object)
    bezier_created = Signal(str, object)
    bezier_committed = Signal(str, object, object)
    tool_changed = Signal(str)
    view_changed = Signal()
    page_changed = Signal(int)

    def __init__(self) -> None:
        self.canvas_scene = QGraphicsScene()
        super().__init__(self.canvas_scene)
        self.setAccessibleName("Document canvas")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setBackgroundBrush(QColor("#35383d"))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.grabGesture(Qt.GestureType.PinchGesture)
        self.canvas_scene.selectionChanged.connect(self._selection_changed)
        self._page_regions: list[PageRegion] = []
        self._object_items: dict[str, QGraphicsItem] = {}
        self._page_summaries: list[dict[str, Any]] = []
        self._layer_names: list[str] = []
        self._layers: list[dict[str, Any]] = []
        self._document_id = ""
        self._active_tool = "select"
        self._create_mode: str | None = None
        self._create_origin: QPointF | None = None
        self._create_page: PageRegion | None = None
        self._create_preview: QGraphicsRectItem | None = None
        self._bezier_points: list[QPointF] = []
        self._bezier_preview: QGraphicsPathItem | None = None
        self._view_mode: ViewMode = "fit"
        self._current_page = 0
        self._has_layout = False
        self._space_pan = False
        self._saved_transform: QTransform | None = None
        self._saved_mode: ViewMode = "fit"
        self._saved_page = 0
        self._scroll_snap_armed = False

    @property
    def view_mode(self) -> ViewMode:
        return self._view_mode

    @property
    def current_page_index(self) -> int:
        return self._current_page

    @property
    def page_summaries(self) -> list[dict[str, Any]]:
        return list(self._page_summaries)

    @property
    def layer_names(self) -> list[str]:
        return list(self._layer_names)

    @property
    def layers(self) -> list[dict[str, Any]]:
        return list(self._layers)

    @property
    def document_id(self) -> str:
        return self._document_id

    def set_layout(self, layout: dict[str, Any]) -> None:
        restore = self._has_layout
        if restore:
            self._saved_transform = QTransform(self.transform())
            self._saved_mode = self._view_mode
            self._saved_page = self._current_page
        self.canvas_scene.clear()
        self._page_regions.clear()
        self._object_items.clear()
        self._page_summaries = []
        self._layer_names = []
        self._layers = []
        self._document_id = ""
        document = layout.get("document")
        if isinstance(document, dict):
            self._document_id = str(document.get("id", ""))
        layers = layout.get("layers")
        if isinstance(layers, list):
            for item in layers:
                if isinstance(item, dict):
                    self._layers.append(dict(item))
                    layer_id = str(item.get("id", ""))
                    if layer_id:
                        self._layer_names.append(layer_id)
                else:
                    self._layer_names.append(str(item))
        y_offset = 24.0
        pages = layout.get("pages", [])
        if not isinstance(pages, list):
            self._has_layout = False
            return
        for page_number, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                continue
            page_id = str(page.get("id", f"page-{page_number}"))
            width = float(page.get("width", 0.0))
            height = float(page.get("height", 0.0))
            self._page_regions.append(PageRegion(page_id, 0.0, y_offset, width, height))
            self._page_summaries.append(
                {"id": page_id, "width": width, "height": height, "index": page_number - 1}
            )
            shadow = self.canvas_scene.addRect(
                4.0,
                y_offset + 4.0,
                width,
                height,
                QPen(Qt.PenStyle.NoPen),
                QColor(0, 0, 0, 55),
            )
            shadow.setZValue(-1001)
            paper = self.canvas_scene.addRect(
                0.0,
                y_offset,
                width,
                height,
                QPen(QColor("#8b929c"), 1.0),
                QColor("#ffffff"),
            )
            paper.setZValue(-1000)
            paper.setData(0, page_id)
            operations = page.get("operations", [])
            if isinstance(operations, list):
                for operation in operations:
                    if isinstance(operation, dict):
                        self._draw_operation(operation, page_id, y_offset)
                        layer_name = operation.get("layer")
                        if isinstance(layer_name, str) and layer_name not in self._layer_names:
                            self._layer_names.append(layer_name)
            label = self.canvas_scene.addSimpleText(
                f"{page_number} · {page_id}", QFont("Sans Serif", 10)
            )
            label.setBrush(QColor("#f3f4f6"))
            label.setPos(0.0, y_offset + height + 6.0)
            y_offset += height + 54.0
        self._has_layout = bool(self._page_regions)
        if not self._has_layout:
            return
        if restore and self._saved_transform is not None:
            self._current_page = min(self._saved_page, len(self._page_regions) - 1)
            self._view_mode = self._saved_mode
            if self._view_mode in {"fit", "fill", "actual", "fit_all"}:
                self._apply_view_mode(self._view_mode, announce=False)
            else:
                self.setTransform(self._saved_transform)
            self.view_changed.emit()
            self.page_changed.emit(self._current_page)
            return
        self._current_page = 0
        self.fit_page(0)

    def _draw_operation(self, operation: dict[str, Any], page_id: str, page_y: float) -> None:
        kind = operation.get("op")
        if kind == "bezier_path":
            self._draw_bezier_operation(operation, page_y)
            return
        if kind not in {"rectangle", "ellipse", "image", "text_placeholder", "glyph_run"}:
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
        if kind in {"rectangle", "ellipse"}:
            fill_value = operation.get("fill")
            stroke_value = operation.get("stroke")
            item.setBrush(
                QColor(str(fill_value)) if fill_value else QColor(Qt.GlobalColor.transparent)
            )
            pen = (
                QPen(QColor(str(stroke_value)), float(operation.get("stroke_width", 1.0)))
                if stroke_value
                else QPen(Qt.PenStyle.NoPen)
            )
            item.set_authored_pen(pen)
            return
        if kind == "image":
            item.setBrush(QColor("#dbe4f0"))
            item.set_authored_pen(QPen(QColor("#7c93b2"), 1.0))
            label = self.canvas_scene.addSimpleText(
                f"IMG {operation.get('path', '')}", QFont("Sans Serif", 8)
            )
            label.setParentItem(item)
            label.setPos(4.0, 4.0)
            label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            return
        if kind == "glyph_run":
            paint_glyph_run(operation, item)
            return
        item.set_authored_pen(QPen(QColor("#4b5563"), 1.0, Qt.PenStyle.DashLine))
        # Placeholder only — not document composition (Stage 3 uses glyph_run outlines).
        label = self.canvas_scene.addSimpleText(
            str(operation.get("text", ""))[:80], QFont("Sans Serif", 9)
        )
        label.setBrush(QColor(str(operation.get("colour", "#111827"))))
        label.setParentItem(item)
        label.setPos(4.0, 4.0)
        label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

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
        authored = (
            QPen(QColor(str(operation.get("stroke"))), float(operation.get("stroke_width", 1.0)))
            if operation.get("stroke")
            else QPen(Qt.PenStyle.NoPen)
        )
        if editable_points is not None:
            bezier = EditableBezierItem(
                object_id=object_id,
                page_y=page_y,
                points=editable_points,
                commit=self._bezier_commit,
            )
            bezier.setBrush(
                QColor(str(operation.get("fill")))
                if operation.get("fill")
                else QColor(Qt.GlobalColor.transparent)
            )
            bezier.set_authored_pen(authored)
            item: QGraphicsPathItem = bezier
        else:
            item = QGraphicsPathItem(path)
            item.setBrush(
                QColor(str(operation.get("fill")))
                if operation.get("fill")
                else QColor(Qt.GlobalColor.transparent)
            )
            item.setPen(authored)
        item.setData(0, object_id)
        item.setToolTip(object_id)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
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
            self.ensureVisible(item, 40, 40)

    def clear_selection(self) -> None:
        self.canvas_scene.clearSelection()

    def set_active_tool(self, tool_id: str, *, shape_variant: str = "rectangle") -> None:
        if tool_id in {"shape", "rectangle", "ellipse"}:
            variant = "ellipse" if tool_id == "ellipse" else shape_variant
            if variant not in {"rectangle", "ellipse"}:
                self.cancel_create()
                self._active_tool = "shape"
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                self.setCursor(Qt.CursorShape.ForbiddenCursor)
                self.tool_changed.emit(self._active_tool)
                return
            self.begin_rectangle(variant=variant)
            return
        if tool_id in {"pen", "bezier"}:
            self.begin_bezier()
            return
        if tool_id == "line":
            self.begin_line()
            return
        if tool_id == "text":
            self.begin_text()
            return
        self.cancel_create()
        allowed = {"select", "direct_select", "hand", "zoom"}
        self._active_tool = tool_id if tool_id in allowed else "select"
        if self._active_tool == "hand":
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self._active_tool == "zoom":
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif self._active_tool == "direct_select":
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.unsetCursor()
        self.tool_changed.emit(self._active_tool)

    def begin_rectangle(self, *, variant: str = "rectangle") -> None:
        from pydesign.gui.canvas_create import begin_rectangle

        begin_rectangle(self, variant=variant)

    def begin_line(self) -> None:
        from pydesign.gui.canvas_create import begin_line

        begin_line(self)

    def begin_bezier(self) -> None:
        from pydesign.gui.canvas_create import begin_bezier

        begin_bezier(self)

    def begin_text(self) -> None:
        from pydesign.gui.canvas_create import begin_text

        begin_text(self)

    def cancel_create(self) -> None:
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

    def cancel_tool(self) -> None:
        creating = self._create_mode is not None
        self.cancel_create()
        if creating:
            self.set_active_tool("select")
            return
        if self.canvas_scene.selectedItems():
            self.clear_selection()
            return
        self.set_active_tool("select")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._active_tool == "zoom" and event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                self.zoom_by(1 / 1.25)
            else:
                self.zoom_by(1.25)
            event.accept()
            return
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
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
                    self.cancel_create()
                    self.set_active_tool("select")
                    self.bezier_created.emit(page_id, points)
                event.accept()
                return
        if (
            self._create_mode in {"rectangle", "ellipse", "text", "line"}
            and event.button() == Qt.MouseButton.LeftButton
        ):
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

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._active_tool == "zoom":
            self.fit_page(self._current_page)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

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
            and self._create_mode in {"rectangle", "ellipse", "text", "line"}
        ):
            mode = self._create_mode
            rectangle = self._create_preview.rect()
            page = self._create_page
            frame: Frame = (
                rectangle.x() - page.x,
                rectangle.y() - page.y,
                rectangle.width(),
                rectangle.height(),
            )
            self.cancel_create()
            self.set_active_tool("select")
            enough = (
                abs(frame[2]) + abs(frame[3]) >= 1.0
                if mode == "line"
                else frame[2] >= 1.0 and frame[3] >= 1.0
            )
            if enough:
                if mode == "text":
                    self.text_created.emit(page.page_id, frame)
                else:
                    self.rectangle_created.emit(page.page_id, frame, mode)
            event.accept()
            return
        if event.button() == Qt.MouseButton.MiddleButton and self._active_tool not in {
            "hand",
            "select",
        }:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        if self._scroll_snap_armed or event.button() in {
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
        }:
            self._scroll_snap_armed = False
            self._update_current_page_from_view()
            self._snap_page_if_near()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: Any) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_tool()
            event.accept()
            return
        if event.key() == Qt.Key.Key_PageDown:
            self.next_page()
            event.accept()
            return
        if event.key() == Qt.Key.Key_PageUp:
            self.previous_page()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pan = True
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: Any) -> None:
        if event.key() == Qt.Key.Key_Space and self._space_pan:
            self._space_pan = False
            if self._active_tool == "zoom":
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
            elif self._active_tool in {"select", "direct_select", "hand"}:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            event.accept()
            return
        super().keyReleaseEvent(event)


def _normal_rect(first: QPointF, second: QPointF) -> Any:
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
