from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from universal_memory.application.memory import (
    DEFAULT_CONTEXT_MAX_SIZE_CHARS,
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
    GetMemoryStatusCommand,
    GetMemoryStatusResult,
)
from universal_memory.application.onboarding import (
    SessionBootstrapCommand,
    SessionBootstrapUseCase,
)
from universal_memory.application.skills import (
    ListSkillsCommand,
    ListSkillsResult,
    SkillListItem,
)
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import ContextSummary, ContextSummaryScope


def _status_result(*, initialized: bool = True) -> GetMemoryStatusResult:
    return GetMemoryStatusResult(
        initialized=initialized,
        project_path=".",
        fact_counts={},
        active_rules_count=0,
        registered_skills_count=1,
        approximate_size_bytes=10,
        last_health_check="2026-08-03T12:00:00Z",
        host_validation={},
        recommended_action=None if initialized else "Run 'umem init'.",
    )


def _context_result() -> AssembleContextSummaryResult:
    now = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    return AssembleContextSummaryResult(
        context_summary=ContextSummary(
            id="11111111-1111-4111-8111-111111111111",
            created_at=now,
            updated_at=now,
            project_summary="Project context",
            universal_preferences="Preferences",
            active_rules="Rules",
            audit_reference="22222222-2222-4222-8222-222222222222",
            status="generated",
            scope=ContextSummaryScope.project,
        ),
        context_markdown="# MEMORY CONTEXT SUMMARY\nProject context",
        included_fact_ids=["fact-1"],
    )


def _skills_result() -> ListSkillsResult:
    return ListSkillsResult(
        skills=[
            SkillListItem(
                id="skill-1",
                name="review-helper",
                scope="project",
                status="active",
                relative_path=".umem/skills/review-helper/SKILL.md",
                created_at="2026-08-03T12:00:00Z",
                updated_at="2026-08-03T12:00:00Z",
                origin="test",
                audit_reference="audit-2",
            )
        ],
        recommendations=[],
    )


def test_session_bootstrap_executes_once_in_order_with_fixed_defaults(tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []

    def status(command: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        calls.append(("status", command))
        return _status_result()

    def context(command: AssembleContextSummaryCommand) -> AssembleContextSummaryResult:
        calls.append(("context", command))
        return _context_result()

    def list_skills(command: ListSkillsCommand) -> ListSkillsResult:
        calls.append(("skills.list", command))
        return _skills_result()

    result = SessionBootstrapUseCase(
        status=status,
        context=context,
        list_skills=list_skills,
    ).execute(SessionBootstrapCommand(project_root=tmp_path))

    assert [name for name, _command in calls] == ["status", "context", "skills.list"]
    assert calls[0][1] == GetMemoryStatusCommand(project_root=tmp_path)
    assert calls[1][1] == AssembleContextSummaryCommand(
        scope=ContextSummaryScope.project,
        max_size_chars=DEFAULT_CONTEXT_MAX_SIZE_CHARS,
        agent_session_key=None,
    )
    assert calls[2][1] == ListSkillsCommand()
    assert result.status == _status_result()
    assert result.context == _context_result()
    assert result.skills_list == _skills_result()


def test_session_bootstrap_stops_when_project_is_uninitialized(tmp_path: Path) -> None:
    later_calls: list[str] = []
    use_case = SessionBootstrapUseCase(
        status=lambda _command: _status_result(initialized=False),
        context=lambda _command: later_calls.append("context") or _context_result(),
        list_skills=lambda _command: later_calls.append("skills.list") or _skills_result(),
    )

    with pytest.raises(ValidationFailedError, match="not initialized"):
        use_case.execute(SessionBootstrapCommand(project_root=tmp_path))

    assert later_calls == []


@pytest.mark.parametrize(
    ("failing_step", "expected_calls"),
    [
        ("status", ["status"]),
        ("context", ["status", "context"]),
        ("skills.list", ["status", "context", "skills.list"]),
    ],
)
def test_session_bootstrap_is_fail_fast(
    tmp_path: Path,
    failing_step: str,
    expected_calls: list[str],
) -> None:
    calls: list[str] = []

    def status(_command: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        calls.append("status")
        if failing_step == "status":
            raise StorageError("status failed")
        return _status_result()

    def context(_command: AssembleContextSummaryCommand) -> AssembleContextSummaryResult:
        calls.append("context")
        if failing_step == "context":
            raise StorageError("context failed")
        return _context_result()

    def list_skills(_command: ListSkillsCommand) -> ListSkillsResult:
        calls.append("skills.list")
        if failing_step == "skills.list":
            raise StorageError("skills list failed")
        return _skills_result()

    use_case = SessionBootstrapUseCase(
        status=status,
        context=context,
        list_skills=list_skills,
    )

    with pytest.raises(StorageError, match="failed"):
        use_case.execute(SessionBootstrapCommand(project_root=tmp_path))

    assert calls == expected_calls
