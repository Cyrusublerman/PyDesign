"""Evaluation implementation used only inside the worker process."""

from __future__ import annotations

import contextlib
import importlib
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

from pydesign.context import BuildContext
from pydesign.layout import layout_document
from pydesign.model import Document
from pydesign.runtime.project import compute_project_revision, load_project_config


def evaluate_project(
    project_root: str | Path,
    *,
    profile: str | None = None,
) -> dict[str, object]:
    config = load_project_config(project_root)
    revision = compute_project_revision(config)
    selected_profile = profile or config.default_profile
    context = BuildContext(
        root=config.root,
        profile=selected_profile,
        deterministic=config.deterministic,
    )

    sys.path.insert(0, str(config.root))
    try:
        # Stdout is protocol-owned. User prints remain visible to the caller on stderr.
        with contextlib.redirect_stdout(sys.stderr):
            module = importlib.import_module(config.module_name)
            build_object = getattr(module, config.function_name, None)
            if not callable(build_object):
                raise TypeError(f"entrypoint {config.entrypoint!r} is not callable")
            build = cast(Callable[[BuildContext], object], build_object)
            result = build(context)
        if not isinstance(result, Document):
            raise TypeError(
                f"entrypoint {config.entrypoint!r} returned {type(result).__name__}, "
                "expected Document"
            )
        from pydesign.runtime.build_cache import BuildCache

        cache = BuildCache(config.root)
        cache_key = cache.key_for(
            relative_paths=tuple(
                path.relative_to(config.root).as_posix()
                for path in sorted(config.root.rglob("*.py"))
                if ".pydesign" not in path.parts
            ),
            salt=f"{revision}:{selected_profile}",
        )
        cached = cache.load_json(cache_key)
        if isinstance(cached, dict) and cached.get("revision") == revision:
            layout = cached.get("layout")
            diagnostics = cached.get("diagnostics")
            if isinstance(layout, dict) and isinstance(diagnostics, list):
                return {
                    "protocol_version": 1,
                    "ok": True,
                    "revision": revision,
                    "project": {
                        "id": config.project_id,
                        "name": config.name,
                        "root": str(config.root),
                        "entrypoint": config.entrypoint,
                        "profile": selected_profile,
                    },
                    "layout": layout,
                    "diagnostics": diagnostics,
                    "cache_hit": True,
                }
        snapshot = layout_document(result, revision=revision)
        payload = {
            "protocol_version": 1,
            "ok": True,
            "revision": revision,
            "project": {
                "id": config.project_id,
                "name": config.name,
                "root": str(config.root),
                "entrypoint": config.entrypoint,
                "profile": selected_profile,
            },
            "layout": snapshot.to_dict(),
            "diagnostics": [item.to_dict() for item in snapshot.diagnostics],
            "cache_hit": False,
        }
        cache.store_json(
            cache_key,
            {
                "revision": revision,
                "layout": payload["layout"],
                "diagnostics": payload["diagnostics"],
            },
        )
        return payload
    finally:
        if sys.path and sys.path[0] == str(config.root):
            sys.path.pop(0)
