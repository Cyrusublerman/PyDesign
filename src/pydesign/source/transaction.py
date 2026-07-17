"""Atomic, conflict-checked application of visible Python source edits."""

from __future__ import annotations

import contextlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from pydesign.source.edits import SourceEditPlan
from pydesign.source.journal import PendingSourceTransaction, discover_project_root


class SourceTransactionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AppliedSourceEdit:
    plan: SourceEditPlan

    def undo_plan(self) -> SourceEditPlan:
        return SourceEditPlan(
            path=self.plan.path,
            before=self.plan.after,
            after=self.plan.before,
            description=f"Undo {self.plan.description}",
            object_id=self.plan.object_id,
            property_name=self.plan.property_name,
            strategy=self.plan.strategy,
        )


@dataclass(frozen=True, slots=True)
class SourceTransaction:
    """A group of source plans that must be accepted or rejected together.

    Every original is checked before the first write. If a later filesystem write
    fails, files already replaced are restored from their byte-exact originals.
    Duplicate paths are rejected because their ordering would otherwise be
    ambiguous and unsafe.
    """

    plans: tuple[SourceEditPlan, ...]
    description: str

    @classmethod
    def create(cls, plans: tuple[SourceEditPlan, ...], *, description: str | None = None) -> Self:
        if not plans:
            raise SourceTransactionError("a source transaction must contain at least one edit")
        paths = [plan.path.resolve() for plan in plans]
        if len(paths) != len(set(paths)):
            raise SourceTransactionError("a source transaction cannot edit one path twice")
        return cls(plans, description or "; ".join(plan.description for plan in plans))

    def undo_transaction(self) -> SourceTransaction:
        return SourceTransaction(
            tuple(
                SourceEditPlan(
                    path=plan.path,
                    before=plan.after,
                    after=plan.before,
                    description=f"Undo {plan.description}",
                    object_id=plan.object_id,
                    property_name=plan.property_name,
                    strategy=plan.strategy,
                )
                for plan in reversed(self.plans)
            ),
            f"Undo {self.description}",
        )


def apply_source_edit(
    plan: SourceEditPlan, *, project_root: str | Path | None = None
) -> AppliedSourceEdit:
    apply_source_transaction(SourceTransaction.create((plan,)), project_root=project_root)
    return AppliedSourceEdit(plan)


def apply_source_transaction(
    transaction: SourceTransaction, *, project_root: str | Path | None = None
) -> SourceTransaction:
    """Apply a preflighted transaction and return its byte-exact inverse."""

    for plan in transaction.plans:
        try:
            current = plan.path.read_text(encoding="utf-8")
        except OSError as error:
            raise SourceTransactionError(f"cannot read {plan.path}: {error}") from error
        if current != plan.before:
            raise SourceTransactionError(
                f"source changed after the edit was planned: {plan.path}; re-run the operation"
            )

    root = (
        Path(project_root).expanduser().resolve()
        if project_root is not None
        else discover_project_root(transaction.plans)
    )
    journal = PendingSourceTransaction.prepare(root, transaction.description, transaction.plans)
    try:
        journal.write()
    except OSError as error:
        raise SourceTransactionError(
            f"cannot create source transaction journal: {error}"
        ) from error

    written: list[SourceEditPlan] = []
    try:
        for plan in transaction.plans:
            _atomic_write_text(plan.path, plan.after)
            written.append(plan)
    except OSError as error:
        rollback_failures: list[str] = []
        for plan in reversed(written):
            try:
                _atomic_write_text(plan.path, plan.before)
            except OSError as rollback_error:
                rollback_failures.append(f"{plan.path}: {rollback_error}")
        detail = f"source transaction failed and was rolled back: {error}"
        if rollback_failures:
            detail += "; rollback also failed for " + ", ".join(rollback_failures)
        else:
            journal.discard()
        raise SourceTransactionError(detail) from error
    journal.discard()
    return transaction.undo_transaction()


def _atomic_write_text(path: Path, content: str) -> None:
    destination = path
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise
