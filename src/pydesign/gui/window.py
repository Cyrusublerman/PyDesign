"""Main PyDesign desktop window and project orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QIODevice, QSaveFile, Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor, QUndoStack
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QStatusBar,
    QTextEdit,
)

from pydesign.gui.appearance_edits import commit_quantity_property, commit_string_property
from pydesign.gui.canvas import PageCanvas
from pydesign.gui.command_palette import CommandPalette
from pydesign.gui.commands import SourcePlanCommand
from pydesign.gui.create_edits import commit_shape_create, commit_text_create
from pydesign.gui.diagnostics_format import format_diagnostics_text
from pydesign.gui.dialogs import choose_geometry_strategy, resolve_buffer_recovery
from pydesign.gui.evaluation import EvaluationController
from pydesign.gui.inspector import GeometryInspector
from pydesign.gui.palette_commands import build_palette_commands
from pydesign.gui.project_lifecycle import ProjectLifecycleMixin
from pydesign.gui.project_rail import ProjectRail
from pydesign.gui.proof_view import ProofView
from pydesign.gui.selection_sync import sync_inspector_selection
from pydesign.gui.settings import ApplicationSettings
from pydesign.gui.shell_actions import install_shell_actions
from pydesign.gui.status_strip import StatusStrip
from pydesign.gui.tool_options import ToolOptionsBar
from pydesign.gui.toolbox import ToolboxBar
from pydesign.gui.tools import TOOL_BY_ID
from pydesign.gui.types import _is_bezier_points, _is_frame
from pydesign.gui.view_bar import ViewBar
from pydesign.gui.window_chrome import WindowChromeMixin
from pydesign.gui.workspace import apply_workspace, make_dock
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
    recover_source_transactions,
)


class MainWindow(WindowChromeMixin, ProjectLifecycleMixin, QMainWindow):
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
        self.selected_object_id = ""
        self.selected_frame: Frame | None = None
        self.source_undo = QUndoStack(self)
        self.evaluator = EvaluationController(self)
        self.evaluator.finished.connect(self._evaluation_finished)
        self.evaluator.protocol_error.connect(self._evaluation_protocol_error)
        self.evaluator.process_error.connect(self._evaluation_process_error)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(15_000)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start()

        self.canvas = PageCanvas()
        self.setCentralWidget(self.canvas)
        self.rail = ProjectRail()
        self.editor = QPlainTextEdit()
        self.editor.setAccessibleName("Python source editor")
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setFont(QFont("Monospace", 11))
        self.editor.textChanged.connect(self._mark_typing)
        self.inspector = GeometryInspector()
        self.diagnostics = QTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setAccessibleName("Build diagnostics")
        self.toolbox = ToolboxBar(self)
        self.view_bar = ViewBar(self)
        self.tool_options = ToolOptionsBar(self)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.toolbox)
        self.proof_view = ProofView()
        self.docks: dict[str, QDockWidget] = {
            "rail": make_dock("Project", "dock-rail", self.rail, self),
            "editor": make_dock("Source", "dock-editor", self.editor, self),
            "inspector": make_dock("Inspector", "dock-inspector", self.inspector, self),
            "diagnostics": make_dock("Diagnostics", "dock-diagnostics", self.diagnostics, self),
            "proof": make_dock("Proof", "dock-proof", self.proof_view, self),
        }
        self.docks["proof"].hide()
        apply_workspace(self, self.docks, "Code + Canvas")
        status = QStatusBar(self)
        self.setStatusBar(status)
        self.status = StatusStrip(status)

        self.canvas.object_selected.connect(self._canvas_selected)
        self.canvas.frame_committed.connect(self._canvas_frame_committed)
        self.canvas.rectangle_created.connect(self._canvas_rectangle_created)
        self.canvas.text_created.connect(self._canvas_text_created)
        self.canvas.bezier_created.connect(self._canvas_bezier_created)
        self.canvas.bezier_committed.connect(self._canvas_bezier_committed)
        self.canvas.tool_changed.connect(self._tool_changed)
        self.canvas.view_changed.connect(self._view_changed)
        self.canvas.page_changed.connect(self._page_changed)
        self.inspector.apply_requested.connect(self._inspector_apply)
        self.inspector.appearance_requested.connect(self._inspector_appearance)
        self.inspector.reveal_requested.connect(self.reveal_selection_source)
        self.rail.file_activated.connect(self._rail_file_activated)
        self.rail.page_activated.connect(self.canvas.go_to_page)
        self.rail.layer_visibility_changed.connect(self._layer_visibility_changed)
        self.rail.pages_reordered.connect(self._pages_reordered)
        self.toolbox.tool_chosen.connect(self._toolbox_tool_chosen)
        self.toolbox.shape_variant_changed.connect(self._shape_variant_changed)
        self.tool_options.shape_variant_changed.connect(self._shape_variant_changed)
        self.view_bar.fit_page.connect(lambda: self.canvas.fit_page())
        self.view_bar.fill_width.connect(lambda: self.canvas.fill_width())
        self.view_bar.actual_size.connect(lambda: self.canvas.actual_size())
        self.view_bar.fit_all.connect(self.canvas.fit_all)
        self.view_bar.zoom_in.connect(lambda: self.canvas.zoom_by(1.25))
        self.view_bar.zoom_out.connect(lambda: self.canvas.zoom_by(1 / 1.25))
        self._create_actions()
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.view_bar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.tool_options)
        if geometry := self.settings.window_geometry():
            self.restoreGeometry(geometry)
        if state := self.settings.window_state():
            self.restoreState(state)
        # Compatibility for smoke tests and lifecycle that expect these names.
        self.file_list = self.rail.file_list
        self.state_label = self.status.widget
        if project is not None:
            self.open_project(project)

    def _create_actions(self) -> None:
        self._view_actions = install_shell_actions(self)
        self.toolbox.apply_shortcuts(self.settings.keymap())

    def open_command_palette(self) -> None:
        CommandPalette(self, build_palette_commands(self)).exec()

    def _apply_workspace(self, name: str) -> None:
        apply_workspace(self, self.docks, name)

    def _toolbox_tool_chosen(self, tool_id: str) -> None:
        self.canvas.set_active_tool(tool_id, shape_variant=self.toolbox.shape_variant())

    def _shape_variant_changed(self, variant_id: str) -> None:
        self.toolbox.set_shape_variant(variant_id)
        self.tool_options.set_shape_variant(variant_id)
        if self.toolbox.current_tool() == "shape":
            self.canvas.set_active_tool("shape", shape_variant=variant_id)

    def _tool_changed(self, tool_id: str) -> None:
        self.toolbox.set_tool(tool_id)
        self.tool_options.set_tool(tool_id)
        tool = TOOL_BY_ID.get(tool_id)
        self.status.set_tool(tool.label if tool else tool_id)

    def _view_changed(self) -> None:
        label = self.canvas.zoom_label()
        self.status.set_zoom(label)
        self.view_bar.set_zoom_text(label)

    def _page_changed(self, index: int) -> None:
        pages = self.canvas.page_summaries
        if not pages:
            self.status.set_page("")
            return
        page = pages[min(index, len(pages) - 1)]
        self.status.set_page(f"Page: {index + 1}/{len(pages)} {page['id']}")
        self.rail.set_current_page(index)

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
        self.status.set_build("Ready")
        self.record_recent_project(config.root)
        if transaction_recovery.recovered:
            self.diagnostics.setPlainText(
                "Recovered interrupted source transaction(s): "
                + ", ".join(transaction_recovery.recovered)
            )
        self.run_project()

    def _populate_sources(self, selected: Path) -> None:
        assert self.project_root is not None
        ignored = {".git", ".pydesign", ".venv", "__pycache__", "exports"}
        paths: list[tuple[str, Path]] = []
        for path in sorted(self.project_root.rglob("*.py")):
            if ignored.intersection(path.relative_to(self.project_root).parts):
                continue
            paths.append((path.relative_to(self.project_root).as_posix(), path))
        self.rail.set_files(paths, selected)
        self._open_source(selected)

    def _rail_file_activated(self, path: object) -> None:
        assert isinstance(path, Path)
        if self.editor.document().isModified() and not self.save_source():
            return
        self._open_source(path)

    def _open_source(
        self, path: Path, *, line: int | None = None, preserve_view: bool = False
    ) -> None:
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
        same_file = self.active_source_path == path
        scroll = self.editor.verticalScrollBar().value() if preserve_view and same_file else None
        cursor_pos = self.editor.textCursor().position() if preserve_view and same_file else None
        self.active_source_path = path
        self.active_base_text = disk_source
        self.editor.blockSignals(True)
        self.editor.setPlainText(source)
        self.editor.document().setModified(restored)
        self.editor.blockSignals(False)
        self.rail.select_file(path)
        if line is not None:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, line - 1
            )
            self.editor.setTextCursor(cursor)
            self.editor.centerCursor()
            self.editor.setFocus()
        elif scroll is not None and cursor_pos is not None:
            cursor = self.editor.textCursor()
            cursor.setPosition(min(cursor_pos, len(source)))
            self.editor.setTextCursor(cursor)
            bar = self.editor.verticalScrollBar()
            bar.setValue(min(scroll, bar.maximum()))

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
        self.status.set_build("Saved")
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
        self.status.set_build("Running")
        self.diagnostics.setPlainText("Evaluating project in an isolated worker…")
        self.evaluator.start(self.project_root)

    def stop_project(self) -> None:
        if self.evaluator.stop():
            self.status.set_build("Cancelled")

    def _evaluation_finished(self, response: object, stderr: str) -> None:
        if not isinstance(response, dict):
            self._evaluation_protocol_error("Worker returned an invalid response")
            return
        selected = self.selected_object_id
        if response.get("ok") and isinstance(response.get("layout"), dict):
            layout = response["layout"]
            self.canvas.set_layout(layout)
            self.rail.set_pages(self.canvas.page_summaries, self.canvas.current_page_index)
            self.rail.set_layers(self.canvas.layers)
            self.last_good_revision = str(response.get("revision", ""))
            self.status.set_build(f"Current · {self.last_good_revision[:12]}")
            self.status.set_zoom(self.canvas.zoom_label())
            if selected:
                self.canvas.select_object(selected)
        else:
            suffix = " · last good preview retained" if self.last_good_revision else ""
            self.status.set_build(f"Error{suffix}")
        self._display_diagnostics(response, stderr)

    def _display_diagnostics(self, response: dict[str, Any], stderr: str) -> None:
        diagnostics = response.get("diagnostics", [])
        items = diagnostics if isinstance(diagnostics, list) else []
        self.diagnostics.setPlainText(format_diagnostics_text(items, stderr))

    def _evaluation_protocol_error(self, detail: str) -> None:
        self.status.set_build("Error · last good preview retained")
        self.diagnostics.setPlainText(detail)

    def _evaluation_process_error(self, detail: str) -> None:
        suffix = " · last good preview retained" if self.last_good_revision else ""
        self.status.set_build(f"Error{suffix}")
        self.diagnostics.setPlainText(detail)

    def _canvas_selected(self, object_id: str, frame_value: object) -> None:
        self.selected_object_id = object_id
        self.selected_frame = frame_value if _is_frame(frame_value) else None
        self.status.set_selection(object_id)
        if not object_id or self.project_root is None:
            self.inspector.set_selection("", None)
            return
        sync_inspector_selection(
            self.inspector,
            project_root=self.project_root,
            object_id=object_id,
            frame=self.selected_frame,
        )

    def _canvas_frame_committed(self, object_id: str, previous: object, desired: object) -> None:
        if _is_frame(previous) and _is_frame(desired):
            self._commit_frame(object_id, previous, desired)

    def _inspector_apply(self, desired: object) -> None:
        if self.selected_object_id and self.selected_frame is not None and _is_frame(desired):
            self._commit_frame(self.selected_object_id, self.selected_frame, desired)

    def _inspector_appearance(self, values: object) -> None:
        if not isinstance(values, dict) or not self.selected_object_id:
            return
        if "fill" in values:
            fill = values.get("fill")
            commit_string_property(self, "fill", None if fill is None else str(fill))
        if "stroke" in values:
            stroke = values.get("stroke")
            commit_string_property(self, "stroke", None if stroke is None else str(stroke))
        if "colour" in values and values.get("colour"):
            commit_string_property(self, "colour", str(values["colour"]))
        if "text" in values and values.get("text") is not None:
            commit_string_property(self, "text", str(values["text"]))
        if "stroke_width" in values:
            commit_quantity_property(self, "stroke_width", float(values["stroke_width"]))

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

    def _canvas_rectangle_created(
        self, page_id: str, frame_value: object, kind: str = "rectangle"
    ) -> None:
        commit_shape_create(self, page_id, frame_value, kind=kind)

    def _canvas_text_created(self, page_id: str, frame_value: object) -> None:
        commit_text_create(self, page_id, frame_value)

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
        self._open_source(declaration.path, line=declaration.span.start_line)

    def after_source_change(self, path: Path, object_id: str) -> None:
        if path == self.active_source_path:
            self._open_source(path, preserve_view=True)
        self.selected_object_id = object_id
        self.run_project()

    def show_source_error(self, message: str) -> None:
        self.status.set_build("Source transaction error")
        self.diagnostics.setPlainText(message)
        QMessageBox.warning(self, "Python source was not changed", message)

    def _mark_typing(self) -> None:
        if self.active_source_path is not None:
            suffix = " · preview stale" if self.last_good_revision else ""
            self.status.set_build(f"Typing{suffix}")

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
