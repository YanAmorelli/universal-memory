from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from universal_memory.application.host import ConfigureHostResult, SyncInstructionsResult
from universal_memory.application.memory import (
    AssembleContextSummaryResult,
    GetMemoryStatusResult,
    ListFactsResult,
    PurgeFactResult,
    RememberFactResult,
)
from universal_memory.application.onboarding import SetupProjectResult
from universal_memory.application.security import (
    ListAuditLogResult,
    ListSnapshotsResult,
    RollbackResult,
)
from universal_memory.application.skills import ProposeSkillCommand, ProposeSkillResult
from universal_memory.domain import StorageError
from universal_memory.domain.entities import (
    ContextSummary,
    ContextSummaryScope,
    Fact,
    FactScope,
    FactStatus,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
)
from universal_memory.interfaces.mcp.server import (
    JSON_RPC_STORAGE_ERROR,
    JSON_RPC_UNEXPECTED_ERROR,
    JSON_RPC_VALIDATION_FAILED,
    MCPUseCases,
    configure_server,
    create_mcp_server,
)

FACT_ID = "11111111-1111-4111-8111-111111111111"
PUBLIC_MCP_TOOLS = {
    "initialize_project": {},
    "status": {},
    "context": {},
    "remember_fact": {"content": "Use respostas concisas."},
    "list_facts": {},
    "purge_fact": {"id": "11111111-1111-4111-8111-111111111111", "confirm": True},
    "list_audit_events": {},
    "list_snapshots": {},
    "rollback_scope": {"confirm": True},
    "host_setup": {"host_id": "codex", "force": True},
    "host_check": {"host_id": "codex"},
    "sync_instructions": {"host_ids": ["codex", "claude_code"], "apply": True},
    "propose_skill": {"latent_skill_id": FACT_ID, "decision": "sim"},
}
CONTRACT_KEYS_BY_TOOL = {
    "initialize_project": {
        "project_path",
        "config_path",
        "memory_path",
        "audit_path",
        "snapshots_path",
        "created",
        "already_initialized",
        "audit_reference",
    },
    "status": {
        "initialized",
        "project_path",
        "fact_counts",
        "active_rules_count",
        "registered_skills_count",
        "approximate_size_bytes",
        "last_health_check",
        "host_validation",
    },
    "context": {
        "project_summary",
        "universal_preferences",
        "active_rules",
        "source_fact_ids",
        "truncated",
        "token_estimate",
        "last_read_at",
    },
    "remember_fact": {"fact_id", "scope", "status", "tags", "created_at", "audit_reference"},
    "list_facts": {"facts"},
    "purge_fact": {"purged_count", "affected_ids", "audit_reference"},
    "list_audit_events": {"events"},
    "list_snapshots": {"snapshots"},
    "rollback_scope": {"scope", "snapshot_reference", "restored_paths", "audit_reference"},
    "host_setup": {
        "host_id",
        "instruction_targets",
        "planned_changes",
        "manual_steps",
        "validation_status",
        "audit_reference",
        "snapshot_reference",
        "timestamp",
    },
    "host_check": {
        "host_id",
        "instruction_targets",
        "planned_changes",
        "manual_steps",
        "validation_status",
        "audit_reference",
        "snapshot_reference",
        "timestamp",
    },
    "sync_instructions": {
        "host_ids",
        "instruction_targets",
        "planned_changes",
        "manual_steps",
        "validation_status",
        "audit_reference",
        "snapshot_reference",
        "timestamp",
    },
    "propose_skill": {
        "skill_id",
        "suggested_name",
        "status",
        "accepted",
        "auto_approval_recorded",
        "audit_reference",
        "snapshot_reference",
        "choices",
        "requires_decision",
        "evidence",
    },
}
CONTRACT_TYPES_BY_TOOL = {
    "initialize_project": {
        "project_path": str,
        "config_path": str,
        "memory_path": str,
        "audit_path": str,
        "snapshots_path": str,
        "created": list,
        "already_initialized": bool,
        "audit_reference": str,
    },
    "status": {
        "initialized": bool,
        "project_path": str,
        "fact_counts": dict,
        "active_rules_count": int,
        "registered_skills_count": int,
        "approximate_size_bytes": int,
        "last_health_check": str,
        "host_validation": dict,
    },
    "context": {
        "project_summary": str,
        "universal_preferences": str,
        "active_rules": str,
        "source_fact_ids": list,
        "truncated": bool,
        "token_estimate": int,
        "last_read_at": str,
    },
    "remember_fact": {
        "fact_id": str,
        "scope": str,
        "status": str,
        "tags": list,
        "created_at": str,
        "audit_reference": str,
    },
    "list_facts": {"facts": list},
    "purge_fact": {"purged_count": int, "affected_ids": list, "audit_reference": str},
    "list_audit_events": {"events": list},
    "list_snapshots": {"snapshots": list},
    "rollback_scope": {
        "scope": str,
        "snapshot_reference": str,
        "restored_paths": list,
        "audit_reference": str,
    },
    "host_setup": {
        "host_id": str,
        "instruction_targets": list,
        "planned_changes": list,
        "manual_steps": list,
        "validation_status": str,
        "audit_reference": str,
        "snapshot_reference": str,
        "timestamp": str,
    },
    "host_check": {
        "host_id": str,
        "instruction_targets": list,
        "planned_changes": list,
        "manual_steps": list,
        "validation_status": str,
        "audit_reference": str,
        "snapshot_reference": str,
        "timestamp": str,
    },
    "sync_instructions": {
        "host_ids": list,
        "instruction_targets": list,
        "planned_changes": list,
        "manual_steps": list,
        "validation_status": str,
        "audit_reference": str,
        "snapshot_reference": str,
        "timestamp": str,
    },
    "propose_skill": {
        "skill_id": str,
        "suggested_name": str,
        "status": str,
        "accepted": bool,
        "auto_approval_recorded": bool,
        "audit_reference": str,
        "snapshot_reference": str,
        "choices": list,
        "requires_decision": bool,
        "evidence": list,
    },
}


