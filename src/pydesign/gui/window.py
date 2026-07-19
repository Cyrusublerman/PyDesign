"""Main PyDesign desktop window and project orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QIODevice, QSaveFile, Qt, QTimer
from PySide6.QtGui import QAction, QFont, QTextCursor, QUndoStack
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
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

from pydesign.gui.canvas import PageCanvas
from pydesign.gui.commands import SourcePlanCommand
from pydesign.gui.dialogs import choose_geometry_strategy, resolve_buffer_recovery
from pydesign.gui.evaluation import EvaluationController
from pydesign.gui.inspector import GeometryInspector
from pydesign.gui.project_lifecycle import ProjectLifecycleMixin
from pydesign.gui.settings import ApplicationSettings
from pydesign.gui.types import _is_bezier_points, _is_frame
from pydesign.runtime.project import ProjectConfigError, load_project_config
from pydesign.runtime.recovery import RecoveryStore
from pydesign.source import (
    Frame,
    FrameStrategy,
    SourceRewriteError,
    bezier_edit_options,
    build_source_index,
    frame_edit_options,
    new_gui_id,
    plan_bezier_insertion,
    plan_bezier_update,
    plan_frame_update,
    plan_rectangle_insertion,
    recover_source_transactions,
)


class MainWindow(ProjectLifecycleMixin, QMainWindow):
    def __init__(
        self, project: Path | None = None, *, settings: ApplicationSettings | None = None
    ) -> None:
        super().__init__()
        self.setWindowTitle("PyDesign — Stage 2")
        self.resize(1540, 940)
        self.settings = settings or ApplicationSettings()
        self.project_root: Path | None = None
        self.entry_source_path: Path | None = None
        self.active_source_path: Path | None = None
        self.active_base_text = ""
        self.recovery: RecoveryStore | None = None
        self._recovery_checked: set[Path] = set()
        self.last_good_revision: str | None = None
        self.evaluator = EvaluationController(self)
        self.evaluator.finished.connect(self._evaluation_finished)
        self.evaluator.protocol_error.connect(self._evaluation_protocol_error)
        self.evaluator.process_error.connect(self._evaluation_process_error)
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
        self.canvas.bezier_committed.connect(self._canvas_bezier_committed)
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
        if geometry := self.settings.window_geometry():
            self.restoreGeometry(geometry)
        if state := self.settings.window_state():
            self.restoreState(state)
        if project is not None:
            self.open_project(project)

    def _create_actions(self) -> None:
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

        toolbar = QToolBar("Authoring")
        toolbar.setObjectName("authoring-toolbar")
        toolbar.setMovable(False)
        file_menu = self.menuBar().addMenu("File")
        self.install_project_actions(file_menu, toolbar, save_action)
        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction(self.source_undo.createUndoAction(self, "Undo Canvas Source Edit"))
        edit_menu.addAction(self.source_undo.createRedoAction(self, "Redo Canvas Source Edit"))
        build_menu = self.menuBar().addMenu("Build")
        build_menu.addAction(run_action)
        build_menu.addAction(stop_action)
        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(reveal_action)

        toolbar.addAction(save_action)
        toolbar.addSeparator()
        toolbar.addAction(run_action)
        toolbar.addAction(stop_action)
        toolbar.addSeparator()
        toolbar.addAction(rectangle_action)
        toolbar.addAction(bezier_action)
        self.addToolBar(toolbar)

    def open_project(self, root: Path, *, offer_example_copy: bool = True) -> None:
        if not self.confirm_project_switch():
            return
        prepared = self.prepare_project_open(root, offer_example_copy=offer_example_copy)
        if prepared is None:
            return
        try:
            config = load_project_config(prepared)
            transaction_recovery = recover_source_transactions(config.root)
            if transaction_recovery.conflicts:
                raise ProjectConfigError(
                    "Interrupted source transaction needs manual recovery: "
                    + "; ".join(transaction_recovery.conflicts)
                )
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
        self.last_good_revision = None
        self.selected_object_id = ""
        self.selected_frame = None
        self._populate_sources(module_path)
        self.setWindowTitle(f"PyDesign — {config.name}")
        self.state_label.setText("Ready")
        self.record_recent_project(config.root)
        if transaction_recovery.recovered:
            self.diagnostics.setPlainText(
                "Recovered interrupted source transaction(s): "
                + ", ".join(transaction_recovery.recovered)
            )
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
                source, restored = resolve_buffer_recovery(
                    self, self.recovery, path, disk_source, snapshot.content
                )
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
        self.evaluator.stop()
        self.state_label.setText("Running")
        self.diagnostics.setPlainText("Evaluating project in an isolated worker…")
        self.evaluator.start(self.project_root)

    def stop_project(self) -> None:
        if self.evaluator.stop():
            self.state_label.setText("Cancelled")

    def _evaluation_finished(self, response: object, stderr: str) -> None:
        if not isinstance(response, dict):
            self._evaluation_protocol_error("Worker returned an invalid response")
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

    def _evaluation_protocol_error(self, detail: str) -> None:
        self.state_label.setText("Error · last good preview retained")
        self.diagnostics.setPlainText(detail)

    def _evaluation_process_error(self, detail: str) -> None:
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
                "safe" if "safe" in options else choose_geometry_strategy(self, options)
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

    def _canvas_bezier_committed(
        self, object_id: str, previous_value: object, desired_value: object
    ) -> None:
        if (
            self.project_root is None
            or not _is_bezier_points(previous_value)
            or not _is_bezier_points(desired_value)
            or not self.save_source()
        ):
            self.run_project()
            return
        try:
            options = bezier_edit_options(self.project_root, object_id)
            strategy: FrameStrategy | None = (
                "safe" if "safe" in options else choose_geometry_strategy(self, options)
            )
            if strategy is None:
                self.run_project()
                return
            plan = plan_bezier_update(
                self.project_root,
                object_id,
                previous=previous_value,
                desired=desired_value,
                strategy=strategy,
            )
        except (OSError, ValueError, KeyError, SourceRewriteError) as error:
            self.show_source_error(str(error))
            self.run_project()
            return
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
        self.save_application_state()
        event.accept()
