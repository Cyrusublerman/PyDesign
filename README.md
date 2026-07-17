# PyDesign

PyDesign is an entirely offline, Python-native editorial layout studio being designed for professional typography, computational composition and deterministic PDF production.

The product combines:

- an IDE-style Python source editor;
- a zoomable page and spread canvas;
- direct manipulation that creates inspectable Python source transactions;
- professional typography, grids, guides, pages, layers, vector paths and colour;
- deterministic PDF/PDF/X export and locally rendered proofing.

## Status

The implementation-grade design baseline is locked. The repository now contains the Stage 0/1 vertical slice, the visible-source Stage 2 foundation, and the first real Stage 3 typography authority. Canvas moves, inspector geometry edits and rectangle creation produce readable Python transactions; exact OpenType font identities and HarfBuzz glyph runs are independently auditable.

Read the [complete design baseline](docs/design/README.md), [decision register](docs/design/00_decision_register.md), [requirements traceability](docs/design/requirements_traceability.md) and [implementation sequence](docs/design/11_implementation_sequence.md).

See [implementation status](docs/implementation_status.md) for the exact completed/staged capability boundary.

## Locked direction

- CPython 3.12+ and PySide6/Qt Widgets;
- visible multi-file Python projects;
- LibCST-backed GUI-to-source transactions;
- retained semantic model and immutable shared layout/display list;
- isolated local evaluation workers;
- ICU, HarfBuzz, FreeType, FontTools and Pyphen typography under a PyDesign paragraph composer;
- a project-owned PDF adapter, initially using ReportLab with pikepdf inspection;
- Poppler-based local PDF proofing and comparison.

Verification spikes may replace an implementation adapter, but may not weaken the locked source, layout, typography or export contracts without an Architecture Decision Record.

## Product principles

- Authored document truth is visible Python source and project assets.
- GUI edits never silently destroy expressions or hide canonical overrides.
- Every editable property exposes its source form, owner, inheritance and derivation.
- One positioned layout result feeds both canvas and PDF.
- Failed/cancelled rendering never blocks source editing or destroys the last good preview.
- Authoring, local help, proofing and export work without network access.
- Accessibility and keyboard operation are designed into each vertical slice.

## Run the build

Install the headless project/source core:

```bash
python -m pip install -e .
pydesign check examples/hello_editorial
pydesign render-json examples/hello_editorial --output /tmp/hello-layout.json
```

Install the desktop shell separately:

```bash
python -m pip install -e '.[gui]'
pydesign open examples/hello_editorial
```

The desktop shell provides a multi-file Python sidebar/editor, isolated Run/Stop evaluation, last-good preview, page canvas selection, dragging and resize, a geometry/source inspector, reveal-in-Python, rectangle and four-point cubic Bézier drawing, source-aware expression choices, undo/redo and unsaved-source recovery. GUI-created document objects receive opaque stable `pd_…` IDs.

Install the typography authority stack to inspect fonts and shape real glyphs:

```bash
python -m pip install -e '.[typography]'
pydesign font-info /path/to/font.otf
pydesign shape-text /path/to/font.otf 'office سلام' --size 12 --language en
```

Add `.[unicode]` plus system ICU development files for ICU line boundaries and composition. The current page canvas still labels `TextFrame` operations as placeholders: glyph shaping, ICU/Pyphen break candidates and the greedy composer exist, but linked-frame flow, fallback, bidi itemisation, justification and outline canvas/PDF painting remain staged work.

Run verification with:

```bash
python -m pip install -e '.[dev,typography]'
ruff check .
mypy
pytest
python scripts/check_architecture.py
```

## Implementation sequence

1. Repository/tooling and architecture guardrails.
2. Headless source-to-page model and serializable display list.
3. PySide6 code/canvas shell with isolated evaluation.
4. LibCST-backed visible GUI edits and recovery (foundation implemented).
5. Typography authority and identical glyph-run rendering (font/shaping foundation implemented).
6. PDF parity and Poppler proofing.
7. Editorial layout, advanced graphics/colour and print production.

## Repository policy

Research and project knowledge are maintained in the associated PKL repository. Normative implementation design is versioned here beside source, tests, fixtures, packaging and developer documentation.

The design baseline selects MPL-2.0 for PyDesign source; the licence file and third-party notices are Stage 0 deliverables.
