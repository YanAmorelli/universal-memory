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
from universal_memory.application.memory.operation_scope import operation_scope
from universal_memory.domain.exceptions import ProjectNotInitializedError  # noqa: F401
from universal_memory.infrastructure.config.project_layout import (
    has_project_identity,
    require_initialized,
)
from universal_memory.infrastructure.security import LocalAuditLogRepository
from universal_memory.infrastructure.storage import LocalContextSummaryRepository


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
        if not has_project_identity(memory_root) and operation_scope(handler, command) != "global":
            if initialize is not None:
                initialize()
            require_initialized(memory_root)
        return handler(command)

    return guarded
