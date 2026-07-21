# PyDesign

PyDesign is an entirely offline, Python-native editorial layout studio being designed for professional typography, computational composition and deterministic PDF production.

The product combines:

- an IDE-style Python source editor;
- a zoomable page and spread canvas;
- direct manipulation that creates inspectable Python source transactions;
- professional typography, grids, guides, pages, layers, vector paths and colour;
- deterministic PDF/PDF/X export and locally rendered proofing.

## Status

The implementation-grade design baseline is locked. The repository contains the Stage 0/1 vertical slice, a substantial visible-source Stage 2 foundation, Stage 3 typography authority modules and the first parity-gated Stage 4 vector PDF slice. Canvas geometry, rectangle/Bézier creation and cubic control-point edits produce readable Python transactions; exact OpenType identities, fallback choices, glyph runs and story source ranges are independently auditable.

Read the [complete design baseline](docs/design/README.md), [decision register](docs/design/00_decision_register.md), [requirements traceability](docs/design/requirements_traceability.md), [implementation sequence](docs/design/11_implementation_sequence.md) and [delivery roadmap](docs/roadmap/README.md).

The [modularity assessment](docs/modularity_assessment.md) records current boundaries, hotspots and enforced dependency rules.

See [implementation status](docs/implementation_status.md) for the exact completed/staged capability boundary.
Baseline 1.1 adds native procedural/data authoring and library-admission contracts on top of the
recorded Stage 0–8 implementation exits. The roadmap distinguishes existing work that needs
conformance evidence from genuinely new generator, data and procedural-GUI work.

## Locked direction

- CPython 3.12+ and PySide6/Qt Widgets;
- visible multi-file Python projects;
- LibCST-backed GUI-to-source transactions;
- retained semantic model and immutable shared layout/display list;
- isolated local evaluation workers;
- ICU, HarfBuzz, FreeType, FontTools and Pyphen typography under a PyDesign paragraph composer;
- a project-owned PDF adapter, initially using ReportLab with pikepdf inspection;
- Poppler-based local PDF proofing and comparison.

Verification spikes may replace an implementation adapter, but may not weaken the locked source, layout, typography or export contracts without an Architecture Decision Record.

## Product principles

- Authored document truth is visible Python source and project assets.
- GUI edits never silently destroy expressions or hide canonical overrides.
- Every editable property exposes its source form, owner, inheritance and derivation.
- One positioned layout result feeds both canvas and PDF.
- Failed/cancelled rendering never blocks source editing or destroys the last good preview.
- Authoring, local help, proofing and export work without network access.
- Accessibility and keyboard operation are designed into each vertical slice.

## Setup from source

### Requirements

- Windows, macOS or a mainstream Linux distribution;
- CPython 3.12 or newer (`python --version`);
- Git for a source checkout;
- a terminal with `python` and `pip` available.

PyDesign itself works offline after installation. Network access is only needed to clone the
repository and initially obtain dependencies unless an offline wheelhouse is used.

Platform prerequisites for the complete source-development stack:

- **Ubuntu/Debian:** `sudo apt-get update && sudo apt-get install -y git libegl1 libicu-dev pkg-config poppler-utils fonts-dejavu-core build-essential`
- **macOS with Homebrew:** install the Xcode command-line tools, then run
  `brew install python@3.12 git pkg-config icu4c poppler`. Because Homebrew's ICU is keg-only,
  add `$(brew --prefix icu4c)/bin` to `PATH` and
  `$(brew --prefix icu4c)/lib/pkgconfig` to `PKG_CONFIG_PATH` before installing `.[unicode]`.
- **Windows:** install 64-bit CPython 3.12+ and Git, select **Add Python to PATH**, and use the
  PowerShell commands below. The core, GUI, typography and PDF extras install from Python wheels.
  The optional PyICU source build additionally requires a compatible C++ toolchain and ICU SDK;
  confirm `pkg-config --cflags --libs icu-i18n` before installing `.[unicode]`.

