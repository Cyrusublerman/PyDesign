# 03 — Document model, geometry and commands

## State layers

PyDesign separates four states:

1. **source revision** — bytes of authored modules, manifest and assets;
2. **semantic snapshot** — validated objects created by evaluating that revision;
3. **layout snapshot** — immutable positioned geometry, glyph runs, paint operations and diagnostics;
4. **view state** — selection, zoom, open files, panel arrangement and temporary gestures.

Exports add artefact state but never feed changes back into the semantic model. Only source transactions alter the document.

## Core object hierarchy

```text
Document
├── metadata, resources, styles, templates
├── Section
└── Page / Spread
    ├── Layer
    │   └── Element
    │       ├── Group / ComponentInstance
    │       ├── TextFrame
    │       ├── ImageFrame
    │       ├── Shape / Path
    │       └── PlacedDocument
    ├── Guide / Grid
    └── annotations
```

Pages own printable content; spreads provide facing-page relationships and pasteboard composition but do not replace pages as PDF units.

## Common element contract

Every element has:

- stable `id` and optional human label;
- parent/layer and deterministic z-order;
- local transform and optional constraint set;
- visibility, lock, printable and accessibility flags;
- optional clipping path, opacity, blend mode and isolation;
- style references plus explicit properties;
- source provenance and diagnostic anchors;
- evaluated ink, logical, hit-test and selection bounds.

No renderer invents defaults. Defaults are resolved in the semantic/layout stages and serialized into the display list.

## Units and coordinates

- API values use `Length`, `Angle`, `Percent` and related immutable quantity types.
- `mm`, `cm`, `inch`, `pt`, `pc` and `px` constructors are available; `px` requires an explicit project DPI when used in print geometry.
- Layout normalizes length to double-precision points.
- Page origin is top-left. x increases right; y increases down.
- Rotation is degrees clockwise. Angles normalize only for display, not source rewriting.
- Rectangles are `(x, y, width, height)`; negative evaluated width/height are errors.
- Transforms use 3×3 affine matrices and compose parent-to-child in documented order.
- Comparisons use domain-specific tolerances; source values are never rounded merely for display.

## Page geometry

A page contains media, trim, bleed, art and crop boxes. Trim defines the author coordinate space. Bleed may extend to negative x/y. Slug and pasteboard are workspace geometry, not automatically exported. Facing pages have explicit binding direction and spine relationship.

Page templates are functions/components, not hidden master-page state. Their returned elements retain source/component provenance and can expose named slots.

## Bounds

- **logical bounds**: unpainted layout extent, e.g. a text frame;
- **ink bounds**: actual painted pixels/vector extents including stroke/effects;
- **selection bounds**: manipulable transform box;
- **hit bounds**: accessible minimum target around thin/small art;
- **clip bounds**: active clipping intersection.

Snapping and alignment state which bound type they use. Export clipping uses exact paths, not rectangular approximations.

## Layers and z-order

Layer and element order are stable ordered collections. Z-order is never inferred from source line alone. Layers support visibility, locking, printing, opacity, blend and isolation. Reordering emits a source list transaction. Cross-layer moves update both collections atomically.

## Groups and components

A group applies a transform and compositing context to child elements. A component is a Python callable or declared factory returning elements with namespaced child identities. Instances may expose typed parameters. Editing an instance parameter changes the call; editing shared internals changes the component; detaching writes an explicit local element tree.

## Constraints

Constraints are explicit source objects, not invisible auto-layout rules. Initial constraints include align, equal gap, pin, fixed aspect, baseline, distribute and frame-relative anchors. The layout solver reports under-, well- and over-constrained systems. A drag of constrained geometry edits a controlling constant/constraint or asks to detach; it does not fight the solver.

The solver operates only on declared geometric variables. Paragraph layout and arbitrary Python expressions are outside the geometric constraint solver.

## Grids, guides and snapping

Document guides are visible source objects and can print only when explicitly configured. Temporary ruler guides and visibility settings are view state. Snapping candidates include guides, grids, margins, columns, baselines, page boxes, object anchors, path nodes and optical bounds.

Candidate distance is calculated in screen pixels so behaviour is stable across zoom. Priority is: explicit guides, selected-object anchors, page/grid anchors, other objects. The user can cycle equal candidates and temporarily disable snapping.

## Layout snapshot and display list

The immutable layout result contains:

- revision and deterministic build identity;
- page/spread records and all page boxes;
- fully composed positioned glyph runs;
- resolved vector paths and image placements;
- ordered graphics-state/display-list operations;
- object-to-operation, object-to-source and source-to-object maps;
- bounds, handles, snap anchors and hit-test geometry;
- diagnostics, overflow and resource usage;
- dependency hashes for incremental invalidation.

Snapshots are published atomically. The GUI may keep the current and last-good snapshots concurrently.

## Commands and history

The history model records source transactions rather than mutations to scene items. A command contains:

- semantic intent and affected stable IDs;
- original and replacement bytes for every file;
- project revision before/after;
- selection/focus before/after;
- optional coalescing key;
- evaluation result reference.

Continuous gestures coalesce to one command on release. Text typing coalesces by buffer, time and cursor continuity. Source editor edits and canvas edits share one project history, while view-only changes use a separate lightweight view history.

Undo/redo verifies current file hashes before replacing bytes. If external edits diverged, PyDesign opens a merge instead of overwriting them.

## Selection and object references

Selection is an ordered set of stable IDs plus optional sub-selection such as a path node, text range or gradient stop. After reevaluation, IDs are resolved against the new snapshot. Missing IDs are removed with a non-modal notice. Component child IDs are deterministic namespaces derived from instance ID and child key, never list index alone.

## Diagnostics contract

Every diagnostic has severity, code, message, revision, source spans, object IDs, page locations, suggested fixes and whether it blocks a selected export profile. Codes are stable and testable. Errors never exist solely as console strings.

## Serialization boundary

Semantic and layout objects may be serialized between worker and GUI using versioned, schema-checked messages. Python callables and live Qt objects never cross the boundary. Large images use content-addressed files/shared memory references rather than message copies.

