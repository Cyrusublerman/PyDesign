# 07 — Rendering, PDF export and proofing

## Rendering invariant

Semantic evaluation and layout decide all geometry, text breaks, glyph positions, resource identities and paint order. Renderers consume the same immutable display list. Renderer-specific coordinate conversion, rasterisation and resource encoding may vary; layout semantics may not.

## Display-list model

The versioned display list includes:

- begin/end page and page boxes;
- save/restore graphics state;
- concatenate affine transform;
- begin/end isolated or knockout group;
- clip path with nonzero/even-odd rule;
- set fill/stroke paint, overprint, opacity and blend mode;
- fill/stroke path;
- draw positioned glyph run;
- draw image with source/destination transform and interpolation policy;
- begin/end semantic marked content;
- annotations, destinations and document structure references.

Operations are immutable and deterministically ordered. Optional debug IDs link each operation to objects and source.

## Interactive renderer

The Qt renderer uses QPainter/QGraphicsItems only as a viewport implementation. It renders vector paths from normalized geometry, glyph outlines/raster caches from the exact font instance and colour-managed preview images. It must not use `QTextDocument` for document flow.

At low zoom it may simplify strokes/effects and use cached page tiles, but geometry and selection maps remain exact. A quality switch forces final display-list rasterisation for proof comparison.

## PDF pipeline

The initial pipeline is:

1. validate the selected export profile;
2. freeze a successful deterministic layout snapshot;
3. collect/deduplicate fonts, images, ICC profiles, patterns and graphics states;
4. subset fonts with FontTools from used glyph closure;
5. emit page content through the project-owned PDF adapter using ReportLab `pdfgen` and controlled low-level PDF operations;
6. use pikepdf to assemble/normalize page resources, metadata, output intents, structure and conformance-related objects;
7. reopen and inspect the result with pikepdf/pdfplumber checks;
8. validate page boxes, fonts, colour and profile-specific rules;
9. atomically publish the PDF;
10. rasterise with Poppler and compare against the reference canvas render.

ReportLab objects never enter the semantic/layout API. If the shaped-glyph spike shows an unfixable writer limitation, the adapter implementation changes while the display list and all document APIs remain stable.

## PDF profiles

### Standard PDF

Default version is selected for used features, with modern transparency preserved. It supports RGB/CMYK/spot colour, embedded fonts, links, bookmarks, metadata, optional layers where requested and tagged structure to the extent implemented.

### PDF/X-4

The first production print profile requires:

- correct trim/bleed/media boxes;
- output intent ICC profile;
- embedded fonts or explicit allowed outline fallback;
- no prohibited actions, encryption, multimedia or unbounded external references;
- profile-compatible colour and transparency;
- required metadata and identifiers;
- preflight without blocking errors.

PDF/X conformance is never claimed only because a filename/profile option was selected. The validator report is stored with the build.

### Future profiles

PDF/A and PDF/UA are separate profiles with different semantic requirements. The model retains structure, language, alt text and reading order from the start, but conformance is claimed only after dedicated test suites and validators pass.

## Font encoding and extraction

Each embedded font instance receives a deterministic subset and encoding. The writer maps positioned glyph IDs without re-shaping and builds ToUnicode maps from cluster/source data. Ligatures, reordered scripts and discretionary hyphens use semantic text mappings appropriate to extraction.

When a run is outlined, its geometry is emitted as paths under a semantic wrapper where possible; preflight records reduced selectability/accessibility. Outlining never occurs merely to simplify implementation of ordinary shaped text.

## Colour and transparency in PDF

- ICCBased and calibrated colour spaces carry project profile identities.
- Spot colour uses Separation/DeviceN with an explicit alternate and tint transform.
- Fill/stroke overprint and overprint mode are retained.
- Transparency uses ExtGState, soft masks and isolated groups.
- Blend colour space follows the declared group/output policy.
- RGB-to-CMYK conversion happens before writing through LittleCMS, not by unprofiled formula.

## Images in PDF

Unmodified compatible JPEG data may pass through without recompression. Other images are decoded, colour managed, resized once to policy and encoded deterministically. Alpha becomes a soft mask where the profile allows. Image interpolation intent and effective DPI are explicit. Original asset hashes and emitted resource hashes appear in the manifest.

## Page boxes, marks and imposition

The page model maps media, crop, bleed, trim and art boxes directly. Printer marks are a profile option drawn outside trim with their own layer/colour policy. Reader spreads remain individual PDF pages. Imposition is a separate deterministic post-layout operation/profile, never confused with authored spreads.

## Metadata and navigation

Document information/XMP includes title, authors, subject, keywords, language, creator/version, creation policy and build fingerprint. Deterministic builds use configured timestamps/IDs. Sections may create page labels, outlines/bookmarks and named destinations. Links are semantic annotations with explicit rectangles and target validation.

## Tagged structure

Semantic roles include document, section, heading levels, paragraph, list, table, figure, caption, note and artifact. Reading order is source-explicit and may differ from z-order. Figures accept alt text; decorative objects are artifacts. Initial releases may label tagged PDF experimental, but the source/document/display-list contracts include structure IDs from the first slice.

## Preflight

Preflight runs at document, page, object and output-resource levels. Checks include:

- missing/changed assets and fonts;
- missing glyphs/fallbacks and outlined text;
- overset text, invalid links and unreachable content;
- low effective image DPI and unintended upsampling;
- page-box/bleed errors and content outside intended regions;
- colour spaces, missing profiles, ink coverage, spot conflicts and overprint;
- transparency/rasterisation incompatible with the selected profile;
- font embedding restrictions and subset/ToUnicode validity;
- prohibited PDF actions/resources and conformance metadata;
- non-deterministic inputs.

Each issue has stable code, severity, source/object/page locations and remediation. Profiles decide blocking severity. Waivers are explicit source/build configuration with reason and diagnostic code.

## Proofing and parity

Three comparable outputs are generated from a frozen snapshot:

1. high-quality reference raster from the internal display list;
2. exported PDF raster from Poppler at the same DPI and colour intent;
3. optional Qt viewport capture for detecting preview-only faults.

Comparison aligns by page boxes and uses pixel difference plus structural checks for paths, glyph positions and resources. Anti-aliasing tolerances are edge-aware. Thresholds are versioned test policy, not arbitrary UI sliders. The UI may amplify differences for visibility without changing pass/fail data.

## Export atomicity and reproducibility

Export writes to a temporary sibling path. Only after writer, reopen, profile validation and required proof steps succeed is it atomically renamed over the destination. A manifest records source revision, dependency versions, platform, fonts/assets, profiles, resource hashes, warnings/waivers and output SHA-256.

Given the same project, lock data, supported platform class and profile, semantic/display-list hashes must match. PDF byte identity is a goal where metadata/compression permit; visual and structural determinism are release requirements.

## Failure behaviour

Writer or validation failure leaves the previous output untouched and retains temporary diagnostics/proof data under `.pydesign/proof/`. Cancellation stops after a safe boundary and never publishes a partial PDF. Errors map back through display-list operation IDs to document objects and source.

