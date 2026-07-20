"""Contextual options for the active toolbox tool only."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QLabel, QToolBar, QWidget

from pydesign.gui.tools import SHAPE_BY_ID, SHAPE_VARIANTS, TOOL_BY_ID


class ToolOptionsBar(QToolBar):
    shape_variant_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Tool options", parent)
        self.setObjectName("tool-options-bar")
        self.setMovable(False)
        self.setFloatable(False)
        self.setAccessibleName("Tool options")
        self._title = QLabel("Tool")
        self._title.setObjectName("section-header")
        self.addWidget(self._title)
        self.addSeparator()
        self._hint = QLabel("Select a tool")
        self._hint.setObjectName("tool-options-hint")
        self.addWidget(self._hint)
        self._shape_label = QLabel("Variant")
        self._shape_combo = QComboBox()
        for variant in SHAPE_VARIANTS:
            label = (
                variant.label
                if variant.availability == "live"
                else f"{variant.label} ({variant.stage_hint})"
            )
            self._shape_combo.addItem(label, variant.variant_id)
        self._shape_combo.currentIndexChanged.connect(self._emit_shape)
        self._shape_label_action = self.addWidget(self._shape_label)
        self._shape_combo_action = self.addWidget(self._shape_combo)
        self._set_shape_visible(False)

    def _set_shape_visible(self, visible: bool) -> None:
        self._shape_label_action.setVisible(visible)
        self._shape_combo_action.setVisible(visible)

    def _emit_shape(self, _index: int) -> None:
        variant = str(self._shape_combo.currentData())
        spec = SHAPE_BY_ID.get(variant)
        if spec is not None and spec.availability == "live":
            self.shape_variant_changed.emit(variant)

    def set_shape_variant(self, variant_id: str) -> None:
        index = self._shape_combo.findData(variant_id)
        if index >= 0:
            self._shape_combo.blockSignals(True)
            self._shape_combo.setCurrentIndex(index)
            self._shape_combo.blockSignals(False)

    def set_tool(self, tool_id: str) -> None:
        tool = TOOL_BY_ID.get(tool_id)
        if tool is None:
            self._title.setText(tool_id)
            self._hint.setText("")
            self._set_shape_visible(False)
            return
        self._title.setText(tool.label)
        if tool.availability == "stub":
            self._hint.setText(f"Not available yet ({tool.stage_hint})")
            self._set_shape_visible(False)
            return
        self._hint.setText(tool.status_hint)
        self._set_shape_visible(tool.tool_id == "shape")
