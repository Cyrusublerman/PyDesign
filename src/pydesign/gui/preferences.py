"""Preferences dialog — remappable shortcuts."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pydesign.gui.keymap import (
    COMMAND_LABELS,
    DEFAULT_SHORTCUTS,
    find_conflicts,
    merge_keymap,
)
from pydesign.gui.settings import ApplicationSettings


class PreferencesDialog(QDialog):
    def __init__(self, settings: ApplicationSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(520, 420)
        self._settings = settings
        self._keymap = merge_keymap(settings.keymap())
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Search commands…")
        self._filter.textChanged.connect(self._populate)
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Command", "Shortcut"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.itemChanged.connect(self._item_changed)
        self._conflict = QLabel("")
        self._conflict.setObjectName("tool-options-hint")
        self._conflict.setWordWrap(True)
        reset = QPushButton("Reset defaults")
        reset.clicked.connect(self._reset)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self._filter)
        layout.addWidget(self._table, 1)
        layout.addWidget(self._conflict)
        row = QHBoxLayout()
        row.addWidget(reset)
        row.addStretch(1)
        row.addWidget(buttons)
        layout.addLayout(row)
        self._populate()

    def _populate(self) -> None:
        query = self._filter.text().strip().casefold()
        rows = [
            (command_id, COMMAND_LABELS.get(command_id, command_id), shortcut)
            for command_id, shortcut in self._keymap.items()
            if not query
            or query in command_id.casefold()
            or query in COMMAND_LABELS.get(command_id, "").casefold()
        ]
        self._table.blockSignals(True)
        self._table.setRowCount(len(rows))
        for row, (command_id, label, shortcut) in enumerate(rows):
            name = QTableWidgetItem(label)
            name.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            name.setData(Qt.ItemDataRole.UserRole, command_id)
            key = QTableWidgetItem(shortcut)
            self._table.setItem(row, 0, name)
            self._table.setItem(row, 1, key)
        self._table.blockSignals(False)
        self._show_conflicts()

    def _item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 1:
            return
        name = self._table.item(item.row(), 0)
        if name is None:
            return
        command_id = str(name.data(Qt.ItemDataRole.UserRole))
        text = item.text().strip()
        sequence = QKeySequence(text)
        if text and sequence.isEmpty():
            item.setText(self._keymap.get(command_id, DEFAULT_SHORTCUTS[command_id]))
            return
        self._keymap[command_id] = sequence.toString() if text else DEFAULT_SHORTCUTS[command_id]
        if not text:
            item.setText(self._keymap[command_id])
        self._show_conflicts()

    def _show_conflicts(self) -> None:
        conflicts = find_conflicts(self._keymap)
        if not conflicts:
            self._conflict.setText("No shortcut conflicts.")
            return
        sample = conflicts[0]
        self._conflict.setText(
            f"Conflict: {COMMAND_LABELS.get(sample.command_id, sample.command_id)} and "
            f"{COMMAND_LABELS.get(sample.other_id, sample.other_id)} both use {sample.shortcut}."
        )

    def _reset(self) -> None:
        self._keymap = dict(DEFAULT_SHORTCUTS)
        self._populate()

    def _accept(self) -> None:
        conflicts = find_conflicts(self._keymap)
        if conflicts:
            answer = QMessageBox.question(
                self,
                "Shortcut conflicts",
                "Some shortcuts conflict. Save anyway?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._settings.set_keymap(self._keymap)
        self.accept()
