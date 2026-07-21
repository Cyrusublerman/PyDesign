# ADR 0002 — Procedural generation is native document authoring

- Status: Accepted
- Date: 2026-07-21
- Decision owners: PyDesign maintainers
- Affected baseline: 01, 02, 03, 05, 06, 08, 09, 10, 11, 12, 13

## Context

PyDesign is intended to combine professional editorial layout with procedural, generative and
data-driven composition. A superficial integration could run a second drawing environment such as
Processing, py5, Shoebot, a chart renderer or an HTML canvas beside the PyDesign document. That
would create two incompatible authorities: one for manually authored page objects and another for
generated pixels or foreign vector output. It would also make GUI edits, source provenance,
deterministic export, preflight and canvas/PDF parity unreliable.

Procedural work also introduces product states that ordinary page-layout tools do not need to make
explicit: generator parameters, random seeds, dependencies, selective rebuilding, variants,
freezing, baking and decisions about whether generated children remain editable.

## Decision

Procedural generation is a first-class form of PyDesign document authoring and uses the same
semantic model, layout snapshot and display list as manually authored objects.

1. PyDesign will provide a native, explicit-context creative API inspired by Processing and
   vector creative-coding systems. It returns normal PyDesign elements and never relies on a
   hidden global canvas.
2. A generator is visible Python with a stable ID, typed parameters, an explicit seed and declared
   or observed dependencies. Deterministic generators are the default and the only kind eligible
   for transparent incremental caching.
3. Generated children receive stable keys derived from semantic keys, not transient list indexes.
   Source, generator and parameter provenance travel into the semantic/layout snapshots.
4. Generator lifecycle state is authored and visible. Live, frozen and baked output are distinct.
   Derived cache files never become document truth.
5. GUI direct manipulation of generated content offers the same explicit ownership choices as
   other computed source: edit the generator/parameter, add a visible exception, freeze, or bake
   to explicit source. The GUI never silently detaches generated output.
6. Parameter controls, seed exploration, variant comparison, dependency status and build errors
   are mandatory desktop capabilities, not optional plug-in chrome.
7. Data sources and chart/document adapters record local inputs, fingerprints, schemas, versions
   and fidelity. Their outputs cross the core boundary only as native elements, structured text or
   data, parsed SVG, placed PDF, or raster assets.
8. Foreign event loops and heavyweight runtimes such as py5/Processing, Manim, browser chart
   stacks and office applications run through isolated adapters or external tools. They do not
   become the canonical canvas, typography or PDF authority.
9. Core remains small. A library is added to default dependencies only when a shipped native
   capability needs it and its offline distribution, licence, determinism and supported-platform
   behaviour are verified.

## Consequences

### Benefits

- Generated and manually drawn content share selection, layering, styling, constraints, PDF
  output, preflight and accessibility contracts.
- Python remains readable and useful after GUI operations.
- Generative documents are reproducible from source, assets, data, versions and seeds.
- The canvas can provide high-value visual exploration without creating hidden project state.
- External libraries can be adopted incrementally behind explicit fidelity boundaries.

### Costs

- Generator provenance and stable child identity must be designed before broad creative APIs.
- Live/frozen/baked transitions require source transactions, history and careful recovery tests.
- Foreign renderers require adapters and cannot be embedded merely because they produce an image.
- Variant browsing and selective invalidation add runtime and UI complexity.
- The native creative API will initially cover fewer primitives than mature external systems.

## Rejected alternatives

### Embed py5 or Processing as the main canvas

Rejected because its Java/OpenGL runtime and event loop would establish an independent drawing
authority and would not naturally produce editable publication objects.

### Store generator parameters and baked output only in `.pydesign/`

Rejected because deleting derived state would change the authored document and violate the visible
Python invariant.

### Treat generated output as an opaque image in all cases

Rejected because it would discard object identity, vector editability, typography, preflight and
structured PDF output. Opaque placement remains an explicit fidelity mode for adapters that cannot
produce native objects.

### Add all candidate creative/data libraries to the default installation

Rejected because it would increase packaging, licence, security and compatibility costs without a
corresponding shipped capability.

## Migration and implementation

The decision adds no project-format data outside visible source. Existing projects continue to
evaluate unchanged. The procedural contracts are introduced through dependency-ordered tasks in
`docs/roadmap/backlog.toml`; the first slice establishes generator identity, parameters, seeds and
native output before the procedural control panel or third-party adapters are added.

