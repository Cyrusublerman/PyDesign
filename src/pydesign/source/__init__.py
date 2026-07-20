"""Visible-Python ownership analysis and source transaction planning."""

from pydesign.source.analysis import (
    Declaration,
    DuplicateSourceIdError,
    OwnershipKind,
    PropertyOwnership,
    SourceIndex,
    build_source_index,
)
from pydesign.source.edits import Frame, FrameStrategy, SourceEditPlan, SourceRewriteError
from pydesign.source.format_source import finalize_edit_plan, format_python_source
from pydesign.source.journal import (
    PendingSourceTransaction,
    SourceJournalError,
    TransactionRecoveryReport,
    recover_source_transactions,
)
from pydesign.source.path_rewrite import (
    BezierPoints,
    bezier_edit_options,
    plan_bezier_update,
)
from pydesign.source.property_rewrite import (
    literal_edit_options,
    plan_quantity_property_update,
    plan_string_property_update,
    style_edit_options,
)
from pydesign.source.rewrite import (
    frame_edit_options,
    new_gui_id,
    plan_bezier_insertion,
    plan_ellipse_insertion,
    plan_frame_update,
    plan_line_insertion,
    plan_rectangle_insertion,
)
from pydesign.source.structure_rewrite import (
    plan_layer_visibility_update,
    plan_page_reorder,
)
from pydesign.source.text_rewrite import plan_text_frame_insertion
from pydesign.source.transaction import (
    SourceTransaction,
    SourceTransactionError,
    apply_source_edit,
    apply_source_transaction,
)

__all__ = [
    "BezierPoints",
    "Declaration",
    "DuplicateSourceIdError",
    "Frame",
    "FrameStrategy",
    "OwnershipKind",
    "PendingSourceTransaction",
    "PropertyOwnership",
    "SourceEditPlan",
    "SourceIndex",
    "SourceJournalError",
    "SourceRewriteError",
    "SourceTransaction",
    "SourceTransactionError",
    "TransactionRecoveryReport",
    "apply_source_edit",
    "apply_source_transaction",
    "bezier_edit_options",
    "build_source_index",
    "finalize_edit_plan",
    "format_python_source",
    "frame_edit_options",
    "literal_edit_options",
    "new_gui_id",
    "plan_bezier_insertion",
    "plan_bezier_update",
    "plan_ellipse_insertion",
    "plan_frame_update",
    "plan_layer_visibility_update",
    "plan_line_insertion",
    "plan_page_reorder",
    "plan_quantity_property_update",
    "plan_rectangle_insertion",
    "plan_string_property_update",
    "plan_text_frame_insertion",
    "recover_source_transactions",
    "style_edit_options",
]
