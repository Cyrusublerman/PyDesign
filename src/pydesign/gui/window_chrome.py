"""Chrome helpers mixed into MainWindow to keep window.py lean."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox

from pydesign.gui.preferences import PreferencesDialog
from pydesign.gui.structure_edits import commit_layer_visibility, commit_page_reorder


class WindowChromeMixin:
    settings: Any
    toolbox: Any
    project_root: Any
    canvas: Any

    def shortcut_for(self, command_id: str) -> str:
        return str(self.settings.shortcut(command_id))

    def _make_view_actions(self) -> list[tuple[str, Any, str]]:
        return [
            ("Fit Page", lambda: self.canvas.fit_page(), "view.fit_page"),
            ("Fill Width", lambda: self.canvas.fill_width(), "view.fill_width"),
            ("Actual Size", lambda: self.canvas.actual_size(), "view.actual_size"),
            ("Fit All", self.canvas.fit_all, "view.fit_all"),
            ("Zoom In", lambda: self.canvas.zoom_by(1.25), "view.zoom_in"),
            ("Zoom Out", lambda: self.canvas.zoom_by(1 / 1.25), "view.zoom_out"),
        ]

    def open_preferences(self) -> None:
        if PreferencesDialog(self.settings, self).exec():  # type: ignore[arg-type]
            self.toolbox.apply_shortcuts(self.settings.keymap())
            QMessageBox.information(
                self,  # type: ignore[arg-type]
                "Preferences",
                "Tool shortcuts updated. Reopen menus if a menu shortcut looks stale.",
            )

    def open_secondary_window(self) -> None:
        from pydesign.gui.multi_window import open_additional_window

        open_additional_window(self.project_root, settings=self.settings)

    def _layer_visibility_changed(self, layer_id: str, visible: bool) -> None:
        commit_layer_visibility(self, layer_id, visible)  # type: ignore[arg-type]

    def _pages_reordered(self, page_ids: object) -> None:
        if isinstance(page_ids, list):
            commit_page_reorder(self, [str(item) for item in page_ids])  # type: ignore[arg-type]
