# Typography authority foundation

PyDesign does not delegate document shaping or line choice to Qt or ReportLab. The first Stage 3 slice establishes independently testable font, glyph and break contracts for later canvas and PDF consumers.

## Exact font identity

`load_font_face()` resolves an explicit file and face index, hashes its bytes with SHA-256, validates requested variable-axis coordinates with FontTools, and includes variations plus synthetic-style settings in an instance fingerprint. Metadata includes names, units per em, glyph count, table tags, variable axes and OS/2 embedding flags. `verify_unchanged()` blocks shaping if bytes changed after resolution.

## Positioned glyph runs

`shape_text()` sends code-point clusters, explicit or guessed direction/script/language, OpenType feature values and variable coordinates to HarfBuzz. It returns immutable point-space glyph positions with:

- exact font instance identity;
- glyph IDs and names;
- logical source clusters;
- x/y advances and offsets;
- unsafe-to-break flags;
- per-glyph ink bounds;
- resolved direction, script, language and feature settings.

No screen hinting feeds geometry back into the run.

## Explicit registry and fallback

`FontRegistry` gives each face a project-defined alias and records whether it came from a project asset or a system path. Project paths may not escape the project root. System faces require the caller's exact SHA-256, so host font discovery can never silently change output. Coverage comes from the font's best Unicode cmap.

`shape_with_fallback()` segments extended grapheme clusters with ICU when available and a conservative combining/variation/ZWJ fallback otherwise. It chooses one explicitly ordered face for each complete cluster, groups adjacent clusters using the same face, and shapes each group with its original source offsets. Missing coverage is a visible error naming the cluster, code points, source index and aliases tried.

## Boundaries and composition

The optional ICU adapter converts UTF-16 boundary offsets to Python code-point indices, including supplementary-plane characters. Pyphen supplies language dictionary candidates without changing source text. `compose_greedy()` chooses legal candidates within a width and re-shapes each candidate boundary so contextual OpenType behavior is not reused incorrectly.

`flow_story()` recomposes as widths change and distributes globally mapped lines through ordered frames and columns. Frame IDs, dimensions, counts and gutters are validated; every positioned line retains exact authored source ranges. The result exposes both unplaced overset text and lines that exceed their column width.

This is still the fast composer contract, not the final paragraph engine. Bidi itemisation, fallback-aware paragraph breaking, Knuth–Plass optimisation, script-appropriate justification and exact outline painting remain required before Stage 3 can exit.

## Audit commands

```bash
pydesign font-info /path/to/font.otf --face-index 0 --variation wght=550
pydesign shape-text /path/to/font.otf 'office' --feature liga=1 --language en
```

Both commands emit deterministic JSON suitable for fixtures and implementation comparisons.
