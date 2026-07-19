# Requirements traceability

Each stable requirement has an owning specification and planned verification. IDs are reused in issues and tests.

| Requirement | Contract | Owner | Verification |
|---|---|---|---|
| R-SRC-001 | Authored truth is visible Python/assets only. | 02 | Delete `.pydesign/`; semantic/display hashes remain equal. |
| R-SRC-002 | GUI document edits are atomic source transactions. | 02 | Gesture tests inspect source diff and failure rollback. |
| R-SRC-003 | Expressions are not silently replaced. | 02 | Fixture for every ownership form and explicit choice. |
| R-SRC-004 | Stable IDs survive re-evaluation/refactoring. | 02, 03 | Selection/source-map round-trip tests. |
| R-SRC-005 | Multi-file page order is explicit. | 02 | Shuffle filenames; page order remains unchanged. |
| R-SRC-006 | Rename/move updates imports atomically. | 02 | Failure-injected multi-file refactor test. |
| R-PRJ-001 | A folder containing `project.toml` is the portable project/save unit and may live anywhere. | 02 | Create and evaluate in an external temporary directory. |
| R-PRJ-002 | Normal creation and Save As do not place user projects in the PyDesign source checkout. | 02 | Checkout-descendant rejection and explicit-override tests. |
| R-PRJ-003 | Save As/Duplicate preserve authored inputs, regenerate project identity and omit derived state. | 02 | Copy fixture with assets, caches, builds, exports and Git metadata. |
| R-PRJ-004 | Packaging is deterministic, inventoried and contains no unresolved symlinks or internal state. | 02, 09 | Repeated ZIP hash, manifest and exclusion tests. |
| R-PRJ-005 | Recent paths and GUI layout are application settings, not project truth. | 02, 06 | Settings-location and project-tree mutation tests. |
| R-MOD-001 | Source, semantic, layout and view states remain separate. | 03 | Import-boundary and cache-deletion tests. |
| R-MOD-002 | Units/coordinates are exact and documented. | 03 | Unit/matrix/page-box property tests. |
| R-MOD-003 | Collections retain deterministic order. | 03 | Repeated build hash and reorder/undo tests. |
| R-MOD-004 | Constraints are visible and diagnosable. | 03 | Under/over-constrained fixtures and drag plans. |
| R-MOD-005 | One immutable layout snapshot feeds both renderers. | 03, 07 | Renderer-input identity contract test. |
| R-TXT-001 | Unicode boundaries/bidi use ICU. | 04 | Unicode conformance/mixed-bidi corpus. |
| R-TXT-002 | Shaping uses exact HarfBuzz font instances. | 04 | Expected glyph/cluster/position corpus. |
| R-TXT-003 | PyDesign owns line/paragraph/frame composition. | 04 | Dependency guard and expected-break tests. |
| R-TXT-004 | Canvas and PDF place identical glyph runs. | 04, 07 | Display-list and PDF position checks. |
| R-TXT-005 | Hyphenation, justification and keeps are deterministic. | 04 | Language/composer fixtures. |
| R-TXT-006 | Fallback is cluster-safe and reported. | 04 | Combining-mark/missing-glyph corpus. |
| R-TXT-007 | Outline fallback is explicit and preflighted. | 04, 07 | Unsupported-effect fixture and diagnostic. |
| R-GFX-001 | Paths support precise Bézier/node editing. | 05, 06 | Pen task and geometry round trip. |
| R-GFX-002 | Graphics state matches canvas/PDF. | 05, 07 | Blend/clip/transform conformance suite. |
| R-GFX-003 | Vector/raster fallbacks are never silent. | 05 | Preflight for each fallback policy. |
| R-IMG-001 | Image layout is non-destructive and linked. | 05 | Original hash unchanged after edit/export. |
| R-IMG-002 | Changed/missing assets cannot silently export. | 05 | Fingerprint mutation and relink tests. |
| R-COL-001 | RGB/CMYK/ICC/Lab/spot are distinct values. | 05 | Type/round-trip/resource tests. |
| R-COL-002 | Conversions use declared ICC intent. | 05 | LittleCMS known-transform fixtures. |
| R-UI-001 | Code and canvas are simultaneous primary surfaces. | 06 | Layout at minimum supported window size. |
| R-UI-002 | Editable properties expose source provenance. | 06 | Inspector content/accessibility tests. |
| R-UI-003 | Last-good preview survives current failure. | 06, 08 | Syntax/runtime/crash integration tests. |
| R-UI-004 | Document workflows are keyboard complete. | 06 | Acceptance tasks without pointer. |
| R-UI-005 | State is not communicated by colour alone. | 06 | Theme/accessibility audit. |
| R-PDF-001 | Standard PDF and PDF/X-4 share one adapter. | 07 | Profile builds and adapter tests. |
| R-PDF-002 | Fonts are subset/embedded with valid ToUnicode. | 07 | Resource and extraction corpus. |
| R-PDF-003 | Export is atomic and inspected before publish. | 07 | Kill/failure injection by phase. |
| R-PDF-004 | Poppler proof compares locally to reference. | 07 | Visual parity CI/difference mapping. |
| R-PDF-005 | Preflight severity follows selected profile. | 07 | Diagnostic matrix by profile. |
| R-RUN-001 | User Python never runs in the GUI process. | 08 | Import/process instrumentation. |
| R-RUN-002 | Worker isolation is not called a sandbox. | 08 | Trust-flow content review. |
| R-RUN-003 | Revisions are cancellable and cannot publish stale. | 08 | Out-of-order completion stress test. |
| R-RUN-004 | Cache reuse is dependency correct. | 08 | Mutation matrix/full-build equivalence. |
| R-RUN-005 | Save/autosave/recovery preserve complete versions. | 08 | Randomized failure tests. |
| R-EXT-001 | CLI uses the same core/runtime. | 09 | GUI/CLI semantic/display hash equality. |
| R-EXT-002 | Plug-ins declare compatibility/capabilities/licence. | 09 | Discovery/rejection tests. |
| R-OFF-001 | Core workflows function without network. | 01, 09 | Network-disabled CI. |
| R-PRV-001 | No telemetry or automatic source transmission. | 08, 09 | Network-call/package audit. |
| R-LIC-001 | Releases contain SPDX/third-party notices. | 09 | Inventory and release gate. |
| R-QLT-001 | Interactions meet published budgets. | 10 | Reference-machine P95 benchmarks. |
| R-QLT-002 | Builds pass determinism/parity gates. | 10 | Repeated/platform-class builds. |
| R-QLT-003 | Features require source, canvas, PDF, diagnostics, docs and tests. | 10 | Pull-request checklist. |

Before Stage 0 closes, each row receives links to concrete test modules or implementation issues. Before 1.0, every row is automated where technically possible; manual checks record operator, platform, fixture and evidence.
