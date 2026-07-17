"""Headless PyDesign command-line interface."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydesign.runtime import WorkerClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pydesign", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser("check", help="evaluate and validate a project")
    _project_arguments(check)
    check.add_argument("--json", action="store_true", dest="as_json")

    render = subcommands.add_parser(
        "render-json", help="write the renderer-neutral Stage 1 display list"
    )
    _project_arguments(render)
    render.add_argument("--output", type=Path, required=True)

    open_command = subcommands.add_parser("open", help="open the desktop application")
    open_command.add_argument("project", type=Path, nargs="?", default=None)
    return parser


def _project_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project", type=Path)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "open":
        return _open_gui(args.project)

    result = WorkerClient().evaluate(args.project, profile=args.profile, timeout=args.timeout)
    if args.command == "check":
        if args.as_json:
            print(json.dumps(result.response, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            _print_human_result(result.response, result.stderr)
        return 0 if result.ok else 2

    if args.command == "render-json":
        if not result.ok or result.layout is None:
            _print_human_result(result.response, result.stderr)
            return 2
        _atomic_json_write(args.output, result.layout)
        print(f"wrote {args.output}")
        return 0
    raise AssertionError(f"unhandled command {args.command}")


def _print_human_result(response: dict[str, Any], stderr: str) -> None:
    if response.get("ok"):
        layout = response.get("layout", {})
        pages = layout.get("pages", []) if isinstance(layout, dict) else []
        revision = str(response.get("revision", "unknown"))[:12]
        print(f"OK: {len(pages)} page(s), revision {revision}")
    else:
        error = response.get("error", {})
        message = error.get("message", "evaluation failed") if isinstance(error, dict) else error
        print(f"ERROR: {message}")
    diagnostics = response.get("diagnostics", [])
    if isinstance(diagnostics, list):
        for item in diagnostics:
            if isinstance(item, dict):
                print(
                    f"{str(item.get('severity', 'info')).upper()} "
                    f"{item.get('code', 'PD-UNKNOWN')}: {item.get('message', '')}"
                )
    if stderr.strip():
        print("Worker output:")
        print(stderr.rstrip())


def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    destination = path.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


def _open_gui(project: Path | None) -> int:
    try:
        from pydesign.gui.app import run
    except ImportError as error:
        print(
            "PyDesign GUI dependencies are unavailable. Install with: pip install 'pydesign[gui]'"
        )
        print(f"Details: {error}")
        return 3
    return run(project)
