# Definition of ready and done

## Ready for implementation

A task is `ready` only when:

- its user or engineering outcome is concrete;
- owning specifications and requirement IDs exist;
- required ADRs are accepted;
- dependencies are done or explicitly included in the same vertical change;
- acceptance statements can be verified;
- necessary fixtures can be legally committed or generated;
- optional/native dependency and supported-platform risks are understood;
- the task is small enough for a reviewable branch or has been split;
- failure, offline and missing-dependency behaviour is described;
- no unresolved choice would materially change the public model.

A research spike may be ready with a decision threshold instead of production acceptance, but it
must name the fixture, versions, time box and ADR/design decision it will close.

## Done for a capability

A task is `done` only when applicable evidence exists for:

1. visible source/public API;
2. semantic model and validation;
3. layout/display-list behaviour;
4. canvas/UI interaction;
5. safe GUI-to-source transaction and undo;
6. headless operation;
7. PDF/export/preflight parity;
8. structured diagnostics and failure behaviour;
9. deterministic/offline execution;
10. unit, contract, integration and regression tests;
11. documentation, example and local help;
12. dependency/licence/notice changes;
13. implementation status and backlog updates.

“Not applicable” must be justified in the PR. A placeholder method, disabled control, unexercised
model or one-renderer-only path is not a completed capability.

## Pull-request evidence

Each task PR should include:

- backlog task IDs and requirement IDs;
- concise behaviour and architecture summary;
- source/canvas/PDF screenshots or artefacts when visually relevant;
- exact commands run and results;
- fixture and determinism details;
- optional dependency/platform coverage;
- known limitations and follow-up task IDs;
- an explicit statement if no baseline decision changed.

## Stage and milestone completion

Individual task completion does not imply stage completion. A stage or milestone closes only when:

- every published exit criterion is demonstrated;
- cross-feature reference projects pass;
- performance/reliability gates applicable to that stage pass;
- implementation status is updated;
- no blocking task remains hidden in prose or a TODO comment;
- the release claim is reviewed separately from the final component PR.

