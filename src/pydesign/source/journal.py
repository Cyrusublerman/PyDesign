"""Persistent write-ahead journals for crash-safe source transactions."""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from pydesign.source.edits import SourceEditPlan


class SourceJournalError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class JournalPlan:
    path: Path
    before: str
    after: str


@dataclass(frozen=True, slots=True)
class PendingSourceTransaction:
    project_root: Path
    transaction_id: str
    description: str
    plans: tuple[JournalPlan, ...]

    @classmethod
    def prepare(
        cls,
        project_root: str | Path,
        description: str,
        plans: tuple[SourceEditPlan, ...],
        *,
        transaction_id: str | None = None,
    ) -> Self:
        root = Path(project_root).expanduser().resolve()
        journal_plans: list[JournalPlan] = []
        for plan in plans:
            path = plan.path.expanduser().resolve()
            try:
                path.relative_to(root)
            except ValueError as error:
                raise SourceJournalError(f"transaction path leaves project root: {path}") from error
            journal_plans.append(JournalPlan(path, plan.before, plan.after))
        return cls(
            root,
            transaction_id or secrets.token_hex(16),
            description,
            tuple(journal_plans),
        )

    @property
    def directory(self) -> Path:
        return self.project_root / ".pydesign" / "recovery" / "transactions"

    @property
    def path(self) -> Path:
        return self.directory / f"{self.transaction_id}.json"

    def write(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "transaction_id": self.transaction_id,
            "description": self.description,
            "plans": [
                {
                    "source": plan.path.relative_to(self.project_root).as_posix(),
                    "before": plan.before,
                    "after": plan.after,
                }
                for plan in self.plans
            ],
        }
        _atomic_write(self.path, json.dumps(payload, ensure_ascii=False, sort_keys=True))

    def discard(self) -> None:
        self.path.unlink(missing_ok=True)


@dataclass(frozen=True, slots=True)
class TransactionRecoveryReport:
    recovered: tuple[str, ...]
    conflicts: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.conflicts


def recover_source_transactions(project_root: str | Path) -> TransactionRecoveryReport:
    """Roll back every valid uncommitted journal without overwriting divergence."""

    root = Path(project_root).expanduser().resolve()
    directory = root / ".pydesign" / "recovery" / "transactions"
    if not directory.is_dir():
        return TransactionRecoveryReport((), ())
    recovered: list[str] = []
    conflicts: list[str] = []
    for journal_path in sorted(directory.glob("*.json")):
        try:
            pending = _load_pending(root, journal_path)
            current = tuple(plan.path.read_text(encoding="utf-8") for plan in pending.plans)
            divergent = [
                plan.path
                for plan, content in zip(pending.plans, current, strict=True)
                if content not in {plan.before, plan.after}
            ]
            if divergent:
                relative = ", ".join(path.relative_to(root).as_posix() for path in divergent)
                conflicts.append(
                    f"{pending.transaction_id}: source diverged from journal ({relative})"
                )
                continue
            for plan, content in zip(reversed(pending.plans), reversed(current), strict=True):
                if content == plan.after:
                    _atomic_write(plan.path, plan.before)
            pending.discard()
            recovered.append(pending.transaction_id)
        except (OSError, SourceJournalError, json.JSONDecodeError) as error:
            conflicts.append(f"{journal_path.name}: {error}")
    return TransactionRecoveryReport(tuple(recovered), tuple(conflicts))


def discover_project_root(plans: tuple[SourceEditPlan, ...]) -> Path:
    resolved = [plan.path.expanduser().resolve() for plan in plans]
    common = Path(os.path.commonpath([str(path.parent) for path in resolved]))
    for candidate in (common, *common.parents):
        if (candidate / "project.toml").is_file():
            return candidate
    if common == Path(common.anchor):
        raise SourceJournalError("cannot journal a transaction across unrelated filesystem roots")
    return common


def _load_pending(root: Path, path: Path) -> PendingSourceTransaction:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise SourceJournalError("unsupported or malformed transaction journal")
    transaction_id = payload.get("transaction_id")
    description = payload.get("description")
    raw_plans = payload.get("plans")
    if not isinstance(transaction_id, str) or not isinstance(description, str):
        raise SourceJournalError("transaction journal identity is malformed")
    if path.stem != transaction_id or not isinstance(raw_plans, list) or not raw_plans:
        raise SourceJournalError("transaction journal plan list is malformed")
    plans: list[JournalPlan] = []
    for raw in raw_plans:
        if not isinstance(raw, dict):
            raise SourceJournalError("transaction journal plan is malformed")
        source = raw.get("source")
        before = raw.get("before")
        after = raw.get("after")
        if not isinstance(source, str) or not isinstance(before, str) or not isinstance(after, str):
            raise SourceJournalError("transaction journal source content is malformed")
        relative = Path(source)
        if relative.is_absolute() or ".." in relative.parts:
            raise SourceJournalError(f"unsafe transaction journal path: {source}")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as error:
            raise SourceJournalError(
                f"transaction journal path leaves project: {source}"
            ) from error
        plans.append(JournalPlan(target, before, after))
    return PendingSourceTransaction(root, transaction_id, description, tuple(plans))


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise
