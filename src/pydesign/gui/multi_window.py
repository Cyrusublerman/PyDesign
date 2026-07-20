"""Secondary MainWindow instances for multi-window mode."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydesign.gui.settings import ApplicationSettings

_WindowFactory = Callable[..., Any]
_factory: _WindowFactory | None = None
_EXTRA_WINDOWS: list[Any] = []


def configure(factory: _WindowFactory) -> None:
    global _factory
    _factory = factory


def open_additional_window(
    project: Path | None = None, *, settings: ApplicationSettings | None = None
) -> Any:
    """Open another main window sharing application settings."""
    if _factory is None:
        raise RuntimeError("multi-window factory is not configured")
    window = _factory(project, settings=settings or ApplicationSettings())
    window.setWindowTitle(f"{window.windowTitle()} — Window {len(_EXTRA_WINDOWS) + 2}")
    _EXTRA_WINDOWS.append(window)
    window.destroyed.connect(lambda *_: _forget_window(window))
    window.show()
    window.raise_()
    window.activateWindow()
    return window


def _forget_window(window: Any) -> None:
    if window in _EXTRA_WINDOWS:
        _EXTRA_WINDOWS.remove(window)
