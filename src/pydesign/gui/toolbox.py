"""Vertical exclusive tool dock — GIMP-like persistent tools only."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QMenu, QToolBar, QToolButton, QWidget

from pydesign.gui.icons import icon_for
from pydesign.gui.tools import SHAPE_VARIANTS, TOOLS, ToolId, ToolSpec


class ToolboxBar(QToolBar):
    tool_chosen = Signal(str)
    shape_variant_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Tools", parent)
        self.setObjectName("toolbox-bar")
        self.setMovable(False)
        self.setFloatable(False)
        self.setOrientation(Qt.Orientation.Vertical)
        self.setIconSize(QSize(22, 22))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setAccessibleName("Canvas tools")
        self._group = QActionGroup(self)
        self._group.setExclusive(True)
        self._actions: dict[str, QAction] = {}
        self._shape_variant = "rectangle"
        self._shape_button: QToolButton | None = None
        previous_group = ""
        for tool in TOOLS:
            if previous_group and tool.group != previous_group:
                self.addSeparator()
            previous_group = tool.group
            if tool.tool_id == "shape":
                self._add_shape_tool(tool)
            else:
                action = self._make_action(tool)
                self._actions[tool.tool_id] = action
                self.addAction(action)
        self._group.triggered.connect(self._emit_tool)
        self.set_tool("select")

    def _make_action(self, tool: ToolSpec) -> QAction:
        tip = tool.label if tool.availability == "live" else f"{tool.label} — {tool.stage_hint}"
        action = QAction(icon_for(tool.tool_id), tool.label, self)
        action.setCheckable(True)
        action.setEnabled(tool.availability == "live")
        action.setToolTip(f"{tip} ({tool.shortcut})" if tool.shortcut else tip)
        action.setStatusTip(tool.status_hint or tip)
        action.setData(tool.tool_id)
        if tool.shortcut and tool.availability == "live":
            action.setShortcut(QKeySequence(tool.shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self._group.addAction(action)
        return action

    def _add_shape_tool(self, tool: ToolSpec) -> None:
        action = self._make_action(tool)
        self._actions[tool.tool_id] = action
        button = QToolButton(self)
        button.setDefaultAction(action)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        menu = QMenu(button)
        variant_group = QActionGroup(menu)
        variant_group.setExclusive(True)
        for variant in SHAPE_VARIANTS:
            item = QAction(icon_for(variant.variant_id), variant.label, menu)
            item.setCheckable(True)
            item.setEnabled(variant.availability == "live")
            item.setData(variant.variant_id)
            tip = (
                variant.label
                if variant.availability == "live"
                else f"{variant.label} — {variant.stage_hint}"
            )
            item.setToolTip(tip)
            if variant.variant_id == self._shape_variant:
                item.setChecked(True)
            item.triggered.connect(self._shape_variant_chosen)
            variant_group.addAction(item)
            menu.addAction(item)
        button.setMenu(menu)
        self._shape_button = button
        self.addWidget(button)

    def _shape_variant_chosen(self, _checked: bool = False) -> None:
        action = self.sender()
        if not isinstance(action, QAction):
            return
        variant = str(action.data())
        self._shape_variant = variant
        shape_action = self._actions["shape"]
        shape_action.setIcon(icon_for(variant))
        shape_action.setChecked(True)
        self.shape_variant_changed.emit(variant)
        self.tool_chosen.emit("shape")

    def _emit_tool(self, action: QAction) -> None:
        self.tool_chosen.emit(str(action.data()))

    def set_tool(self, tool_id: ToolId | str) -> None:
        mapped = (
            "shape"
            if tool_id == "rectangle"
            else "pen"
            if tool_id in {"bezier", "pen"}
            else str(tool_id)
        )
        action = self._actions.get(mapped)
        if action is None or not action.isEnabled():
            action = self._actions["select"]
        action.setChecked(True)

    def set_shape_variant(self, variant_id: str) -> None:
        if variant_id not in {item.variant_id for item in SHAPE_VARIANTS}:
            return
        self._shape_variant = variant_id
        self._actions["shape"].setIcon(icon_for(variant_id))
        if self._shape_button is not None and self._shape_button.menu() is not None:
            for action in self._shape_button.menu().actions():
                action.setChecked(str(action.data()) == variant_id)

    def shape_variant(self) -> str:
        return self._shape_variant

    def current_tool(self) -> str:
        checked = self._group.checkedAction()
        return str(checked.data()) if checked is not None else "select"

    def apply_shortcuts(self, keymap: dict[str, str]) -> None:
        for tool_id, action in self._actions.items():
            command_id = f"tool.{tool_id}"
            shortcut = keymap.get(command_id, "")
            if shortcut and action.isEnabled():
                action.setShortcut(QKeySequence(shortcut))
            elif not action.isEnabled():
                action.setShortcut(QKeySequence())
