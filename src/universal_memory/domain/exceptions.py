import time
from pathlib import Path


class UniversalMemoryError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class SecretDetectedError(UniversalMemoryError):
    """Raised when a secret is detected in the input content.

    WARNING: The metadata dict contains a 'span' key indicating the start and end
    position of the detected secret. Downstream consumers (adapters, CLI, MCP) MUST
    NEVER use this span to extract and display or log the raw sensitive substring.
    """

    def __init__(self, message: str, metadata: dict[str, object] | None = None) -> None:
        self.metadata = metadata or {}
        super().__init__(message)


class SnapshotFailedError(UniversalMemoryError):
    pass


class ValidationFailedError(UniversalMemoryError):
    pass


class FactNotFoundError(UniversalMemoryError):
    pass


class InvalidConfigError(UniversalMemoryError):
    pass


class StorageError(UniversalMemoryError):
    pass


class ProjectNotInitializedError(ValidationFailedError):
    def __init__(self, memory_root: Path) -> None:
        self.memory_root = str(memory_root)
        super().__init__(
            "Project memory is not initialized. "
            "Hint: Ask the person whether to initialize, then run `umem init`."
        )


class LockAcquisitionError(StorageError):
    def __init__(
        self, message: str, *, path: Path | None = None, unknown_owner: bool = False
    ) -> None:
        self.lock_path = str(path) if path is not None else None
        self.lock_age_seconds: float | None = None
        if path is not None:
            try:
                self.lock_age_seconds = round(time.time() - path.stat().st_mtime, 3)
            except OSError:
                pass
        self.recovery_hint = (
            "Stop all CLI/MCP writers, including old and suspended sessions; back up storage. "
            "After confirming no writer owns this lock, quarantine only the indicated .lock "
            "file and retry. Never remove or replace its .guard sidecar. Age does not prove "
            "owner death; a negative age can be the compatibility timestamp."
            if unknown_owner
            else "Wait for the writer and retry. If acquisition still fails, check filesystem "
            "permissions and hard-link/timestamp support. Never remove a live lock or its .guard."
        )
        super().__init__(message + (f" at {path}" if path is not None else ""))
