"""Top View bar — framing and zoom, separate from tool options."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QToolBar, QWidget


class ViewBar(QToolBar):
    fit_page = Signal()
    fill_width = Signal()
    actual_size = Signal()
    fit_all = Signal()
    zoom_in = Signal()
    zoom_out = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("View", parent)
        self.setObjectName("view-bar")
        self.setMovable(False)
        self.setFloatable(False)
        self.setAccessibleName("View controls")
        label = QLabel("View")
        label.setObjectName("section-header")
        self.addWidget(label)
        self.addSeparator()
        self._add("Fit Page", lambda: self.fit_page.emit())
        self._add("Fill Width", lambda: self.fill_width.emit())
        self._add("Actual Size", lambda: self.actual_size.emit())
        self._add("Fit All", lambda: self.fit_all.emit())
        self.addSeparator()
        self._add("Zoom In", lambda: self.zoom_in.emit())
        self._add("Zoom Out", lambda: self.zoom_out.emit())
        self.addSeparator()
        self._zoom_label = QLabel("Zoom: —")
        self._zoom_label.setObjectName("view-zoom-label")
        self.addWidget(self._zoom_label)

    def _add(self, label: str, callback: Callable[[], None]) -> None:
        action = QAction(label, self)
        action.triggered.connect(lambda _checked=False: callback())
        self.addAction(action)

    def set_zoom_text(self, text: str) -> None:
        self._zoom_label.setText(text)
