"""Stage 2 visible-source code-and-canvas desktop shell."""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeGuard

from PySide6.QtCore import QIODevice, QPointF, QProcess, QSaveFile, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QTextCursor,
    QUndoCommand,
    QUndoStack,
)
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from pydesign.runtime.project import ProjectConfigError, load_project_config
from pydesign.runtime.recovery import RecoveryStore
from pydesign.source import (
    SourceEditPlan,
    SourceRewriteError,
    SourceTransactionError,
    apply_source_edit,
    build_source_index,
    frame_edit_options,
    new_gui_id,
    plan_bezier_insertion,
    plan_frame_update,
    plan_rectangle_insertion,
)
from pydesign.source.rewrite import Frame, FrameStrategy

type BezierPoints = tuple[
    tuple[float, float],
    tuple[float, float],
    tuple[float, float],
    tuple[float, float],
]


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


class PageCanvas(QGraphicsView):
    object_selected = Signal(str, object)
    frame_committed = Signal(str, object, object)
    rectangle_created = Signal(str, object)
    bezier_created = Signal(str, object)

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


class GeometryInspector(QWidget):
    apply_requested = Signal(object)
    reveal_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setAccessibleName("Selection inspector")
        self.object_id = QLabel("No selection")
        self.source = QLabel("—")
        self.source.setWordWrap(True)
        self.ownership = QLabel("—")
        self.fields = [self._field() for _ in range(4)]
        form = QFormLayout()
        form.addRow("Object", self.object_id)
        form.addRow("Source", self.source)
        form.addRow("Ownership", self.ownership)
        for label, field in zip(("X", "Y", "Width", "Height"), self.fields, strict=True):
            form.addRow(label, field)
        apply_button = QPushButton("Apply geometry")
        apply_button.clicked.connect(self._apply)
        reveal_button = QPushButton("Reveal in Python")
        reveal_button.clicked.connect(self.reveal_requested)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Inspector"))
        layout.addLayout(form)
        layout.addWidget(apply_button)
        layout.addWidget(reveal_button)
        layout.addStretch(1)
        self.set_enabled(False)

    @staticmethod
    def _field() -> QDoubleSpinBox:
        field = QDoubleSpinBox()
        field.setRange(-1_000_000.0, 1_000_000.0)
        field.setDecimals(4)
        field.setSuffix(" pt")
        field.setKeyboardTracking(False)
        return field

    def set_selection(
        self,
        object_id: str,
        frame: Frame | None,
        *,
        source: str = "—",
        ownership: str = "—",
    ) -> None:
        self.object_id.setText(object_id or "No selection")
        self.source.setText(source)
        self.ownership.setText(ownership)
        self.set_enabled(bool(object_id and frame))
        if frame is not None:
            for field, value in zip(self.fields, frame, strict=True):
                field.setValue(value)

    def set_enabled(self, enabled: bool) -> None:
        for field in self.fields:
            field.setEnabled(enabled)

    def frame(self) -> Frame:
        return tuple(field.value() for field in self.fields)  # type: ignore[return-value]

    def _apply(self) -> None:
        self.apply_requested.emit(self.frame())


class SourcePlanCommand(QUndoCommand):
    def __init__(self, window: MainWindow, plan: SourceEditPlan) -> None:
        super().__init__(plan.description)
        self.window = window
        self.plan = plan

    def redo(self) -> None:
        self._apply(self.plan)

    def undo(self) -> None:
        reverse = SourceEditPlan(
            path=self.plan.path,
            before=self.plan.after,
            after=self.plan.before,
            description=f"Undo {self.plan.description}",
            object_id=self.plan.object_id,
            property_name=self.plan.property_name,
            strategy=self.plan.strategy,
        )
        self._apply(reverse)

    def _apply(self, plan: SourceEditPlan) -> None:
        try:
            apply_source_edit(plan)
        except SourceTransactionError as error:
            self.setObsolete(True)
            self.window.show_source_error(str(error))
            return
        self.window.after_source_change(plan.path, plan.object_id)


