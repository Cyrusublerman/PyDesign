"""Qt process adapter for isolated project evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal


class EvaluationController(QObject):
    finished = Signal(object, str)
    protocol_error = Signal(str)
    process_error = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._process: QProcess | None = None

    @property
    def running(self) -> bool:
        return (
            self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning
        )

    def start(self, project_root: Path) -> bool:
        self.stop()
        request = {
            "protocol_version": 1,
            "action": "evaluate",
            "project_root": str(project_root),
            "profile": None,
        }
        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments(["-m", "pydesign.runtime.worker"])
        process.finished.connect(self._finished)
        process.errorOccurred.connect(self._errored)
        self._process = process
        process.start()
        if not process.waitForStarted(1500):
            self.process_error.emit(process.errorString())
            self._process = None
            return False
        process.write(json.dumps(request).encode("utf-8"))
        process.closeWriteChannel()
        return True

    def stop(self) -> bool:
        process = self._process
        if process is not None and process.state() != QProcess.ProcessState.NotRunning:
            process.kill()
            process.waitForFinished(1000)
            was_running = True
        else:
            was_running = False
        self._process = None
        return was_running

    def _finished(self, _exit_code: int, _status: QProcess.ExitStatus) -> None:
        process = self.sender()
        if not isinstance(process, QProcess):
            return
        stdout = bytes(process.readAllStandardOutput().data()).decode("utf-8", errors="replace")
        stderr = bytes(process.readAllStandardError().data()).decode("utf-8", errors="replace")
        self._process = None
        try:
            response = json.loads(stdout)
        except json.JSONDecodeError:
            self.protocol_error.emit(f"Worker protocol error\n{stdout}\n{stderr}")
            return
        if not isinstance(response, dict):
            self.protocol_error.emit(f"Worker returned a non-object response\n{stdout}\n{stderr}")
            return
        self.finished.emit(response, stderr)

    def _errored(self, _error: QProcess.ProcessError) -> None:
        process = self._process
        self.process_error.emit(process.errorString() if process is not None else "process error")
