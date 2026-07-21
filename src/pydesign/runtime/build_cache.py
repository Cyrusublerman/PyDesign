"""Dependency-keyed layout/PDF cache (Stage 8)."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CacheEntry:
    key: str
    path: Path


class BuildCache:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.directory = self.root / ".pydesign" / "cache"
        self.directory.mkdir(parents=True, exist_ok=True)

    def key_for(self, *, relative_paths: tuple[str, ...], salt: str = "") -> str:
        digest = hashlib.sha256()
        digest.update(salt.encode("utf-8"))
        for relative in sorted(relative_paths):
            path = (self.root / relative).resolve()
            try:
                path.relative_to(self.root)
            except ValueError as error:
                raise ValueError(f"cache dependency escapes project root: {relative!r}") from error
            digest.update(relative.encode("utf-8"))
            if path.is_file():
                digest.update(path.read_bytes())
        return digest.hexdigest()

    def path_for(self, key: str, *, suffix: str) -> Path:
        return self.directory / f"{key}{suffix}"

    def store_json(self, key: str, payload: object) -> CacheEntry:
        path = self.path_for(key, suffix=".json")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{key}.",
            suffix=".tmp",
            dir=self.directory,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return CacheEntry(key, path)

    def load_json(self, key: str) -> object | None:
        path = self.path_for(key, suffix=".json")
        if not path.is_file():
            return None
        try:
            payload: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            with contextlib.suppress(OSError):
                path.unlink()
            return None
        return payload
