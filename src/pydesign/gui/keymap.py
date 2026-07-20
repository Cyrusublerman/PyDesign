"""Remappable application shortcuts with conflict detection."""

from __future__ import annotations

import json
from dataclasses import dataclass

DEFAULT_SHORTCUTS: dict[str, str] = {
    "file.save": "Ctrl+S",
    "build.run": "Ctrl+Return",
    "build.stop": "Shift+F5",
    "view.reveal_source": "F4",
    "view.fit_page": "Ctrl+1",
    "view.fill_width": "Ctrl+2",
    "view.actual_size": "Ctrl+0",
    "view.fit_all": "Ctrl+Shift+1",
    "view.zoom_in": "Ctrl+=",
    "view.zoom_out": "Ctrl+-",
    "view.command_palette": "Ctrl+Shift+P",
    "tool.select": "V",
    "tool.direct_select": "A",
    "tool.shape": "R",
    "tool.pen": "B",
    "tool.text": "T",
    "tool.hand": "H",
    "tool.zoom": "Z",
}

COMMAND_LABELS: dict[str, str] = {
    "file.save": "Save",
    "build.run": "Run",
    "build.stop": "Stop",
    "view.reveal_source": "Reveal Selection in Python",
    "view.fit_page": "Fit Page",
    "view.fill_width": "Fill Width",
    "view.actual_size": "Actual Size",
    "view.fit_all": "Fit All",
    "view.zoom_in": "Zoom In",
    "view.zoom_out": "Zoom Out",
    "view.command_palette": "Command Palette",
    "tool.select": "Select tool",
    "tool.direct_select": "Direct Select tool",
    "tool.shape": "Shape tool",
    "tool.pen": "Pen tool",
    "tool.text": "Text tool",
    "tool.hand": "Hand tool",
    "tool.zoom": "Zoom tool",
}


@dataclass(frozen=True, slots=True)
class ShortcutConflict:
    command_id: str
    other_id: str
    shortcut: str


def merge_keymap(overrides: dict[str, str] | None) -> dict[str, str]:
    merged = dict(DEFAULT_SHORTCUTS)
    if not overrides:
        return merged
    for key, value in overrides.items():
        if key in DEFAULT_SHORTCUTS and isinstance(value, str) and value.strip():
            merged[key] = value.strip()
    return merged


def find_conflicts(keymap: dict[str, str]) -> tuple[ShortcutConflict, ...]:
    by_shortcut: dict[str, list[str]] = {}
    for command_id, shortcut in keymap.items():
        by_shortcut.setdefault(shortcut.casefold(), []).append(command_id)
    conflicts: list[ShortcutConflict] = []
    for _shortcut, command_ids in by_shortcut.items():
        if len(command_ids) < 2:
            continue
        for index, command_id in enumerate(command_ids):
            other = command_ids[index - 1] if index else command_ids[1]
            conflicts.append(ShortcutConflict(command_id, other, keymap[command_id]))
    return tuple(conflicts)


def parse_keymap_json(raw: str) -> dict[str, str]:
    try:
        values = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    if not isinstance(values, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in values.items():
        if isinstance(key, str) and isinstance(value, str) and key in DEFAULT_SHORTCUTS:
            result[key] = value
    return result


def dump_keymap_json(keymap: dict[str, str]) -> str:
    payload = {key: keymap[key] for key in DEFAULT_SHORTCUTS if key in keymap}
    return json.dumps(payload, sort_keys=True)
