# 12 — Procedural generation, data and creative coding

## Objective

PyDesign must support generative composition with the same source visibility, direct manipulation,
typography, rendering and export guarantees as ordinary editorial objects. Procedural work is not a
separate sketch window pasted into a page. It is normal document authoring whose rules happen to be
expressed as functions, parameters, data and deterministic variation.

## Generator contract

A generator is a normal Python callable or callable object registered through a small public
contract. It has:

- a source-visible stable ID and label;
- a versioned callable reference or source fingerprint;
- typed parameters with defaults, constraints and presentation hints;
- an explicit deterministic seed or an explicit declaration that no randomness is used;
- declared inputs plus dependencies observed during evaluation;
- a stable namespace for generated child identities;
- lifecycle state: `live`, `frozen` or `baked`;
- output and diagnostic provenance;
- a deterministic cache key when eligible.

The public API does not depend on decorators, but decorators provide a concise authoring form:

```python
@generator(id="cover_pattern", seed=1842)
@controls(
    density=Slider(0.0, 1.0, default=0.65),
    count=IntegerField(1, 500, default=80),
    colour=ColourField("accent.orange"),
    mode=Choice(("grid", "radial", "flow"), default="flow"),
)
def make_cover_pattern(g: Graphics, density: float, count: int, colour: Colour, mode: str):
    ...
```

The evaluated semantic snapshot contains resolved parameter values and generator provenance. It
does not contain the callable itself. Python callables never cross the worker protocol boundary.

## Explicit creative context

The creative API uses an explicit `Graphics` or `BuildContext` value. There is no process-global
current canvas, fill, stroke, transformation or random-number generator. Context managers may
provide readable scoped state without hiding ownership:

```python
def rings(g: Graphics, count: int) -> Group:
    with g.style(fill=None, stroke="accent", stroke_width=0.7 * mm):
        return g.group(
            g.circle(center=(0, 0), radius=(index + 1) * 3 * mm, key=f"ring-{index}")
            for index in range(count)
        )
```

Initial creative primitives include:

- line, rectangle, rounded rectangle, ellipse, circle, polygon, star and arc;
- move, line, quadratic/cubic curve and compound path construction;
- fill, stroke, dash, opacity, blend, clip, mask and group;
- translate, rotate, scale, skew and matrix transforms;
- linear, radial and polar repetition;
- grids, tilings and along-path placement;
- interpolation, remapping, easing and sampling;
- deterministic random distributions and coherent noise;
- vector-field sampling and streamline helpers;
- explicit image and text-frame creation;
- reusable components and data repeaters.

Primitives return semantic PyDesign objects. They do not paint directly into Qt, PDF or an external
surface. Animation-oriented functions may later return frame/time-dependent document revisions,
but the still-document contract is implemented first.

## Determinism and randomness

Generators use a project-owned random service derived from:

```text
project identity + generator stable ID + authored seed + variant key + child semantic key
```

Changing iteration order must not change previously keyed children. APIs therefore distinguish
sequential random sampling from key-addressed sampling. Key-addressed randomness is preferred for
editable repeated systems.

The build manifest records:

- the authored and effective seed;
- generator source fingerprint;
- relevant PyDesign and adapter versions;
- input asset/data fingerprints;
- parameter values;
- determinism and cache eligibility;
- warnings for time, environment, unseeded randomness or undeclared external state.

A generator that reads the current time, environment, network, arbitrary filesystem state or
uncontrolled global randomness is considered impure. It may run only with disclosed capabilities,
cannot claim reproducibility and is ineligible for transparent cache reuse.

## Stable generated identity

Generated children use semantic keys supplied by the generator or data record:

```python
g.text_frame(key=f"article-{article.id}-title", ...)
```

The retained object ID is namespaced by generator instance and key. List position alone is not a
stable key. Duplicate keys are errors. Missing keys on a collection intended for direct editing
produce a diagnostic and prevent exceptions from being attached ambiguously.

Stable identity supports:

- selection across reevaluation;
- source and generator navigation;
- per-child exceptions;
- diffing variants;
- dependency-accurate invalidation;
- readable diagnostics;
- accessibility relationships.

## Parameters and controls

Parameters are typed authored values, not GUI-only metadata. Baseline types are:

- Boolean;
- integer and floating-point ranges;
- length, angle, percentage and other unit-aware quantities;
- colour and swatch reference;
- text and path;
- choice/enum;
- asset, data-source, component and style references;
- point, rectangle, transform and small structured records.

Each definition may include label, description, grouping, valid range, step, logarithmic mapping,
unit, display precision and whether continuous preview is safe. Presentation hints never change the
semantic value.

Parameter changes from the GUI update visible Python. Scrubbing produces provisional evaluation
with coalescing/cancellation; release commits one source/history transaction. Expensive generators
may opt into delayed evaluation while the control is moving.

## Live, frozen and baked output

### Live

The generator reruns when parameters or dependencies change. Its children retain generator
ownership. Direct edits offer parameter/generator, exception or bake choices.

### Frozen

The authored project records a source-visible frozen reference to a verified generated snapshot and
its manifest. Freezing is useful for expensive generation and controlled publication builds. The
snapshot is a portable project input, not a disposable `.pydesign/` cache. Thawing re-evaluates and
reports dependency/version differences before replacing it.

### Baked

Baking is an atomic source transaction that writes explicit native objects and removes their live
generator ownership. The history entry retains the inverse transaction. The generator call may be
preserved as commented provenance or a separate named variant only when the user explicitly asks;
PyDesign does not leave dead executable output in normal page order.

