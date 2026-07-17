# 02 — Project format and Python authoring

## Source model

PyDesign projects are ordinary Python packages with a small declarative API and permission to use normal Python composition. Python source and referenced assets completely describe the authored document. There is no parallel scene file.

“All Python is visible” means all authored choices, generated exceptions and GUI changes are represented in the project’s source. It does not mean PyDesign’s library implementation or derived cache must be copied into every project.

## Default project structure

```text
my_publication/
├── project.toml
├── document.py
├── pages/
│   ├── __init__.py
│   ├── cover.py
│   ├── contents.py
│   └── feature.py
├── components/
│   ├── __init__.py
│   ├── folio.py
│   └── pull_quote.py
├── styles/
│   ├── __init__.py
│   ├── colour.py
│   └── typography.py
├── content/
├── assets/
├── fonts/
├── exports/
└── .pydesign/
    ├── cache/
    ├── recovery/
    ├── proof/
    └── view.json
```

Only `project.toml`, Python modules and user assets are authored truth. `exports/` is reproducible output. `.pydesign/` is disposable and normally ignored by version control, except a team may deliberately track a portable view preset separately.

## `project.toml`

The manifest contains portable build configuration, never element geometry.

```toml
[project]
format = 1
name = "My Publication"
entrypoint = "document:build"
default_profile = "print"

[python]
requires = ">=3.12"

[paths]
assets = ["assets", "content", "fonts"]
exports = "exports"

[colour]
working_rgb = "profiles/sRGB.icc"
working_cmyk = "profiles/FOGRA39.icc"
rendering_intent = "relative-colorimetric"

[build]
deterministic = true
allow_system_fonts = false

[profiles.screen]
kind = "pdf"
colour = "rgb"

[profiles.print]
kind = "pdf-x-4"
output_intent = "profiles/FOGRA39.icc"
bleed = "3mm"
```

Unknown keys are retained when the GUI edits the manifest. Format migrations are explicit commands that first create a backup and show a diff.

## Entrypoint and page order

`document.py` exposes a pure build function:

```python
from pydesign import Document, BuildContext
from pages import cover, contents, feature

def build(ctx: BuildContext) -> Document:
    return Document(
        id="publication",
        title="My Publication",
        pages=[
            cover.page(ctx),
            contents.page(ctx),
            *feature.pages(ctx),
        ],
    )
```

The order of this list is authoritative. A page module may return one page, a spread or a sequence. The GUI moves pages by editing this list or the owning data structure; it never relies on alphabetical filenames.

## Public authoring style

The API favours explicit constructors, typed quantities and keyword properties:

```python
from pydesign import Page, TextFrame, mm, pt

def page(ctx):
    return Page(
        id="contents",
        size=(210 * mm, 297 * mm),
        elements=[
            TextFrame(
                id="contents-title",
                frame=(18 * mm, 22 * mm, 174 * mm, 32 * mm),
                text="Contents",
                style="display",
                tracking=-8,
            )
        ],
    )
```

Constructors validate shape but do not perform layout. Values may be literals, named variables, expressions, loops, functions, comprehensions and imported data.

## Stable identity

- Every GUI-addressable document object has an `id` unique within the document.
- User-authored human-readable IDs are encouraged.
- GUI-created IDs are literal strings such as `pd_7k2m4z9q`.
- IDs do not encode page number, hierarchy or source line.
- Renaming an ID is a refactoring that updates source references transactionally.
- Duplicate IDs are evaluation errors with all declarations listed.

## Source ownership map

Evaluation instrumentation and LibCST analysis create a map from each semantic object/property to:

- module and source span;
- CST node kind;
- literal, name, expression, inherited, generated or derived ownership;
- dependency symbols and call stack frames relevant to the declaration;
- whether a safe automatic rewrite plan is available.

This map is revision-specific. A canvas action against a stale map is rejected and replanned against the current source.

## GUI-to-source transactions

Every document-changing gesture follows this protocol:

1. Capture the current project revision hash and selected stable IDs.
2. Calculate the intended semantic delta in evaluated units.
3. Resolve property ownership and produce one or more candidate source edit plans.
4. If exactly one non-destructive plan exists, preview it in the inspector/source gutter.
5. If meaning changes, ask the user to choose among explicit plans.
6. Apply all file patches in memory, parse them and reject if syntax is invalid.
7. Write the affected files with atomic replace.
8. Record old/new bytes, semantic intent and selection as one history command.
9. Evaluate a new revision.

No partial multi-file source transaction may reach disk.

## Rewrite rules by source form

| Source form | Default GUI behaviour |
|---|---|
| Numeric or quantity literal | Replace only the literal, preserving units and formatting where possible. |
| Tuple/list of literals | Replace affected elements without reformatting siblings. |
| Named constant in the same project | Offer “edit shared value” and list all dependants. |
| Arithmetic expression | Offer visible additive adjustment, edit a named input, or detach to evaluated literal. |
| Function/component argument | Edit the call argument when that instance is uniquely owned. |
| Loop-generated object | Offer edit collection/input, add an explicit ID-keyed exception, or detach the instance. |
| Inherited style value | Offer edit style (show scope) or add an explicit instance property. |
| Constraint-derived value | Edit the owning constraint/input; direct replacement is unavailable until detached. |
| Read-only imported package | Create a visible local wrapper/adjustment; never modify site packages. |

Visible adjustment example:

```python
base_x = column(2)

TextFrame(
    id="pull-quote",
    x=base_x + 3.5 * mm,  # GUI adjustment remains visible Python
    ...
)
```

Generated exception example:

```python
adjustments = {
    "entry-07": dict(y=2 * mm, rotation=1.5),
}

elements = [
    make_entry(item, **adjustments.get(item.id, {}))
    for item in data
]
```

## Creating source from tools

- A new object is inserted into the current page’s declared element collection.
- If no writable collection can be resolved, PyDesign offers to create a local `elements` list and splice it into the page.
- Source templates are simple, documented Python and pass the project formatter.
- Creation commits only after the gesture completes; cancelled drawing creates no source.
- A tool may generate helper variables when repeated values or complex path data would otherwise harm readability.

## Code formatting and comments

LibCST preserves comments and formatting around changed nodes. PyDesign does not format entire files after a GUI operation. A separate explicit “Format project” action uses Ruff format with a preview. Generated blocks include a lightweight marker comment only where it improves future placement; markers are hints, not identity or truth.

## File operations

- Creating a page writes the module, updates `__init__.py` only if needed and updates `document.py` atomically.
- Rename/move uses LibCST import updates and filesystem changes in one recoverable transaction.
- Delete defaults to removing the document reference and moving the module to the operating system trash when it has no remaining references.
- Asset paths are project-relative `pathlib.Path` values resolved by `BuildContext`.
- Symlinks are allowed but packaging resolves and reports them.

## Text and external content

Long editorial content may remain in UTF-8 Markdown, plain text, JSON, CSV or project Python. Parsers return semantic spans and source locations so text diagnostics can link back to content. Imported content is immutable during layout unless the user explicitly opens and edits the source file.

## Determinism

In deterministic mode the build context fixes locale, timezone, random seed, page order and metadata timestamps. Network APIs are unavailable by policy, directory iteration must be explicitly sorted, and volatile calls produce diagnostics. A build manifest records Python, PyDesign, dependency, font and asset fingerprints.

