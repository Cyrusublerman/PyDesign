"""Undoable source transaction commands, decoupled from the main window."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtGui import QUndoCommand

from pydesign.source import SourceEditPlan, SourceTransactionError, apply_source_edit


class SourceCommandHost(Protocol):
    def show_source_error(self, message: str) -> None: ...

    def after_source_change(self, path: Path, object_id: str) -> None: ...


class SourcePlanCommand(QUndoCommand):
    def __init__(self, window: SourceCommandHost, plan: SourceEditPlan) -> None:
        super().__init__(plan.description)
        self.window = window
        self.plan = plan

    def redo(self) -> None:
        self._apply(self.plan)

    def undo(self) -> None:
        reverse = SourceEditPlan(
            path=self.plan.path,
            before=self.plan.after,
            after=self.plan.before,
            description=f"Undo {self.plan.description}",
            object_id=self.plan.object_id,
            property_name=self.plan.property_name,
            strategy=self.plan.strategy,
        )
        self._apply(reverse)

    def _apply(self, plan: SourceEditPlan) -> None:
        try:
            apply_source_edit(plan)
        except SourceTransactionError as error:
            self.setObsolete(True)
            self.window.show_source_error(str(error))
            return
        self.window.after_source_change(plan.path, plan.object_id)
