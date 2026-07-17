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

## Boundaries and composition

The optional ICU adapter converts UTF-16 boundary offsets to Python code-point indices, including supplementary-plane characters. Pyphen supplies language dictionary candidates without changing source text. `compose_greedy()` chooses legal candidates within a width and re-shapes each candidate boundary so contextual OpenType behavior is not reused incorrectly.

This is the fast single-line composer contract, not the final paragraph engine. Bidi itemisation, grapheme-safe fallback, Knuth–Plass optimisation, justification, linked frame flow and exact outline painting remain required before Stage 3 can exit.

## Audit commands

```bash
pydesign font-info /path/to/font.otf --face-index 0 --variation wght=550
pydesign shape-text /path/to/font.otf 'office' --feature liga=1 --language en
```

Both commands emit deterministic JSON suitable for fixtures and implementation comparisons.
