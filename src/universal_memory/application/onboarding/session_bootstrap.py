from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from universal_memory.application.memory import (
    DEFAULT_CONTEXT_MAX_SIZE_CHARS,
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
    GetMemoryStatusCommand,
    GetMemoryStatusResult,
)
from universal_memory.application.skills import (
    ListSkillsCommand,
    ListSkillsResult,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import ContextSummaryScope

StatusHandler = Callable[[GetMemoryStatusCommand], GetMemoryStatusResult]
ContextHandler = Callable[[AssembleContextSummaryCommand], AssembleContextSummaryResult]
ListSkillsHandler = Callable[[ListSkillsCommand], ListSkillsResult]


@dataclass(frozen=True, slots=True)
class SessionBootstrapCommand:
    project_root: Path


@dataclass(frozen=True, slots=True)
class SessionBootstrapResult:
    status: GetMemoryStatusResult
    context: AssembleContextSummaryResult
    skills_list: ListSkillsResult


class SessionBootstrapUseCase:
    def __init__(
        self,
        *,
        status: StatusHandler,
        context: ContextHandler,
        list_skills: ListSkillsHandler,
    ) -> None:
        self.status = status
        self.context = context
        self.list_skills = list_skills

    def execute(self, command: SessionBootstrapCommand) -> SessionBootstrapResult:
        status_result = self.status(GetMemoryStatusCommand(project_root=command.project_root))
        if not status_result.initialized:
            raise ValidationFailedError(
                "Project memory is not initialized. Initialize project memory before retrying."
            )

        context_result = self.context(
            AssembleContextSummaryCommand(
                scope=ContextSummaryScope.project,
                max_size_chars=DEFAULT_CONTEXT_MAX_SIZE_CHARS,
                agent_session_key=None,
            )
        )
        skills_result = self.list_skills(ListSkillsCommand())
        return SessionBootstrapResult(
            status=status_result,
            context=context_result,
            skills_list=skills_result,
        )
