"""Stable desktop entrypoint and compatibility exports."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from pydesign.gui.canvas import PageCanvas
from pydesign.gui.canvas_items import EditableBezierItem
from pydesign.gui.chrome import apply_chrome
from pydesign.gui.multi_window import configure as configure_multi_window
from pydesign.gui.multi_window import open_additional_window
from pydesign.gui.window import MainWindow

__all__ = ["EditableBezierItem", "MainWindow", "PageCanvas", "open_additional_window", "run"]


def run(project: Path | None = None) -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    application.setOrganizationName("PyDesign")
    application.setOrganizationDomain("pydesign.local")
    application.setApplicationName("PyDesign")
    apply_chrome(application)
    configure_multi_window(MainWindow)
    window = MainWindow(project)
    window.show()
    return application.exec()
