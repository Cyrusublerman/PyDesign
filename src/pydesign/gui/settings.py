"""Application-level settings kept outside portable project folders."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths


class ApplicationSettings:
    """Small typed facade over platform-native Qt application settings."""

    def __init__(self, backend: QSettings | None = None) -> None:
        self._backend = backend or QSettings()

    def default_projects_directory(self) -> Path:
        configured = str(self._backend.value("projects/defaultDirectory", "")).strip()
        if configured:
            return Path(configured).expanduser()
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        base = Path(documents) if documents else Path.home() / "Documents"
        return base / "PyDesign Projects"

    def set_default_projects_directory(self, path: str | Path) -> None:
        self._backend.setValue("projects/defaultDirectory", str(Path(path).expanduser()))

    def recent_projects(self) -> tuple[Path, ...]:
        raw = str(self._backend.value("projects/recent", "[]"))
        try:
            values = json.loads(raw)
        except (TypeError, ValueError):
            return ()
        if not isinstance(values, list):
            return ()
        result: list[Path] = []
        for value in values:
            if not isinstance(value, str):
                continue
            path = Path(value).expanduser()
            if path.is_dir() and (path / "project.toml").is_file():
                result.append(path)
        return tuple(result)

    def add_recent_project(self, path: str | Path, *, limit: int = 12) -> None:
        resolved = Path(path).expanduser().resolve()
        ordered = [resolved]
        ordered.extend(item for item in self.recent_projects() if item.resolve() != resolved)
        self._backend.setValue(
            "projects/recent", json.dumps([str(item) for item in ordered[:limit]])
        )

    def remove_recent_project(self, path: str | Path) -> None:
        resolved = Path(path).expanduser().resolve()
        remaining = [item for item in self.recent_projects() if item.resolve() != resolved]
        self._backend.setValue("projects/recent", json.dumps([str(item) for item in remaining]))

    def window_geometry(self) -> bytes | None:
        value = self._backend.value("window/mainGeometry")
        return bytes(value) if value is not None else None

    def window_state(self) -> bytes | None:
        value = self._backend.value("window/mainState")
        return bytes(value) if value is not None else None

    def save_window(self, *, geometry: bytes, state: bytes) -> None:
        self._backend.setValue("window/mainGeometry", geometry)
        self._backend.setValue("window/mainState", state)
        self._backend.sync()
