# Current focus

Updated: 2026-07-21

## Product state

The current `main` branch records exit proofs for Stages 0–8. It includes visible source editing,
typography and glyph-run PDF paths, proofing/preflight, editorial fixtures, images/colour, package
output, whole-layout deterministic caching, extension hooks and substantial desktop chrome.

Baseline 1.1 does not revoke those stage exits. It adds deeper contracts for native procedural
authoring, data/interchange, stable generated identity, lifecycle states, dependency-accurate
generator caching and the mandatory procedural GUI. It also makes some previously broad UI and
production claims more explicit. Existing implementations must therefore be mapped to the new
acceptance statements before those backlog items are called done.

## Ready now

### `QLT-101` — Baseline 1.1 implementation conformance audit

Map every existing Stage 0–8 capability to the expanded requirement and backlog acceptance set.
Record concrete tests/evidence, mark genuinely complete tasks done, and split any remaining gap
instead of rewriting working systems. This is a bounded code/test audit, not a new research phase.

### `RUN-202` — Generator/data dependency graph and incremental invalidation

The repository has deterministic whole-layout caching. Extend that foundation so declared
generator, parameter, seed, data and asset changes can invalidate the correct subgraph. This is the
runtime prerequisite for live procedural work and is also the recommended follow-up recorded by the
current cache implementation.

### `GEN-501` — Generator, parameter and provenance contracts

Introduce the first renderer-neutral generator values, typed controls, explicit seed, stable child
namespace and worker serialization. The first vertical fixture should create ordinary native
objects, render through the existing display list and expose provenance without adding a GUI panel
or foreign drawing runtime yet.

`RUN-202` and `GEN-501` may proceed together if their public boundary is agreed first and each stays
inside its workstream. `QLT-101` should update task states continuously rather than block this clear
new procedural work.

## Next after the first procedural contracts

1. `GEN-502` deterministic keyed random/noise services.
2. `DATA-501` local structured data sources.
3. `GEN-504` stable repeaters and keyed exceptions.
4. `GEN-506` dependency/cache integration.
5. `GEN-505` visible live/frozen/baked source workflows.
6. `GUI-506` procedural controls and provenance panel.
7. `GEN-507` and `GUI-507` bounded variant generation/browser.
8. `GEN-503` broader native creative primitives once the identity/lifecycle core is proven.

## Explicitly not next

- Embedding py5, Shoebot or another sketch runtime into the Qt canvas.
- Installing the complete candidate library inventory.
- Building visual parameter controls before generator/source contracts exist.
- Implementing charts as canvas-only Qt widgets.
- Treating prior stage-exit prose as proof of every newly expanded 1.1 acceptance statement.
- Moving user project truth into `.pydesign/` or application settings.

## Handover evidence expected

Every active task should leave:

- a narrow implementation and architectural summary;
- tests and exact commands run;
- updated task state and implementation status;
- known limitations and newly unblocked tasks;
- no claim that a 1.1 task is complete without its published acceptance evidence.