class MainWindow(QMainWindow):
    def __init__(self, project: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("PyDesign — Stage 2")
        self.resize(1540, 940)
        self.project_root: Path | None = None
        self.entry_source_path: Path | None = None
        self.active_source_path: Path | None = None
        self.active_base_text = ""
        self.recovery: RecoveryStore | None = None
        self._recovery_checked: set[Path] = set()
        self.last_good_revision: str | None = None
        self.process: QProcess | None = None
        self.selected_object_id = ""
        self.selected_frame: Frame | None = None
        self.source_undo = QUndoStack(self)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(15_000)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start()

        self.file_list = QListWidget()
        self.file_list.setAccessibleName("Project Python files")
        self.file_list.currentItemChanged.connect(self._source_file_selected)
        self.editor = QPlainTextEdit()
        self.editor.setAccessibleName("Python source editor")
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setFont(QFont("Monospace", 10))
        self.editor.textChanged.connect(self._mark_typing)

        source_splitter = QSplitter(Qt.Orientation.Vertical)
        source_splitter.addWidget(self.file_list)
        source_splitter.addWidget(self.editor)
        source_splitter.setStretchFactor(0, 1)
        source_splitter.setStretchFactor(1, 5)

        self.canvas = PageCanvas()
        self.canvas.object_selected.connect(self._canvas_selected)
        self.canvas.frame_committed.connect(self._canvas_frame_committed)
        self.canvas.rectangle_created.connect(self._canvas_rectangle_created)
        self.canvas.bezier_created.connect(self._canvas_bezier_created)
        self.diagnostics = QTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setAccessibleName("Build diagnostics")
        diagnostics_container = QWidget()
        diagnostics_layout = QVBoxLayout(diagnostics_container)
        diagnostics_layout.setContentsMargins(0, 0, 0, 0)
        diagnostics_layout.addWidget(QLabel("Diagnostics"))
        diagnostics_layout.addWidget(self.diagnostics)

        centre = QSplitter(Qt.Orientation.Vertical)
        centre.addWidget(self.canvas)
        centre.addWidget(diagnostics_container)
        centre.setStretchFactor(0, 5)
        centre.setStretchFactor(1, 1)

        self.inspector = GeometryInspector()
        self.inspector.apply_requested.connect(self._inspector_apply)
        self.inspector.reveal_requested.connect(self.reveal_selection_source)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(source_splitter)
        splitter.addWidget(centre)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 1)
        self.setCentralWidget(splitter)

        self.state_label = QLabel("No project")
        status = QStatusBar()
        status.addPermanentWidget(self.state_label)
        self.setStatusBar(status)
        self._create_actions()
        if project is not None:
            self.open_project(project)

    def _create_actions(self) -> None:
        open_action = QAction("Open Project…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.choose_project)
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_source)
        run_action = QAction("Run", self)
        run_action.setShortcut("Ctrl+Return")
        run_action.triggered.connect(self.run_project)
        stop_action = QAction("Stop", self)
        stop_action.setShortcut("Shift+F5")
        stop_action.triggered.connect(self.stop_project)
        rectangle_action = QAction("Rectangle", self)
        rectangle_action.setShortcut("R")
        rectangle_action.triggered.connect(self.canvas.begin_rectangle)
        bezier_action = QAction("Bézier", self)
        bezier_action.setShortcut("B")
        bezier_action.triggered.connect(self.canvas.begin_bezier)
        reveal_action = QAction("Reveal Selection in Python", self)
        reveal_action.setShortcut("F4")
        reveal_action.triggered.connect(self.reveal_selection_source)

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction(self.source_undo.createUndoAction(self, "Undo Canvas Source Edit"))
        edit_menu.addAction(self.source_undo.createRedoAction(self, "Redo Canvas Source Edit"))
        build_menu = self.menuBar().addMenu("Build")
        build_menu.addAction(run_action)
        build_menu.addAction(stop_action)
        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(reveal_action)

        toolbar = QToolBar("Authoring")
        toolbar.setMovable(False)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addSeparator()
        toolbar.addAction(run_action)
        toolbar.addAction(stop_action)
        toolbar.addSeparator()
        toolbar.addAction(rectangle_action)
        toolbar.addAction(bezier_action)
        self.addToolBar(toolbar)

    def choose_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Open PyDesign project")
        if directory:
            self.open_project(Path(directory))

    def open_project(self, root: Path) -> None:
        try:
            config = load_project_config(root)
            module_path = config.root.joinpath(*config.module_name.split(".")).with_suffix(".py")
            module_path.read_text(encoding="utf-8")
            build_source_index(config.root)
        except (OSError, ProjectConfigError, UnicodeError, ValueError) as error:
            QMessageBox.critical(self, "Cannot open project", str(error))
            return
        self.project_root = config.root
        self.recovery = RecoveryStore(config.root)
        self._recovery_checked.clear()
        self.entry_source_path = module_path
        self.source_undo.clear()
        self._populate_sources(module_path)
        self.setWindowTitle(f"PyDesign — {config.name}")
        self.state_label.setText("Ready")
        self.run_project()

    def _populate_sources(self, selected: Path) -> None:
        assert self.project_root is not None
        self.file_list.blockSignals(True)
        self.file_list.clear()
        selected_item: QListWidgetItem | None = None
        ignored = {".git", ".pydesign", ".venv", "__pycache__", "exports"}
        for path in sorted(self.project_root.rglob("*.py")):
            if ignored.intersection(path.relative_to(self.project_root).parts):
                continue
            item = QListWidgetItem(path.relative_to(self.project_root).as_posix())
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.file_list.addItem(item)
            if path == selected:
                selected_item = item
        self.file_list.blockSignals(False)
        if selected_item is not None:
            self.file_list.setCurrentItem(selected_item)
            self._open_source(selected)

    def _source_file_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            return
        if self.editor.document().isModified() and not self.save_source():
            return
        self._open_source(Path(str(current.data(Qt.ItemDataRole.UserRole))))

    def _open_source(self, path: Path, *, line: int | None = None) -> None:
        try:
            disk_source = path.read_text(encoding="utf-8")
        except OSError as error:
            self.show_source_error(str(error))
            return
        source = disk_source
        restored = False
        if self.recovery is not None and path not in self._recovery_checked:
            self._recovery_checked.add(path)
            snapshot = self.recovery.load(path)
            if snapshot is not None and snapshot.content != disk_source:
                source, restored = self._resolve_recovery(path, disk_source, snapshot.content)
        self.active_source_path = path
        self.active_base_text = disk_source
        self.editor.blockSignals(True)
        self.editor.setPlainText(source)
        self.editor.document().setModified(restored)
        self.editor.blockSignals(False)
        if line is not None:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, line - 1
            )
            self.editor.setTextCursor(cursor)
            self.editor.centerCursor()
            self.editor.setFocus()

    def _resolve_recovery(self, path: Path, disk_source: str, recovered: str) -> tuple[str, bool]:
        message = QMessageBox(self)
        message.setWindowTitle("Recovered unsaved Python")
        message.setText(f"PyDesign found unsaved source for {path.name}.")
        message.setInformativeText(
            "Restore it into the editor, discard the recovery snapshot, or keep it for later."
        )
        restore = message.addButton("Restore", QMessageBox.ButtonRole.AcceptRole)
        discard = message.addButton("Discard recovery", QMessageBox.ButtonRole.DestructiveRole)
        message.addButton("Keep for later", QMessageBox.ButtonRole.RejectRole)
        message.exec()
        if message.clickedButton() is restore:
            return recovered, True
        if message.clickedButton() is discard and self.recovery is not None:
            self.recovery.clear(path)
        return disk_source, False

    def save_source(self) -> bool:
        if self.active_source_path is None:
            return False
        if self.editor.document().isModified():
            try:
                disk_source = self.active_source_path.read_text(encoding="utf-8")
            except OSError as error:
                self.show_source_error(str(error))
                return False
            if disk_source != self.active_base_text:
                self.show_source_error(
                    "The file changed on disk while this editor had unsaved work. "
                    "PyDesign did not overwrite either version; reload or merge the changes."
                )
                return False
        output = QSaveFile(str(self.active_source_path))
        if not output.open(QIODevice.OpenModeFlag.WriteOnly):
            QMessageBox.critical(self, "Save failed", output.errorString())
            return False
        payload = self.editor.toPlainText().encode("utf-8")
        if output.write(payload) != len(payload) or not output.commit():
            QMessageBox.critical(self, "Save failed", output.errorString())
            return False
        self.editor.document().setModified(False)
        self.active_base_text = self.editor.toPlainText()
        if self.recovery is not None:
            self.recovery.clear(self.active_source_path)
        self.state_label.setText("Saved")
        return True

    def _autosave(self) -> None:
        if (
            self.recovery is None
            or self.active_source_path is None
            or not self.editor.document().isModified()
        ):
            return
        try:
            self.recovery.save(
                self.active_source_path,
                self.editor.toPlainText(),
                base_content=self.active_base_text,
            )
        except OSError as error:
            self.diagnostics.setPlainText(f"Autosave failed: {error}")

    def run_project(self) -> None:
        if self.project_root is None:
            return
        if self.editor.document().isModified() and not self.save_source():
            return
        self.stop_project()
        request = {
            "protocol_version": 1,
            "action": "evaluate",
            "project_root": str(self.project_root),
            "profile": None,
        }
        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments(["-m", "pydesign.runtime.worker"])
        process.finished.connect(self._evaluation_finished)
        process.errorOccurred.connect(self._evaluation_process_error)
        self.process = process
        self.state_label.setText("Running")
        self.diagnostics.setPlainText("Evaluating project in an isolated worker…")
        process.start()
        if not process.waitForStarted(1500):
            self._evaluation_process_error(process.error())
            return
        process.write(json.dumps(request).encode("utf-8"))
        process.closeWriteChannel()

    def stop_project(self) -> None:
        if self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
            self.state_label.setText("Cancelled")
        self.process = None

    def _evaluation_finished(self, _exit_code: int, _status: QProcess.ExitStatus) -> None:
        process = self.sender()
        if not isinstance(process, QProcess):
            return
        stdout = bytes(process.readAllStandardOutput().data()).decode("utf-8", errors="replace")
        stderr = bytes(process.readAllStandardError().data()).decode("utf-8", errors="replace")
        try:
            response = json.loads(stdout)
        except json.JSONDecodeError:
            self.state_label.setText("Error · last good preview retained")
            self.diagnostics.setPlainText(f"Worker protocol error\n{stdout}\n{stderr}")
            self.process = None
            return
        selected = self.selected_object_id
        if response.get("ok") and isinstance(response.get("layout"), dict):
            self.canvas.set_layout(response["layout"])
            self.last_good_revision = str(response.get("revision", ""))
            self.state_label.setText(f"Current · {self.last_good_revision[:12]}")
            if selected:
                self.canvas.select_object(selected)
        else:
            suffix = " · last good preview retained" if self.last_good_revision else ""
            self.state_label.setText(f"Error{suffix}")
        self._display_diagnostics(response, stderr)
        self.process = None

    def _display_diagnostics(self, response: dict[str, Any], stderr: str) -> None:
        lines: list[str] = []
        diagnostics = response.get("diagnostics", [])
        if isinstance(diagnostics, list):
            for item in diagnostics:
                if isinstance(item, dict):
                    lines.append(
                        f"{str(item.get('severity', 'info')).upper()} "
                        f"{item.get('code', 'PD-UNKNOWN')}: {item.get('message', '')}"
                    )
        if stderr.strip():
            lines.extend(["", "Worker output:", stderr.rstrip()])
        self.diagnostics.setPlainText("\n".join(lines) or "No diagnostics")

    def _evaluation_process_error(self, _error: QProcess.ProcessError) -> None:
        detail = self.process.errorString() if self.process is not None else "unknown process error"
        suffix = " · last good preview retained" if self.last_good_revision else ""
        self.state_label.setText(f"Error{suffix}")
        self.diagnostics.setPlainText(detail)

    def _canvas_selected(self, object_id: str, frame_value: object) -> None:
        self.selected_object_id = object_id
        self.selected_frame = frame_value if _is_frame(frame_value) else None
        if not object_id or self.project_root is None:
            self.inspector.set_selection("", None)
            return
        try:
            declaration = build_source_index(self.project_root).require(object_id)
            ownership = declaration.property("frame")
            source = (
                f"{declaration.path.relative_to(self.project_root)}:{declaration.span.start_line}"
            )
            ownership_text = ownership.kind.value if ownership is not None else "derived/missing"
            if ownership is not None and ownership.components:
                ownership_text += " · " + ", ".join(item.value for item in ownership.components)
        except (OSError, ValueError, KeyError) as error:
            source = str(error)
            ownership_text = "unresolved"
        self.inspector.set_selection(
            object_id, self.selected_frame, source=source, ownership=ownership_text
        )

    def _canvas_frame_committed(self, object_id: str, previous: object, desired: object) -> None:
        if _is_frame(previous) and _is_frame(desired):
            self._commit_frame(object_id, previous, desired)

    def _inspector_apply(self, desired: object) -> None:
        if self.selected_object_id and self.selected_frame is not None and _is_frame(desired):
            self._commit_frame(self.selected_object_id, self.selected_frame, desired)

    def _commit_frame(self, object_id: str, previous: Frame, desired: Frame) -> None:
        if self.project_root is None or not self.save_source():
            self.run_project()
            return
        try:
            declaration = build_source_index(self.project_root).require(object_id)
            options = frame_edit_options(declaration)
            strategy: FrameStrategy | None = (
                "safe" if "safe" in options else self._choose_frame_strategy(options)
            )
            if strategy is None:
                self.run_project()
                return
            plan = plan_frame_update(
                self.project_root,
                object_id,
                previous=previous,
                desired=desired,
                strategy=strategy,
            )
        except (OSError, ValueError, KeyError, SourceRewriteError) as error:
            self.show_source_error(str(error))
            self.run_project()
            return
        self.source_undo.push(SourcePlanCommand(self, plan))

    def _choose_frame_strategy(self, options: tuple[FrameStrategy, ...]) -> FrameStrategy | None:
        message = QMessageBox(self)
        message.setWindowTitle("Computed Python geometry")
        message.setText("This frame is controlled by Python rather than editable literals.")
        message.setInformativeText("Choose the visible source change PyDesign should make.")
        buttons: dict[object, FrameStrategy] = {}
        if "edit_shared" in options:
            button = message.addButton("Edit shared value", QMessageBox.ButtonRole.AcceptRole)
            buttons[button] = "edit_shared"
        if "adjust" in options:
            button = message.addButton("Add visible adjustment", QMessageBox.ButtonRole.AcceptRole)
            buttons[button] = "adjust"
        if "detach" in options:
            button = message.addButton(
                "Detach to point literals", QMessageBox.ButtonRole.DestructiveRole
            )
            buttons[button] = "detach"
        message.addButton(QMessageBox.StandardButton.Cancel)
        message.exec()
        return buttons.get(message.clickedButton())

    def _canvas_rectangle_created(self, page_id: str, frame_value: object) -> None:
        if self.project_root is None or not _is_frame(frame_value) or not self.save_source():
            return
        try:
            index = build_source_index(self.project_root)
            object_id = new_gui_id({item.object_id for item in index.declarations})
            plan = plan_rectangle_insertion(
                self.project_root, page_id, object_id=object_id, frame=frame_value
            )
        except (OSError, ValueError, KeyError, SourceRewriteError) as error:
            self.show_source_error(str(error))
            return
        self.selected_object_id = object_id
        self.source_undo.push(SourcePlanCommand(self, plan))

    def _canvas_bezier_created(self, page_id: str, points_value: object) -> None:
        if (
            self.project_root is None
            or not _is_bezier_points(points_value)
            or not self.save_source()
        ):
            return
        try:
            index = build_source_index(self.project_root)
            object_id = new_gui_id({item.object_id for item in index.declarations})
            plan = plan_bezier_insertion(
                self.project_root,
                page_id,
                object_id=object_id,
                start=points_value[0],
                control_1=points_value[1],
                control_2=points_value[2],
                end=points_value[3],
            )
        except (OSError, ValueError, KeyError, SourceRewriteError) as error:
            self.show_source_error(str(error))
            return
        self.selected_object_id = object_id
        self.source_undo.push(SourcePlanCommand(self, plan))

    def reveal_selection_source(self) -> None:
        if not self.selected_object_id or self.project_root is None:
            return
        try:
            declaration = build_source_index(self.project_root).require(self.selected_object_id)
        except (OSError, ValueError, KeyError) as error:
            self.show_source_error(str(error))
            return
        if self.editor.document().isModified() and not self.save_source():
            return
        for row in range(self.file_list.count()):
            item = self.file_list.item(row)
            if Path(str(item.data(Qt.ItemDataRole.UserRole))) == declaration.path:
                self.file_list.setCurrentItem(item)
                break
        self._open_source(declaration.path, line=declaration.span.start_line)

    def after_source_change(self, path: Path, object_id: str) -> None:
        if path == self.active_source_path:
            self._open_source(path)
        self.selected_object_id = object_id
        self.run_project()

    def show_source_error(self, message: str) -> None:
        self.state_label.setText("Source transaction error")
        self.diagnostics.setPlainText(message)
        QMessageBox.warning(self, "Python source was not changed", message)

    def _mark_typing(self) -> None:
        if self.active_source_path is not None:
            suffix = " · preview stale" if self.last_good_revision else ""
            self.state_label.setText(f"Typing{suffix}")

    def closeEvent(self, event: Any) -> None:
        if self.editor.document().isModified():
            choice = QMessageBox.question(
                self,
                "Unsaved source",
                "Save the current Python source before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if choice == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if choice == QMessageBox.StandardButton.Save and not self.save_source():
                event.ignore()
                return
            if (
                choice == QMessageBox.StandardButton.Discard
                and self.recovery is not None
                and self.active_source_path is not None
            ):
                self.recovery.clear(self.active_source_path)
        self.stop_project()
        event.accept()


def _normal_rect(first: QPointF, second: QPointF) -> Any:
    from PySide6.QtCore import QRectF

    return QRectF(first, second).normalized()


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


def run(project: Path | None = None) -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("PyDesign")
    window = MainWindow(project)
    window.show()
    return application.exec()
