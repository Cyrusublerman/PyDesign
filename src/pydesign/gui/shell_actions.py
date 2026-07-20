"""Menu and authoring-toolbar action installation for MainWindow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenuBar, QToolBar

from pydesign.gui.keymap import DEFAULT_SHORTCUTS
from pydesign.gui.workspace import PRESETS


class ActionHost(Protocol):
    def menuBar(self) -> QMenuBar: ...
    def addToolBar(self, *args: Any) -> Any: ...
    def install_project_actions(
        self, file_menu: Any, toolbar: QToolBar, save_action: QAction
    ) -> None: ...
    def save_source(self) -> bool: ...
    def run_project(self) -> None: ...
    def stop_project(self) -> None: ...
    def reveal_selection_source(self) -> None: ...
    def open_command_palette(self) -> None: ...
    def open_preferences(self) -> None: ...
    def open_secondary_window(self) -> None: ...
    def _apply_workspace(self, name: str) -> None: ...
    def _make_view_actions(self) -> list[tuple[str, Callable[[], None], str]]: ...
    def shortcut_for(self, command_id: str) -> str: ...

    source_undo: Any


def install_shell_actions(host: ActionHost) -> list[tuple[str, Callable[[], None], str]]:
    parent = cast(QObject, host)

    def shortcut(command_id: str) -> QKeySequence:
        return QKeySequence(host.shortcut_for(command_id) or DEFAULT_SHORTCUTS.get(command_id, ""))

    save_action = QAction("Save", parent)
    save_action.setShortcut(shortcut("file.save"))
    save_action.triggered.connect(host.save_source)
    run_action = QAction("Run", parent)
    run_action.setShortcut(shortcut("build.run"))
    run_action.triggered.connect(host.run_project)
    stop_action = QAction("Stop", parent)
    stop_action.setShortcut(shortcut("build.stop"))
    stop_action.triggered.connect(host.stop_project)
    reveal_action = QAction("Reveal Selection in Python", parent)
    reveal_action.setShortcut(shortcut("view.reveal_source"))
    reveal_action.triggered.connect(host.reveal_selection_source)
    toolbar = QToolBar("Authoring")
    toolbar.setObjectName("authoring-toolbar")
    toolbar.setMovable(False)
    file_menu = host.menuBar().addMenu("File")
    host.install_project_actions(file_menu, toolbar, save_action)
    edit_menu = host.menuBar().addMenu("Edit")
    edit_menu.addAction(host.source_undo.createUndoAction(parent, "Undo Canvas Source Edit"))
    edit_menu.addAction(host.source_undo.createRedoAction(parent, "Redo Canvas Source Edit"))
    prefs = QAction("Preferences…", parent)
    prefs.setShortcut(QKeySequence("Ctrl+,"))
    prefs.triggered.connect(host.open_preferences)
    edit_menu.addSeparator()
    edit_menu.addAction(prefs)
    build_menu = host.menuBar().addMenu("Build")
    build_menu.addAction(run_action)
    build_menu.addAction(stop_action)
    view_menu = host.menuBar().addMenu("View")
    view_menu.addAction(reveal_action)
    view_menu.addSeparator()
    view_actions = host._make_view_actions()
    for label, slot, command_id in view_actions:
        action = QAction(label, parent)
        action.setShortcut(shortcut(command_id))
        action.triggered.connect(slot)
        view_menu.addAction(action)
    workspace_menu = view_menu.addMenu("Workspace")
    for name in PRESETS:
        action = QAction(name, parent)
        action.triggered.connect(lambda _c=False, n=name: host._apply_workspace(n))
        workspace_menu.addAction(action)
    reset = QAction("Reset Workspace", parent)
    reset.triggered.connect(lambda: host._apply_workspace("Code + Canvas"))
    workspace_menu.addAction(reset)
    float_action = QAction("Open Secondary Window", parent)
    float_action.triggered.connect(host.open_secondary_window)
    view_menu.addSeparator()
    view_menu.addAction(float_action)
    palette_action = QAction("Command Palette…", parent)
    palette_action.setShortcut(shortcut("view.command_palette"))
    palette_action.triggered.connect(host.open_command_palette)
    view_menu.addSeparator()
    view_menu.addAction(palette_action)
    toolbar.addAction(save_action)
    toolbar.addSeparator()
    toolbar.addAction(run_action)
    toolbar.addAction(stop_action)
    host.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
    return view_actions
