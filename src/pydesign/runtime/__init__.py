"""Project evaluation runtime.

The GUI imports only the client. User projects are imported by ``pydesign.runtime.worker``
in a disposable subprocess.
"""

from pydesign.runtime.client import EvaluationResult, WorkerClient
from pydesign.runtime.project import ProjectConfig, load_project_config
from pydesign.runtime.project_files import (
    PackageResult,
    ProjectOperationError,
    UnsafeProjectLocationError,
    create_project,
    duplicate_project,
    ensure_safe_project_destination,
    find_pydesign_source_checkout,
    is_bundled_example,
    package_project,
)
from pydesign.runtime.recovery import RecoverySnapshot, RecoveryStore

__all__ = [
    "EvaluationResult",
    "PackageResult",
    "ProjectConfig",
    "ProjectOperationError",
    "RecoverySnapshot",
    "RecoveryStore",
    "UnsafeProjectLocationError",
    "WorkerClient",
    "create_project",
    "duplicate_project",
    "ensure_safe_project_destination",
    "find_pydesign_source_checkout",
    "is_bundled_example",
    "load_project_config",
    "package_project",
]
