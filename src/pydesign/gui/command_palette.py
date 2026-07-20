"""Searchable command palette for menu/tool actions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class PaletteCommand:
    title: str
    callback: Callable[[], None]
    shortcut: str = ""
    keywords: str = ""


class CommandPalette(QDialog):
    def __init__(self, parent: QWidget | None, commands: list[PaletteCommand]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setModal(True)
        self.resize(520, 360)
        self.setAccessibleName("Command palette")
        self._commands = commands
        self._search = QLineEdit()
        self._search.setPlaceholderText("Type a command…")
        self._search.setClearButtonEnabled(True)
        self._list = QListWidget()
        self._list.setAccessibleName("Matching commands")
        hint = QLabel("Enter runs the selected command · Esc closes")
        layout = QVBoxLayout(self)
        layout.addWidget(self._search)
        layout.addWidget(self._list, 1)
        layout.addWidget(hint)
        self._search.textChanged.connect(self._filter)
        self._search.returnPressed.connect(self._activate_current)
        self._list.itemActivated.connect(self._activate_item)
        self._filter("")
        self._search.setFocus()

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        self._list.clear()
        for command in self._commands:
            haystack = f"{command.title} {command.shortcut} {command.keywords}".lower()
            if needle and needle not in haystack:
                continue
            label = (
                command.title if not command.shortcut else f"{command.title}  ·  {command.shortcut}"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, command)
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _activate_current(self) -> None:
        item = self._list.currentItem()
        if item is not None:
            self._activate_item(item)

    def _activate_item(self, item: QListWidgetItem) -> None:
        command = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(command, PaletteCommand):
            self.accept()
            command.callback()

    def keyPressEvent(self, event: object) -> None:
        from PySide6.QtGui import QKeyEvent

        if isinstance(event, QKeyEvent) and event.key() in {Qt.Key.Key_Down, Qt.Key.Key_Up}:
            self._list.setFocus()
            self._list.keyPressEvent(event)
            return
        super().keyPressEvent(event)  # type: ignore[arg-type]


def shortcut_text(sequence: str) -> str:
    return QKeySequence(sequence).toString(QKeySequence.SequenceFormat.NativeText)
