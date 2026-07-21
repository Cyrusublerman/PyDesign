# 09 — Extensions, CLI, packaging and licensing

## Core package boundaries

```text
pydesign.model       semantic objects, units, styles and validation
pydesign.text        Unicode, shaping and composition
pydesign.layout      constraints, frames, pages and display-list creation
pydesign.graphics    paths, paints, colour and effects
pydesign.assets      fonts, images, profiles and fingerprints
pydesign.pdf         PDF adapter, profiles and preflight
pydesign.runtime     workers, protocol, graph, cache and builds
pydesign.source      source maps and LibCST transactions
pydesign.procedural  generators, parameters, deterministic random and lifecycle values
pydesign.adapters    optional typed data/chart/document/format family adapters
pydesign.cli         headless commands
pydesign.gui         Qt application and adapters
```

Core/headless modules do not import PySide6. GUI code consumes public core protocols. Internal packages remain `_internal` and have no compatibility promise.

## Python API principles

- typed, explicit immutable value objects;
- keyword-only configuration after essential identity/content arguments;
- no global current canvas/document state;
- normal context managers only for scoped graphics helpers, never hidden ownership;
- deterministic iteration/order;
- useful `repr`, source locations and validation errors;
- semantic constructors separate from layout results;
- deprecations last at least one minor release and include automated migration where practical.

The public authoring API is documented with executable offline examples. The display-list and worker protocols are versioned separately from the Python API.

## Extension model

Installed extensions register Python entry points under versioned groups:

- `pydesign.importers` and `pydesign.exporters`;
- `pydesign.effects`;
- `pydesign.preflight_checks`;
- `pydesign.panels` and `pydesign.tools`;
- `pydesign.templates`;
- `pydesign.cli_commands`.

Each extension declares package/version, PyDesign API range, capabilities, deterministic/offline characteristics, added dependencies and licence. Incompatible extensions are disabled with diagnostics before import.

Library admission, adapter fidelity levels and preferred integration families follow Specification
13. An extension may cross into the canonical document only as native semantic values, structured
text/data, parsed SVG, placed PDF or a colour-managed raster asset. A panel-only drawing surface is
not a document integration.

Project-local modules are the preferred extension mechanism for document components and generators. They need no special registration unless adding application UI/import/export behaviour.

## Extension trust and isolation

Extensions are Python code with user privileges. Document/build extensions load in evaluation/service workers where possible. GUI panel/tool extensions necessarily load in the GUI process and therefore require explicit enablement. A capability declaration is informative and enforceable where practical; it is not presented as a sandbox.

There is no built-in remote marketplace in 1.x. Installation is from explicit local packages/wheelhouses or normal Python tooling initiated by the user.

## CLI

The `pydesign` executable exposes:

```text
pydesign open PROJECT
pydesign check PROJECT [--profile NAME]
pydesign build PROJECT [--profile NAME] [--output PATH]
pydesign proof PROJECT [--profile NAME] [--dpi N]
pydesign package PROJECT --output DIRECTORY
pydesign migrate PROJECT [--to FORMAT]
pydesign env inspect PROJECT
pydesign cache inspect|clear PROJECT
```

Commands use the same runtime, profiles and diagnostics as the GUI. Human output is concise; `--json` emits a versioned schema. Exit codes distinguish success, warnings-as-errors, source/evaluation failure, preflight failure, export failure and internal error. No command starts a GUI unless `open` is used.

## Reproducible environments

PyDesign records direct project dependencies and a lock file when external packages are needed. The exact installer is an adapter; the baseline supports standard `pyproject.toml` and offline wheels. Core project source does not require a virtual environment when it uses only bundled PyDesign APIs.

Build manifests record interpreter, platform class, PyDesign version and every loaded distribution. Plug-in/module code used by the build is fingerprinted.

## Desktop packaging

Official builds package Python, PySide6/Qt, native text/colour libraries, Poppler proof tools, dictionaries, local help and validator components permitted for redistribution. Targets are:

- Windows signed installer and portable/test archive;
- macOS signed/notarised universal or per-architecture app bundle;
- Linux AppImage and distribution-friendly package metadata.

Platform packaging must not download runtime dependencies on first launch. Native components and licences are included in an About/Licences view and distribution directory.

## Updates

The application works indefinitely without checking for updates. Optional update checks are disabled by default, clearly network-labelled and can download only after confirmation. Offline update packages are supported and signature-verified before installation. Project format migration remains separate from app installation.

## Versioning

PyDesign follows semantic versioning once the public API reaches 1.0. Project format, display-list schema, IPC protocol and plug-in API each have explicit integer/semantic versions. Reading older projects is supported through migration; writing an older format is not promised. A newer unsupported project opens source-only rather than being mutated.

## Licence policy

- PyDesign source is licensed under MPL-2.0 from the first code-bearing release.
- User projects and exported artefacts receive no licence claim from PyDesign.
- Bundled examples/assets/fonts state their own licences.
- Dependencies must permit the chosen distribution model and offline bundling.
- Strong-copyleft reference code is not copied into core unless the whole affected distribution decision is deliberately revisited.
- No-licence repositories are idea/reference only; their code is not copied.
- Reuse records capture origin, file, licence, adaptation and notices.

An SPDX manifest and third-party notices are generated for each release. Automated dependency scans assist but do not replace review of unusual font/data/native-tool terms.

## Contribution and repository policy

The repository requires formatting, typing, tests, changelog fragment for user-visible changes and an ADR for baseline changes. Generated/vendor files are identified. Commits must not include proprietary test fonts or reference images. Security-sensitive reports use a private disclosure address once established.

## Data portability

A valid project can be built from the command line without user preferences/database state. Package-for-output captures all lawful dependencies. Settings have documented text formats and migrations. Users can uninstall PyDesign without losing the ability to read their source/assets.
