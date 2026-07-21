# 11 — Implementation sequence

This sequence is dependency ordered. A slice must prove its vertical contracts rather than build an isolated layer with no user-visible validation.

## Stage 0 — Repository and decision guardrails

Deliver the package skeleton and tooling, MPL-2.0 licence, dependency/reuse register, ADR template, CI matrix and redistributable fixture policy.

Exit: a clean checkout runs tests and a trivial headless command offline; architecture changes require an ADR and traceability update.

## Stage 1 — Source-to-page vertical slice

Deliver:

- `project.toml`, `document.py`, multi-file imports and `BuildContext`;
- typed units, Document/Page/Layer/basic Shape/TextFrame models and stable IDs;
- disposable evaluation worker with revisioned structured diagnostics;
- immutable layout/display list for one page;
- PySide6 shell with source editor, canvas, Run/Stop and last-good preview;
- headless `check` command.

Exit: edit Python, run and see one physical-size page; syntax/runtime failure retains a labelled last-good canvas; the GUI never imports user code.

## Stage 2 — Visible GUI source editing

Deliver:

- LibCST ownership for literals, tuples, names, call arguments and styles;
- select/move/resize/create shape operations;
- transaction journal and unified source/canvas undo;
- inspector provenance and reveal-source;
- expression choices: controlling value, visible adjustment, detach;
- multi-file atomic save, autosave and crash recovery.

Exit: every GUI document change creates readable Python; undo restores byte-identical files; computed expressions are never silently destroyed; crash tests recover.

## Stage 3 — Typography authority slice

Deliver:

- deterministic font registry/fingerprints;
- ICU boundaries/bidi, HarfBuzz shaping and FreeType/FontTools integration;
- `GlyphRun`, fallback, features and variation axes;
- single-line and paragraph composers, language hyphenation/justification;
- text frames, columns, linked flow and overset;
- exact outline-based canvas rendering and typography diagnostics.

Exit: the multilingual corpus has stable glyph IDs, clusters, positions and frame breaks; Qt text layout does not participate in document composition.

## Stage 4 — PDF parity slice

Deliver:

- project-owned PDF adapter and ReportLab writer implementation;
- shaped glyph placement, subset embedding and ToUnicode;
- vector paths, images, transforms, clipping and standard transparency;
- pikepdf inspection, atomic export and build manifest;
- Poppler proof raster and Canvas/PDF/Difference views;
- `build` and `proof` CLI commands.

Exit: reference projects export searchable text and pass structural/visual parity; writer failures do not replace prior outputs. The shaped-glyph verification spike closes here.

## Stage 5 — Editorial layout slice

Deliver pages/spreads/sections/page labels, margins/columns/grids/guides/snapping, paragraph/character styles, keeps/exclusions/balancing, templates/components/generated-object edit workflows, and page/layer/project trees with dependency invalidation.

Exit: a 32-page magazine fixture is authorable with reusable styles/components, incremental reflow and no hidden document state.

## Stage 6 — Advanced graphics, images and colour

Deliver full Bézier editing/source mapping; gradients, masks, groups, blends and effect fallbacks; colour-managed images/crop/relink; RGB/CMYK/ICC/Lab/spot, overprint, separations and soft proof; and resource/effective-DPI diagnostics.

Exit: every visual fixture follows the shared display-list/PDF policy, every fallback is disclosed and changed assets cannot silently export stale content.

## Stage 7 — Print production

Deliver PDF/X-4, output intent/page boxes/marks, expanded offline preflight/validation, package-for-output, links/bookmarks/metadata/initial structure tagging, and failure injection across export.

Exit: print fixtures pass the selected PDF/X-4 validator and portable package rebuild; waivers are explicit and publishing is atomic.

## Stage 8 — Scale, polish and extensibility

Deliver dependency-accurate caching, performance budgets, keyboard/screen-reader/scalable-theme work, extension entry points, signed/notarised offline packages, local documentation, stress/fuzz/migration testing.

Exit: all release tasks and budgets in Specification 10 pass on supported platforms and the installed application works offline end to end.

## Stage 9 — Native procedural and data authoring

This stage extends the completed 0–8 baseline rather than reopening its exits. Deliver:

- generator, typed parameter, explicit seed and stable generated-child contracts;
- an explicit-context native creative API whose primitives return normal semantic objects;
- deterministic keyed random/noise services and generator build manifests;
- generator/data dependency tracking, cancellation and incremental cache invalidation;
- visible live/frozen/baked and keyed exception source workflows;
- local structured data sources and stable repeaters;
- procedural controls, generated hierarchy and bounded variant browser;
- headless generator inspection/build/bake paths.

Exit: the procedural acceptance corpus reproduces from source, assets, data, versions and seeds;
visual parameter exploration writes no hidden document state; selected output remains editable and
passes the same canvas/PDF parity gate as manually authored content.

## Stage 10 — Advanced adapters and editorial UX depth

Deliver curve-aware Boolean geometry and SVG interchange; the fully coordinated pages/layers,
styles/components, story, assets/data, preflight and procedural panels; and the first
Matplotlib/document adapters admitted through Specification 13.

Exit: every admitted adapter has an offline deterministic fixture and fidelity report, while a
complete editorial/procedural reference project can be authored through coordinated code and GUI
without foreign document or renderer authority.

## Later 1.x capabilities already accommodated

These are not prerequisites for the first stable editorial workflow, but the locked model must accept them without a project-format rewrite:

- vertical writing, ruby and advanced script-specific justification;
- footnotes, sidenotes, floats and tables;
- mesh gradients and expanded effects;
- mature tagged PDF, PDF/UA and archival profiles;
- improved SVG/PDF editable import;
- imposition and printer-mark presets;
- a replaceable high-performance canvas viewport;
- animation timelines and frame/video export;
- expanded charts, diagrams, maps and scientific/domain adapters.

## Spike discipline

A spike has a fixture, success/failure threshold, recorded versions, result and ADR conclusion. Spike code does not become production code by default. A failed component choice must preserve the locked external contract or explicitly seek a baseline change.

## First coding issue

Stage 0 is one bootstrap pull request. The first runtime pull request implements a headless `Document(Page(Rectangle))` build and serializable display list before Qt, establishing the core boundary every later surface uses.
