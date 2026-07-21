# 13 — Library integration and interchange strategy

## Purpose

PyDesign should exploit the Python graphics, scientific and document ecosystems without allowing
their incompatible document models, event loops, renderers or licences to weaken the core
contracts. This specification defines when a dependency belongs in core, how an adapter crosses the
boundary and which library families are preferred for planned capabilities.

The list is a design inventory, not permission to install every package. A package enters
`pyproject.toml` only with an implemented capability, tests, notices and a verified offline
distribution path.

## Integration classes

| Class | Meaning | Loading policy |
|---|---|---|
| Core authority | Required to interpret or render ordinary PyDesign projects | Shipped and pinned by supported range |
| Native optional backend | Produces editable PyDesign values behind a public adapter | Optional extra; lazy import |
| Import/export adapter | Translates a foreign local format with a fidelity report | Optional extra or extension |
| Isolated plug-in | Heavy/native runtime, foreign event loop or unusual licence boundary | Worker/service process and explicit enablement |
| External executable | Mature non-Python tool invoked locally | Capability probe, version record and clear installation guidance |

Candidate integrations must answer:

1. What exact user capability does the library unlock?
2. Does it produce native objects, structured vector/text/data, placed PDF or raster output?
3. Is the result deterministic from declared local inputs?
4. Does it require a GUI or event loop?
5. Can it run outside the GUI process?
6. Does it work without a network after installation?
7. What are its licence and redistribution obligations?
8. What native libraries, JavaScript runtimes, browsers or executables does it require?
9. Which supported platforms and Python versions have wheels or reproducible builds?
10. How are source provenance, versions, warnings and fidelity exposed?

## Boundary result types

An integration may cross into the canonical pipeline only as:

- native PyDesign semantic elements;
- native paths/paints/transforms;
- structured text, styles or data;
- parsed SVG converted to a PyDesign group;
- opaque placed PDF with page box and fidelity metadata;
- colour-managed raster asset with resolution/profile metadata.

An integration must not draw independently to the interactive canvas and then use an unrelated
export path. Canvas and PDF continue to consume the shared display list.

## Core and near-core authorities

| Capability | Preferred authority | Policy |
|---|---|---|
| Desktop UI | PySide6 / Qt Widgets | Existing core GUI extra |
| Source transactions | LibCST | Existing core dependency |
| Unicode and bidi | ICU / PyICU | Typography authority |
| Text shaping | uharfbuzz / HarfBuzz | Typography authority |
| Font metrics/outlines | FreeType and FontTools | Typography authority |
| Hyphenation | Pyphen initially | Replaceable language adapter |
| PDF writing/inspection | ReportLab pdfgen and pikepdf | Existing PDF adapter |
| Everyday raster IO | Pillow | Add with first image-frame slice |
| ICC conversion | Pillow ImageCms / LittleCMS | Add with colour-managed image slice |
| Interactive constraints | kiwisolver | Add with declared constraint slice |
| Numeric arrays | NumPy | Add when packed geometry/procedural API needs it |
| Modern authoring colour | ColorAide | Verify against internal colour types before adoption |

## Creative coding and rendering

### Native creative API

The preferred integration is PyDesign’s own explicit-context vector creative API specified in 12.
It borrows familiar concepts from Processing, py5, Shoebot and Cairo while returning normal
PyDesign objects.

### Candidate systems

| Library/system | Useful capability | Integration decision |
|---|---|---|
| py5 | Processing-style generative art, Java/OpenGL and scientific-Python interoperability | Isolated sketch adapter; never the canonical canvas |
| Shoebot | Python vector creative coding, Cairo and scripted controls | Architectural inspiration or isolated adapter; GPL review required |
| Pycairo | Mature vector drawing to image/PDF/SVG/PS targets | Optional renderer/interchange benchmark |
| drawsvg | Straightforward SVG generation and animation | Optional SVG generator/import fixture |
| Gizeh | Small Cairo-oriented creative wrapper | Reference/inspiration rather than core authority |
| Manim Community | Programmatic mathematical animation | Isolated animation/vector-sequence adapter |
| ModernGL | High-performance OpenGL and shaders | Future preview/effect plug-in only |
| pygame-ce, pyglet, Kivy | Interactive/game/application runtimes | Not core; foreign event-loop plug-ins only |

