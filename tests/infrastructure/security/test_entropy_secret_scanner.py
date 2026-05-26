import pytest

from universal_memory.domain.exceptions import SecretDetectedError
from universal_memory.domain.ports import SecretScannerPort
from universal_memory.infrastructure.security import EntropySecretScanner

HIGH_ENTROPY_THRESHOLD = 4.2


def assert_secret_is_not_exposed(error: SecretDetectedError, secret: str) -> None:
    public_values = [str(error), error.message, repr(getattr(error, "metadata", {}))]

    for public_value in public_values:
        assert secret not in public_value


@pytest.mark.parametrize(
    ("content", "secret", "expected_pattern"),
    [
        (
            "aws_access_key_id = AKIAIOSFODNN7EXAMPLE",
            "AKIAIOSFODNN7EXAMPLE",
            "aws_access_key",
        ),
        (
            "token = ghp_abcdefghijklmnopqrstuvwxyzABCDEF1234",
            "ghp_abcdefghijklmnopqrstuvwxyzABCDEF1234",
            "github_pat",
        ),
        (
            "Authorization: Bearer sk-abc1234567890SECRETtokenVALUE",
            "sk-abc1234567890SECRETtokenVALUE",
            "bearer_token",
        ),
        (
            "API_KEY=abc1234567890SECRETtokenVALUE",
            "abc1234567890SECRETtokenVALUE",
            "sensitive_assignment",
        ),
        (
            "SECRET=abc1234567890SECRETtokenVALUE",
            "abc1234567890SECRETtokenVALUE",
            "sensitive_assignment",
        ),
        (
            "TOKEN=abc1234567890SECRETtokenVALUE",
            "abc1234567890SECRETtokenVALUE",
            "sensitive_assignment",
        ),
        (
            "PASSWORD=abc1234567890SECRETtokenVALUE",
            "abc1234567890SECRETtokenVALUE",
            "sensitive_assignment",
        ),
    ],
)
def test_scanner_blocks_known_secret_patterns_without_exposing_values(
    content: str, secret: str, expected_pattern: str
) -> None:
    scanner = EntropySecretScanner()

    with pytest.raises(SecretDetectedError) as raised:
        scanner.scan(content, origin="unit-test")

    error = raised.value

    assert isinstance(scanner, SecretScannerPort)
    assert error.metadata["detection_type"] == "pattern"
    assert error.metadata["pattern"] == expected_pattern
    assert error.metadata["origin"] == "unit-test"
    assert "span" in error.metadata
    assert "Secret detected" in error.message
    assert_secret_is_not_exposed(error, secret)


def test_scanner_blocks_high_entropy_tokens_without_exposing_values() -> None:
    detected_value = "D8f9K2pQ7xZ4mN6vR1sT3yU5wA0bC"
    scanner = EntropySecretScanner(
        entropy_threshold=HIGH_ENTROPY_THRESHOLD,
        min_token_length=24,
    )

    with pytest.raises(SecretDetectedError) as raised:
        scanner.scan(f"opaque session token: {detected_value}")

    error = raised.value
    entropy = error.metadata["entropy"]

    assert error.metadata["detection_type"] == "entropy"
    assert error.metadata["pattern"] == "generic_high_entropy"
    assert isinstance(entropy, float)
    assert entropy > HIGH_ENTROPY_THRESHOLD
    assert_secret_is_not_exposed(error, detected_value)


@pytest.mark.parametrize(
    "content",
    [
        "request id 550e8400-e29b-41d4-a716-446655440000",
        "path: _bmad-output/implementation-artifacts/story.md",
        "commit facd129",
        "remember to update the local config file",
        "api key placeholder: your_api_key_here",
        "token placeholder: not-a-secret",
        "setting name: API_KEY_NAME",
    ],
)
def test_scanner_allows_common_non_secret_content(content: str) -> None:
    scanner = EntropySecretScanner()

    assert scanner.scan(content) is None


def test_scanner_handles_empty_content_as_safe() -> None:
    scanner = EntropySecretScanner()

    assert scanner.scan("") is None
