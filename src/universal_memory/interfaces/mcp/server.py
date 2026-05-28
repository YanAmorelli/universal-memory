from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP
from pydantic import ValidationError

from universal_memory.application.memory import (
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
    GetMemoryStatusCommand,
    GetMemoryStatusResult,
)
from universal_memory.domain import (
    FactNotFoundError,
    InvalidConfigError,
    SecretDetectedError,
    SnapshotFailedError,
    StorageError,
    UniversalMemoryError,
    ValidationFailedError,
)
from universal_memory.domain.entities import ContextSummaryScope
from universal_memory.domain.entities.base import format_utc_iso

DEFAULT_CONTEXT_MAX_SIZE_CHARS = 4000
TOKEN_ESTIMATE_CHARS = 4

StatusCommandHandler = Callable[[GetMemoryStatusCommand], GetMemoryStatusResult]
ContextCommandHandler = Callable[[AssembleContextSummaryCommand], AssembleContextSummaryResult]


@dataclass(frozen=True, slots=True)
class MCPUseCases:
    status: StatusCommandHandler
    context: ContextCommandHandler


def create_mcp_server(name: str = "universal-memory") -> FastMCP:
    return FastMCP(name)


def configure_server(
    server: FastMCP,
    use_cases: MCPUseCases,
    *,
    project_root: Path | None = None,
) -> FastMCP:
    root = project_root or Path.cwd()

    @server.tool(name="status")
    def status() -> dict[str, Any]:
        """Expose local cognitive persistence memory initialization and health check status.

        Returns initialization state, fact counts, active rules, registered skills,
        approximate size, host validations, and recommended actions.
        """
        try:
            result = use_cases.status(GetMemoryStatusCommand(project_root=root))
            return _success_envelope(
                operation="status",
                scope="project",
                data=_status_payload(result),
            )
        except Exception as error:
            return _error_envelope(error)

    @server.tool(name="context")
    def context(
        scope: Literal["project", "global"] = "project",
        max_size_chars: int = DEFAULT_CONTEXT_MAX_SIZE_CHARS,
        agent_session_key: str | None = None,
    ) -> dict[str, Any]:
        """Assemble the active cognitive memory context for AI agent operations.

        Retrieves and compiles project-specific or global context facts, preferences,
        and rules formatted in Markdown, optimized for injection into system prompts.
        """
        try:
            context_scope = _context_scope(scope)
            result = use_cases.context(
                AssembleContextSummaryCommand(
                    scope=context_scope,
                    max_size_chars=max_size_chars,
                    agent_session_key=agent_session_key,
                )
            )
            return _success_envelope(
                operation="context",
                scope=context_scope.value,
                data=_context_payload(result, max_size_chars=max_size_chars),
            )
        except Exception as error:
            return _error_envelope(error)

    return server


def _success_envelope(*, operation: str, scope: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": operation,
        "scope": scope,
        "data": data,
        "warnings": [],
    }


def _status_payload(result: GetMemoryStatusResult) -> dict[str, Any]:
    if not result.initialized:
        return {
            "initialized": False,
            "project_path": result.project_path,
            "recommended_action": result.recommended_action,
        }

    return {
        "initialized": True,
        "project_path": result.project_path,
        "fact_counts": result.fact_counts,
        "active_rules_count": result.active_rules_count,
        "registered_skills_count": result.registered_skills_count,
        "approximate_size_bytes": result.approximate_size_bytes,
        "last_health_check": result.last_health_check,
        "host_validation": result.host_validation,
    }


def _context_payload(
    result: AssembleContextSummaryResult,
    *,
    max_size_chars: int,
) -> dict[str, Any]:
    summary = result.context_summary
    markdown_size = len(result.context_markdown)
    return {
        "project_summary": summary.project_summary,
        "universal_preferences": summary.universal_preferences,
        "active_rules": summary.active_rules,
        "context_markdown": result.context_markdown,
        "source_fact_ids": result.included_fact_ids,
        "truncated": markdown_size >= max_size_chars,
        "token_estimate": max(1, round(markdown_size / TOKEN_ESTIMATE_CHARS)),
        "last_read_at": format_utc_iso(summary.created_at),
    }


def _context_scope(value: Literal["project", "global"]) -> ContextSummaryScope:
    normalized = value.lower()
    if normalized == "global":
        return ContextSummaryScope.global_
    if normalized == "project":
        return ContextSummaryScope.project
    raise ValidationFailedError("scope must be 'project' or 'global'.")


def _error_envelope(error: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "operation": "mcp",
        "scope": "project",
        "error": {
            "code": _error_code(error),
            "message": _error_message(error),
            "detail": _sanitize_error_detail(error),
        },
        "warnings": [],
    }


def _error_code(error: Exception) -> str:
    mappings: tuple[tuple[type[Exception] | tuple[type[Exception], ...], str], ...] = (
        (SecretDetectedError, "secret_detected"),
        ((ValidationError, ValidationFailedError), "validation_failed"),
        (InvalidConfigError, "invalid_config"),
        (FactNotFoundError, "fact_not_found"),
        (SnapshotFailedError, "snapshot_failed"),
        (StorageError, "storage_error"),
    )
    return next(
        (code for error_type, code in mappings if isinstance(error, error_type)),
        "unexpected_error",
    )


def _error_message(error: Exception) -> str:
    mappings: tuple[tuple[type[Exception] | tuple[type[Exception], ...], str], ...] = (
        (SecretDetectedError, "Sensitive content blocked."),
        ((ValidationError, ValidationFailedError), "Validation failed."),
        (InvalidConfigError, "Invalid configuration."),
        (FactNotFoundError, "Fact not found."),
        (SnapshotFailedError, "Snapshot failed."),
        (StorageError, "Storage error."),
    )
    return next(
        (message for error_type, message in mappings if isinstance(error, error_type)),
        "Unexpected error.",
    )


def _sanitize_error_detail(error: Exception) -> str:
    if isinstance(error, SecretDetectedError):
        return "Sensitive content was detected and blocked."
    detail = getattr(error, "message", str(error)) if isinstance(error, UniversalMemoryError) else str(error)
    # Scrub Unix absolute paths
    detail = re.sub(r"/(?:[^/\s:]+/)+[^/\s:]+", "<path>", detail)
    # Scrub Windows absolute and UNC paths
    detail = re.sub(r"(?:[a-zA-Z]:)?\\(?:[^\\\s:]+\\)+[^\\\s:]+", "<path>", detail)
    detail = re.sub(r"\b(?:sk|pk)-[A-Za-z0-9_-]{6,}\b", "<secret>", detail)
    return detail[:240]
