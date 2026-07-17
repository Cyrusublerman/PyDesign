"""Visible-Python ownership analysis and source transaction planning."""

from pydesign.source.analysis import (
    Declaration,
    DuplicateSourceIdError,
    OwnershipKind,
    PropertyOwnership,
    SourceIndex,
    build_source_index,
)
from pydesign.source.rewrite import (
    Frame,
    SourceEditPlan,
    SourceRewriteError,
    frame_edit_options,
    new_gui_id,
    plan_bezier_insertion,
    plan_frame_update,
    plan_rectangle_insertion,
)
from pydesign.source.transaction import (
    SourceTransaction,
    SourceTransactionError,
    apply_source_edit,
    apply_source_transaction,
)

__all__ = [
    "Declaration",
    "DuplicateSourceIdError",
    "Frame",
    "OwnershipKind",
    "PropertyOwnership",
    "SourceEditPlan",
    "SourceIndex",
    "SourceRewriteError",
    "SourceTransaction",
    "SourceTransactionError",
    "apply_source_edit",
    "apply_source_transaction",
    "build_source_index",
    "frame_edit_options",
    "new_gui_id",
    "plan_bezier_insertion",
    "plan_frame_update",
    "plan_rectangle_insertion",
]
