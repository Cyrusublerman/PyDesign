# 06 — Desktop UI, canvas and accessibility

## Workspace architecture

The default desktop layout has five coordinated regions:

1. **project rail/tree** — files, pages, layers and assets in switchable tabs;
2. **source editor** — visible Python with tabs, minimap optional, diagnostics and ownership navigation;
3. **canvas** — page/spread/pasteboard, rulers, guides and direct manipulation;
4. **context inspector** — properties, source ownership, typography, colour and export controls;
5. **diagnostics drawer** — problems, build log, preflight and proof differences.

Code and canvas are primary and remain visible together at the default desktop width. Other regions collapse, float or move to a second monitor. Layout presets include Code + Canvas, Canvas Focus, Code Focus, Typography, Path Editing and Proofing.

Qt dock state is user view state, not project truth.

## Visual language

The application chrome is quiet and neutral so document colour remains perceptually dominant. Spacing follows a 4 px base grid. Controls have compact and comfortable density modes. Icon-only actions always have tooltips and accessible names; uncommon or destructive actions retain text labels.

Colour never carries state alone. Code-owned/computed/constraint/derived states use icon, label and colour. Canvas overlays remain legible on light, dark and coloured artwork through contrast-aware dual strokes.

## Source editor

The editor provides:

- Python syntax highlighting, line numbers, bracket/indent guides and multiple files;
- parse, evaluation, source-map and preflight diagnostics with revision labels;
- find/replace, go-to definition/reference, rename stable ID and symbol outline;
- project symbol and PyDesign API completion driven locally;
- format selection/file and code actions with diff preview;
- ownership gutter markers for selected canvas objects;
- reveal declaration and reveal controlling expression;
- inline evaluated value previews that are view-only;
- Run, Stop, auto-run mode and current/stale/error build state.

Completion and documentation are local. The initial editor is replaceable behind an interface so future Tree-sitter/LSP integration does not affect document semantics.

## Canvas navigation

- Mouse/trackpad wheel zooms at the pointer using platform conventions.
- Space-drag or middle-drag pans; fit page/spread/selection shortcuts are provided.
- Zoom is continuous with useful preset percentages and physical-size calibration.
- Art remains vector-sharp where possible; image preview selects a suitable mip level.
- Pasteboard can show neighbouring pages without implying export content.
- Rulers display the active unit and allow zero-origin changes as view state.

The viewport displays Current, Typing, Queued, Running, Stale, Error, Cancelled, PDF Proof and Difference states in a compact status strip.

## Selection

Click selects topmost hittable content. Repeated click/cycle selects underlapping objects. Modifiers add/remove; marquee direction selects containing or intersecting objects according to a visible preference. Locked items are inspectable but not transformable. Selection synchronizes the layer tree, inspector and source ownership marker.

Double-click descends into groups/components or enters the primary editing mode. Escape ascends/cancels in predictable layers: current gesture, sub-edit mode, tool, then selection.

## Transform interaction

Bounding handles scale; a separated handle rotates; the pivot is movable and source-visible only when used by authored transforms. Modifiers constrain proportions, transform about centre, duplicate or temporarily disable snapping. The inspector supports exact x/y/width/height/rotation and reference-point selection.

During a gesture, the scene applies a provisional transform and shows live measurement/snap feedback. No source is written until commit. On release:

- a safe literal edit commits immediately;
- a computed/constraint value opens a compact source-plan popover;
- an evaluation failure restores the previous published preview while leaving the new source available to fix or undo.

## Tool model

Persistent tools are Select, Direct Select, Text, Frame, Shape, Pen, Line, Eyedropper, Hand and Zoom. Shape variants live behind one tool, not as permanent toolbar clutter. Single-letter shortcuts are disabled while a text field/editor owns input unless a platform-standard modifier is used.

Tools expose a short options row and contextual inspector sections. The canvas cursor, status hint and accessible announcement state the active action. Tool state never changes document semantics until a gesture commits.

## Path editing

