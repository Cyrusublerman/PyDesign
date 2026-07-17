# Implementation status

Updated: 2026-07-17

## Complete in the initial build

- Stage 0 packaging, MPL-2.0 licence, contribution/security policy, ADR template and CI.
- Core package boundary with no PySide6 imports outside `pydesign.gui`.
- Typed point, millimetre, centimetre, inch, pica and CSS-pixel quantities.
- Immutable Document, Page, Layer, Rectangle and Stage 1 TextFrame objects.
- Stable-ID, geometry and document validation with structured diagnostic codes.
- Immutable renderer-neutral display list and JSON schema version.
- Deterministic conservative project hashing and `project.toml` loading.
- Fresh subprocess evaluation with versioned JSON-over-stdio messages.
- `pydesign check`, `render-json` and `open` commands.
- PySide6 code/canvas/diagnostics shell with Run, Stop, atomic save and last-good-preview behaviour.
- Two-page, multi-file offline example project.
- Unit, worker, CLI, architecture, packaging and optional GUI smoke verification.

## Deliberately not claimed yet

- LibCST GUI-to-source transactions and unified undo: Stage 2.
- Production text shaping/composition: Stage 3. Current text operations are explicitly labelled placeholders.
- PDF export, preflight and Poppler proof comparison: Stage 4.
- Advanced editorial flow, drawing, colour and print production: Stages 5–7.

## Verification commands

```bash
ruff format --check .
ruff check .
mypy
mypy --config-file mypy-gui.ini src/pydesign/gui/app.py
pytest
python scripts/check_architecture.py
python -m build
pydesign check examples/hello_editorial --json
pydesign render-json examples/hello_editorial --output /tmp/pydesign-layout.json
```

The GUI smoke job installs its optional Qt dependency and required Linux EGL runtime in CI. Core tests remain dependency-free and run with the network unavailable after installation.

