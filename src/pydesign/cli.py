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

from pydesign.runtime import (
    WorkerClient,
    create_project,
    duplicate_project,
    package_project,
)
from pydesign.runtime.package_output import package_for_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pydesign", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    new = subcommands.add_parser("new", help="create a portable PyDesign project folder")
    new.add_argument("destination", type=Path)
    new.add_argument("--name", default=None)
    new.add_argument("--allow-in-source-checkout", action="store_true")

    duplicate = subcommands.add_parser(
        "duplicate", help="copy authored project files to a new independent folder"
    )
    duplicate.add_argument("project", type=Path)
    duplicate.add_argument("destination", type=Path)
    duplicate.add_argument("--name", default=None)
    duplicate.add_argument("--allow-in-source-checkout", action="store_true")

    package = subcommands.add_parser("package", help="validate and package portable project inputs")
    _project_arguments(package)
    package.add_argument("--output", type=Path, required=True)

    package_out = subcommands.add_parser(
        "package-for-output",
        help="package authored inputs plus a published PDF for offline rebuild",
    )
    _project_arguments(package_out)
    package_out.add_argument("--output", type=Path, required=True)
    package_out.add_argument("--pdf", type=Path, default=None)

    check = subcommands.add_parser("check", help="evaluate and validate a project")
    _project_arguments(check)
    check.add_argument("--json", action="store_true", dest="as_json")

    render = subcommands.add_parser(
        "render-json", help="write the renderer-neutral Stage 1 display list"
    )
    _project_arguments(render)
    render.add_argument("--output", type=Path, required=True)

    build_pdf = subcommands.add_parser(
        "build-pdf", help="write a parity-gated vector PDF and build manifest"
    )
    _project_arguments(build_pdf)
    build_pdf.add_argument("--output", type=Path, required=True)
    build_pdf.add_argument("--manifest", type=Path, default=None)
    build_pdf.add_argument(
        "--pdf-profile",
        default="vector",
        choices=("vector", "pdfx4"),
        help="export profile (pdfx4 records output-intent metadata)",
    )

    proof = subcommands.add_parser(
        "proof", help="rasterize a PDF proof under .pydesign/proof (Poppler when available)"
    )
    _project_arguments(proof)
    proof.add_argument("--pdf", type=Path, required=True)
    proof.add_argument("--dpi", type=int, default=72)

    open_command = subcommands.add_parser("open", help="open the desktop application")
    open_command.add_argument("project", type=Path, nargs="?", default=None)

    font_info = subcommands.add_parser(
        "font-info", help="inspect exact OpenType identity and embedding metadata"
    )
    _font_arguments(font_info)

    shape = subcommands.add_parser(
        "shape-text", help="shape one itemised text run and write positioned glyph JSON"
    )
    _font_arguments(shape)
    shape.add_argument("text")
    shape.add_argument("--size", type=float, default=12.0)
    shape.add_argument("--direction", choices=("ltr", "rtl", "ttb", "btt"), default=None)
    shape.add_argument("--script", default=None)
    shape.add_argument("--language", default=None)
    shape.add_argument("--feature", action="append", default=[], metavar="TAG=VALUE")
    return parser


def _project_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project", type=Path)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)


def _font_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("font", type=Path)
    parser.add_argument("--face-index", type=int, default=0)
    parser.add_argument("--variation", action="append", default=[], metavar="TAG=VALUE")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"new", "duplicate"}:
        return _run_project_creation_command(args)
    if args.command == "open":
        return _open_gui(args.project)
    if args.command in {"font-info", "shape-text"}:
        return _run_typography_command(args)

    result = WorkerClient().evaluate(args.project, profile=args.profile, timeout=args.timeout)
    if args.command == "package":
        if not result.ok:
            _print_human_result(result.response, result.stderr)
            return 2
        try:
            package_result = package_project(args.project, args.output)
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}")
            return 2
        print(f"wrote {package_result.output} ({package_result.file_count} project files)")
        print(f"package manifest {package_result.manifest_sha256[:12]}")
        return 0
    if args.command == "package-for-output":
        if not result.ok:
            _print_human_result(result.response, result.stderr)
            return 2
        try:
            output_package = package_for_output(
                args.project, args.output, pdf_path=getattr(args, "pdf", None)
            )
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}")
            return 2
        print(
            f"wrote {output_package.output} ({output_package.file_count} files; "
            f"pdf={'yes' if output_package.included_pdf else 'no'})"
        )
        return 0
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
    if args.command == "build-pdf":
        if not result.ok or result.layout is None:
            _print_human_result(result.response, result.stderr)
            return 2
        return _build_pdf(
            result.layout,
            args.output,
            args.manifest,
            profile=getattr(args, "pdf_profile", "vector"),
            project=args.project,
        )
    if args.command == "proof":
        if not result.ok:
            _print_human_result(result.response, result.stderr)
            return 2
        return _run_proof(args.project, args.pdf, args.dpi)
    raise AssertionError(f"unhandled command {args.command}")


