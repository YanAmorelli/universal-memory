from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from universal_memory.domain import (
    FactNotFoundError,
    InvalidConfigError,
    SecretDetectedError,
    SnapshotFailedError,
    StorageError,
    UniversalMemoryError,
    ValidationFailedError,
)

JSON_RPC_SECRET_DETECTED = -32010
JSON_RPC_SNAPSHOT_FAILED = -32020
JSON_RPC_VALIDATION_FAILED = -32602
JSON_RPC_FACT_NOT_FOUND = -32040
JSON_RPC_INVALID_CONFIG = -32050
JSON_RPC_STORAGE_ERROR = -32060
JSON_RPC_UNEXPECTED_ERROR = -32603

DOMAIN_ERROR_TYPES = (
    SecretDetectedError,
    SnapshotFailedError,
    ValidationFailedError,
    FactNotFoundError,
    InvalidConfigError,
    StorageError,
)

_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{6,}\b"),
    re.compile(r"\b[A-Za-z0-9_]*api[_-]?key[A-Za-z0-9_]*\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9_]*token[A-Za-z0-9_]*\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
)
_UNIX_ABSOLUTE_PATH = re.compile(r"(?<![\w.-])/(?:[^/\s:]+/)+[^/\s:]+")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"(?<![\w.-])(?:[a-zA-Z]:\\|\\\\)(?:[^\\\s:]+\\)+[^\\\s:]+")


@dataclass(frozen=True, slots=True)
class ErrorDescriptor:
    slug: str
    json_rpc_code: int
    cli_message: str
    mcp_message: str
    recovery_hint: str


def error_descriptor(error: Exception) -> ErrorDescriptor:
    mappings: tuple[tuple[type[Exception] | tuple[type[Exception], ...], ErrorDescriptor], ...] = (
        (
            SecretDetectedError,
            ErrorDescriptor(
                "secret_detected",
                JSON_RPC_SECRET_DETECTED,
                "Sensitive content blocked.",
                "Sensitive content blocked.",
                "Remove or mask sensitive values before retrying.",
            ),
        ),
        (
            SnapshotFailedError,
            ErrorDescriptor(
                "snapshot_failed",
                JSON_RPC_SNAPSHOT_FAILED,
                "Snapshot failed.",
                "Snapshot failed.",
                "Run a safe mutation before retrying rollback, or check the scope.",
            ),
        ),
        (
            (ValidationError, ValidationFailedError),
            ErrorDescriptor(
                "validation_failed",
                JSON_RPC_VALIDATION_FAILED,
                "Validation failed.",
                "Validation failed.",
                "Fix the invalid input data.",
            ),
        ),
        (
            FactNotFoundError,
            ErrorDescriptor(
                "fact_not_found",
                JSON_RPC_FACT_NOT_FOUND,
                "Fact not found.",
                "Fact not found.",
                "Check the provided identifier or scope.",
            ),
        ),
        (
            InvalidConfigError,
            ErrorDescriptor(
                "invalid_config",
                JSON_RPC_INVALID_CONFIG,
                "Invalid configuration.",
                "Invalid configuration.",
                "Check the settings in config.toml.",
            ),
        ),
        (
            StorageError,
            ErrorDescriptor(
                "storage_error",
                JSON_RPC_STORAGE_ERROR,
                "Storage error.",
                "Storage error.",
                "Check the local layout and run umem init at the project root.",
            ),
        ),
    )
    return next(
        (descriptor for error_type, descriptor in mappings if isinstance(error, error_type)),
        ErrorDescriptor(
            "unexpected_error",
            JSON_RPC_UNEXPECTED_ERROR,
            "Unexpected error.",
            "Unexpected error.",
            "Try again. If the problem persists, check the diagnostic logs.",
        ),
    )


def recovery_hint(error: Exception) -> str:
    if isinstance(error, SecretDetectedError):
        return error_descriptor(error).recovery_hint
    message = str(error)
    if "Hint: " in message:
        return sanitize_error_detail(message.split("Hint: ", 1)[1])
    return error_descriptor(error).recovery_hint


def _recovery_hint_for_locale(error: Exception, *, message_locale: str) -> str:
    hint = recovery_hint(error)
    return hint


def sanitize_error_detail(error_or_detail: Exception | str, *, max_length: int = 240) -> str:
    if isinstance(error_or_detail, SecretDetectedError):
        return "Sensitive content was detected and blocked."
    if isinstance(error_or_detail, Exception):
        if not _is_expected_error(error_or_detail):
            return "Unexpected error."
        detail = (
            getattr(error_or_detail, "message", None) or str(error_or_detail)
            if isinstance(error_or_detail, UniversalMemoryError)
            else str(error_or_detail)
        )
    else:
        detail = error_or_detail

    detail = _UNIX_ABSOLUTE_PATH.sub("<path>", detail)
    detail = _WINDOWS_ABSOLUTE_PATH.sub("<path>", detail)
    for pattern in _SECRET_PATTERNS:
        detail = pattern.sub("<secret>", detail)
    return detail[:max_length]


def error_payload(error: Exception, *, message_locale: str) -> dict[str, Any]:
    descriptor = error_descriptor(error)
    return {
        "code": descriptor.slug,
        "message": descriptor.cli_message if message_locale == "pt-BR" else descriptor.mcp_message,
        "detail": sanitize_error_detail(error),
        "recovery_hint": _recovery_hint_for_locale(error, message_locale=message_locale),
        "audit_reference": getattr(error, "audit_reference", None),
    }


def json_rpc_error_payload(error: Exception) -> dict[str, Any]:
    descriptor = error_descriptor(error)
    return {
        "code": descriptor.json_rpc_code,
        "message": descriptor.mcp_message,
        "data": {
            "detail": sanitize_error_detail(error),
            "recovery_hint": _recovery_hint_for_locale(error, message_locale="en"),
            "audit_reference": getattr(error, "audit_reference", None),
        },
    }


def normalize_bootstrap_error(error: Exception) -> Exception:
    """Normalize composite read failures before adapter-specific presentation."""
    if isinstance(error, (*DOMAIN_ERROR_TYPES, ValidationError)):
        return error
    if isinstance(error, KeyError):
        return ValidationFailedError("Skill not found.")
    if isinstance(error, OSError):
        return StorageError(str(error))
    if isinstance(error, ValueError):
        return ValidationFailedError(str(error))
    return error


def _is_expected_error(error: Exception) -> bool:
    return isinstance(error, (*DOMAIN_ERROR_TYPES, ValidationError))
