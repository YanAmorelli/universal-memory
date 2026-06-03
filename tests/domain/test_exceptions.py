import pytest

from universal_memory.domain.exceptions import (
    FactNotFoundError,
    InvalidConfigError,
    SecretDetectedError,
    SnapshotFailedError,
    StorageError,
    UniversalMemoryError,
    ValidationFailedError,
)


@pytest.mark.parametrize(
    "error_type",
    [
        SecretDetectedError,
        SnapshotFailedError,
        ValidationFailedError,
        FactNotFoundError,
        InvalidConfigError,
        StorageError,
    ],
)
def test_domain_errors_share_base_class_and_detailed_message(
    error_type: type[UniversalMemoryError],
) -> None:
    error = error_type("detailed message")

    assert isinstance(error, UniversalMemoryError)
    assert str(error) == "detailed message"
    assert error.message == "detailed message"


def test_base_domain_error_requires_detailed_message() -> None:
    error = UniversalMemoryError("known failure")

    assert str(error) == "known failure"
    assert error.message == "known failure"