def _run_project_creation_command(args: argparse.Namespace) -> int:
    try:
        if args.command == "new":
            config = create_project(
                args.destination,
                name=args.name,
                allow_in_source_checkout=args.allow_in_source_checkout,
            )
            verb = "created"
        else:
            config = duplicate_project(
                args.project,
                args.destination,
                name=args.name,
                allow_in_source_checkout=args.allow_in_source_checkout,
            )
            verb = "duplicated"
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    print(f"{verb} {config.name}: {config.root}")
    return 0


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


def _build_pdf(
    layout: dict[str, Any],
    output: Path,
    manifest: Path | None,
    *,
    profile: str = "vector",
    project: Path | None = None,
) -> int:
    try:
        from pydesign.pdf import PdfExportError, export_layout_pdf
        from pydesign.pdf.preflight import load_waivers, preflight_layout
    except ImportError as error:
        print("PDF dependencies are unavailable. Install with: pip install 'pydesign[pdf]'")
        print(f"Details: {error}")
        return 3
    waivers = load_waivers(project) if project is not None else ()
    issues = preflight_layout(layout, profile=profile, asset_root=project, waivers=waivers)
    blocking = [item for item in issues if item.severity == "error"]
    if blocking:
        for item in blocking:
            print(f"ERROR {item.code}: {item.message}")
        return 2
    for item in issues:
        print(f"{item.severity.upper()} {item.code}: {item.message}")
    try:
        result = export_layout_pdf(
            layout,
            output,
            manifest_path=manifest,
            profile=profile,
            asset_root=project,
            waivers=waivers,
        )
    except (OSError, PdfExportError) as error:
        print(f"ERROR: {error}")
        return 2
    if profile == "pdfx4":
        from pydesign.pdf.validate_pdfx4 import validate_pdfx4

        for issue in validate_pdfx4(output):
            print(f"ERROR {issue.code}: {issue.message}")
            return 2
    manifest_output = manifest or output.with_name(f"{output.name}.manifest.json")
    print(f"wrote {output}")
    print(f"wrote {manifest_output} ({result.pdf_sha256[:12]})")
    return 0


def _run_proof(project: Path, pdf: Path, dpi: int) -> int:
    try:
        from pydesign.pdf.proof import run_proof
    except ImportError as error:
        print(f"ERROR: {error}")
        return 3
    result = run_proof(pdf, project, dpi=dpi)
    print(result.message)
    return 0 if result.ok else 2


def _run_typography_command(args: argparse.Namespace) -> int:
    try:
        from pydesign.text import FontValidationError, ShapingError, load_font_face, shape_text
    except ImportError as error:
        print(
            "Typography dependencies are unavailable. Install with: "
            "pip install 'pydesign[typography]'"
        )
        print(f"Details: {error}")
        return 3
    try:
        variations = _numeric_assignments(args.variation, label="variation")
        face = load_font_face(args.font, face_index=args.face_index, variations=variations)
        if args.command == "font-info":
            payload = face.to_dict()
        else:
            features = _feature_assignments(args.feature)
            run = shape_text(
                face,
                args.text,
                font_size=args.size,
                direction=args.direction,
                script=args.script,
                language=args.language,
                features=features,
            )
            payload = run.to_dict()
    except (FontValidationError, ShapingError, OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _numeric_assignments(values: list[str], *, label: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for assignment in values:
        tag, separator, raw_value = assignment.partition("=")
        if not separator:
            raise ValueError(f"{label} must have the form TAG=VALUE: {assignment!r}")
        result[tag] = float(raw_value)
    return result


def _feature_assignments(values: list[str]) -> dict[str, int | bool]:
    result: dict[str, int | bool] = {}
    for assignment in values:
        tag, separator, raw_value = assignment.partition("=")
        if not separator:
            raise ValueError(f"feature must have the form TAG=VALUE: {assignment!r}")
        lowered = raw_value.lower()
        if lowered in {"true", "on"}:
            result[tag] = True
        elif lowered in {"false", "off"}:
            result[tag] = False
        else:
            result[tag] = int(raw_value)
    return result
