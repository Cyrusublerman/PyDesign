# PyDesign design baseline

Status: **locked for implementation**  
Baseline: **1.1**
Date: **2026-07-21**

This directory is the normative product and engineering design for PyDesign. It converts the research phase into testable contracts. Implementation may expose a false assumption, but code must not silently diverge from these documents.

## Authority order

When documents disagree, use this order:

1. this index and the decision register;
2. the domain specification that owns the subject;
3. the requirements traceability matrix;
4. the repository README;
5. research notes and examples.

Research explains why a direction was considered. This baseline states what will be built.

## Non-negotiable invariants

1. Authored document truth is visible Python source and project assets.
2. A GUI operation that changes the document commits an atomic, inspectable Python source transaction.
3. `.pydesign/` contains derived cache, recovery, proof and view state only; deleting it cannot change the designed document.
4. One layout result supplies both the interactive canvas and PDF renderer.
5. Text is shaped once into positioned glyph runs; renderers do not independently reflow it.
6. Page geometry uses physical units and deterministic ordering.
7. Authoring, preview, proofing and export work without a network connection.
8. The last successful preview remains usable when a newer revision fails.
9. User Python executes in a disposable worker, never in the GUI process.
10. Project files remain normal, diffable files that can be edited without PyDesign.
11. Procedural generators, parameters, seeds, exceptions and lifecycle state are visible authored
    source; generated output uses normal semantic/layout/display-list contracts.
12. Third-party libraries enter through declared adapters and cannot create independent canvas,
    typography or PDF authorities.

## Specification map

| Document | Owns |
|---|---|
| [00 — Decision register](00_decision_register.md) | Locked technology and policy decisions; change process |
| [01 — Product and workflows](01_product_scope_and_workflows.md) | Users, scope, workflows, capability boundaries |
| [02 — Project and Python authoring](02_project_format_and_python_authoring.md) | Multi-file format, source API, GUI-to-code editing, imports |
| [03 — Document model and commands](03_document_model_geometry_and_commands.md) | Objects, identity, geometry, constraints, history |
| [04 — Typography and text](04_typography_and_text_layout.md) | Unicode, shaping, composition, fonts, advanced typography |
| [05 — Graphics, images and colour](05_graphics_images_colour_and_assets.md) | Paths, painting, images, colour management, assets |
| [06 — Desktop UI and canvas](06_desktop_ui_canvas_and_accessibility.md) | Workspace, tools, inspector, feedback, accessibility |
| [07 — PDF and proofing](07_rendering_pdf_export_and_proofing.md) | Display list, export, standards, parity, preflight |
| [08 — Runtime and reliability](08_runtime_build_graph_security_and_recovery.md) | Processes, evaluation, incremental builds, recovery |
| [09 — Extensions and distribution](09_extensions_cli_packaging_and_licensing.md) | APIs, plug-ins, CLI, packaging, licence policy |
| [10 — Quality and acceptance](10_quality_performance_and_acceptance.md) | Tests, performance budgets, release gates |
| [11 — Implementation sequence](11_implementation_sequence.md) | Dependency-ordered slices and exit criteria |
| [12 — Procedural generation and data](12_procedural_generation_and_data.md) | Generators, parameters, seeds, creative API, data and variants |
| [13 — Library integration and interchange](13_library_integration_and_interchange.md) | Dependency classes, adapter boundaries and preferred ecosystems |
| [Requirements traceability](requirements_traceability.md) | Requirement-to-design-to-test mapping |

Execution state and dependency-ordered tasks live in the [delivery roadmap](../roadmap/README.md).
The roadmap may refine sequencing but cannot weaken this baseline.

## Normative language

“Must” is required for the baseline. “Should” is a strong default that may vary only with a recorded decision. “May” is optional. A “verification spike” tests how to implement a locked behaviour; it is not permission to change the product behaviour.

## Changing the baseline

A change requires an Architecture Decision Record in `docs/adr/`, updates to every affected specification and traceability row, and tests demonstrating the new contract. An ADR records context, decision, consequences, migration and superseded decisions. Product decisions do not live only in issues or source comments.
