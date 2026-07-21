# 01 — Product scope and workflows

## Product promise

PyDesign lets a designer make sophisticated pages, spreads and multipage editorial documents with the reproducibility of Python and the spatial fluency of a visual editor. A project remains understandable in a text editor, works offline and exports deterministic, inspectable PDFs.

## Intended users

- designers who are comfortable learning a small Python API;
- programmers building computational typography and generative layouts;
- researchers producing repeatable publications and reports;
- studios needing version-controlled, reusable editorial systems.

The interface teaches through discoverable tools and generated source, but it does not conceal that the document is Python.

## Included capability

### Documents

- custom physical page sizes, orientation, bleed, trim, slug and page boxes;
- single pages, facing-page spreads, sections, folios and reusable page templates;
- margins, columns, gutters, modular grids, baseline grids and guides;
- layers, groups, symbols/components, z-order, clipping and masks;
- linked text frames and content that spans pages;
- deterministic procedural generation and data-driven repetition.

### Typography

- OpenType shaping and features, variable fonts and optical sizing;
- multilingual Unicode text, bidirectional paragraphs and vertical writing architecture;
- paragraph and character styles with inheritance;
- multi-column composition, balancing, exclusions and text on paths;
- hyphenation, justification, tracking, kerning, baseline shift and leading;
- drop caps, rules, tabs, indents, keep constraints, widows and orphans;
- glyph-level inspection and deliberate outline conversion.

### Visual composition

- primitive shapes and arbitrary Bézier paths;
- fills, strokes, dashes, joins, caps, gradients, transparency and blend modes;
- image frames, crop, fit, clipping, masks, filters and colour treatments;
- alignment, distribution, snapping, constraints and reusable components;
- precise numeric entry in physical units.

### Output

- normal PDF and PDF/X-4;
- raster page proofs and contact sheets;
- preflight reports, package-for-output and deterministic build manifests;
- optional SVG/PNG export for selected pages or objects where semantics permit.

## Explicit non-goals for 1.x

- raster painting and photo retouching comparable to dedicated image editors;
- cloud accounts, cloud storage, real-time collaboration or a plug-in marketplace;
- importing arbitrary proprietary InDesign documents with full fidelity;
- running untrusted downloaded Python safely;
- replacing a full general-purpose IDE or digital asset manager;
- imposing a no-code authoring mode.

## Primary workflows

### Create a project

1. Choose page preset, facing-pages mode, units, colour intent and starter structure.
2. PyDesign creates valid Python modules, `project.toml`, asset directories and a first page.
3. The project opens with source and page canvas visible.
4. A first successful evaluation becomes the last-good preview.

### Author with code

1. Edit any project module.
2. Diagnostics update from parse and static checks.
3. Explicit Run or a configured debounce starts a new worker revision.
4. Successful evaluation atomically replaces the semantic snapshot and layout.
5. Failure leaves the previous preview visible, labels it stale and maps the error to source.

### Author with the GUI

1. Select or create an object on the canvas.
2. The source editor reveals the owning declaration and the inspector states the property’s source form.
3. Dragging previews only transient geometry.
4. Release requests a LibCST edit plan.
5. Literal changes commit directly; computed values show explicit edit choices.
6. One atomic source edit, history entry and evaluation revision are produced.

### Author procedurally

1. Create a generator with stable ID, typed parameters and an explicit seed.
2. Use the native explicit-context creative API to return normal shapes, paths, text, images,
   components or repeated data records.
3. Evaluation records generator, parameter, input and stable-child provenance in the published
   snapshot.
4. Adjust parameters or seed in source or the procedural controls panel; provisional variants do
   not change source.
5. Apply one variant, add a visible keyed exception, freeze a verified result or bake it to explicit
   native source.
6. Canvas and PDF consume the same generated display operations and preflight reports stale or
   impure inputs.

### Build from local data

1. Declare a fingerprinted local data source, schema and stable record key.
2. Filter, sort, group and map records to a reusable component in visible Python.
3. Inspect schema, records, identity and refresh status in the data/procedural panels.
4. Changed records preserve identity for unchanged keys and invalidate only affected dependants.
5. Missing, changed or incompatible inputs retain a labelled last-good view but cannot silently
   publish as current output.

### Draw a path

1. Activate Pen with keyboard or toolbar.
2. Click for corners; drag for smooth nodes; modifiers constrain or break handles.
3. Enter closes or finishes; Escape cancels the active segment or tool.
4. PyDesign inserts a named `Path` object with explicit nodes into the current module.
5. Node edits rewrite only the affected node data while preserving surrounding formatting.

### Compose flowing text

1. Create frames or a frame chain and assign content/styles.
2. Layout reports fit, overset, missing glyphs, fallback fonts and violated keep rules.
3. The user edits text, frames or composition settings.
4. Glyph runs and affected downstream frames recompute; unrelated pages remain cached.

### Proof and export

1. Select an export profile and run preflight.
2. Fix errors or explicitly waive eligible warnings with a visible build-note entry.
3. Export writes to a temporary file, validates it, then atomically publishes it.
4. Poppler rasterises the output locally.
5. Canvas/PDF difference views and the report are attached to the build manifest.

### Package a document

1. Resolve all imported modules and linked assets.
2. Copy required fonts when licensing permits, assets, content and source to a portable directory.
3. Rewrite paths to project-relative paths without changing asset fingerprints.
4. Include a manifest, preflight report, dependency versions and rebuild command.

## Usability principles

- Show the document before showing configuration.
- Keep code and canvas simultaneously available on normal desktop widths.
- Reveal ownership: every editable value says where its Python comes from.
- Prefer reversible gestures and preview before commitment.
- Keep errors close to both the source span and affected object.
- Never replace a successful view with a blank canvas solely because a new revision failed.
- Support keyboard-complete operation and do not encode state by colour alone.

## Definition of “entirely offline”

After installation, all authoring, font discovery, rendering, proofing, validation, help and export functions work with network interfaces unavailable. Documentation ships locally. Dependencies are bundled or declared for offline installation. External URLs may be displayed as inert references but are never required for a build.
