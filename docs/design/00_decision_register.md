# 00 — Decision register

This is the compact register of decisions that implementation may rely upon.

## Product and source authority

| ID | Locked decision |
|---|---|
| D-001 | PyDesign is an offline, desktop, Python-authored editorial layout and vector composition environment. |
| D-002 | Visible Python is the canonical authored document truth. The retained semantic model is the canonical in-memory interpretation of a source revision. |
| D-003 | GUI document edits write Python through LibCST-backed transactions. No hidden visual-override document layer exists. |
| D-004 | Arbitrary Python remains allowed. Direct manipulation is guaranteed only for objects with stable IDs and properties whose source ownership can be resolved. |
| D-005 | When a value is computed, the GUI offers explicit source-level choices: edit the controlling parameter, add a visible adjustment, or detach to a literal. It never silently replaces an expression. |
| D-006 | Projects are multi-file. Page order is explicit in `document.py`; directory scanning never defines document order. |
| D-007 | One file normally represents a meaningful page, spread, article or reusable section—not mechanically every physical page. |

## Core technology

| ID | Locked decision |
|---|---|
| D-010 | Runtime language: CPython 3.12 or later, with a supported-version matrix rather than dependence on one interpreter patch. |
| D-011 | Desktop framework: PySide6 / Qt Widgets. Canvas: QGraphicsScene/QGraphicsView with an replaceable viewport renderer. |
| D-012 | Source transformations: LibCST. Syntax highlighting and editing begin with a purpose-built QPlainTextEdit component behind a `SourceEditor` interface. |
| D-013 | User code evaluates in spawn-created disposable worker processes using a documented trust model. Process isolation is a reliability boundary, not a security sandbox. |
| D-014 | Public core packages are under `pydesign`; GUI packages do not leak into the headless document/layout API. |

## Geometry and rendering

| ID | Locked decision |
|---|---|
| D-020 | Public geometry accepts typed physical units. Evaluated geometry is IEEE-754 double precision in PostScript points, 1 pt = 1/72 inch. |
| D-021 | Author coordinates begin at the page’s top-left, x rightwards and y downwards; positive rotation is clockwise. PDF coordinate conversion occurs only in the PDF renderer. |
| D-022 | Layout produces an immutable revisioned display list plus semantic maps. Canvas and PDF consume it without reflowing or reordering content. |
| D-023 | Stable source-visible object IDs are mandatory for selection persistence, source mapping, GUI edits and diagnostics. GUI-created IDs use a `pd_` prefix and random base32 payload. |
| D-024 | Every renderer implements the same graphics-state semantics: transform, clipping, opacity, blend mode, paint, stroke and isolation. |

## Typography

| ID | Locked decision |
|---|---|
| D-030 | ICU supplies Unicode boundaries, bidi resolution and line-break opportunities. HarfBuzz performs shaping. FreeType supplies raster metrics. FontTools supplies font parsing, outlines, variations and subsetting. Pyphen supplies language-aware hyphenation dictionaries. |
| D-031 | PyDesign owns paragraph composition, justification, columns, exclusions, linked frames, widows/orphans and optical adjustments. No GUI or PDF toolkit may independently lay out body text. |
| D-032 | The atomic renderer input is a positioned `GlyphRun` carrying font instance, glyph IDs, clusters, advances, offsets, direction, script, language and source mapping. |
| D-033 | Semantic PDF text is preferred. Outline conversion is an explicit per-run fallback for unsupported effects and must be reported by preflight. |
| D-034 | Fonts are project assets or explicitly resolved system fonts pinned by fingerprint. Export embeds a legal subset unless embedding permissions prohibit it. |

## PDF, colour and images

| ID | Locked decision |
|---|---|
| D-040 | The internal display list and PDF adapter are project-owned. The initial production writer uses ReportLab `pdfgen` plus controlled low-level extensions; pikepdf assembles, inspects and post-processes; Flat is a parity benchmark, not an API dependency. |
| D-041 | The first print-standard target is PDF/X-4, while normal PDF export remains available. Export is blocked only by errors applicable to the selected profile. |
| D-042 | Poppler rasterisation is the local PDF ground truth for proof and visual comparison. |
| D-043 | Colour objects distinguish device RGB, device CMYK, calibrated ICC colour, greyscale and named spot colour. LittleCMS via Pillow ImageCms performs conversions. |
| D-044 | Images remain linked by default, are fingerprinted, colour-managed and decoded off the UI thread. Original pixels are never destructively rewritten by layout operations. |

## Interaction and persistence

| ID | Locked decision |
|---|---|
| D-050 | The primary workspace is code + canvas, with contextual inspector, project/layer trees and collapsible diagnostics. |
| D-051 | Canvas transforms show a provisional preview during the gesture and commit one source transaction on release. Escape cancels; undo restores exact previous file bytes and selection. |
| D-052 | Save uses atomic replace. Autosave stores recoverable source snapshots separately and never overwrites the last explicit user save. |
| D-053 | GUI preferences and view state are separate from portable project state. Portable project settings are visible in `project.toml`. |
| D-054 | File watching detects external changes. Clean buffers reload; dirty buffers receive a three-way merge workflow. |

## Extensions, privacy and distribution

| ID | Locked decision |
|---|---|
| D-060 | Extension points use Python entry points and project-local modules. Plug-ins run with the user project’s trust level and declare API compatibility and capabilities. |
| D-061 | No network is required or contacted by default. There is no telemetry. Update checking and network-capable plug-ins require explicit opt-in. |
| D-062 | Headless build, export, preflight and proof are available through a `pydesign` CLI and the same core packages used by the GUI. |
| D-063 | PyDesign source is intended for MPL-2.0 release. User source, assets and generated output remain the user’s property. Dependency licences are checked in CI and release review. |
| D-064 | Supported desktop targets are current Windows, macOS and mainstream Linux distributions; exact minimum OS versions are stated per release. |

## Verification spikes that do not reopen product decisions

1. Prove that ReportLab can emit positioned shaped glyphs with correct subsetting and ToUnicode maps; otherwise implement the same adapter contract with direct PDF objects.
2. Measure PyICU and native dependency packaging on all supported operating systems.
3. Compare FreeType, Qt and exported-PDF raster bounds across the reference font corpus.
4. Establish PDF/X-4 validation tooling and tolerances usable offline in CI.
5. Benchmark QGraphicsView with outline glyph caches and thousands of elements; switch viewport implementation without changing interaction contracts if necessary.

Failures in these spikes may change an implementation component through an ADR, but not the visible-source, shared-layout, typographic or export semantics.