Direct Select exposes nodes, Bézier handles, path direction and open/closed state. Handles scale visually with UI density rather than zooming to invisibility. Users can add/delete/convert/join/split nodes, reverse path, set node type and edit numeric coordinates/handles. Smart and exact operations are separate commands.

For paths generated by an expression, node selection maps to source data when possible. Otherwise the same visible edit-choice policy applies: edit generator input, add source exception or detach to explicit path data.

## Text editing and typography UI

Text mode shows frame edges, columns, baselines, linked-frame ports, overset and hidden-character options. A story editor is available for dense text independent of page zoom. Character/paragraph controls show resolved value and origin, including style inheritance.

The OpenType panel lists only features supported by the resolved font for the selection. Variable axes use numeric entry and sliders with reset/named instances. The glyph inspector provides search by Unicode/name, alternates and insertion while warning when insertion changes semantic text.

## Inspector

The inspector is selection-contextual but structurally stable. Sections are Geometry, Constraints, Appearance, Typography, Image, Flow, Accessibility and Source. Each property shows:

- resolved value and units;
- source form and owning module/line;
- style/inheritance provenance;
- mixed-value state for multi-selection;
- reset/remove-explicit-value action;
- edit plan when direct manipulation is not unique.

Edits validate during typing and commit on Enter/focus change according to control type. Escape restores the pre-edit value. Scrubbable labels and arrow-key increments respect units and modifiers.

## Pages, layers and project trees

Page thumbnails display section/folio, master/template provenance, size and error badges. Drag reorder generates a source-list diff before commit. Layer rows support visibility, lock, print and disclosure; keyboard reorder is available. File operations distinguish import/module relationships from document page order.

The tree never fabricates an edit that source cannot represent. Generated repeated pages appear with provenance and offer edit-generator, exception or detach actions.

## Diagnostics and failure states

Diagnostics group by current revision and category, not only timestamp. Clicking one focuses its source span and canvas object/page. When the current revision fails, the canvas keeps the last-good snapshot with a prominent “stale from revision …” label and optional ghost of safe provisional changes.

Stop cancels the worker revision. Slow builds show elapsed time and current phase without blocking editing. Cascading errors are collapsed under their root cause.

## Proofing interface

Proof mode displays Canvas, PDF Proof, Difference and Split views at matching zoom/page. Difference has adjustable amplification and threshold, but the raw comparison remains available. Page thumbnails badge geometry/text/raster differences. Clicking a region maps to likely display-list operations and stable object IDs.

Soft proof exposes output intent, paper simulation, gamut warning and separation preview. Proof state is visibly distinct from normal canvas preview.

## Undo and safety UX

Undo descriptions name semantic intent: “Move pull-quote 3.5 mm”, “Edit shared gutter (12 uses)” or “Detach entry-07”. Operations with broad scope show dependants before commit. Deletion uses normal undo; filesystem module deletion uses trash and reports recoverability.

PyDesign never shows a confirmation for actions already safely reversible unless their scope is surprising. Destructive export overwrite and non-recoverable external actions require explicit confirmation.

## Keyboard and accessibility

- All commands are reachable through menu/command palette and keyboard.
- Focus order follows visible workspace order and remains visible.
- Canvas objects expose an accessible hierarchy with role, label, bounds, state and actions.
- Keyboard selection/movement uses configurable increments and announces geometry.
- Handles meet a minimum screen hit target even when artwork is small.
- UI text supports zoom/scaling and 200% layouts without loss of function.
- Themes meet WCAG 2.2 AA contrast for application UI; document art itself is not altered.
- Animation respects reduced-motion preferences.
- Screen-reader announcements are concise and suppress high-frequency gesture noise.
- Shortcuts are remappable, searchable and checked for conflicts.

## Localisation

Application strings are translatable. Python API names, source identifiers, file paths and diagnostic codes remain stable English tokens. Number display follows locale; Python source insertion always uses locale-independent syntax. Unit parsing accepts localized display forms but writes canonical Python.

## First-run and help

First run offers a local example gallery and a five-minute code/canvas tutorial. Every tool links to shipped local reference pages. Generated code is intentionally readable enough to function as instruction. No login, account or network prompt blocks entry.

