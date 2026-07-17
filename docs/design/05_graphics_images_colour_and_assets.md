# 05 — Graphics, images, colour and assets

## Vector object model

Primitive shapes compile to paths before the display-list boundary. The public API retains semantic rectangles, rounded rectangles, ellipses, lines, polygons, stars and arcs so inspectors can expose meaningful parameters. Arbitrary paths contain ordered subpaths of move, line, quadratic/cubic curve and close segments.

Path nodes retain stable keys within an object. GUI node edits update the smallest source node structure possible. Boolean operations create a new explicit path and retain provenance to the inputs; they are not live unless expressed as a Python operation.

## Pen and node semantics

- Click creates a corner; click-drag creates a smooth node.
- Modifier keys constrain angle, break/link handles, convert node type and temporarily snap.
- Handles may be collinear, mirrored, independent or automatic.
- Closing a path is distinct from placing a final coincident point.
- Open subpaths can fill only according to the selected fill rule and emit a warning when likely accidental.
- Node deletion preserves neighbouring curve shape when “smart delete” is chosen; plain delete removes exactly the node.

## Paint model

Fill and stroke are independent paint objects. Supported paints are none, solid process colour, named spot colour, axial/radial/conic gradient, mesh-gradient architecture, image/pattern and reusable swatch reference.

Stroke properties include width, alignment policy, cap, join, miter limit, dash pattern/phase, start/end markers and variable-width profile. Since PDF natively centres strokes, inside/outside alignment compiles to geometry where necessary and preflight reports expansion.

Gradients have stable stop IDs, colour/interpolation space, spread method, transform and opacity per stop. Conic and mesh gradients fall back to deterministic vector tessellation or rasterisation according to export policy; the fallback is reported.

## Graphics state and effects

Each operation resolves transform, clip stack, fill/stroke, opacity, blend mode, overprint and isolation. Supported blend modes mirror PDF’s standard set. Knockout/isolation groups are explicit. Effects include blur, shadow and colour matrix behind an effect interface with declared vector or raster output.

Rasterisation is never silent. Each effect chooses resolution, colour space, alpha, bounds expansion and cache key. Preflight lists rasterised regions and effective DPI.

## Images

An `ImageAsset` is content-addressed metadata for a linked file. An `ImageFrame` references the asset, frame path, fit mode and non-destructive image transform.

Fit modes: none, contain, cover, stretch, fit-width, fit-height and explicit crop. The crop transform is stored independently of the frame transform. GUI dragging within a frame edits the visible source crop/transform parameters.

Supported baseline inputs are PNG, JPEG, TIFF, WebP and formats Pillow can decode reliably. PDF/SVG placement is mediated through dedicated importers with explicit fidelity reports; unsupported executable or external-resource SVG features are disabled.

## Image processing

The pipeline is ordered and non-destructive:

1. decode and apply EXIF orientation;
2. interpret embedded ICC profile or declared fallback;
3. crop/transform at source resolution;
4. apply explicit channel/duotone/filter operations;
5. convert for proof/export intent;
6. resample once to the required effective resolution;
7. encode with profile-appropriate lossless/lossy settings.

Preview mipmaps are derived cache. Export never upsamples merely to satisfy a nominal DPI. Preflight reports effective DPI, missing/invalid profiles, alpha flattening and compression choices.

## Colour model

Colour values are typed; RGB tuples cannot be mistaken for CMYK. Core types are:

- `Gray` and `DeviceGray`;
- `RGB`, `LinearRGB` and `DeviceRGB`;
- `CMYK` and `DeviceCMYK`;
- `ICCColor(profile, components)`;
- `SpotColor(name, alternate, tint)`;
- `Lab` for device-independent definitions.

Author-facing colour components use documented 0–1 values with convenience percentages. Alpha is separate from colour. Conversion uses LittleCMS with explicit source/destination profiles, rendering intent and black-point compensation.

## Working and output spaces

The project declares RGB and CMYK working spaces and policy for untagged content. A document object retains its authored colour space until a profile/export operation requires conversion. Canvas fast preview uses monitor RGB; soft proof uses the same colour transform and output intent as export, including paper simulation where supported.

Exact monitor calibration depends on OS/Qt support and is labelled accordingly. A colour-managed raster proof is the authoritative on-screen print simulation.

## Spot colour and print controls

Spot colours retain names and tint values into PDF separations when the export profile permits. Duplicate names with differing definitions are errors. Objects and strokes may set fill/stroke overprint. Rich black is an explicit swatch, never an automatic substitution. Total ink coverage is measured during proof/preflight when an output profile is available.

## Transparency

PDF/X-4 retains live transparency. Profiles requiring flattening invoke a deterministic flattener and report affected regions. Transparency groups, soft masks and blend colour spaces are explicit display-list operations so canvas and PDF implement the same compositing intent.

## Asset registry

Every external asset record includes:

- project-relative path and normalized URI;
- SHA-256 content fingerprint;
- media type, dimensions and metadata;
- ICC/profile and font-embedding information where applicable;
- source modules and object IDs that use it;
- last verified timestamp outside deterministic build identity.

Missing or changed assets do not disappear silently. The canvas retains a labelled placeholder/last cached preview, and export blocks when fidelity cannot be guaranteed.

## Asset browser and relinking

The asset panel filters by type/status/usage, previews local files and identifies duplicates by content. Relink offers one file, search directory or fingerprint match. Bulk relink previews path changes. Packaging preserves relative directory structure where possible and records renames in the manifest.

## Imported vector/PDF content

Importers normalize supported content into PyDesign paths, text/images or an opaque placed-document object. Editable import is best-effort and emits a fidelity report. Opaque placement preserves original bytes and a page box; it cannot be edited internally. External actions, scripts, forms, multimedia and network references are stripped or rejected.

## Resource deduplication

Layout/export resources are keyed by content and transformation fingerprints. Identical font subsets, image encodings, ICC profiles, patterns and reusable graphics are shared where this does not change semantics. Deduplication never changes object identity or source mapping.

