# Milestones and release gates

Milestones are user-observable capability gates. Stage numbers remain the dependency-oriented
engineering sequence in Specification 11; milestones package those stages into useful releases.

## M0 — Stage 0–8 implementation baseline

Status: **complete under the recorded 1.0 stage-exit criteria**

Includes the repository's recorded Stage 0–8 vertical proofs: portable visible-Python projects,
source transactions, typography/glyph-run PDF, editorial and image/colour fixtures, preflight/proof,
package output, build caching, extension hooks and desktop acceptance foundations.

Exit evidence is recorded in `docs/implementation_status.md` and the existing test suite.

## M1 — Baseline 1.1 conformance and hardening

Target: preserve the completed vertical slices while measuring them against the expanded 1.1
requirements and closing concrete depth/reliability gaps.

Exit requires:

- every existing Stage 0–8 claim maps to concrete code, tests and the expanded requirement rows;
- backlog tasks with existing implementations are marked done only after their 1.1 acceptance is
  proven, otherwise split into precise gaps;
- no completed functionality is needlessly rewritten;
- current cache/cancellation, source, typography, PDF and GUI limitations are represented as tasks;
- the current reference projects pass their structural, deterministic and visual gates.

## M2 — Editorial UX depth

Target: deepen the existing Stage 5/editorial foundations into a coherent professional multipage
GUI rather than reimplementing the already proven model paths.

Exit requires:

- pages, spreads, sections, folios, margins, columns, guides and baseline grids;
- paragraph, character and object styles with visible inheritance/overrides;
- master/template components and deterministic instance identity;
- page, layer and object trees plus assets/links status;
- linked story editing, columns, exclusions, keeps and overset navigation;
- explicit constraints and snapping;
- a 32-page magazine reference project that remains editable through both Python and GUI;
- incremental reflow that does not rebuild unrelated content.

## M3 — Procedural alpha

Target: Stage 5B native generative authoring.

Exit requires:

- generator, parameter, seed and stable-child contracts;
- explicit-context creative primitives that produce normal document objects;
- deterministic random/noise services and build manifests;
- generator dependency tracking and incremental cache invalidation;
- live, frozen and baked states implemented as visible source workflows;
- repeaters and a local structured `DataSource` foundation;
- procedural controls panel, source navigation and generated collection hierarchy;
- cancellable variant browser with apply/save behaviour;
- canvas/PDF parity for the procedural acceptance corpus.

## M4 — Advanced graphics and interchange beta

Target: Stage 6 plus the first high-value adapters.

Exit requires:

- complete path/node editing, Boolean operations and SVG interchange;
- gradients, masks, groups, blends and disclosed effect fallbacks;
- colour-managed image frames, crop/relink and effective-DPI diagnostics;
- typed RGB/CMYK/ICC/Lab/spot colour and soft-proof foundations;
- Matplotlib structured-vector charts and one native chart-mark example;
- Markdown and DOCX semantic content import with explicit fidelity reports;
- dependency extras remain optional and the core opens projects without them;
- every adapter passes offline, licence, provenance and missing-dependency tests.

## M5 — Print-production beta

Target: Stage 7.

Exit requires:

- PDF/X-4 output intent and conformance path;
- page boxes, marks, spot separations, overprint and total-ink diagnostics;
- expanded preflight and profile-specific blocking rules;
- package-for-output with lawful resources and deterministic rebuild instructions;
- atomic failure-injected export;
- selected external validator and print fixtures passing.

## M6 — PyDesign 1.0

Target: Stage 8 release quality.

Exit requires:

- performance budgets on reference hardware and large documents;
- accessibility acceptance tasks and scalable/remappable interface;
- stable extension/adapter API with local-only installation path;
- signed/notarised offline desktop packages for supported platforms;
- migration, fuzz, stress and recovery suites;
- shipped offline documentation and examples;
- no critical or high-severity known defect against the locked 1.0 scope.

## Post-1.0 programme

The model reserves but does not make 1.0 depend on advanced vertical writing/ruby, mature tagged
PDF/PDF-UA, footnotes/sidenotes/tables, deeper editable PDF/SVG import, imposition, animation and
additional scientific/domain adapters.
