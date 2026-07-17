# 04 — Typography and text layout

## Objective

PyDesign’s typography engine must support professional magazine composition without delegating line layout to Qt or ReportLab. It uses specialist libraries at their proper boundaries and owns composition policy so canvas and PDF receive identical positioned glyphs.

## Authority stack

| Responsibility | Authority |
|---|---|
| Unicode properties, grapheme/word/sentence boundaries | ICU |
| Bidirectional paragraph resolution | ICU Bidi |
| Script/language itemisation inputs | Unicode data + ICU, with explicit author overrides |
| OpenType shaping and glyph positioning | HarfBuzz through `uharfbuzz` |
| Font face loading, raster metrics and hinting | FreeType through `freetype-py` |
| Font tables, cmap, outlines, variations, colour-font data and subsetting | FontTools |
| Dictionary hyphenation | Pyphen with packaged dictionaries |
| Paragraph composition and page flow | PyDesign |
| Display and PDF placement | PyDesign layout `GlyphRun` |

Qt text layout may render UI labels but must not decide document glyphs or line breaks.

## Text input model

Text content is Unicode. A `TextStory` contains the source string, language spans, bidi overrides only when explicitly required, semantic roles and character/paragraph style spans. Indices exposed to Python are Unicode code-point offsets; internal maps also retain UTF-8/UTF-16 and grapheme indices for libraries and UI selection.

Normalisation is never silently applied to authored text. Preflight may warn about mixed or unexpected normalisation and offer an explicit source edit.

## Style system

Resolved text style is immutable and includes:

- font family/face or explicit font asset;
- variable axes and named instance;
- point size and optical sizing policy;
- OpenType script, language and feature map;
- fill/stroke, opacity and overprint;
- tracking, kerning policy, horizontal/vertical scale and baseline shift;
- leading mode/value and baseline-grid alignment;
- underline, strike, decoration geometry and emphasis marks;
- paragraph direction, alignment, indents, spacing, tabs and rules;
- hyphenation and justification settings;
- keeps, widows/orphans, span/column rules and composer choice;
- accessibility language and semantic role.

Character and paragraph styles use single inheritance with cycle detection. Explicit instance properties win over character style, which wins over paragraph style, which wins over document defaults. The inspector displays this provenance.

## Font resolution

Font lookup is deterministic:

1. exact project font path and fingerprint;
2. project-declared font family mapping;
3. explicitly permitted system font fingerprint;
4. declared fallback chain;
5. visible missing-glyph diagnostic.

The resolver never silently substitutes a font by family-name similarity. Font identity includes file hash, face index, variation coordinates and synthetic-style flags. Synthetic bold/italic are off by default and reported when enabled.

Font embedding permission bits are inspected but not treated as legal advice. Restricted fonts block profiles that require embedding. Package-for-output copies a font only when the project permits it and reports the action.

## Shaping pipeline

For each paragraph:

1. Determine paragraph base direction from style or ICU default.
2. Calculate bidi embedding levels and visual runs with ICU.
3. Segment at style, font, script, language, direction and feature boundaries without breaking grapheme clusters.
4. Resolve font fallback per cluster; emoji/colour glyph policy is explicit.
5. Shape each run with HarfBuzz using font variation coordinates and scale derived from font units.
6. Preserve glyph IDs, clusters, advances, offsets, unsafe-to-break flags and source ranges.
7. Feed shaped measures to the paragraph composer.
8. Re-shape only when a chosen line break or contextual feature requires boundary-sensitive shaping.

Fallback is cluster-safe. Combining marks cannot be stranded in another font solely because the base glyph exists.

## `GlyphRun` contract

A positioned run contains:

- font resource key and exact instance fingerprint;
- glyph IDs in paint order;
- x/y origin per glyph or advances plus offsets;
- source clusters and logical text range;
- bidi level, direction, script and language;
- applied features and variation axes;
- paint/decorations and transform;
- logical, typographic and ink bounds;
- semantic text payload for PDF extraction;
- outline-fallback reason when applicable.

Positions are in unhinted page points. Screen hinting affects rasterisation only and never feeds geometry back into layout.

## Paragraph composition