PyICU is a C++ extension over the system ICU libraries, so a source installation requires both
ICU headers and `pkg-config`; this is why Unicode installation is kept as an explicit step. See
the [PyICU installation documentation](https://pyicu.org/) when the platform cannot use a wheel.
PySide6 itself is installed through the `gui` extra following the normal
[Qt for Python installation model](https://doc.qt.io/qtforpython-6/gettingstarted.html).
If the interpreter is exposed as `python3.12` or `py -3.12`, substitute that command for `python`
throughout the instructions.

### Clone and create an isolated environment

```bash
git clone https://github.com/Cyrusublerman/PyDesign.git
cd PyDesign
python -m venv .venv
```

Activate the environment on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it in Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Upgrade packaging tools and install the complete currently supported development stack:

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[gui,typography,pdf,dev]'
```

The optional `unicode` extra builds PyICU and therefore also needs ICU development files and
platform build tools. Install those through the operating system, then run:

```bash
python -m pip install -e '.[unicode]'
```

Poppler is not required by the current vector PDF slice. It is the locked local proofing and
visual-comparison backend for the later proofing stage and will be documented as a release
dependency when that stage ships.

### Verify the installation

```bash
pydesign check examples/hello_editorial
pydesign render-json examples/hello_editorial --output /tmp/hello-layout.json
ruff check .
mypy
pytest
python scripts/check_architecture.py
python scripts/check_roadmap.py
```

On Windows, replace `/tmp/hello-layout.json` with a writable path such as
`$env:TEMP\hello-layout.json`.

## User projects are portable folders

A PyDesign project functions as the application's save document, but remains an ordinary open
folder. `project.toml` identifies the folder; visible Python, content and project assets contain
the authored truth. The complete folder can be moved, copied, backed up or shared and then opened
from its new location.

User projects should live outside this source repository. The desktop application defaults to the
operating system's Documents directory under `PyDesign Projects`. Project creation refuses a
destination inside the PyDesign source checkout unless the CLI's explicit development override is
provided. PyDesign never initialises Git or syncs a user project automatically.

Create and open a project from the command line:

```bash
pydesign new "$HOME/Documents/PyDesign Projects/My Magazine"
pydesign open "$HOME/Documents/PyDesign Projects/My Magazine"
```

On Windows PowerShell, a typical destination is:

```powershell
pydesign new "$HOME\Documents\PyDesign Projects\My Magazine"
pydesign open "$HOME\Documents\PyDesign Projects\My Magazine"
```

The desktop **File** menu provides New Project, Open Project, Open Recent, Save Project As,
Duplicate Project and Package Project. Save As opens the independent copy; Duplicate leaves the
current project open. Copies receive a new project identity and omit caches, recovery data,
exports, build output, virtual environments and version-control internals.

The projects in `examples/` are tracked executable documentation, not a location for user work.
When one is opened in the desktop application, PyDesign offers to create an editable external copy.
For temporary source-development projects only, `/projects/` and `/user-projects/` are ignored by
this repository; creation there still requires an explicit safety override:

```bash
pydesign new user-projects/Local-Test --allow-in-source-checkout
```

## Project validation, output and packaging

Evaluate an arbitrary project folder without opening the GUI:

```bash
pydesign check "/path/to/My Magazine"
pydesign render-json "/path/to/My Magazine" --output /tmp/my-layout.json
```

Install the first vector PDF adapter and build supported vector-only projects:

```bash
python -m pip install -e '.[pdf]'
pydesign build-pdf "/path/to/vector-project" --output /tmp/publication.pdf
```

`build-pdf` writes a deterministic PDF plus a SHA-256 manifest, reopens page geometry with
pikepdf and publishes atomically after validation. It refuses placeholder text until the shared
shaped-glyph embedding path is complete.

Create a deterministic, portable ZIP only after the project evaluates successfully:

```bash
pydesign package "/path/to/My Magazine" --output "/path/to/My Magazine-package.zip"
```

The package contains authored source and project-local assets plus `package-manifest.json` with
file sizes and SHA-256 hashes. It excludes `.pydesign/`, `build/`, `exports/`, virtual environments,
Git metadata and caches. Symbolic links are rejected because they cannot guarantee a self-contained
package. Font and asset redistribution remains subject to the resource licences.

## Feature-specific installation

Install only the headless project/source core:

```bash
python -m pip install -e .
```

Install the desktop shell:

```bash
python -m pip install -e '.[gui]'
pydesign open
```

Install the typography authority stack and inspect or shape a font:

```bash
python -m pip install -e '.[typography]'
pydesign font-info /path/to/font.otf
pydesign shape-text /path/to/font.otf 'office سلام' --size 12 --language en
```

Explicit font registration, cluster-safe fallback, greedy composition, columns, linked frames and
overset tracking exist as renderer-neutral APIs. Full bidi itemisation, optimised justification,
fallback-aware paragraph composition and outline canvas/PDF painting remain staged work.

The desktop shell currently provides a multi-file Python sidebar/editor, isolated Run/Stop
evaluation, last-good preview, page canvas selection, dragging and resize, a geometry/source
inspector, reveal-in-Python, rectangle and four-point cubic Bézier drawing/editing, source-aware
expression choices, undo/redo, autosave recovery and persistent transaction crash recovery.

## Troubleshooting and maintenance

- **`pydesign` is not found:** activate `.venv` and repeat the editable install.
- **Qt cannot load a platform plug-in:** reinstall the `gui` extra in the active environment and
  check that the host's desktop/OpenGL libraries are available.
- **PyICU fails to build:** install ICU headers, a compiler and `pkg-config`, then retry the
  `unicode` extra. The rest of PyDesign can be used without this optional extra.
- **A PDF dependency is unavailable:** install `.[pdf]`; the core and GUI deliberately do not load
  PDF dependencies at startup.
- **A project will not open:** select the folder containing `project.toml`, then run
  `pydesign check /path/to/project` for structured diagnostics.
- **A bundled example should be edited:** create the copy offered by the GUI or run
  `pydesign duplicate examples/hello_editorial /external/path/Hello-Editorial`.

Update an editable checkout:

```bash
git pull --ff-only
python -m pip install -e '.[gui,typography,pdf,dev]'
```

Remove the editable installation without deleting user projects:

```bash
python -m pip uninstall pydesign
```

## Implementation sequence

1. Repository/tooling and architecture guardrails.
2. Headless source-to-page model and serializable display list.
3. PySide6 code/canvas shell with isolated evaluation.
4. LibCST-backed visible GUI edits and recovery (foundation implemented).
5. Typography authority and identical glyph-run rendering (font/shaping foundation implemented).
6. PDF parity and Poppler proofing.
7. Editorial layout, advanced graphics/colour and print production.

## Repository policy

Research and project knowledge are maintained in the associated PKL repository. Normative implementation design is versioned here beside source, tests, fixtures, packaging and developer documentation.

The design baseline selects MPL-2.0 for PyDesign source; the licence file and third-party notices are Stage 0 deliverables.