@pytest.mark.anyio
async def test_mcp_compliance_covers_every_public_tool_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_network_access(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("MCP compliance suite must stay offline; network access attempted")

    monkeypatch.setattr("socket.create_connection", fail_network_access)
    monkeypatch.setattr("socket.socket", fail_network_access)
    server = configure_server(create_mcp_server(), mcp_use_cases(tmp_path), project_root=tmp_path)

    discovered_tools = {tool.name for tool in await server.list_tools()}

    assert discovered_tools == set(PUBLIC_MCP_TOOLS), (
        "MCP public tool inventory changed; update tests/interfaces/mcp/test_compliance.py "
        f"missing={sorted(set(PUBLIC_MCP_TOOLS) - discovered_tools)} "
        f"unexpected={sorted(discovered_tools - set(PUBLIC_MCP_TOOLS))}"
    )
    for tool_name, args in PUBLIC_MCP_TOOLS.items():
        result = await server.call_tool(tool_name, args)
        payload = result.structured_content
        assert payload is not None, f"{tool_name}: missing structured_content"
        assert payload["ok"] is True, f"{tool_name}: expected success envelope, got {payload}"
        assert payload["data"], f"{tool_name}: success data payload is empty"
        assert set(payload["data"]) == CONTRACT_KEYS_BY_TOOL[tool_name], (
            f"{tool_name}: data keys differ from CLI/MCP contract; "
            f"missing={sorted(CONTRACT_KEYS_BY_TOOL[tool_name] - set(payload['data']))} "
            f"unexpected={sorted(set(payload['data']) - CONTRACT_KEYS_BY_TOOL[tool_name])}"
        )
        _assert_contract_types(tool_name, payload["data"])


@pytest.mark.anyio
async def test_mcp_compliance_returns_structured_error_for_domain_exception(
    tmp_path: Path,
) -> None:
    def status_error(_command: object) -> object:
        raise StorageError(f"storage failed at {tmp_path}/.umem")

    server = configure_server(
        create_mcp_server(),
        replace(mcp_use_cases(tmp_path), status=status_error),
        project_root=tmp_path,
    )

    result = await server.call_tool("status", {})
    payload = _mcp_error_payload(result.structured_content)

    assert payload is not None
    assert payload["isError"] is True
    assert payload["ok"] is False
    assert payload["error"]["code"] == JSON_RPC_STORAGE_ERROR
    assert payload["error"]["data"]["detail"]
    assert str(tmp_path) not in payload["error"]["data"]["detail"]
    assert payload["error"]["data"]["recovery_hint"]


@pytest.mark.anyio
async def test_mcp_compliance_returns_structured_error_for_unexpected_exception(
    tmp_path: Path,
) -> None:
    def context_error(_command: object) -> object:
        raise RuntimeError("boom")

    server = configure_server(
        create_mcp_server(),
        replace(mcp_use_cases(tmp_path), context=context_error),
        project_root=tmp_path,
    )

    result = await server.call_tool("context", {})
    payload = _mcp_error_payload(result.structured_content)

    assert payload is not None
    assert payload["isError"] is True
    assert payload["ok"] is False
    assert payload["error"]["code"] == JSON_RPC_UNEXPECTED_ERROR
    assert payload["error"]["data"]["detail"] == "Unexpected error."
    assert payload["error"]["data"]["recovery_hint"]


@pytest.mark.anyio
async def test_mcp_compliance_blocks_destructive_tools_without_confirmation(
    tmp_path: Path,
) -> None:
    server = configure_server(create_mcp_server(), mcp_use_cases(tmp_path), project_root=tmp_path)

    for tool_name in ("purge_fact", "rollback_scope"):
        payload = _mcp_error_payload(
            (await server.call_tool(tool_name, {"confirm": False})).structured_content
        )
        assert payload is not None, f"{tool_name}: missing error payload"
        assert payload["isError"] is True
        assert payload["ok"] is False, f"{tool_name}: destructive call should fail without confirm"
        assert payload["error"]["code"] == JSON_RPC_VALIDATION_FAILED
        assert "destructive" in payload["error"]["data"]["detail"]


def _assert_contract_types(tool_name: str, data: dict[str, Any]) -> None:
    for key, expected_type in CONTRACT_TYPES_BY_TOOL[tool_name].items():
        assert key in data, f"{tool_name}: missing contract key {key!r}"
        assert isinstance(data[key], expected_type), (
            f"{tool_name}.{key}: expected {expected_type}, got {type(data[key]).__name__}"
        )


def _mcp_error_payload(structured_content: dict[str, Any] | None) -> dict[str, Any]:
    assert structured_content is not None
    if "structuredContent" in structured_content:
        return {
            "isError": bool(structured_content.get("isError")),
            **structured_content["structuredContent"],
        }
    return {"isError": True, **structured_content}


def mcp_use_cases(project_root: Path | None = None) -> MCPUseCases:
    root = project_root or Path(".")
    return MCPUseCases(
        initialize_project=lambda _project_root: setup_result(root),
        status=lambda _command: status_result(),
        context=lambda _command: context_result(),
        remember=lambda _command: RememberFactResult(
            fact=fact_fixture(),
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        ),
        list_facts=lambda _command: ListFactsResult(facts=[fact_fixture()]),
        purge_fact=lambda _command: PurgeFactResult(1, [FACT_ID], "audit-1"),
        list_audit_events=lambda _command: ListAuditLogResult(events=[]),
        list_snapshots=lambda _command: ListSnapshotsResult(snapshots=[]),
        rollback_scope=lambda command: RollbackResult(
            scope=command.scope,
            snapshot_reference="snapshot-1",
            restored_paths=[".umem/memory/facts.jsonl"],
            audit_reference="audit-1",
        ),
        host_setup=lambda _command: host_result(),
        host_check=lambda _command: host_result(planned_changes=[]),
        sync_instructions=lambda _command: sync_result(),
        propose_skill=propose_skill_result,
    )


def propose_skill_result(command: ProposeSkillCommand) -> ProposeSkillResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    skill = LatentSkill(
        id=command.latent_skill_id,
        created_at=now,
        updated_at=now,
        name="TDD recorrente",
        description="Usuario pede ciclo red green refactor",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.active,
        recurrence_count=3,
        metadata={},
    )
    return ProposeSkillResult(
        latent_skill=skill,
        proposal={
            "suggested_name": skill.name,
            "purpose": skill.description,
            "scope": skill.scope.value,
            "evidence": ["Pedido em story anterior"],
        },
        accepted=True,
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def setup_result(project_root: Path) -> SetupProjectResult:
    return SetupProjectResult(
        project_path=project_root,
        config_path=project_root / ".umem" / "config.toml",
        memory_path=project_root / ".umem" / "memory",
        audit_path=project_root / ".umem" / "audit" / "events.jsonl",
        snapshots_path=project_root / ".umem" / "snapshots",
        skills_path=project_root / ".umem" / "skills",
        benchmarks_path=project_root / ".umem" / "benchmarks",
        created=True,
        created_paths=[".umem/config.toml"],
        existing_paths=[],
        already_initialized=False,
    )


def status_result() -> GetMemoryStatusResult:
    return GetMemoryStatusResult(
        initialized=True,
        project_path=".",
        fact_counts={"project": {"active": 1}, "global": {"active": 0}},
        active_rules_count=0,
        registered_skills_count=0,
        approximate_size_bytes=123,
        last_health_check="2026-05-28T12:00:00Z",
        host_validation={},
        recommended_action=None,
    )


def context_result() -> AssembleContextSummaryResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    summary = ContextSummary(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        project_summary="Projeto",
        universal_preferences="Preferencias",
        active_rules="Regras",
        audit_reference="22222222-2222-4222-8222-222222222222",
        status="generated",
        scope=ContextSummaryScope.project,
    )
    return AssembleContextSummaryResult(
        context_summary=summary,
        context_markdown="# MEMORY CONTEXT SUMMARY\nProjeto",
        included_fact_ids=["fact-1"],
    )


def fact_fixture() -> Fact:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    return Fact(
        id=FACT_ID,
        created_at=now,
        updated_at=now,
        content="Use respostas concisas.",
        scope=FactScope.project,
        source="test",
        status=FactStatus.active,
        tags=["style"],
    )


def host_result(
    planned_changes: list[dict[str, str]] | None = None,
) -> ConfigureHostResult:
    return ConfigureHostResult(
        host_id="codex",
        instruction_targets=["agents_md"],
        planned_changes=planned_changes
        if planned_changes is not None
        else [{"target": "agents_md", "action": "create", "path": "AGENTS.md"}],
        manual_steps=[],
        validation_status="success",
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
        timestamp="2026-05-28T12:00:00Z",
    )


def sync_result() -> SyncInstructionsResult:
    return SyncInstructionsResult(
        host_ids=["codex", "claude_code"],
        instruction_targets=["AGENTS.md", "CLAUDE.md"],
        planned_changes=[
            {"target": "agents_md", "action": "create", "path": "AGENTS.md"},
            {"target": "claude_md", "action": "create", "path": "CLAUDE.md"},
        ],
        manual_steps=[],
        validation_status="success",
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
        timestamp="2026-05-28T12:00:00Z",
    )
