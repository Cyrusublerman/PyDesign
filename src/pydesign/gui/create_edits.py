"""Canvas create-tool commits for rectangles and text frames."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydesign.gui.commands import SourcePlanCommand
from pydesign.gui.types import _is_frame
from pydesign.source import (
    SourceRewriteError,
    build_source_index,
    new_gui_id,
    plan_ellipse_insertion,
    plan_line_insertion,
    plan_rectangle_insertion,
)
from pydesign.source.text_rewrite import plan_text_frame_insertion


class CreateHost(Protocol):
    project_root: Any
    source_undo: Any
    selected_object_id: str

    def save_source(self) -> bool: ...
    def show_source_error(self, message: str) -> None: ...
    def after_source_change(self, path: Path, object_id: str) -> None: ...


def commit_rectangle_create(host: CreateHost, page_id: str, frame_value: object) -> None:
    commit_shape_create(host, page_id, frame_value, kind="rectangle")


def commit_ellipse_create(host: CreateHost, page_id: str, frame_value: object) -> None:
    commit_shape_create(host, page_id, frame_value, kind="ellipse")


def commit_shape_create(
    host: CreateHost, page_id: str, frame_value: object, *, kind: str = "rectangle"
) -> None:
    if host.project_root is None or not _is_frame(frame_value) or not host.save_source():
        return
    try:
        index = build_source_index(host.project_root)
        object_id = new_gui_id({item.object_id for item in index.declarations})
        if kind == "line":
            x, y, width, height = frame_value
            plan = plan_line_insertion(
                host.project_root,
                page_id,
                object_id=object_id,
                start=(x, y),
                end=(x + width, y + height),
            )
        elif kind == "ellipse":
            plan = plan_ellipse_insertion(
                host.project_root, page_id, object_id=object_id, frame=frame_value
            )
        else:
            plan = plan_rectangle_insertion(
                host.project_root, page_id, object_id=object_id, frame=frame_value
            )
    except (OSError, ValueError, KeyError, SourceRewriteError) as error:
        host.show_source_error(str(error))
        return
    host.selected_object_id = object_id
    host.source_undo.push(SourcePlanCommand(host, plan))


def commit_text_create(host: CreateHost, page_id: str, frame_value: object) -> None:
    if host.project_root is None or not _is_frame(frame_value) or not host.save_source():
        return
    try:
        index = build_source_index(host.project_root)
        object_id = new_gui_id({item.object_id for item in index.declarations})
        plan = plan_text_frame_insertion(
            host.project_root, page_id, object_id=object_id, frame=frame_value
        )
    except (OSError, ValueError, KeyError, SourceRewriteError) as error:
        host.show_source_error(str(error))
        return
    host.selected_object_id = object_id
    host.source_undo.push(SourcePlanCommand(host, plan))
