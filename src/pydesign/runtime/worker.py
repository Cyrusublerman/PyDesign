"""Disposable JSON-over-stdio project evaluation worker."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from pydesign.runtime.evaluate import evaluate_project


def handle_request(request: dict[str, Any]) -> dict[str, object]:
    if request.get("protocol_version") != 1:
        raise ValueError("unsupported worker protocol version")
    if request.get("action") != "evaluate":
        raise ValueError("unsupported worker action")
    project_root = request.get("project_root")
    if not isinstance(project_root, str) or not project_root:
        raise ValueError("project_root must be a non-empty string")
    profile = request.get("profile")
    if profile is not None and not isinstance(profile, str):
        raise ValueError("profile must be a string or null")
    return evaluate_project(project_root, profile=profile)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("worker request must be a JSON object")
        response = handle_request(payload)
    except BaseException as error:  # The worker must always return a protocol response.
        response = {
            "protocol_version": 1,
            "ok": False,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            },
            "diagnostics": [
                {
                    "code": "PD-RUN-001",
                    "severity": "error",
                    "message": str(error),
                    "object_id": None,
                    "page_id": None,
                    "source": None,
                }
            ],
        }
    json.dump(response, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0 if response.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
