"""Portable PyDesign project creation, copying, and packaging.

This module deliberately has no Qt dependency.  The CLI and desktop application use
the same filesystem rules, which keeps project folders portable and makes lifecycle
operations independently testable.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pydesign.runtime.project import ProjectConfig, load_project_config

TRANSIENT_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".pydesign",
        ".svn",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "exports",
    }
)
TRANSIENT_FILE_SUFFIXES = (".pyc", ".pyo", ".tmp")


class ProjectOperationError(ValueError):
    """Raised when a project lifecycle operation cannot be completed safely."""


class UnsafeProjectLocationError(ProjectOperationError):
    """Raised when a new project would be created in the PyDesign source checkout."""


@dataclass(frozen=True, slots=True)
class PackageResult:
    output: Path
    file_count: int
    manifest_sha256: str


def find_pydesign_source_checkout(start: str | Path | None = None) -> Path | None:
    """Return the editable PyDesign source checkout containing *start*, if any."""

    candidate = Path(start).resolve() if start is not None else Path(__file__).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for parent in (candidate, *candidate.parents):
        if _is_pydesign_source_root(parent):
            return parent
    return None


def is_within(path: str | Path, parent: str | Path) -> bool:
    """Return whether *path* is equal to or below *parent* after resolution."""

    try:
        Path(path).expanduser().resolve().relative_to(Path(parent).expanduser().resolve())
    except ValueError:
        return False
    return True


def is_bundled_example(path: str | Path) -> bool:
    checkout = find_pydesign_source_checkout()
    return checkout is not None and is_within(path, checkout / "examples")


def ensure_safe_project_destination(
    destination: str | Path,
    *,
    allow_in_source_checkout: bool = False,
    source_checkout: str | Path | None = None,
) -> Path:
    """Resolve *destination* and reject accidental writes into this source checkout."""

    resolved = Path(destination).expanduser().resolve()
    checkout = (
        Path(source_checkout).expanduser().resolve()
        if source_checkout is not None
        else find_pydesign_source_checkout()
    )
    if checkout is not None and is_within(resolved, checkout) and not allow_in_source_checkout:
        raise UnsafeProjectLocationError(
            f"user projects cannot be created inside the PyDesign source checkout: {checkout}. "
            "Choose a folder such as Documents/PyDesign Projects instead."
        )
    return resolved


def create_project(
    destination: str | Path,
    *,
    name: str | None = None,
    allow_in_source_checkout: bool = False,
    source_checkout: str | Path | None = None,
) -> ProjectConfig:
    """Create a complete starter project as one atomic directory operation."""

    target = ensure_safe_project_destination(
        destination,
        allow_in_source_checkout=allow_in_source_checkout,
        source_checkout=source_checkout,
    )
    _require_new_destination(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    display_name = _normalise_project_name(name or target.name)
    project_id = str(uuid.uuid4())
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.creating-", dir=target.parent))
    try:
        _write_starter_project(staging, name=display_name, project_id=project_id)
        load_project_config(staging)
        os.replace(staging, target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return load_project_config(target)


def duplicate_project(
    source: str | Path,
    destination: str | Path,
    *,
    name: str | None = None,
    allow_in_source_checkout: bool = False,
    source_checkout: str | Path | None = None,
) -> ProjectConfig:
    """Copy authored project inputs while discarding caches, output, and VCS state."""

    source_config = load_project_config(source)
    target = ensure_safe_project_destination(
        destination,
        allow_in_source_checkout=allow_in_source_checkout,
        source_checkout=source_checkout,
    )
    _require_new_destination(target)
    if is_within(target, source_config.root):
        raise ProjectOperationError("a project copy cannot be placed inside its source project")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.copying-", dir=target.parent))
    try:
        _copy_portable_tree(source_config.root, staging)
        manifest = staging / "project.toml"
        source_text = manifest.read_text(encoding="utf-8")
        source_text = _set_project_manifest_value(source_text, "id", str(uuid.uuid4()))
        source_text = _set_project_manifest_value(
            source_text, "name", _normalise_project_name(name or target.name)
        )
        manifest.write_text(source_text, encoding="utf-8")
        load_project_config(staging)
        os.replace(staging, target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return load_project_config(target)


def package_project(source: str | Path, output: str | Path) -> PackageResult:
    """Create a portable project folder or deterministic ZIP with an input manifest."""

    config = load_project_config(source)
    destination = Path(output).expanduser().resolve()
    if destination == config.root:
        raise ProjectOperationError("package output cannot replace the source project")
    if is_within(destination, config.root):
        relative = destination.relative_to(config.root)
        if not relative.parts or relative.parts[0] != "exports":
            raise ProjectOperationError(
                "package output inside a project must be placed under its exports directory"
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlinks(config.root)
    files = tuple(_portable_files(config.root, excluded_paths={destination}))
    manifest = _package_manifest(config, files)
    manifest_bytes = _json_bytes(manifest)
    if destination.suffix.lower() == ".zip":
        _write_package_zip(config.root, destination, files, manifest_bytes)
    else:
        _write_package_directory(config.root, destination, files, manifest_bytes)
    return PackageResult(
        output=destination,
        file_count=len(files),
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )


def _is_pydesign_source_root(path: Path) -> bool:
    manifest = path / "pyproject.toml"
    package = path / "src" / "pydesign"
    if not manifest.is_file() or not package.is_dir():
        return False
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError:
        return False
    return re.search(r"(?m)^name\s*=\s*[\"']pydesign[\"']\s*$", text) is not None


def _require_new_destination(destination: Path) -> None:
    if destination.exists():
        raise ProjectOperationError(f"destination already exists: {destination}")


def _normalise_project_name(name: str) -> str:
    value = " ".join(name.split()).strip()
    if not value:
        raise ProjectOperationError("project name cannot be empty")
    if any(character in value for character in "\r\n\0"):
        raise ProjectOperationError("project name contains an invalid character")
    return value


def _write_starter_project(root: Path, *, name: str, project_id: str) -> None:
    for relative in (
        "pages",
        "components",
        "styles",
        "content",
        "assets/images",
        "assets/vectors",
        "assets/fonts",
        "assets/colour_profiles",
        "profiles",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "project.toml").write_text(
        "\n".join(
            (
                "[project]",
                "format = 1",
                f"id = {json.dumps(project_id)}",
                f"name = {json.dumps(name, ensure_ascii=False)}",
                'entrypoint = "document:build"',
                'default_profile = "screen"',
                "",
                "[python]",
                'requires = ">=3.12"',
                "",
                "[paths]",
                'assets = ["assets", "content"]',
                'exports = "exports"',
                "",
                "[build]",
                "deterministic = true",
                "allow_system_fonts = false",
                "",
                "[profiles.screen]",
                'kind = "display-list"',
                "",
            )
        ),
        encoding="utf-8",
    )
    (root / "document.py").write_text(
        "from pydesign import BuildContext, Document\n"
        "from pages.page_001 import page\n\n\n"
        "def build(ctx: BuildContext) -> Document:\n"
        "    return Document(\n"
        '        id="document",\n'
        f"        title={name!r},\n"
        "        pages=[page(ctx)],\n"
        "    )\n",
        encoding="utf-8",
    )
    (root / "pages" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pages" / "page_001.py").write_text(
        "from pydesign import BuildContext, Page, mm\n\n\n"
        "def page(_ctx: BuildContext) -> Page:\n"
        "    return Page(\n"
        '        id="page-001",\n'
        "        size=(210 * mm, 297 * mm),\n"
        "        elements=[],\n"
        "    )\n",
        encoding="utf-8",
    )
    for package in ("components", "styles", "profiles"):
        (root / package / "__init__.py").write_text("", encoding="utf-8")
    (root / ".gitignore").write_text(
        ".pydesign/\nexports/\nbuild/\n.venv/\n__pycache__/\n*.py[cod]\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"# {name}\n\n"
        "This folder is a portable PyDesign project. `project.toml` identifies the project, "
        "and the visible Python source is the authored document truth.\n\n"
        "```bash\n"
        "pydesign open .\n"
        "pydesign check .\n"
        "pydesign package . --output ../project-package.zip\n"
        "```\n",
        encoding="utf-8",
    )


def _set_project_manifest_value(source: str, key: str, value: str) -> str:
    lines = source.splitlines(keepends=True)
    project_start: int | None = None
    project_end = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[project]":
            project_start = index
            continue
        if project_start is not None and stripped.startswith("[") and stripped.endswith("]"):
            project_end = index
            break
    if project_start is None:
        raise ProjectOperationError("project.toml has no [project] table")
    replacement = f"{key} = {json.dumps(value, ensure_ascii=False)}\n"
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for index in range(project_start + 1, project_end):
        if pattern.match(lines[index]):
            lines[index] = replacement
            return "".join(lines)
    lines.insert(project_start + 1, replacement)
    return "".join(lines)


def _is_transient(relative: Path) -> bool:
    return bool(TRANSIENT_DIRECTORY_NAMES.intersection(relative.parts)) or relative.name.endswith(
        TRANSIENT_FILE_SUFFIXES
    )


def _portable_files(root: Path, *, excluded_paths: set[Path] | None = None) -> Iterable[Path]:
    excluded = {path.resolve() for path in excluded_paths or set()}
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if _is_transient(relative) or not path.is_file() or path.resolve() in excluded:
            continue
        yield path


def _portable_directories(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if _is_transient(relative) or not path.is_dir() or path.is_symlink():
            continue
        yield path


def _copy_portable_tree(source: Path, destination: Path) -> None:
    for source_path in _portable_directories(source):
        (destination / source_path.relative_to(source)).mkdir(parents=True, exist_ok=True)
    for source_path in _portable_files(source):
        relative = source_path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_symlink():
            target.symlink_to(os.readlink(source_path))
        else:
            shutil.copy2(source_path, target)


def _reject_symlinks(root: Path) -> None:
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not _is_transient(relative) and path.is_symlink():
            raise ProjectOperationError(
                f"portable packages cannot contain symbolic links: {relative}"
            )


def _package_manifest(config: ProjectConfig, files: Iterable[Path]) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for path in files:
        payload = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(config.root).as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
            }
        )
    return {
        "schema_version": 1,
        "generator": "PyDesign",
        "project": {
            "id": config.project_id,
            "name": config.name,
            "format": config.format_version,
        },
        "files": entries,
    }


def _json_bytes(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _write_package_zip(
    root: Path, destination: Path, files: Iterable[Path], manifest: bytes
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    try:
        with zipfile.ZipFile(
            temporary_name, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in _portable_directories(root):
                _zip_directory(archive, f"{path.relative_to(root).as_posix()}/")
            for path in files:
                _zip_bytes(archive, path.relative_to(root).as_posix(), path.read_bytes())
            _zip_bytes(archive, "package-manifest.json", manifest)
        os.replace(temporary_name, destination)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _zip_bytes(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, payload)


def _zip_directory(archive: zipfile.ZipFile, name: str) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.external_attr = (0o40755 << 16) | 0x10
    archive.writestr(info, b"")


def _write_package_directory(
    root: Path, destination: Path, files: Iterable[Path], manifest: bytes
) -> None:
    _require_new_destination(destination)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.packaging-", dir=destination.parent)
    )
    try:
        for source_path in _portable_directories(root):
            (staging / source_path.relative_to(root)).mkdir(parents=True, exist_ok=True)
        for source_path in files:
            target = staging / source_path.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
        (staging / "package-manifest.json").write_bytes(manifest)
        os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
