"""User-decision dialogs kept separate from project orchestration."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from pydesign.runtime.recovery import RecoveryStore
from pydesign.source import FrameStrategy


def resolve_buffer_recovery(
    parent: QWidget,
    recovery: RecoveryStore,
    path: Path,
    disk_source: str,
    recovered: str,
) -> tuple[str, bool]:
    message = QMessageBox(parent)
    message.setWindowTitle("Recovered unsaved Python")
    message.setText(f"PyDesign found unsaved source for {path.name}.")
    message.setInformativeText(
        "Restore it into the editor, discard the recovery snapshot, or keep it for later."
    )
    restore = message.addButton("Restore", QMessageBox.ButtonRole.AcceptRole)
    discard = message.addButton("Discard recovery", QMessageBox.ButtonRole.DestructiveRole)
    message.addButton("Keep for later", QMessageBox.ButtonRole.RejectRole)
    message.exec()
    if message.clickedButton() is restore:
        return recovered, True
    if message.clickedButton() is discard:
        recovery.clear(path)
    return disk_source, False


def choose_geometry_strategy(
    parent: QWidget, options: tuple[FrameStrategy, ...]
) -> FrameStrategy | None:
    message = QMessageBox(parent)
    message.setWindowTitle("Computed Python geometry")
    message.setText("This geometry is controlled by Python rather than editable literals.")
    message.setInformativeText("Choose the visible source change PyDesign should make.")
    buttons: dict[object, FrameStrategy] = {}
    if "edit_shared" in options:
        button = message.addButton("Edit shared value", QMessageBox.ButtonRole.AcceptRole)
        buttons[button] = "edit_shared"
    if "adjust" in options:
        button = message.addButton("Add visible adjustment", QMessageBox.ButtonRole.AcceptRole)
        buttons[button] = "adjust"
    if "detach" in options:
        button = message.addButton(
            "Detach to point literals", QMessageBox.ButtonRole.DestructiveRole
        )
        buttons[button] = "detach"
    message.addButton(QMessageBox.StandardButton.Cancel)
    message.exec()
    return buttons.get(message.clickedButton())
