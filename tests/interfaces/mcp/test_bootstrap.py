from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from universal_memory.application.memory import (
    AssembleContextSummaryResult,
    GetMemoryStatusResult,
)
from universal_memory.application.onboarding import SessionBootstrapResult
from universal_memory.application.skills import ListSkillsResult
from universal_memory.domain import StorageError
from universal_memory.domain.entities import ContextSummary, ContextSummaryScope
from universal_memory.interfaces.errors import JSON_RPC_STORAGE_ERROR
from universal_memory.interfaces.mcp.server import (
    MCPUseCases,
    configure_server,
    create_mcp_server,
)


def _status() -> GetMemoryStatusResult:
    return GetMemoryStatusResult(
        initialized=True,
        project_path=".",
        fact_counts={"project": {"active": 1}},
        active_rules_count=0,
        registered_skills_count=0,
        approximate_size_bytes=12,
        last_health_check="2026-08-03T12:00:00Z",
        host_validation={},
    )


def _context() -> AssembleContextSummaryResult:
    now = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    return AssembleContextSummaryResult(
        context_summary=ContextSummary(
            id="11111111-1111-4111-8111-111111111111",
            created_at=now,
            updated_at=now,
            project_summary="Project",
            universal_preferences="Preferences",
            active_rules="Rules",
            audit_reference="22222222-2222-4222-8222-222222222222",
            status="generated",
            scope=ContextSummaryScope.project,
        ),
        context_markdown="# MEMORY CONTEXT SUMMARY\nProject",
        included_fact_ids=["fact-1"],
    )


def _result() -> SessionBootstrapResult:
    return SessionBootstrapResult(
        status=_status(),
        context=_context(),
        skills_list=ListSkillsResult(skills=[], recommendations=[]),
    )


@pytest.mark.anyio
async def test_bootstrap_mcp_returns_same_compact_aggregate(tmp_path: Path) -> None:
    seen_roots: list[Path] = []
    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: _status(),
            context=lambda _command: _context(),
            bootstrap=lambda command: seen_roots.append(command.project_root) or _result(),
        ),
        project_root=tmp_path,
    )

    response = await server.call_tool("bootstrap", {})
    payload = response.structured_content

    assert payload is not None
    assert seen_roots == [tmp_path]
    assert payload["ok"] is True
    assert payload["operation"] == "bootstrap"
    assert payload["data"]["status"]["initialized"] is True
    assert payload["data"]["context"]["project_summary"] == "Project"
    assert payload["data"]["skills"]["list"] == {
        "skills": [],
        "recommendations": [],
    }


@pytest.mark.anyio
async def test_bootstrap_mcp_preserves_native_error_contract(tmp_path: Path) -> None:
    def fail(_command):
        raise StorageError("bootstrap storage failed")

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: _status(),
            context=lambda _command: _context(),
            bootstrap=fail,
        ),
        project_root=tmp_path,
    )

    response = await server.call_tool("bootstrap", {})
    payload = response.structured_content

    assert payload is not None
    assert payload["ok"] is False
    assert payload["operation"] == "bootstrap"
    assert payload["error"]["code"] == JSON_RPC_STORAGE_ERROR
    assert payload["error"]["data"]["detail"] == "bootstrap storage failed"
