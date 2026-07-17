"""Portable project manifest loading and deterministic revision hashing."""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProjectConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    root: Path
    name: str
    format_version: int
    entrypoint: str
    default_profile: str
    deterministic: bool

    @property
    def module_name(self) -> str:
        return self.entrypoint.partition(":")[0]

    @property
    def function_name(self) -> str:
        return self.entrypoint.partition(":")[2]


def load_project_config(root: str | Path) -> ProjectConfig:
    project_root = Path(root).expanduser().resolve()
    manifest_path = project_root / "project.toml"
    if not manifest_path.is_file():
        raise ProjectConfigError(f"project manifest not found: {manifest_path}")

    with manifest_path.open("rb") as stream:
        data = tomllib.load(stream)

    project = _table(data, "project")
    build = data.get("build", {})
    if not isinstance(build, dict):
        raise ProjectConfigError("[build] must be a TOML table")

    entrypoint = str(project.get("entrypoint", "document:build"))
    module_name, separator, function_name = entrypoint.partition(":")
    if not separator or not module_name or not function_name:
        raise ProjectConfigError("project.entrypoint must have the form 'module:function'")
    if any(part in {"", ".", ".."} for part in module_name.split(".")):
        raise ProjectConfigError("project.entrypoint contains an invalid module name")

    format_version = int(project.get("format", 1))
    if format_version != 1:
        raise ProjectConfigError(f"unsupported project format {format_version}; expected 1")

    return ProjectConfig(
        root=project_root,
        name=str(project.get("name", project_root.name)),
        format_version=format_version,
        entrypoint=entrypoint,
        default_profile=str(project.get("default_profile", "screen")),
        deterministic=bool(build.get("deterministic", True)),
    )


def compute_project_revision(config: ProjectConfig) -> str:
    digest = hashlib.sha256()
    ignored_parts = {".git", ".pydesign", ".venv", "__pycache__", "exports"}
    paths = sorted(
        path
        for path in config.root.rglob("*")
        if path.is_file() and not ignored_parts.intersection(path.relative_to(config.root).parts)
    )
    for path in paths:
        relative = path.relative_to(config.root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        with path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


def _table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ProjectConfigError(f"[{key}] must be a TOML table")
    return value