Generated children may also receive visible exception records while remaining live. Exceptions
target stable child keys and explicit properties. A missing target produces a diagnostic rather
than silently applying to a different child.

## Repetition and data binding

`DataSource` values describe local structured inputs such as CSV, JSON, YAML, SQLite, spreadsheets
or project Python records. A source records:

- project-relative path or explicit local URI;
- content fingerprint and media type;
- schema and field/type mapping;
- parsing options and locale assumptions;
- primary/stable key;
- refresh state and diagnostics;
- adapter name/version and licence metadata.

Repeaters map stable data records to components:

```python
products = DataSource.csv("data/products.csv", key="sku")

catalogue = Repeat(
    records=products,
    component=product_card,
    layout=Grid(columns=3, gap=6 * mm),
    key=lambda row: row.sku,
)
```

Filtering, sorting and grouping remain visible Python. The GUI may construct or modify simple
operations, preview schemas and values, and reveal the controlling expression. It does not maintain
a hidden query pipeline.

Changed, missing or schema-incompatible data cannot silently export the previous content. The
last-good preview may remain visible with a stale label, while preflight blocks publication when the
selected profile requires current data.

## Charts, diagrams and maps

Chart and diagram adapters declare one of three fidelity levels:

1. **native** — produces semantic chart marks, text and paths that remain fully editable;
2. **structured vector** — produces parsed SVG/PDF-derived groups with source specification and a
   fidelity report;
3. **opaque** — places a PDF or raster result with its generator specification and manifest.

The default chart path is Matplotlib static SVG/PDF converted through the structured-vector
boundary, followed by a smaller native mark API for charts that need full editability. Altair with
`vl-convert-python` is the preferred declarative second adapter. NetworkX/rustworkx provide graph
data/algorithms while Graphviz provides optional local layout. No chart library becomes the core
document or typography authority.

Map integrations use the same adapter contract. GeoPandas/Shapely supply feature geometry,
pyproj/Cartopy supply projections and Rasterio supplies local raster data. Network basemaps are not
required and are never fetched implicitly.

## Dependency graph and invalidation

The runtime records dependencies at project-module, generator, parameter, asset, data and adapter
levels. A generator reruns when any cache-key input changes. Downstream layout invalidation uses the
existing semantic/layout dependency graph.

Cache entries contain only derived results and manifests. Deleting `.pydesign/cache` may reduce
performance but cannot alter the next valid build. Frozen output is intentionally outside the
derived cache and is visible as a project input.

Evaluation is revisioned, cancellable and publish-on-success. The GUI may retain the last-good
generator output while a newer revision runs or fails, but must label its revision and stale inputs.

## Procedural desktop experience

The procedural controls panel provides:

- generator hierarchy and search;
- parameter controls with source provenance;
- authored/effective seed, reroll and key-addressed reroll;
- live, frozen and baked state;
- rebuild, cancel and cache status;
- runtime, output count and memory estimate;
- input/dependency list and changed/stale status;
- traceback and structured diagnostics;
- reveal generator, parameter and generated child in source;
- create exception, remove exception, freeze, thaw and bake actions;
- variant browser and comparison.

The variant browser renders a bounded matrix of seed/parameter combinations in background workers.
Variants are temporary view state until one is explicitly applied, saved as a named variant or
written as source. Users can lock parameters, compare differences and promote a variant without
creating dozens of project revisions.

Canvas selection of generated content identifies its generator, child key, parameters and active
exceptions. Generated collections remain collapsed by default in the layer tree and virtualize
large child lists.

## GUI edit policy

Direct manipulation of generated content offers only semantically valid plans:

- edit an exposed controlling parameter;
- edit generator source;
- add a visible exception for the stable child key;
- edit a shared component or style;
- freeze the generator;
- bake selected output or the whole generator;
- cancel.

The GUI previews the scope and dependant count before applying broad edits. It never rewrites an
arbitrary algorithm based only on its current evaluated numbers.

## Headless and project API

Generators work without Qt. Required CLI operations are:

```text
pydesign generators PROJECT list
pydesign generators PROJECT inspect GENERATOR_ID
pydesign generators PROJECT build [GENERATOR_ID]
pydesign variants PROJECT GENERATOR_ID --seeds RANGE --output DIRECTORY
pydesign bake PROJECT GENERATOR_ID [--children KEYS]
```

Exact command grouping may change through implementation, but GUI and CLI use the same runtime and
source transaction contracts. Headless builds never require a display server.

## Performance and safety budgets

- Parameter gestures publish provisional results only when the generator declares interactive
  suitability; otherwise the UI remains responsive and evaluates on release.
- Variant jobs have explicit concurrency, time, output-count and memory bounds.
- Large generated collections use immutable packed geometry/display values and virtualized UI
  representation rather than one heavyweight Qt item per child where avoidable.
- Cancellation prevents stale generator results from publishing.
- Adapters declare file/process/native-code capabilities and run outside the GUI process where
  possible.
- Procedural evaluation is reliability isolation, not a security sandbox.

## Acceptance corpus

The procedural reference corpus includes:

- keyed random grid whose existing children remain stable when count changes;
- radial and along-path repetition with physical-unit geometry;
- noise/vector-field composition with repeatable output;
- data-driven catalogue with reorder, insert, delete and schema-change cases;
- generator exception, freeze/thaw and bake/undo workflows;
- variant matrix with cancellation and selected-variant promotion;
- generated typography using the shared text authority;
- chart adapter at each declared fidelity level;
- failure fixtures for duplicate keys, missing data, impure input and stale dependencies;
- canvas/PDF identity for generated paths, images and glyph runs.

