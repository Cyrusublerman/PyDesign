"""Inspector appearance property commits for MainWindow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydesign.gui.commands import SourcePlanCommand
from pydesign.gui.dialogs import choose_geometry_strategy
from pydesign.source import FrameStrategy, SourceRewriteError
from pydesign.source.analysis import OwnershipKind, build_source_index
from pydesign.source.property_rewrite import (
    literal_edit_options,
    plan_quantity_property_update,
    plan_string_property_update,
)


class AppearanceHost(Protocol):
    project_root: Any
    source_undo: Any
    selected_object_id: str

    def save_source(self) -> bool: ...
    def run_project(self) -> None: ...
    def show_source_error(self, message: str) -> None: ...
    def after_source_change(self, path: Path, object_id: str) -> None: ...


def commit_string_property(host: AppearanceHost, property_name: str, desired: str | None) -> None:
    if not host.selected_object_id or host.project_root is None or not host.save_source():
        return
    try:
        declaration = build_source_index(host.project_root).require(host.selected_object_id)
        ownership = declaration.property(property_name)
        kind = None if ownership is None else ownership.kind
        options = literal_edit_options(kind)
        strategy: FrameStrategy | None = (
            "safe" if "safe" in options else choose_geometry_strategy(host, options)  # type: ignore[arg-type]
        )
        if strategy is None:
            return
        plan = plan_string_property_update(
            host.project_root,
            host.selected_object_id,
            property_name,
            desired=desired,
            strategy=strategy,
        )
    except (OSError, ValueError, KeyError, SourceRewriteError) as error:
        host.show_source_error(str(error))
        return
    host.source_undo.push(SourcePlanCommand(host, plan))


def commit_quantity_property(
    host: AppearanceHost, property_name: str, desired_points: float
) -> None:
    if not host.selected_object_id or host.project_root is None or not host.save_source():
        return
    try:
        declaration = build_source_index(host.project_root).require(host.selected_object_id)
        ownership = declaration.property(property_name)
        kind: OwnershipKind | None = None if ownership is None else ownership.kind
        options = literal_edit_options(kind)
        strategy: FrameStrategy | None = (
            "safe" if "safe" in options else choose_geometry_strategy(host, options)  # type: ignore[arg-type]
        )
        if strategy is None:
            return
        plan = plan_quantity_property_update(
            host.project_root,
            host.selected_object_id,
            property_name,
            desired_points=desired_points,
            strategy=strategy,
        )
    except (OSError, ValueError, KeyError, SourceRewriteError) as error:
        host.show_source_error(str(error))
        return
    host.source_undo.push(SourcePlanCommand(host, plan))
