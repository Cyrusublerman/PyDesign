"""Reusable component instances (Stage 5 editorial)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydesign.model import LeafElement


@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    id: str
    generator: Callable[[dict[str, Any]], tuple[LeafElement, ...]]


@dataclass(frozen=True, slots=True)
class ComponentInstance:
    id: str
    definition_id: str
    overrides: dict[str, Any]
    detached: bool = False


def instantiate(
    definition: ComponentDefinition,
    instance: ComponentInstance,
) -> tuple[LeafElement, ...]:
    if instance.detached:
        raise ValueError(f"component instance {instance.id!r} is detached")
    return definition.generator(dict(instance.overrides))
