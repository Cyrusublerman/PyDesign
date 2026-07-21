# 08 — Runtime, build graph, security and recovery

## Process architecture

PyDesign uses three logical process roles:

- **GUI process** — Qt event loop, source buffers, commands, view state and presentation of published snapshots;
- **evaluation workers** — disposable spawn-created processes that import/evaluate project Python and create semantic snapshots;
- **service workers** — bounded background processes for layout, image decoding, proof rasterisation and export where isolation/cost warrants it.

The GUI never imports a user project. A worker is replaced after cancellation, crash, configured job count or detected resource leak. Native-library crashes therefore cannot normally destroy unsaved editor buffers.

## Trust model

A project is executable Python with the current user’s permissions. Opening source for inspection is safe; Running it is equivalent to running a local script. Process isolation prevents UI corruption and improves cancellation but is not advertised as protection from malicious code.

On first run of a project from an untrusted/downloaded location, PyDesign shows a concise trust prompt before evaluation and allows source-only mode. Trust is keyed to project path/repository identity and can be revoked. Network access is not initiated by PyDesign, but arbitrary trusted Python could access the network unless the operating system restricts it.

## Evaluation protocol

1. GUI computes a content revision over manifest, relevant Python/content and declared asset metadata.
2. It writes dirty in-memory source buffers to an isolated revision staging area, without claiming they are explicitly saved.
3. A worker starts with project root, entrypoint, profile, deterministic context and message protocol version.
4. Worker resets import state, validates the manifest and imports only from the staged project/environment.
5. It calls the build entrypoint and validates/finalizes the semantic model.
6. It serializes the model/source map/diagnostics or structured failure.
7. Layout creates the display-list snapshot and dependency records.
8. The GUI publishes the result only if its revision is still wanted.

Older successful revisions may populate content caches but can never replace the viewport after a newer successful revision.

## Run modes

- **Manual**: only Run evaluates; best for expensive/procedural work.
- **On save**: explicit save starts evaluation.
- **Debounced live**: syntactically valid changes wait for configurable quiet time, then evaluate.

Typing never blocks. A new request cancels/obsoletes queued work; a running job may be cancelled immediately or allowed to finish for reusable cache depending on phase.

## Message contracts

IPC messages are versioned tagged schemas with maximum sizes and validation. They carry revision IDs, phases, progress, diagnostics, semantic/layout records and content-addressed references. Pickle is not accepted from an untrusted worker boundary. Large binary payloads use files or shared memory with lifecycle tokens.

Protocol incompatibility yields a clear restart/update diagnostic. Worker stdout/stderr are captured, rate-limited and attached to the revision log.

## Dependency graph

The build graph tracks:

- modules and imported local modules;
- content/assets/font/profile files read through `BuildContext`;
- generators, authored parameters, seeds, stable generated children and exceptions;
- local data sources, schemas, stable record keys and adapter versions;
- semantic objects and style/component dependencies;
- text stories → paragraphs → frame chains → pages;
- resources → display-list operations → pages;
- export profile and toolchain versions.

Workers instrument project imports and `BuildContext` access. Undeclared arbitrary filesystem reads are permitted for trusted Python but mark the build conservatively non-incremental/non-portable unless registered.

## Incremental invalidation

- View changes repaint only.
- Element paint changes invalidate its operations and intersecting compositing group/page.
- Geometry changes invalidate dependent constraints, wraps, hit maps and page operations.
- Story/style/font changes invalidate affected paragraphs and downstream linked frames.
- Template/component changes invalidate instances.
- Generator source/parameter/seed changes invalidate that generator and downstream dependants;
  key-addressed children preserve unaffected identities and cache entries where proven safe.
- Data mutations invalidate affected keyed records/repeaters; schema or parser changes invalidate the
  complete source and its downstream dependants.
- Output-profile changes reuse semantic/layout data when layout semantics are unchanged but rebuild PDF/proof resources.
- Unknown Python side effects invalidate the entire semantic snapshot.

Correctness always wins over reuse. Cache misses cost time; stale reuse is a defect.

## Cache design

Caches are content-addressed and include schema/toolchain fingerprints. Categories include decoded images/mipmaps, font metadata/outlines, shaped runs, paragraph layouts, normalized paths, page display lists, PDF resources and proof rasters. Entries are immutable and written atomically. An index may be rebuilt by scanning entries.

Cache eviction uses size/age budgets and never touches authored assets or explicit exports. “Clear cache” is safe and reports the target size.

## Cancellation and timeouts

Every phase accepts a cancellation token at bounded intervals. If Python or a native call does not cooperate, the worker is terminated and replaced. Soft timeouts warn; hard limits are configurable for evaluation/export. Killing a worker cannot affect source buffers, last-good snapshots or published exports.

## Saving

The GUI owns dirty source buffers. Save performs:

1. verify on-disk base hashes;
2. stage all changed files as siblings;
3. flush and fsync according to platform capability;
4. atomically replace all files using a recoverable transaction journal;
5. update buffer base hashes;
6. remove the journal only after success.

If true cross-file atomic replacement is unavailable, the journal makes roll-forward/rollback deterministic on restart.

## Autosave and recovery

Autosave stores compressed, content-addressed snapshots of dirty buffers and transaction metadata under `.pydesign/recovery/` or the user recovery area. It never changes authored files or clears dirty state. Retention is bounded by time/count/size.

On restart after an unclean exit, the recovery UI compares explicit save, recovery snapshot and current disk content. Users can preview a three-way diff, restore as new files, apply selected hunks or discard. Recovery data is deleted only after explicit resolution/retention expiry.

## External file changes

File watching is debounced and hash-based. Clean buffers reload automatically while preserving cursor/selection. Dirty buffers enter conflict state and show base/disk/buffer three-way merge. Deleted/renamed assets remain represented with diagnostics and fingerprint-assisted relink suggestions.

## Crash containment

- GUI exceptions are caught at command/event boundaries and logged locally.
- A failed command does not enter history.
- Published snapshots are immutable, preventing half-updated scenes.
- Export uses temporary destinations.
- Worker crashes are revision diagnostics and trigger clean replacement.
- The application periodically verifies recovery writes and available disk space.

No crash report is transmitted automatically. A user can export a redacted local diagnostic bundle.

## Logs and privacy

Logs contain versions, phases, diagnostic codes, timings and opt-in paths/snippets necessary for debugging. Source/content is excluded by default from support bundles. Logs rotate locally. There is no telemetry, account identity or remote analytics.

## Environment and dependencies

The packaged app ships a controlled runtime for built-in libraries. Project-specific packages use a selected local Python environment recorded in `project.toml`/lock metadata. Environment creation and package installation are explicit operations that can use offline wheelhouses; opening/editing does not mutate an environment.

## Resource controls

Workers receive configurable CPU concurrency, memory advisory/hard limits where supported, maximum decoded image size, maximum message size and maximum recursion/object count guards. Limits generate actionable diagnostics rather than silently dropping content.
