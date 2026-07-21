# 10 — Quality, performance and acceptance

## Quality strategy

Tests are layered around contracts rather than screenshots alone. Each bug adds the smallest deterministic fixture that would have prevented it.

## Test layers

### Unit tests

Units, transforms, paths, colour conversions, source rewrite rules, style inheritance, font resolution, Unicode segmentation, shaping adapters, composition items, constraints, display operations, diagnostics and profile rules.

### Contract tests

- semantic model/schema round trips;
- worker IPC compatibility and malformed-message rejection;
- display-list renderer conformance;
- `GlyphRun` equality between layout consumers;
- plug-in/API version negotiation;
- CLI JSON and exit codes;
- source transaction comment/format preservation;
- generator parameter/seed/stable-child identity and lifecycle transitions;
- data/chart/document adapter fidelity, capability and version negotiation.

### Integration tests

Multi-file evaluation, cancellation/restart, external changes, recovery, image/font/profile pipelines, linked text frames, PDF generation/reopen, package-for-output and headless/GUI parity.

### Visual regression

Reference projects exercise editorial grids, dense typography, experimental paths, images/transparency, spot colour and mixed scripts. Internal and Poppler PDF rasters are compared with edge-aware tolerances. Baselines store toolchain/platform class and are reviewed through difference images.

The corpus also includes deterministic keyed random grids, radial/along-path repetition, coherent
noise/vector fields, data-driven catalogues, generator exceptions, freeze/thaw/bake, variant
promotion and native/structured/opaque adapter fidelity examples.

### Accessibility tests

Keyboard-only task scripts, focus order, accessible names/roles/states, theme contrast, screen-reader smoke tests and 200% layout. Canvas object actions have programmatic equivalents.

### Property/fuzz tests

Random valid paths/transforms/units, malformed fonts/images/PDF imports, Unicode/bidi strings, CST source forms and command sequences. Invariants include no crash, bounded resource use, undo byte equality and deterministic diagnostics.

## Reference corpus

The repository uses redistributable fixtures only. It includes:

- small OFL fonts covering Latin, Arabic, Hebrew, Indic, CJK subset and variable axes;
- generated images with known profiles/alpha/compression;
- synthetic ICC/spot/overprint documents;
- deterministic long stories and edge-case Unicode;
- hand-authored source files for every rewrite ownership category;
- intentionally invalid projects for every diagnostic family.

Large/proprietary compatibility corpora live outside public CI and report anonymized results.

## Performance budgets

Budgets are measured on a published reference machine and representative project. P95 targets after warm start:

| Interaction | Target |
|---|---:|
| UI feedback to pointer/keyboard input | under 50 ms |
| Provisional move/resize/path frame time | under 16.7 ms for typical page; no repeated frames over 50 ms |
| Source syntax/parse diagnostic after pause | under 150 ms for a 2,000-line module |
| First visible page after Run, simple document | under 500 ms |
| Incremental repaint for one paint-only change | under 100 ms |
| Incremental reflow of one typical story | under 300 ms |
| Open 100-page reference project to last-good thumbnails | under 3 s warm cache |
| Cancel acknowledgement | under 100 ms; forced worker termination under 1 s |
| Memory, 100-page reference project | under 1.5 GB excluding deliberately huge source images |
| Parameter feedback, interactive-suitable generator | provisional state under 100 ms; stale work cancellable |
| Variant browser | first completed thumbnail under 1 s for the simple generator fixture |

Full PDF export budgets are corpus-specific and tracked as pages/second plus peak memory. Performance never justifies semantic divergence or hidden rasterisation.

## Determinism gates

- repeated semantic/display-list builds produce identical hashes;
- object and resource order does not depend on hash randomisation or filesystem enumeration;
- locale/timezone do not change output unless declared content uses them;
- font/asset changes alter the manifest and invalidate relevant caches;
- undo followed by rebuild restores the previous semantic/display-list hashes;
- supported platform classes produce geometry within declared tolerance.

## PDF release gates

For the print fixture set:

- every PDF reopens without repair warnings;
- all required fonts are embedded/subset with valid ToUnicode maps;
- page boxes/output intent/profile rules pass the selected validator;
- extracted semantic text meets script-specific expectations;
- no unexpected RGB/CMYK/spot resources, rasterised regions or missing glyphs;
- Poppler parity passes geometry/visual thresholds;
- output destination remains unchanged on injected failures/cancellation.

## GUI acceptance tasks

Automated/manual release candidates complete these tasks without source corruption:

1. Create a project and a two-page facing spread.
2. Add a text frame in the GUI and inspect readable generated Python.
3. Drag a literal-owned object, undo and redo.
4. Drag an expression-owned object and choose each edit policy.
5. Edit a shared component and preview affected instances.
6. Draw/edit a cubic path with keyboard alternatives.
7. Link text frames and resolve overset.
8. Relink a changed image by fingerprint.
9. Trigger an evaluation error while retaining last-good preview.
10. Export PDF/X-4, inspect proof difference and locate an object from a discrepancy.
11. Recover unsaved source after simulated crash.
12. Build the same project headlessly.
13. Adjust a generator parameter/seed, inspect provenance and undo the source change.
14. Add a generated-child exception, then freeze, thaw and bake with exact undo.
15. Compare a bounded variant matrix and apply one result without retaining hidden variants.
16. Refresh a changed keyed data source and verify unchanged records retain selection/identity.

## Reliability gates

- randomized kill at every save/export stage recovers to old or new complete state, never a mixture;
- worker crash/restart loops do not leak GUI state or publish obsolete revisions;
- cache corruption is detected and rebuilt;
- disk-full and permission errors preserve source/output and explain recovery;
- external edit conflicts never overwrite either version without a merge decision.

## Compatibility matrix

CI covers supported Python versions and representative Windows/macOS/Linux runners. Native typography and PDF outputs use version-pinned golden environments plus compatibility jobs for newer dependencies. A dependency update that changes shaping, line breaks, colour or PDF structure requires reviewed baseline changes.

## Severity and release policy

P0 data loss/security, P1 wrong export/source corruption and P2 major authoring failures block release. A known parity or accessibility regression blocks the affected stable feature. Experimental features are labelled at the API/UI and cannot be required for core workflows.

## Definition of done for a capability

A capability is done only when it has public API/source syntax, semantic validation, source mapping/GUI ownership behaviour, layout/display-list support, canvas rendering, appropriate PDF behaviour, diagnostics/preflight, undo/recovery coverage, accessibility path, local documentation and tests. “Works in the canvas” alone is not complete.