Any external creative system must either return native commands or export a local asset that enters
through the declared SVG/PDF/raster boundary.

## Vector geometry

| Library | Preferred role | Important limit |
|---|---|---|
| skia-pathops | Boolean operations on curved paths | Adapter must preserve PyDesign stable node/provenance policy |
| Shapely | Planar topology, offsets, containment, collision and spatial indexes | Polygon/line topology is not the canonical Bézier model |
| FontTools pens | Glyph outline conversion and pen interoperability | Font licences and semantic-text loss remain explicit |
| svgpathtools | SVG path measurement, intersections and calculus | Parser/geometry helper, not document authority |
| svgelements | SVG parsing, transforms and geometry | Fidelity report required |
| drawsvg/svgwrite | SVG generation | Export/generation rather than full editable import |
| bezier | Exact curve evaluation and intersections | Optional specialist backend |
| pyclipper | Robust integer polygon clipping/offset | Curves require controlled flattening |
| mapbox-earcut/triangle | Tessellation for previews/fallbacks | Tessellation is derived data |
| ezdxf | DXF interchange | Optional domain adapter |

The canonical path remains PyDesign’s ordered line/quadratic/cubic segment model. Flattening always
creates derived geometry and records tolerance.

## Raster images and colour

| Library | Preferred role |
|---|---|
| Pillow | Baseline image decode/encode, transforms, thumbnails and ImageCms |
| pyvips/libvips | Streaming, tiled and very large image processing |
| scikit-image | Transparent scientific filters, segmentation and measurement |
| opencv-python-headless | Computer vision, perspective correction and high-performance transforms |
| tifffile | Advanced TIFF/metadata support |
| rawpy | Camera RAW decoding |
| imageio/PyAV/FFmpeg | Frame sequence and animation/video interchange |
| ColorAide | Modern colour spaces, interpolation, difference and gamut mapping |
| colour-science | Specialist scientific colour calculations and validation |
| colorspacious | Perceptual colour and vision-deficiency analysis |
| pytesseract/Tesseract | Optional local OCR |
| Potrace-compatible adapter | Optional raster-to-vector tracing |

OpenCV and large-image operations run in workers. Image edits remain ordered non-destructive
operations and original asset bytes remain unchanged.

## Data, charts, diagrams and maps

| Library | Preferred role |
|---|---|
| NumPy | Arrays, geometry, sampling and numeric primitives |
| SciPy | Interpolation, spatial algorithms, optimisation and scientific helpers |
| pandas | Default familiar tabular data adapter |
| Polars | Optional lazy/streaming large-data adapter |
| PyArrow | Columnar interchange and large datasets |
| DuckDB | Local analytical SQL over project data |
| Matplotlib | First static publication chart adapter; SVG/PDF path |
| Seaborn | Statistical presets over Matplotlib |
| plotnine | Grammar-of-graphics alternative |
| Altair + vl-convert-python | Preferred declarative second chart adapter |
| Plotly + Kaleido | Optional interactive/opaque adapter with local browser/runtime requirements |
| Bokeh | Optional browser-oriented interactive adapter |
| PyQtGraph | Fast live scientific plots in application tooling, not print authority |
| Datashader | Large-point-count rasterisation with disclosed resolution |
| NetworkX | Graph model and algorithms |
| rustworkx/python-igraph | High-performance graph algorithms |
| Graphviz | Local automatic graph layout and SVG/PDF generation |
| GeoPandas | Geographic feature tables |
| pyproj/Cartopy | Projection and publication map composition |
| Rasterio | Local geospatial raster data |

Matplotlib is the first planned chart adapter because it is local, mature and supports static
vector output. Altair is second because declarative specifications map well to visible Python and
`vl-convert-python` can render locally. Plotly/Bokeh remain optional because their export stacks
introduce browser/runtime complexity and may rasterise some content.

