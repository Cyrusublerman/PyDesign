"""Stage 1 code-and-canvas desktop shell."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QIODevice, QProcess, QSaveFile, Qt
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from pydesign.runtime.project import ProjectConfigError, load_project_config


class PageCanvas(QGraphicsView):
    def __init__(self) -> None:
        self.canvas_scene = QGraphicsScene()
        super().__init__(self.canvas_scene)
        self.setAccessibleName("Document canvas")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setBackgroundBrush(QColor("#35383d"))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._has_snapshot = False

    def set_layout(self, layout: dict[str, Any]) -> None:
        self.canvas_scene.clear()
        y_offset = 24.0
        pages = layout.get("pages", [])
        if not isinstance(pages, list):
            return
        for page_number, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                continue
            width = float(page.get("width", 0.0))
            height = float(page.get("height", 0.0))
            paper = self.canvas_scene.addRect(
                0.0,
                y_offset,
                width,
                height,
                QPen(QColor("#b8bcc2"), 0.75),
                QColor("#ffffff"),
            )
            paper.setZValue(-1000)
            paper.setData(0, str(page.get("id", f"page-{page_number}")))

            operations = page.get("operations", [])
            if isinstance(operations, list):
                for operation in operations:
                    if isinstance(operation, dict):
                        self._draw_operation(operation, y_offset)

            label = self.canvas_scene.addSimpleText(
                f"{page_number} · {page.get('id', '')}", QFont("Sans Serif", 7)
            )
            label.setBrush(QColor("#d8dbe0"))
            label.setPos(0.0, y_offset + height + 4.0)
            y_offset += height + 54.0

        self._has_snapshot = bool(pages)
        if self._has_snapshot:
            self.fitInView(
                self.canvas_scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio
            )

    def _draw_operation(self, operation: dict[str, Any], page_y: float) -> None:
        kind = operation.get("op")
        object_id = str(operation.get("object_id", ""))
        x = float(operation.get("x", 0.0))
        y = page_y + float(operation.get("y", 0.0))
        width = float(operation.get("width", 0.0))
        height = float(operation.get("height", 0.0))

        if kind == "rectangle":
            fill_value = operation.get("fill")
            stroke_value = operation.get("stroke")
            fill = QColor(str(fill_value)) if fill_value else QColor(Qt.GlobalColor.transparent)
            pen = (
                QPen(QColor(str(stroke_value)), float(operation.get("stroke_width", 1.0)))
                if stroke_value
                else QPen(Qt.PenStyle.NoPen)
            )
            item = self.canvas_scene.addRect(x, y, width, height, pen, fill)
            item.setData(0, object_id)
            item.setToolTip(object_id)
            return

        if kind == "text_placeholder":
            frame_pen = QPen(QColor("#87909c"), 0.5, Qt.PenStyle.DashLine)
            frame = self.canvas_scene.addRect(x, y, width, height, frame_pen)
            frame.setData(0, object_id)
            text = self.canvas_scene.addText(str(operation.get("text", "")))
            font = text.font()
            font.setPointSizeF(max(1.0, float(operation.get("font_size", 12.0))))
            text.setFont(font)
            text.setDefaultTextColor(QColor(str(operation.get("colour", "#000000"))))
            text.setTextWidth(width)
            text.setPos(x, y)
            text.setToolTip(f"{object_id} · Stage 1 text placeholder")
            text.setData(0, object_id)

    def wheelEvent(self, event: Any) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, project: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("PyDesign — Stage 1")
        self.resize(1440, 900)
        self.project_root: Path | None = None
        self.source_path: Path | None = None
        self.last_good_revision: str | None = None
        self.process: QProcess | None = None

        self.editor = QPlainTextEdit()
        self.editor.setAccessibleName("Python source editor")
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setFont(QFont("Monospace", 10))
        self.editor.textChanged.connect(self._mark_typing)

        self.canvas = PageCanvas()
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

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.editor)
        splitter.addWidget(centre)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
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

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        build_menu = self.menuBar().addMenu("Build")
        build_menu.addAction(run_action)
        build_menu.addAction(stop_action)

        toolbar = QToolBar("Build")
        toolbar.setMovable(False)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addSeparator()
        toolbar.addAction(run_action)
        toolbar.addAction(stop_action)
        self.addToolBar(toolbar)

    def choose_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Open PyDesign project")
        if directory:
            self.open_project(Path(directory))

    def open_project(self, root: Path) -> None:
        try:
            config = load_project_config(root)
            module_path = config.root.joinpath(*config.module_name.split(".")).with_suffix(".py")
            source = module_path.read_text(encoding="utf-8")
        except (OSError, ProjectConfigError, UnicodeError) as error:
            QMessageBox.critical(self, "Cannot open project", str(error))
            return
        self.project_root = config.root
        self.source_path = module_path
        self.editor.blockSignals(True)
        self.editor.setPlainText(source)
        self.editor.document().setModified(False)
        self.editor.blockSignals(False)
        self.setWindowTitle(f"PyDesign — {config.name}")
        self.state_label.setText("Ready")
        self.run_project()

    def save_source(self) -> bool:
        if self.source_path is None:
            return False
        output = QSaveFile(str(self.source_path))
        if not output.open(QIODevice.OpenModeFlag.WriteOnly):
            QMessageBox.critical(self, "Save failed", output.errorString())
            return False
        payload = self.editor.toPlainText().encode("utf-8")
        if output.write(payload) != len(payload) or not output.commit():
            QMessageBox.critical(self, "Save failed", output.errorString())
            return False
        self.editor.document().setModified(False)
        self.state_label.setText("Saved")
        return True

    def run_project(self) -> None:
        if self.project_root is None or not self.save_source():
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
        if response.get("ok") and isinstance(response.get("layout"), dict):
            layout = response["layout"]
            self.canvas.set_layout(layout)
            self.last_good_revision = str(response.get("revision", ""))
            self.state_label.setText(f"Current · {self.last_good_revision[:12]}")
        else:
            suffix = " · last good preview retained" if self.last_good_revision else ""
            self.state_label.setText(f"Error{suffix}")
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
        self.process = None

    def _evaluation_process_error(self, _error: QProcess.ProcessError) -> None:
        detail = self.process.errorString() if self.process is not None else "unknown process error"
        suffix = " · last good preview retained" if self.last_good_revision else ""
        self.state_label.setText(f"Error{suffix}")
        self.diagnostics.setPlainText(detail)

    def _mark_typing(self) -> None:
        if self.source_path is not None:
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
        self.stop_project()
        event.accept()


def run(project: Path | None = None) -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("PyDesign")
    window = MainWindow(project)
    window.show()
    return application.exec()
