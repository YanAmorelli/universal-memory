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
