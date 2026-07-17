"""Subprocess client for disposable evaluation workers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class WorkerProtocolError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    ok: bool
    response: dict[str, Any]
    stderr: str
    returncode: int

    @property
    def revision(self) -> str | None:
        value = self.response.get("revision")
        return value if isinstance(value, str) else None

    @property
    def layout(self) -> dict[str, Any] | None:
        value = self.response.get("layout")
        return value if isinstance(value, dict) else None

    @property
    def error_message(self) -> str | None:
        error = self.response.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            return message if isinstance(message, str) else str(error)
        return None


class WorkerClient:
    def __init__(self, *, python_executable: str | None = None) -> None:
        self.python_executable = python_executable or sys.executable

    def evaluate(
        self,
        project_root: str | Path,
        *,
        profile: str | None = None,
        timeout: float = 30.0,
    ) -> EvaluationResult:
        request = {
            "protocol_version": 1,
            "action": "evaluate",
            "project_root": str(Path(project_root).expanduser().resolve()),
            "profile": profile,
        }
        environment = os.environ.copy()
        process = subprocess.run(
            [self.python_executable, "-m", "pydesign.runtime.worker"],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=environment,
        )
        try:
            response = json.loads(process.stdout)
        except json.JSONDecodeError as error:
            raise WorkerProtocolError(
                f"worker returned invalid JSON (exit {process.returncode}): {process.stdout!r}; "
                f"stderr={process.stderr!r}"
            ) from error
        if not isinstance(response, dict) or response.get("protocol_version") != 1:
            raise WorkerProtocolError("worker returned an incompatible response")
        return EvaluationResult(
            ok=bool(response.get("ok")),
            response=response,
            stderr=process.stderr,
            returncode=process.returncode,
        )