The engine supports two composers behind one interface:

- **single-line composer**: greedy, predictable and fast for interactive drafts;
- **paragraph composer**: Knuth–Plass-style global optimisation with penalties and fitness classes for final composition.

The selected composer is part of source style and defaults to paragraph composition for body text. Both obey the same legal break opportunities and must produce deterministic output.

The composition item stream includes boxes, glue and penalties derived from shaped clusters, spaces, discretionary hyphens, explicit breaks, tabs, inline objects and language rules. Cost considers badness, consecutive hyphens, loose/tight adjacency, rivers proxy, keep constraints and author penalties.

## Hyphenation and line breaking

- ICU provides legal line-break opportunities.
- Pyphen adds language dictionary candidates within legal words.
- Soft hyphen and nonbreaking characters retain Unicode semantics.
- Style controls minimum word length, minimum prefix/suffix, maximum consecutive hyphens and hyphenation zone.
- Proper hyphen glyph selection is font/language aware.
- The source string remains unchanged; inserted line-end hyphens are layout artefacts with extraction mapping.

## Justification

Justification may vary word spacing, letter spacing and glyph scaling within explicit min/preferred/max ranges. Arabic kashida and script-specific methods are architecture-level capabilities and are applied only through script-aware policies. Last-line alignment, forced-line alignment and single-word lines are independent settings.

Optical margin alignment hangs selected punctuation using font/Unicode-informed values that can be overridden by style. It changes visual edge placement without corrupting text selection maps.

## Frames, columns and flow

Text frames support rectangular or arbitrary path interiors, inset, multiple columns, fixed/automatic column widths, gutters and vertical alignment. Exclusion paths are transformed into scanline intervals per candidate line. A frame chain flows one story through ordered containers; cycles are errors.

Layout records the exact source range consumed by each frame. Overset text is a first-class diagnostic and canvas marker. Frame balancing is a constrained search over breakpoints and is disabled for intermediate linked frames unless requested.

## Pagination controls

Paragraph properties include keep-together, keep-with-next/previous, minimum lines at frame start/end, page/column break-before/after and maximum keep strength. Composition reports unsatisfied soft constraints and errors only when no legal placement exists for a hard constraint.

Footnote, endnote, sidenote and float anchoring are reserved in the model from the start. Initial implementation may stage them later, but their anchors and numbering are semantic story objects rather than manually placed strings.

## Advanced typography

The engine design includes:

- drop caps spanning N baselines;
- nested and GREP-like styles implemented as explicit deterministic span rules;
- tabs with left/right/centre/decimal alignment and leaders;
- paragraph rules, borders and shading;
- inline/anchored objects;
- text on path with offset, side, alignment and overflow controls;
- vertical writing modes and rotated-sideways glyph orientation;
- ruby/emphasis annotation model;
- OpenType feature inspection and per-range activation;
- variable font axes and `avar`-aware instances;
- colour fonts with explicit raster/vector fallback diagnostics.

Features may ship in slices, but the data model and glyph-run mapping must not preclude them.

## Editing and inspection

Text editing operates on the source story, not on rendered glyph strings. Canvas text mode maps hits through glyph clusters to grapheme-safe caret positions. Bidi caret movement distinguishes visual arrow movement from logical source movement. The typography inspector can show resolved face, glyph ID/name, cluster, features, axes, advance, offset, fallback and source span.

## PDF text policy

- Prefer embedded subsets with positioned glyph encoding and ToUnicode maps.
- Preserve reading text and language metadata separately from visual glyph order.
- Use actual text for ligatures and discretionary substitutions.
- Convert to outlines only for effects the writer cannot express accurately.
- Preflight counts outlined runs and warns about lost search/accessibility.
- Never ask ReportLab to re-shape or re-wrap a run.

## Required corpus

Tests include Latin with ligatures/diacritics, Arabic, Hebrew, Devanagari, Thai, CJK, emoji/colour fonts, combining marks, mixed bidi, variable fonts, small caps, old-style numerals, vertical forms, long unbreakable strings and missing glyphs. Expected values cover clusters, glyph IDs, positions, breaks, frame consumption and extraction.

