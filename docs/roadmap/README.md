# PyDesign delivery roadmap

Updated: 2026-07-21

This directory turns the locked design baseline into dependency-ordered work. It is the canonical
planning layer for maintainers and coding agents. It does not replace the product specifications or
claim that planned work has been implemented.

## Authority and roles

Use repository documents in this order:

1. `docs/design/README.md` and the decision register define product contracts.
2. Domain specifications define required behaviour.
3. `docs/design/requirements_traceability.md` defines how contracts are verified.
4. `docs/implementation_status.md` records what is actually implemented and verified.
5. This roadmap defines intended sequencing and the next actionable work.
6. Issues and pull requests execute individual backlog tasks.

When code and the roadmap disagree, inspect tests and update `implementation_status.md`; never mark
a task complete merely because a partial class or placeholder exists.

## Files

| File | Purpose |
|---|---|
| [Current focus](current_focus.md) | Small, ordered working set and immediate handover context |
| [Milestones](milestones.md) | User-observable releases and exit gates |
| [Workstreams](workstreams.md) | Long-lived areas, responsibilities and dependency boundaries |
| [`backlog.toml`](backlog.toml) | Machine-readable tasks, dependencies, requirements and acceptance |
| [Definition of ready/done](definition_of_ready_done.md) | Entry, completion and evidence policy |

Run `python scripts/check_roadmap.py` after editing the backlog. The check rejects unknown statuses,
duplicate IDs, invalid dependency references, cycles, unknown milestones/workstreams and incomplete
task records.

## Task model

Backlog items use stable IDs such as `SRC-201`, `TXT-304` or `GEN-503`. The prefix names the owning
workstream; the number is stable and is not a priority score.

Required task fields are:

- `id`, `title` and `description`;
- `workstream`, `stage` and `milestone`;
- `status` and `priority`;
- `depends_on`;
- linked requirement IDs and owning specification documents;
- observable acceptance statements.

Status values are:

| Status | Meaning |
|---|---|
| `ready` | Dependencies and decisions are sufficient for implementation now |
| `in_progress` | A named branch/issue is actively implementing the task |
| `planned` | Valid work, but an earlier dependency or milestone should land first |
| `needs_audit` | A related implementation exists, but has not been checked against the expanded 1.1 acceptance contract |
| `blocked` | Cannot proceed; `blocked_by` explains a concrete unresolved condition |
| `done` | Acceptance evidence exists and implementation status/docs are updated |
| `deferred` | Intentionally outside the active 1.0 sequence |

Only one or a very small number of tasks should be `in_progress`. `needs_audit` is not a regression
claim: it prevents an earlier, narrower stage proof from being mistaken for complete conformance to
new acceptance criteria. `ready` is deliberately narrower
than “could theoretically be coded”. A planned task becomes ready only after its dependencies and
required architectural decisions are complete.

Priority values are `critical`, `high`, `normal` and `low`. Dependency order outranks local
convenience. A low-priority prerequisite can still precede a high-priority dependant.

## Vertical-slice rule

A task should deliver the thinnest useful path through all affected layers:

```text
visible source → evaluation → semantic model → layout/display list
               → canvas → GUI source edit → export/preflight → tests/docs
```

Not every task touches every layer, but planning must state why a layer is not applicable. Avoid
parallel placeholder implementations that cannot yet be exercised by a user or a headless fixture.

## Updating the roadmap

When starting a task:

1. Confirm every dependency is complete or explicitly included in the same change.
2. Apply the definition of ready.
3. Set the task to `in_progress` and attach its issue/branch when available.
4. Keep `current_focus.md` small and ordered.

When completing a task:

1. Meet every acceptance statement or split unfinished acceptance into a new task.
2. Add requirement/test evidence.
3. Update `docs/implementation_status.md` without overstating the stage exit.
4. Update affected specifications and ADRs.
5. Set the task to `done`.
6. Promote newly unblocked planned work to `ready` deliberately.
7. Run the roadmap, architecture, lint, type and test checks.

Do not encode transient implementation discussion in the locked design baseline. Use issues and PRs
for discussion, ADRs for decisions, and backlog tasks for durable execution state.
