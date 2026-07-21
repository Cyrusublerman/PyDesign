# Contributing to PyDesign

PyDesign is design-baseline driven. Read `docs/design/README.md` before changing public behaviour.

## Development setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev,gui]'
python -m pytest
ruff check .
mypy
python scripts/check_architecture.py
python scripts/check_roadmap.py
```

The core and tests must also run without the GUI extra:

```bash
python -m pip install -e '.[dev]'
python -m pytest
```

## Change requirements

- Add tests for behaviour and regressions.
- Keep `pydesign.gui` out of core imports.
- Add a changelog entry for user-visible changes.
- Add an ADR and update traceability when changing the locked baseline.
- Update `docs/roadmap/backlog.toml` and `docs/implementation_status.md` for completed roadmap tasks.
- Do not add proprietary fonts, images or documents to fixtures.
- Record copied/adapted code and its licence in `THIRD_PARTY.md`.

## Commit and review checklist

1. Format and lint.
2. Run typing and tests.
3. Exercise headless evaluation with the example project.
4. Verify the application still works with network unavailable.
5. Confirm source transactions, output and recovery remain deterministic.
