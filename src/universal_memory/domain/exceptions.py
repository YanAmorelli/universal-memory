class UniversalMemoryError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class SecretDetectedError(UniversalMemoryError):
    pass


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
