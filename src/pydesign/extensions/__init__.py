"""Extension entry points (Stage 8)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

PreflightHook = Callable[[dict[str, Any]], list[str]]


@dataclass
class ExtensionRegistry:
    preflight_hooks: list[PreflightHook]

    def __init__(self) -> None:
        self.preflight_hooks = []

    def register_preflight(self, hook: PreflightHook) -> None:
        self.preflight_hooks.append(hook)

    def run_preflight(self, layout: dict[str, Any]) -> list[str]:
        messages: list[str] = []
        for hook in self.preflight_hooks:
            messages.extend(hook(layout))
        return messages


REGISTRY = ExtensionRegistry()


def register_preflight(hook: PreflightHook) -> PreflightHook:
    REGISTRY.register_preflight(hook)
    return hook


@register_preflight
def _sample_page_count_preflight(layout: dict[str, Any]) -> list[str]:
    pages = layout.get("pages")
    if isinstance(pages, list) and len(pages) > 64:
        return [f"sample extension: large document ({len(pages)} pages)"]
    return []