## Documents and editorial interchange

| Library/system | Preferred role | Fidelity boundary |
|---|---|---|
| python-docx | Read/write DOCX structure, styles, sections, tables and media | Not a Word pagination engine |
| Pandoc/pypandoc | Broad semantic document conversion and AST filters | External executable; layout is not retained exactly |
| Mammoth | DOCX to clean semantic HTML/content | Deliberately discards visual fidelity |
| markdown-it-py | Markdown token/AST input | Semantic content only |
| Jinja2 | Data-driven text and template generation | Output still enters normal authored source/content |
| lxml | OOXML, XML, HTML and structured content processing | Low-level adapter utility |
| docutils/Sphinx | reStructuredText and technical-document pipelines | Import/build adapter |
| LibreOffice UNO/headless | High-fidelity office conversion fallback | External heavyweight tool; never canonical layout |
| python-pptx | Presentation interchange | Best-effort structured import/export |
| openpyxl/XlsxWriter | Spreadsheet tables and data interchange | Cell data/styles, not spreadsheet application fidelity |
| pybtex/citeproc-py | Bibliography and CSL citation formatting | Semantic generated content |
| SymPy/MathJax/LaTeX/Typst | Equation source and vector/raster rendering | Preserve source and renderer/version metadata |

PyDesign owns story, paragraph, frame flow and pagination. Qt rich text may support the editing UI,
but it does not determine final glyph runs or line breaks.

## Layout and optimisation

| Library | Preferred role |
|---|---|
| kiwisolver | Interactive Cassowary-style geometric constraints |
| OR-Tools | Heavy combinatorial layout, packing and scheduling workers |
| rectpack | Contact-sheet and rectangle-packing heuristics |
| scipy.optimize | Numerical optimisation helpers |
| PuLP/Pyomo | Optional explicit mathematical programming adapters |
| SymPy | Symbolic expressions and geometry helpers |

Interactive dragging must not wait on general combinatorial optimisation. Heavy solvers produce
proposed layouts in cancellable workers and return explicit native geometry/constraints.

## Optional dependency groups

The target packaging shape, introduced only as capabilities land, is:

```toml
geometry = ["numpy", "shapely", "skia-pathops", "svgpathtools", "svgelements"]
images = ["Pillow", "pyvips", "scikit-image", "opencv-python-headless", "tifffile"]
colour = ["coloraide"]
charts = ["matplotlib", "pandas", "altair", "vl-convert-python"]
graphs = ["networkx", "graphviz", "rustworkx"]
documents = ["python-docx", "mammoth", "markdown-it-py", "Jinja2", "lxml"]
maps = ["geopandas", "cartopy", "pyproj", "rasterio"]
optimisation = ["kiwisolver", "ortools", "rectpack"]
```

These names describe ownership boundaries, not a requirement that each extra be installed as one
large set. Fine-grained extras or extension packages may be preferable when native dependencies are
large.

## Adapter contract

Each adapter declares:

- adapter ID, package and version;
- compatible PyDesign API/schema range;
- accepted inputs and produced boundary result type;
- fidelity level and known losses;
- deterministic/offline characteristics;
- worker, filesystem, process and native-code capabilities;
- licence and redistribution metadata;
- cache-key inputs;
- diagnostics and preflight checks;
- whether results can be edited, refreshed, frozen and baked.

Adapters receive explicit context and local resources. They do not import GUI modules. GUI-specific
panels communicate with adapters through typed core/runtime values.

## Admission checklist

A dependency is admitted only when a pull request includes:

- a user-visible vertical capability;
- a minimal adapter rather than leaked third-party types;
- deterministic fixtures and failure tests;
- headless and network-disabled verification where applicable;
- supported-platform installation evidence;
- dependency and licence records in `THIRD_PARTY.md`/release inventory;
- source, object and export provenance;
- fidelity/preflight diagnostics;
- documentation and an uninstall/missing-dependency experience;
- no weakening of the display-list, typography or PDF authority.

