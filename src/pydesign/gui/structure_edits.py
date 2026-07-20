"""Layer visibility and page-reorder commits for MainWindow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from PySide6.QtWidgets import QMessageBox

from pydesign.gui.commands import SourcePlanCommand
from pydesign.source import SourceRewriteError
from pydesign.source.structure_rewrite import plan_layer_visibility_update, plan_page_reorder


class StructureHost(Protocol):
    project_root: Any
    source_undo: Any
    canvas: Any
    rail: Any

    def save_source(self) -> bool: ...
    def run_project(self) -> None: ...
    def show_source_error(self, message: str) -> None: ...
    def after_source_change(self, path: Path, object_id: str) -> None: ...


def commit_layer_visibility(host: StructureHost, layer_id: str, visible: bool) -> None:
    if host.project_root is None or not host.save_source():
        host.run_project()
        return
    try:
        plan = plan_layer_visibility_update(host.project_root, layer_id, visible=visible)
    except (OSError, ValueError, KeyError, SourceRewriteError) as error:
        host.show_source_error(str(error))
        host.run_project()
        return
    host.source_undo.push(SourcePlanCommand(host, plan))


def commit_page_reorder(host: StructureHost, desired_page_ids: list[str]) -> None:
    if host.project_root is None or not host.save_source():
        return
    current = [str(page["id"]) for page in host.canvas.page_summaries]
    if current == desired_page_ids:
        return
    document_id = str(host.canvas.document_id or "")
    if not document_id:
        QMessageBox.warning(host.rail, "Reorder pages", "Document id is unavailable.")
        return
    try:
        plan = plan_page_reorder(
            host.project_root,
            document_id,
            current_page_ids=tuple(current),
            desired_page_ids=tuple(desired_page_ids),
        )
    except (OSError, ValueError, KeyError, SourceRewriteError) as error:
        host.show_source_error(str(error))
        return
    host.source_undo.push(SourcePlanCommand(host, plan))
