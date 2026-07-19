"""Stable desktop entrypoint and compatibility exports."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from pydesign.gui.canvas import PageCanvas
from pydesign.gui.window import MainWindow

__all__ = ["MainWindow", "PageCanvas", "run"]


def run(project: Path | None = None) -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    application.setOrganizationName("PyDesign")
    application.setOrganizationDomain("pydesign.local")
    application.setApplicationName("PyDesign")
    window = MainWindow(project)
    window.show()
    return application.exec()
