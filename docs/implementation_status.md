# Implementation status

Updated: 2026-07-17

## Implemented and verified

- Stage 0 packaging, MPL-2.0 licence, contribution/security policy, ADR template and CI.
- Core package boundary with no PySide6 imports outside `pydesign.gui`.
- Typed point, millimetre, centimetre, inch, pica and CSS-pixel quantities.
- Immutable Document, Page, Layer, Rectangle and Stage 1 TextFrame objects.
- Stable-ID, geometry and document validation with structured diagnostic codes.
- Immutable renderer-neutral display list and JSON schema version.
- Deterministic conservative project hashing and `project.toml` loading.
- Fresh subprocess evaluation with versioned JSON-over-stdio messages.
- `pydesign check`, `render-json` and `open` commands.
- PySide6 multi-file code/canvas/diagnostics shell with Run, Stop, atomic save and last-good-preview behaviour.
- Two-page, multi-file offline example project.
- LibCST stable-ID source index with literal, physical-quantity, tuple, name and expression ownership.
- Formatting-preserving frame plans with safe, shared-value, visible-adjustment and detach strategies.
- Canvas selection/move/direct resize, inspector geometry, rectangle and four-point cubic Bézier creation, reveal-source and opaque GUI IDs.
- Conflict-checked atomic source transactions, byte-exact inverses, multi-file preflight/rollback and Qt undo.
- Derived recovery snapshots, external-change protection and last-good preview retention.
- Exact font-file/face/variation fingerprints, OpenType metadata and embedding-bit inspection.
- HarfBuzz shaping into renderer-neutral `GlyphRun` values with IDs, clusters, advances, offsets, unsafe-break flags and ink bounds.
- ICU line-boundary adapter, Pyphen dictionary candidates and boundary-sensitive greedy composition APIs.
- `font-info` and `shape-text` audit commands.
- Unit, source-rewrite, recovery, typography, worker, CLI, architecture, packaging and optional GUI/ICU verification.

## Deliberately not claimed yet

- Stage 2 exit is not declared: style-property rewrites, persistent transaction journalling and broad crash/fuzz matrices remain. Bézier creation is present, but control-point editing remains Stage 6.
- Stage 3 exit is not declared: bidi itemisation, cluster-safe font fallback, paragraph optimisation/justification, linked frames, columns, overset and exact outline canvas rendering remain. Current `TextFrame` page operations are explicitly labelled placeholders.
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

The GUI smoke job installs Qt and the Linux EGL runtime. A separate typography job installs DejaVu fixtures, ICU development files and all typography extras. The offline-core job runs with the network unavailable after package installation.
