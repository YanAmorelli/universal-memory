"""Adapter guard for operations that may persist project state."""

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

from universal_memory.application.memory import (
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
    AssembleContextSummaryUseCase,
)
from universal_memory.domain.exceptions import ValidationFailedError
from universal_memory.infrastructure.config.project_layout import is_project_initialized
from universal_memory.infrastructure.security import LocalAuditLogRepository
from universal_memory.infrastructure.storage import LocalContextSummaryRepository


class ProjectNotInitializedError(ValidationFailedError):
    def __init__(self, memory_root: Path) -> None:
        self.memory_root = str(memory_root)
        super().__init__(
            "Project memory is not initialized. "
            "Hint: Ask the person whether to initialize, then run `umem init`."
        )


def require_initialized(memory_root: Path) -> None:
    if not is_project_initialized(memory_root):
        raise ProjectNotInitializedError(memory_root)


def scoped_context_handler(
    project_context: AssembleContextSummaryUseCase,
    global_root: Path,
) -> Callable[[AssembleContextSummaryCommand], AssembleContextSummaryResult]:
    global_context = AssembleContextSummaryUseCase(
        fact_repository=project_context.fact_repository,
        rule_repository=project_context.rule_repository,
        secret_scanner=project_context.secret_scanner,
        audit_log_repository=LocalAuditLogRepository(
            project_root=global_root,
            data_root=global_root,
        ),
        context_summary_repository=LocalContextSummaryRepository(
            project_root=global_root,
            data_root=global_root,
        ),
    )

    def execute(command: AssembleContextSummaryCommand) -> AssembleContextSummaryResult:
        handler = global_context if command.scope.value == "global" else project_context
        return handler.execute(command)

    return execute


def guard_project_operation[T](
    handler: Callable[[Any], T],
    memory_root: Path,
    *,
    initialize: Callable[[], None] | None = None,
) -> Callable[[Any], T]:
    @wraps(handler)
    def guarded(command: Any) -> T:
        if (
            not is_project_initialized(memory_root)
            and operation_scope(handler, command) != "global"
        ):
            if initialize is not None:
                initialize()
            require_initialized(memory_root)
        return handler(command)

    return guarded


def operation_scope(handler: Callable[..., Any], command: Any) -> str | None:
    scope = getattr(command, "scope", None)
    if scope is not None:
        return getattr(scope, "value", scope)
    owner = getattr(handler, "__self__", None)
    identifier = next(
        (
            getattr(command, key)
            for key in (
                "latent_skill_id",
                "recommendation_id",
                "skill_id_or_name",
                "draft_or_path",
                "id",
            )
            if getattr(command, key, None)
        ),
        None,
    )
    if not identifier:
        return None
    for key in ("repository", "recommendation_repository", "fact_repository"):
        repository = getattr(owner, key, None)
        if repository is None:
            continue
        for entity in repository.list():
            if identifier in (
                entity.id,
                getattr(entity, "name", None),
                getattr(entity, "slug", None),
                getattr(entity, "canonical_path", None),
            ):
                return entity.scope.value
    return None
