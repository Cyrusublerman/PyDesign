# PyDesign

PyDesign is the intended implementation repository for an entirely offline, Python-native editorial layout studio.

The product combines:

- an IDE-style Python source editor;
- a zoomable page and spread canvas;
- direct manipulation of frames, shapes and Bézier paths;
- professional typography, grids, guides, pages and layers;
- deterministic PDF export and locally rendered PDF proofing;
- explicit synchronisation between source-controlled values and visual overrides.

## Status

Design and architecture specification. Runtime implementation has not started.

The initial implementation direction is:

- Python;
- PySide6 and Qt Graphics View;
- a controlled Python document language;
- a retained semantic document model;
- isolated local evaluation workers;
- a shared layout result used by the interactive and PDF renderers;
- FontTools and HarfBuzz-oriented typography;
- ReportLab and Flat benchmarking for PDF output;
- Poppler-based local PDF proofing and comparison.

These technologies remain subject to documented spikes and adoption decisions.

## Product principles

- Entirely offline authoring, preview and export.
- The semantic document model is authoritative; widget state is not.
- Visual edits never silently destroy Python expressions.
- Every editable property exposes whether it is controlled by code, an expression, an override, a constraint or derived layout.
- Failed or cancelled rendering never blocks source editing or destroys the last good preview.
- Canvas and exported PDF can be compared locally.
- Accessibility and keyboard operation are designed in from the first vertical slice.

## Planned first vertical slice

1. PySide6 split-pane application shell.
2. Python editor, Run/Stop and revision-aware diagnostics.
3. One physical-size page in a QGraphicsScene canvas.
4. Stable-ID shapes, text and image frames.
5. Move, resize, selection, inspector and undo.
6. Safe visual overrides.
7. PDF export from the same layout result.
8. Local PDF raster proof and preview comparison.

## Repository policy

The detailed project knowledge, research, architecture, interface specification and canonical work plan are maintained in the associated PKL repository. This repository will contain executable source, tests, fixtures, packaging and developer documentation.

A licence will be added only after the intended distribution and dependency-licence compatibility are approved.
