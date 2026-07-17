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
- Persistent write-ahead source transaction journals with conservative interrupted-write recovery.
- Derived recovery snapshots, external-change protection and last-good preview retention.
- Editable four-point cubic Bézier handles with safe/adjust/detach visible-Python rewrites.
- Exact font-file/face/variation fingerprints, OpenType metadata and embedding-bit inspection.
- Explicit project/system font registry, exact system hashes and grapheme-cluster-safe ordered fallback.
- HarfBuzz shaping into renderer-neutral `GlyphRun` values with IDs, clusters, advances, offsets, unsafe-break flags and ink bounds.
- ICU line/grapheme adapters, Pyphen dictionary candidates and boundary-sensitive greedy composition APIs.
- Linked frame/column story flow with global source ranges, width overflow and unplaced overset reporting.
- `font-info` and `shape-text` audit commands.
- Deterministic vector-only PDF adapter, pikepdf structural inspection, atomic publication, build manifest and `build-pdf` CLI.
- Split GUI evaluation/view/command/canvas seams and explicit source edit/CST helper modules.
- Unit, source-rewrite, recovery, typography, PDF, worker, CLI, architecture, packaging and optional GUI/ICU verification.

## Deliberately not claimed yet

- Stage 2 exit is not declared: style/inheritance rewrites, broad property coverage and expanded crash/fuzz matrices remain.
- Stage 3 exit is not declared: bidi itemisation, fallback-aware paragraph breaking, paragraph optimisation/justification and exact outline canvas rendering remain. Current `TextFrame` page operations are explicitly labelled placeholders.
- Stage 4 exit is not declared: the initial adapter exports verified rectangles/paths but deliberately rejects placeholder text. Shaped text embedding/ToUnicode, images/transforms/clipping, preflight and Poppler difference proofing remain.
- Advanced editorial flow, drawing, colour and print production: Stages 5–7.

## Verification commands

```bash
ruff format --check .
ruff check .
mypy
mypy --config-file mypy-gui.ini src/pydesign/gui
pytest
python scripts/check_architecture.py
python -m build
pydesign check examples/hello_editorial --json
pydesign render-json examples/hello_editorial --output /tmp/pydesign-layout.json
pydesign build-pdf /path/to/vector-project --output /tmp/pydesign-vector.pdf
```

The GUI smoke job installs Qt and the Linux EGL runtime. Separate typography and PDF jobs install their optional authorities and focused test suites. The offline-core job runs with the network unavailable after package installation.
