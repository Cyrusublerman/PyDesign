# Workstreams

Workstreams define long-lived ownership, not team silos. A vertical task may touch several areas,
but one workstream owns its contract and integration.

| ID | Name | Owns |
|---|---|---|
| `source` | Visible Python and transactions | Source analysis, ownership, rewrite plans, atomic changes, undo/recovery |
| `runtime` | Evaluation and dependency graph | Workers, protocol, cancellation, builds, dependencies, cache and publication |
| `document` | Editorial semantic model | Pages, spreads, styles, components, constraints, stories and layout structures |
| `typography` | Text authority | Unicode, shaping, breaking, composition, flow, outlines and text diagnostics |
| `graphics` | Vector, paint and geometry | Paths, Boolean geometry, paint, effects, transforms and SVG |
| `images-colour` | Images, assets and colour | Linked assets, processing, ICC, swatches, crop, profiles and proof inputs |
| `procedural` | Generators and creative coding | Parameters, seeds, stable generated identity, creative API, lifecycle and variants |
| `data-interchange` | Data, charts and documents | Data sources, repeaters, charts, graphs, maps and semantic document adapters |
| `gui` | Desktop interaction | Canvas, panels, tools, editor integration, accessibility and coordinated state |
| `pdf-preflight` | Output and proofing | Display-list adapter, PDF profiles, proof, difference, preflight and packaging |
| `extensions-packaging` | Integration and distribution | Adapter API, optional dependencies, licences, CLI and desktop packaging |
| `quality` | Cross-cutting evidence | Architecture checks, fixtures, determinism, performance, fuzz and release gates |

## Boundary rules

- `gui` emits semantic/source intents and consumes public snapshots; it does not own document truth.
- `source` edits visible project files and does not import GUI, runtime or typography.
- `runtime` publishes versioned semantic/layout values and does not call GUI widgets.
- `typography`, `graphics`, `images-colour` and `document` expose renderer-neutral values.
- `procedural` produces normal semantic objects through explicit context; it does not paint Qt/PDF.
- `data-interchange` translates foreign inputs through declared fidelity boundaries.
- `pdf-preflight` consumes the shared display list and never independently reflows text.
- `extensions-packaging` admits dependencies only through Specification 13.
- `quality` may depend on public/testing surfaces but production modules never depend on tests.

## Workstream outcomes

### Visible Python and transactions

Every editable property reports source form, ownership and a safe plan. GUI actions produce narrow,
formatting-preserving atomic transactions with byte-exact undo and crash recovery.

### Evaluation and dependency graph

Source, assets, data and generators evaluate in revisioned disposable workers. Stale work cannot
publish; dependency-accurate caching is equivalent to a full rebuild.

### Editorial semantic model

Multipage documents, reusable styles/components and explicit constraints remain normal source and
compile to immutable layout snapshots without hidden master-page or override state.

### Text authority

PyDesign, not Qt or a PDF toolkit, chooses glyphs, line breaks and frame flow. Canvas and PDF place
the same glyph runs.

### Vector, image and colour

All visible operations have shared display-list semantics, non-destructive assets and disclosed
fallbacks. Print colour remains typed and profile-aware.

### Procedural authoring

Generators are inspectable Python objects with parameters, seeds, stable children and reproducible
results. GUI exploration changes source only through deliberate application.

### Data and interchange

Local data and documents enter through versioned adapters with schema/fidelity diagnostics. Charts
and diagrams become native or structured document content where possible.

### Desktop interaction

Spatial, typographic and generative judgement is fast on the canvas while code, inspector, trees,
story, assets, diagnostics and preflight remain coordinated and keyboard accessible.

### Output and proof

Export is deterministic, inspectable, profile-aware, atomic and locally comparable to the canvas.

