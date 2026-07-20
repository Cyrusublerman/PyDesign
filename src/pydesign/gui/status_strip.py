"""Composed desktop status strip."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar, QWidget


class StatusStrip:
    """Owns the permanent status label and composes build/tool/page/zoom text."""

    def __init__(self, status_bar: QStatusBar) -> None:
        self._label = QLabel("No project")
        self._label.setAccessibleName("Application status")
        status_bar.addPermanentWidget(self._label, 1)
        self.build = "No project"
        self.tool = "Select"
        self.page = ""
        self.selection = ""
        self.zoom = ""

    @property
    def widget(self) -> QWidget:
        return self._label

    def set_build(self, text: str) -> None:
        self.build = text
        self._refresh()

    def set_tool(self, text: str) -> None:
        self.tool = text
        self._refresh()

    def set_page(self, text: str) -> None:
        self.page = text
        self._refresh()

    def set_selection(self, text: str) -> None:
        self.selection = text
        self._refresh()

    def set_zoom(self, text: str) -> None:
        self.zoom = text
        self._refresh()

    def _refresh(self) -> None:
        parts = [self.build, f"Tool: {self.tool}"]
        if self.page:
            parts.append(self.page)
        if self.selection:
            parts.append(f"Selection: {self.selection}")
        if self.zoom:
            parts.append(self.zoom)
        self._label.setText(" | ".join(parts))
