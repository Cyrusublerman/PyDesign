"""Derived autosave snapshots that never replace authored project source."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RecoverySnapshot:
    source_path: Path
    content: str
    base_sha256: str
    saved_at: float


class RecoveryStore:
    def __init__(self, project_root: str | Path) -> None:
        self.root = Path(project_root).expanduser().resolve()
        self.directory = self.root / ".pydesign" / "recovery" / "buffers"

    def save(self, source_path: str | Path, content: str, *, base_content: str) -> None:
        path = self._source(source_path)
        payload = {
            "version": 1,
            "source": path.relative_to(self.root).as_posix(),
            "base_sha256": hashlib.sha256(base_content.encode("utf-8")).hexdigest(),
            "saved_at": time.time(),
            "content": content,
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        _atomic_write(
            self._snapshot_path(path), json.dumps(payload, ensure_ascii=False, sort_keys=True)
        )

    def load(self, source_path: str | Path) -> RecoverySnapshot | None:
        path = self._source(source_path)
        snapshot_path = self._snapshot_path(path)
        if not snapshot_path.is_file():
            return None
        try:
            payload: Any = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or payload.get("version") != 1:
            return None
        content = payload.get("content")
        base_sha256 = payload.get("base_sha256")
        saved_at = payload.get("saved_at")
        if not isinstance(content, str) or not isinstance(base_sha256, str):
            return None
        if not isinstance(saved_at, (int, float)):
            return None
        return RecoverySnapshot(path, content, base_sha256, float(saved_at))

    def clear(self, source_path: str | Path) -> None:
        self._snapshot_path(self._source(source_path)).unlink(missing_ok=True)

    def _source(self, source_path: str | Path) -> Path:
        path = Path(source_path).expanduser().resolve()
        try:
            path.relative_to(self.root)
        except ValueError as error:
            raise ValueError(f"recovery source leaves project root: {path}") from error
        return path

    def _snapshot_path(self, source_path: Path) -> Path:
        relative = source_path.relative_to(self.root).as_posix()
        key = hashlib.sha256(relative.encode("utf-8")).hexdigest()
        return self.directory / f"{key}.json"


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
