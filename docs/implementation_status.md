# Implementation status

Updated: 2026-07-20

## Implemented and verified

- Stage 0 packaging, MPL-2.0 licence, contribution/security policy, ADR template and CI.
- Core package boundary with no PySide6 imports outside `pydesign.gui`.
- Typed point, millimetre, centimetre, inch, pica and CSS-pixel quantities.
- Immutable Document, Page, Layer, Rectangle, Ellipse, ImageFrame, Guide and TextFrame objects.
- CharacterStyle / ParagraphStyle with cycle detection and `resolve_character_style`.
- Stable-ID, geometry and document validation with structured diagnostic codes.
- Immutable renderer-neutral display list and JSON schema version.
- Deterministic conservative project hashing and `project.toml` loading.
- Fresh subprocess evaluation with versioned JSON-over-stdio messages and build-cache hits.
- CLI: `new`, `duplicate`, `package`, `package-for-output`, `check`, `render-json`, `build-pdf`, `proof`, `open`, `font-info`, `shape-text`.
- LibCST ownership, frame/Bézier/appearance/text/layer/page-order/ellipse plans, Ruff finalize on GUI commits.
- Atomic source transactions, journals, recovery, Qt undo; create/move/undo fuzz.
- Typography: project font corpus, HarfBuzz GlyphRun, bidi itemisation in compose, flow_story, justification, FreeType outlines, `PD-TEXT-003` overset.
- PDF: rectangles/ellipses/paths/images/glyph_run (subset+ToUnicode or outlines), preflight/waivers, proof rasters + difference PNGs, PDF/X-4 boxes stamp.
- Editorial: guides in display list, page labels/sections, components helper, `examples/magazine_32`.
- Colour objects, extension preflight registry hooks, perf budget smoke script.
- Docked GUI chrome, remappable shortcuts, command palette, multi-window, proof difference dock.

## Stage exits

| Stage | Exit | Notes |
|------:|:----:|-------|
| 0–1 | Yes | Baseline vertical slice |
| 2 | Yes | Appearance property rewrites, style ownership options, journal recover + create/move/undo fuzz |
| 3 | Yes | Corpus fonts + goldens, flow/bidi/justify/outlines, overset `PD-TEXT-003`, outline canvas for `font=` |
| 4 | Yes | Subset glyph_run PDF, proof CLI + difference panes, atomic publish, placeholder reject |
| 5 | Yes | Styles resolve, guides/labels/sections, components, magazine_32 with styles/flow |
| 6 | Yes | Ellipse/line→Python, ImageFrame hash/stale refuse, colour objects, resource DPI warnings |
| 7 | Yes | pdfx4 boxes + structural validator, waivers, package-for-output CLI, expanded preflight |
| 8 | Yes | Build-cache, extension preflight sample, perf budget smoke, proof a11y chrome |

## Verification commands

```bash
ruff format --check .
ruff check .
mypy
mypy --config-file mypy-gui.ini src/pydesign/gui
pytest
python scripts/check_architecture.py
python scripts/check_perf_budgets.py
pydesign check examples/typography_corpus --json
pydesign check examples/magazine_32 --json
pydesign build-pdf examples/typography_corpus --output /tmp/corpus.pdf
pydesign proof examples/typography_corpus --pdf /tmp/corpus.pdf
```
