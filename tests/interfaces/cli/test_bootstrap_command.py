from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from universal_memory.application.memory import (
    AssembleContextSummaryResult,
    GetMemoryStatusResult,
)
from universal_memory.application.onboarding import SessionBootstrapResult
from universal_memory.application.skills import ListSkillsResult
from universal_memory.domain import StorageError
from universal_memory.domain.entities import ContextSummary, ContextSummaryScope
from universal_memory.interfaces.cli.init_command import main


def _result() -> SessionBootstrapResult:
    now = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    return SessionBootstrapResult(
        status=GetMemoryStatusResult(
            initialized=True,
            project_path=".",
            fact_counts={"project": {"active": 1}},
            active_rules_count=0,
            registered_skills_count=0,
            approximate_size_bytes=12,
            last_health_check="2026-08-03T12:00:00Z",
            host_validation={},
        ),
        context=AssembleContextSummaryResult(
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
        ),
        skills_list=ListSkillsResult(
            skills=[],
            recommendations=[],
            recommended_action="Track durable repeated workflows.",
        ),
    )


def test_bootstrap_cli_json_returns_compact_aggregate(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    seen_roots: list[Path] = []

    exit_code = main(
        ["bootstrap", "--format", "json"],
        bootstrap_command=lambda command: seen_roots.append(command.project_root) or _result(),
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen_roots == [tmp_path]
    assert payload["operation"] == "bootstrap"
    assert payload["scope"] == "project"
    assert payload["warnings"] == []
    assert payload["data"]["status"]["initialized"] is True
    assert payload["data"]["context"]["project_summary"] == "Project"
    assert payload["data"]["skills"]["list"] == {
        "skills": [],
        "recommendations": [],
        "recommended_action": "Track durable repeated workflows.",
    }
    assert "operation" not in payload["data"]["status"]


def test_bootstrap_cli_preserves_native_error_contract(capsys) -> None:
    def fail(_command):
        raise StorageError("bootstrap storage failed")

    exit_code = main(
        ["bootstrap", "--format", "json"],
        bootstrap_command=fail,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "storage_error"
    assert payload["error"]["detail"] == "bootstrap storage failed"
    assert "operation" not in payload
