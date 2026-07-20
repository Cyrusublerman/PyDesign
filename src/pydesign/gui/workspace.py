"""Named workspace dock arrangements."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow

PRESETS = (
    "Code + Canvas",
    "Canvas Focus",
    "Code Focus",
    "Path Editing",
    "Typography",
    "Proofing",
)


def apply_workspace(window: QMainWindow, docks: dict[str, QDockWidget], name: str) -> None:
    """Show/hide and arrange docks for a named preset."""
    rail = docks["rail"]
    editor = docks["editor"]
    inspector = docks["inspector"]
    diagnostics = docks["diagnostics"]

    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, rail)
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, editor)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, inspector)
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, diagnostics)
    window.splitDockWidget(rail, editor, Qt.Orientation.Vertical)

    for dock in docks.values():
        dock.show()
        dock.setFloating(False)

    if name == "Canvas Focus":
        editor.hide()
        diagnostics.hide()
    elif name == "Code Focus":
        inspector.hide()
        diagnostics.hide()
    elif name == "Path Editing":
        editor.hide()
        rail.show()
        inspector.show()
        diagnostics.hide()
    elif name == "Typography":
        editor.show()
        inspector.show()
        diagnostics.hide()
        rail.show()
    elif name == "Proofing":
        editor.hide()
        diagnostics.show()
        if "proof" in docks:
            docks["proof"].show()
            docks["proof"].setFloating(True)
            docks["proof"].resize(420, 280)
        rail.show()
        inspector.show()


def make_dock(title: str, object_name: str, widget: object, window: QMainWindow) -> QDockWidget:
    dock = QDockWidget(title, window)
    dock.setObjectName(object_name)
    dock.setWidget(widget)  # type: ignore[arg-type]
    dock.setFeatures(
        QDockWidget.DockWidgetFeature.DockWidgetMovable
        | QDockWidget.DockWidgetFeature.DockWidgetClosable
        | QDockWidget.DockWidgetFeature.DockWidgetFloatable
    )
    return dock
