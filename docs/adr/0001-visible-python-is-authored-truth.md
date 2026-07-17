# ADR 0001 — Visible Python is authored truth

Status: accepted  
Date: 2026-07-17

## Context

PyDesign combines procedural Python with direct canvas manipulation. A hidden override file would make the rendered document diverge from the code a user reads, undermine version control and create ambiguous ownership for expressions.

## Decision

Python source and project assets are the authored truth. The retained semantic model is the in-memory interpretation of one source revision. GUI document changes are atomic LibCST-backed Python edits. Computed values require an explicit source-level choice: edit an input, add visible adjustment code or detach to a literal.

`.pydesign/` stores disposable cache, proof, recovery and view state only.

## Consequences

Source rewriting and ownership mapping are core product infrastructure. Some arbitrary Python results cannot be directly manipulated until the user exposes an editable boundary or detaches them. Projects remain transparent, diffable and buildable without a hidden scene database.

## Migration

No released project format predates this decision.

## Supersedes

Research-era hidden visual override proposals.

## Verification

Requirements R-SRC-001 through R-SRC-006 in `docs/design/requirements_traceability.md`.

