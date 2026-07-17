# Visible Python source transactions

PyDesign treats project Python as authored truth. The Stage 2 foundation indexes literal stable `id=` declarations with LibCST, records source spans and classifies each property as a literal, physical quantity, tuple, shared name or computed expression.

## Geometry behavior

Moving or resizing a frame follows an explicit source policy:

| Source form | Available behavior |
|---|---|
| Numeric or unit quantities | Safe replacement preserving units and surrounding formatting/comments |
| Shared simple name | Edit the controlling assignment, add a visible adjustment or detach |
| Computed expression | Add a visible point adjustment or detach to point quantities |
| Missing/non-literal frame | Detach by adding an explicit frame |

PyDesign never silently replaces a computed expression. The GUI asks before any non-safe strategy. Rectangle and four-point cubic Bézier drawing append readable `Rectangle(...)` or `BezierPath(... MoveTo(...), CurveTo(...))` calls to a literal `Page.elements` list and update an existing `from pydesign import ...` statement where possible. Moving the start, control or end handles of that cubic applies the same safe/adjust/detach policy while preserving units, comments and formatting.

## Transaction guarantees

`SourceEditPlan` retains complete before/after text and provides a unified diff. `SourceTransaction` rejects duplicate target paths and preflights every byte-exact original before its first write. Before replacement it durably writes a project-local transaction journal containing the expected before/after hashes and text. Each replacement is written to a same-directory temporary file, flushed, `fsync`ed and atomically replaced. A later write failure restores already-written files; the returned inverse transaction restores exact original bytes.

On project open, an interrupted journal is recovered only when every target still matches its recorded before or after bytes. Partial writes roll back to the exact pre-transaction content. A divergent file is never overwritten: the conflict journal remains for manual recovery and project opening is blocked with its paths.

Qt canvas commands push these plans through one undo stack and immediately re-evaluate in a fresh worker. Unsaved editor buffers are stored only as derived `.pydesign/recovery` snapshots. Disk divergence blocks overwrite and asks the author to reload or merge.

## Current boundary

The API and recovery journal support multi-file transaction groups, while current canvas operations generate one-file plans. Style/inheritance rewrites, broad property coverage and expanded fault/fuzz matrices remain before the full Stage 2 exit.
