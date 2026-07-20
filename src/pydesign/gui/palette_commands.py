"""Build the searchable command-palette catalogue for MainWindow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from pydesign.gui.command_palette import PaletteCommand, shortcut_text
from pydesign.gui.keymap import DEFAULT_SHORTCUTS
from pydesign.gui.tools import TOOL_BY_ID
from pydesign.gui.workspace import PRESETS


class PaletteHost(Protocol):
    def save_source(self) -> bool: ...
    def run_project(self) -> None: ...
    def stop_project(self) -> None: ...
    def reveal_selection_source(self) -> None: ...
    def open_command_palette(self) -> None: ...
    def open_preferences(self) -> None: ...
    def open_secondary_window(self) -> None: ...
    def shortcut_for(self, command_id: str) -> str: ...
    def _apply_workspace(self, name: str) -> None: ...
    def _toolbox_tool_chosen(self, tool_id: str) -> None: ...

    _view_actions: list[tuple[str, Callable[[], None], str]]


def build_palette_commands(host: PaletteHost) -> list[PaletteCommand]:
    def sc(command_id: str) -> str:
        return shortcut_text(host.shortcut_for(command_id) or DEFAULT_SHORTCUTS.get(command_id, ""))

    def save() -> None:
        host.save_source()

    commands = [
        PaletteCommand("Save", save, sc("file.save"), "file"),
        PaletteCommand("Run", host.run_project, sc("build.run"), "build"),
        PaletteCommand("Stop", host.stop_project, sc("build.stop"), "build"),
        PaletteCommand(
            "Reveal Selection in Python",
            host.reveal_selection_source,
            sc("view.reveal_source"),
            "source",
        ),
        PaletteCommand("Preferences", host.open_preferences, shortcut_text("Ctrl+,"), "settings"),
        PaletteCommand(
            "Open Secondary Window",
            host.open_secondary_window,
            keywords="window multi float",
        ),
        PaletteCommand("Command Palette", host.open_command_palette, sc("view.command_palette")),
    ]
    for label, slot, command_id in host._view_actions:
        commands.append(PaletteCommand(label, slot, sc(command_id), "view zoom"))
    for name in PRESETS:

        def apply(workspace: str = name) -> None:
            host._apply_workspace(workspace)

        commands.append(PaletteCommand(f"Workspace: {name}", apply, keywords="workspace layout"))
    for tool_id, tool in TOOL_BY_ID.items():
        if tool.availability != "live":
            continue

        def choose(selected: str = tool_id) -> None:
            host._toolbox_tool_chosen(selected)

        commands.append(
            PaletteCommand(f"Tool: {tool.label}", choose, sc(f"tool.{tool_id}"), "tool")
        )
    return commands
