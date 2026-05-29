from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastmcp import FastMCP

from universal_memory.__main__ import main
from universal_memory.application.host import ConfigureHostCommand, ConfigureHostResult
from universal_memory.application.host.sync_instructions_use_case import (
    SyncInstructionsCommand,
    SyncInstructionsResult,
)
from universal_memory.application.memory import (
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
    GetMemoryStatusCommand,
    GetMemoryStatusResult,
)
from universal_memory.application.skills import (
    GenerateSkillCommand,
    GenerateSkillResult,
    GetSkillDetailCommand,
    GetSkillDetailResult,
    ListSkillsCommand,
    ListSkillsResult,
    ProposeSkillCommand,
    ProposeSkillDecision,
    ProposeSkillResult,
    SkillListItem,
)
from universal_memory.bootstrap.mcp import build_server
from universal_memory.domain import SecretDetectedError
from universal_memory.domain.entities import (
    ContextSummary,
    ContextSummaryScope,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
)
from universal_memory.interfaces.mcp.server import (
    JSON_RPC_SECRET_DETECTED,
    MCPUseCases,
    configure_server,
    create_mcp_server,
)

SKILL_ID = "11111111-1111-4111-8111-111111111111"


def initialized_status() -> GetMemoryStatusResult:
    return GetMemoryStatusResult(
        initialized=True,
        project_path=".",
        fact_counts={
            "global": {"active": 0, "stale": 0, "archived": 0, "purged": 0},
            "project": {"active": 1, "stale": 0, "archived": 0, "purged": 0},
        },
        active_rules_count=2,
        registered_skills_count=3,
        approximate_size_bytes=42,
        last_health_check="2026-05-27T20:00:00Z",
        host_validation={
            "claude_code": {
                "status": "unconfigured",
                "timestamp": None,
                "method": None,
                "audit_reference": None,
            },
            "codex": {
                "status": "success",
                "timestamp": "2026-05-27T20:00:00Z",
                "method": "agents_md_compact_validator",
                "audit_reference": "audit-codex",
            },
        },
        recommended_action=None,
    )


def context_result() -> AssembleContextSummaryResult:
    now = datetime(2026, 5, 27, 20, 0, tzinfo=UTC)
    audit_reference = str(uuid4())
    summary = ContextSummary(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        project_summary="Resumo do projeto",
        universal_preferences="Preferencias universais",
        active_rules="Regras ativas",
        audit_reference=audit_reference,
        status="generated",
        scope=ContextSummaryScope.project,
    )
    return AssembleContextSummaryResult(
        context_summary=summary,
        context_markdown="# MEMORY CONTEXT SUMMARY\nResumo do projeto",
        included_fact_ids=["fact-1", "fact-2"],
    )


def skill_result(
    *,
    decision: ProposeSkillDecision | None = None,
    requires_decision: bool = False,
) -> ProposeSkillResult:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    skill = LatentSkill(
        id=SKILL_ID,
        created_at=now,
        updated_at=now,
        name="TDD recorrente",
        description="Usuario pede ciclo red green refactor",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.proposed
        if requires_decision
        else (
            LatentSkillStatus.ignored
            if decision == ProposeSkillDecision.nao
            else LatentSkillStatus.active
        ),
        recurrence_count=3,
        metadata={},
    )
    return ProposeSkillResult(
        latent_skill=skill,
        proposal={
            "suggested_name": skill.name,
            "purpose": skill.description,
            "scope": "project",
            "evidence": ["Pedido em story anterior", "Pedido em review"],
        },
        requires_decision=requires_decision,
        accepted=decision in {ProposeSkillDecision.sim, ProposeSkillDecision.sempre},
        auto_approval_recorded=decision == ProposeSkillDecision.sempre,
        audit_reference="audit-1" if decision is not None else "",
        snapshot_reference="snapshot-1" if decision is not None else "",
    )


def generated_skill_result() -> GenerateSkillResult:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    skill = LatentSkill(
        id=SKILL_ID,
        created_at=now,
        updated_at=now,
        name="TDD recorrente",
        description="Usuario pede ciclo red green refactor",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.active,
        recurrence_count=3,
        metadata={},
    )
    return GenerateSkillResult(
        latent_skill=skill,
        slug="tdd-recorrente",
        skill_dir=".umem/skills/tdd-recorrente",
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        created_paths=[".umem/skills/tdd-recorrente/SKILL.md"],
        affected_paths=[".umem/skills/tdd-recorrente/SKILL.md"],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def list_skills_result() -> ListSkillsResult:
    return ListSkillsResult(
        skills=[
            SkillListItem(
                name="TDD recorrente",
                scope="project",
                status="active",
                relative_path=".umem/skills/tdd-recorrente/SKILL.md",
                created_at="2026-05-29T12:00:00Z",
                updated_at="2026-05-29T12:05:00Z",
                origin="cli",
                audit_reference="audit-1",
            )
        ]
    )


def skill_detail_result() -> GetSkillDetailResult:
    return GetSkillDetailResult(
        name="TDD recorrente",
        scope="project",
        status="active",
        relative_path=".umem/skills/tdd-recorrente/SKILL.md",
        triggers=["red green refactor", "implementar story"],
        audit_reference="audit-1",
        references_loaded=False,
    )


@pytest.mark.anyio
async def test_server_factory_initializes_fastmcp_offline() -> None:
    server = create_mcp_server()

    assert isinstance(server, FastMCP)
    assert server.name == "universal-memory"


@pytest.mark.anyio
async def test_status_tool_uses_injected_use_case_and_matches_cli_json_contract(
    tmp_path: Path,
) -> None:
    received: list[GetMemoryStatusCommand] = []

    def status_use_case(command: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        received.append(command)
        return initialized_status()

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(status=status_use_case, context=lambda _command: context_result()),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool("status", {})

    assert "status" in tool_names
    assert received == [GetMemoryStatusCommand(project_root=tmp_path)]
    assert result.structured_content == {
        "ok": True,
        "operation": "status",
        "scope": "project",
        "warnings": [],
        "data": {
            "initialized": True,
            "project_path": ".",
            "fact_counts": {
                "global": {"active": 0, "stale": 0, "archived": 0, "purged": 0},
                "project": {"active": 1, "stale": 0, "archived": 0, "purged": 0},
            },
            "active_rules_count": 2,
            "registered_skills_count": 3,
            "approximate_size_bytes": 42,
            "last_health_check": "2026-05-27T20:00:00Z",
            "host_validation": {
                "claude_code": {
                    "status": "unconfigured",
                    "timestamp": None,
                    "method": None,
                    "audit_reference": None,
                },
                "codex": {
                    "status": "success",
                    "timestamp": "2026-05-27T20:00:00Z",
                    "method": "agents_md_compact_validator",
                    "audit_reference": "audit-codex",
                },
            },
        },
    }


@pytest.mark.anyio
async def test_context_tool_uses_injected_use_case_and_matches_cli_json_contract(
    tmp_path: Path,
) -> None:
    received: list[AssembleContextSummaryCommand] = []

    def context_use_case(command: AssembleContextSummaryCommand) -> AssembleContextSummaryResult:
        received.append(command)
        return context_result()

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(status=lambda _command: initialized_status(), context=context_use_case),
        project_root=tmp_path,
    )

    result = await server.call_tool(
        "context",
        {"scope": "project", "max_size_chars": 1234, "agent_session_key": "session-1"},
    )

    assert received == [
        AssembleContextSummaryCommand(
            scope=ContextSummaryScope.project,
            max_size_chars=1234,
            agent_session_key="session-1",
        )
    ]
    assert result.structured_content == {
        "ok": True,
        "operation": "context",
        "scope": "project",
        "warnings": [],
        "data": {
            "project_summary": "Resumo do projeto",
            "universal_preferences": "Preferencias universais",
            "active_rules": "Regras ativas",
            "source_fact_ids": ["fact-1", "fact-2"],
            "truncated": False,
            "token_estimate": 10,
            "last_read_at": "2026-05-27T20:00:00Z",
        },
    }


@pytest.mark.anyio
async def test_host_setup_tool_uses_injected_use_case_and_matches_cli_json_contract(
    tmp_path: Path,
) -> None:
    received: list[ConfigureHostCommand] = []

    def host_setup(command: ConfigureHostCommand) -> ConfigureHostResult:
        received.append(command)
        return ConfigureHostResult(
            host_id="codex",
            instruction_targets=["agents_md"],
            planned_changes=[{"target": "agents_md", "action": "create", "path": "AGENTS.md"}],
            manual_steps=[],
            validation_status="success",
            audit_reference="uuid-v4-reference",
            snapshot_reference="snapshot-reference",
            timestamp="2026-05-28T20:00:00Z",
        )

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            host_setup=host_setup,
            host_check=host_setup,
        ),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool("host_setup", {"host_id": "codex", "force": True})

    assert "host_setup" in tool_names
    assert received == [ConfigureHostCommand(host_id="codex", apply=True, origin="mcp")]
    assert result.structured_content == {
        "ok": True,
        "operation": "host_setup",
        "scope": "project",
        "data": {
            "host_id": "codex",
            "instruction_targets": ["agents_md"],
            "planned_changes": [{"target": "agents_md", "action": "create", "path": "AGENTS.md"}],
            "manual_steps": [],
            "validation_status": "success",
            "audit_reference": "uuid-v4-reference",
            "snapshot_reference": "snapshot-reference",
            "timestamp": "2026-05-28T20:00:00Z",
        },
        "warnings": [],
    }


@pytest.mark.anyio
async def test_propose_skill_without_decision_returns_proposal_for_follow_up(
    tmp_path: Path,
) -> None:
    received: list[ProposeSkillCommand] = []

    def propose_skill(command: ProposeSkillCommand) -> ProposeSkillResult:
        received.append(command)
        return skill_result(requires_decision=True)

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            propose_skill=propose_skill,
        ),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool("propose_skill", {"latent_skill_id": SKILL_ID})

    assert "propose_skill" in tool_names
    assert received == [ProposeSkillCommand(latent_skill_id=SKILL_ID, origin="mcp")]
    assert result.structured_content == {
        "ok": True,
        "operation": "skills.propose",
        "scope": "project",
        "data": {
            "skill_id": SKILL_ID,
            "suggested_name": "TDD recorrente",
            "status": "proposed",
            "accepted": False,
            "auto_approval_recorded": False,
            "audit_reference": "",
            "snapshot_reference": "",
            "choices": ["Sim", "Sempre", "Não"],
            "requires_decision": True,
            "evidence": ["Pedido em story anterior", "Pedido em review"],
        },
        "warnings": [],
    }


@pytest.mark.anyio
async def test_propose_skill_with_decision_invokes_use_case_and_matches_cli_json_contract(
    tmp_path: Path,
) -> None:
    received: list[ProposeSkillCommand] = []

    def propose_skill(command: ProposeSkillCommand) -> ProposeSkillResult:
        received.append(command)
        return skill_result(decision=command.decision)

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            propose_skill=propose_skill,
        ),
        project_root=tmp_path,
    )

    result = await server.call_tool(
        "propose_skill",
        {"latent_skill_id": SKILL_ID, "decision": "sempre"},
    )

    assert received == [
        ProposeSkillCommand(
            latent_skill_id=SKILL_ID,
            decision=ProposeSkillDecision.sempre,
            origin="mcp",
        )
    ]
    assert result.structured_content is not None
    assert result.structured_content["data"]["auto_approval_recorded"] is True
    assert result.structured_content["data"]["audit_reference"] == "audit-1"


@pytest.mark.anyio
async def test_generate_skill_tool_invokes_use_case_and_matches_cli_json_contract(
    tmp_path: Path,
) -> None:
    received: list[GenerateSkillCommand] = []

    def generate_skill(command: GenerateSkillCommand) -> GenerateSkillResult:
        received.append(command)
        return generated_skill_result()

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            generate_skill=generate_skill,
        ),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool(
        "generate_skill",
        {"latent_skill_id": SKILL_ID, "update_existing": True},
    )

    assert "generate_skill" in tool_names
    assert received == [
        GenerateSkillCommand(
            latent_skill_id=SKILL_ID,
            origin="mcp",
            update_existing=True,
        )
    ]
    assert result.structured_content == {
        "ok": True,
        "operation": "skills.generate",
        "scope": "project",
        "data": {
            "skill_id": SKILL_ID,
            "name": "TDD recorrente",
            "slug": "tdd-recorrente",
            "skill_dir": ".umem/skills/tdd-recorrente",
            "skill_file": ".umem/skills/tdd-recorrente/SKILL.md",
            "created_paths": [".umem/skills/tdd-recorrente/SKILL.md"],
            "affected_paths": [".umem/skills/tdd-recorrente/SKILL.md"],
            "audit_reference": "audit-1",
            "snapshot_reference": "snapshot-1",
            "collision_detected": False,
            "suggested_slug": None,
        },
        "warnings": [],
    }


@pytest.mark.anyio
async def test_list_skills_tool_invokes_use_case_and_matches_cli_json_contract(
    tmp_path: Path,
) -> None:
    received: list[ListSkillsCommand] = []

    def list_skills(command: ListSkillsCommand) -> ListSkillsResult:
        received.append(command)
        return list_skills_result()

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            list_skills=list_skills,
        ),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool("list_skills", {})

    assert "list_skills" in tool_names
    assert received == [ListSkillsCommand()]
    assert result.structured_content == {
        "ok": True,
        "operation": "skills.list",
        "scope": "all",
        "data": {
            "skills": [
                {
                    "name": "TDD recorrente",
                    "scope": "project",
                    "status": "active",
                    "relative_path": ".umem/skills/tdd-recorrente/SKILL.md",
                    "created_at": "2026-05-29T12:00:00Z",
                    "updated_at": "2026-05-29T12:05:00Z",
                    "origin": "cli",
                    "audit_reference": "audit-1",
                }
            ]
        },
        "warnings": [],
    }


@pytest.mark.anyio
async def test_get_skill_detail_tool_invokes_use_case_and_matches_cli_json_contract(
    tmp_path: Path,
) -> None:
    received: list[GetSkillDetailCommand] = []

    def get_skill_detail(command: GetSkillDetailCommand) -> GetSkillDetailResult:
        received.append(command)
        return skill_detail_result()

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            get_skill_detail=get_skill_detail,
        ),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool("get_skill_detail", {"name_or_id": "TDD recorrente"})

    assert "get_skill_detail" in tool_names
    assert received == [GetSkillDetailCommand(name_or_id="TDD recorrente")]
    assert result.structured_content == {
        "ok": True,
        "operation": "skills.detail",
        "scope": "project",
        "data": {
            "name": "TDD recorrente",
            "scope": "project",
            "status": "active",
            "relative_path": ".umem/skills/tdd-recorrente/SKILL.md",
            "triggers": ["red green refactor", "implementar story"],
            "audit_reference": "audit-1",
            "references_loaded": False,
        },
        "warnings": [],
    }


@pytest.mark.anyio
async def test_host_check_tool_uses_same_contract_without_mutation(tmp_path: Path) -> None:
    received: list[ConfigureHostCommand] = []

    def host_check(command: ConfigureHostCommand) -> ConfigureHostResult:
        received.append(command)
        return ConfigureHostResult(
            host_id="codex",
            instruction_targets=["agents_md"],
            planned_changes=[],
            manual_steps=[],
            validation_status="success",
            audit_reference="not-applied",
            snapshot_reference="planned",
            timestamp="2026-05-28T20:00:00Z",
        )

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            host_setup=host_check,
            host_check=host_check,
        ),
        project_root=tmp_path,
    )

    result = await server.call_tool("host_check", {"host_id": "codex"})

    assert received == [
        ConfigureHostCommand(host_id="codex", apply=False, check=True, origin="mcp")
    ]
    payload = result.structured_content
    assert payload is not None
    assert payload["operation"] == "host_check"
    assert payload["data"]["validation_status"] == "success"


@pytest.mark.anyio
async def test_claude_code_host_setup_tool_returns_devex_contract_with_warnings(
    tmp_path: Path,
) -> None:
    def host_setup(command: ConfigureHostCommand) -> ConfigureHostResult:
        assert command.host_id == "claude_code"
        return ConfigureHostResult(
            host_id="claude_code",
            instruction_targets=["claude_md"],
            planned_changes=[{"target": "claude_md", "action": "create", "path": "CLAUDE.md"}],
            manual_steps=[],
            validation_status="success",
            audit_reference="uuid-v4-reference",
            snapshot_reference="uuid-v4-snapshot",
            timestamp="2026-05-29T00:00:00Z",
            warnings=["Instrucao duplicada em AGENTS.md e CLAUDE.md: Use relative paths."],
        )

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            host_setup=host_setup,
            host_check=host_setup,
        ),
        project_root=tmp_path,
    )

    result = await server.call_tool("host_setup", {"host_id": "claude_code", "force": True})

    assert result.structured_content == {
        "ok": True,
        "operation": "host_setup",
        "scope": "project",
        "data": {
            "host_id": "claude_code",
            "instruction_targets": ["claude_md"],
            "planned_changes": [{"target": "claude_md", "action": "create", "path": "CLAUDE.md"}],
            "manual_steps": [],
            "validation_status": "success",
            "audit_reference": "uuid-v4-reference",
            "snapshot_reference": "uuid-v4-snapshot",
            "timestamp": "2026-05-29T00:00:00Z",
        },
        "warnings": ["Instrucao duplicada em AGENTS.md e CLAUDE.md: Use relative paths."],
    }


@pytest.mark.anyio
async def test_sync_instructions_tool_uses_injected_use_case_and_matches_cli_json_contract(
    tmp_path: Path,
) -> None:
    received: list[SyncInstructionsCommand] = []

    def sync_instructions(command: SyncInstructionsCommand) -> SyncInstructionsResult:
        received.append(command)
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
            timestamp="2026-05-29T12:00:00Z",
        )

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            sync_instructions=sync_instructions,
        ),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool(
        "sync_instructions",
        {"host_ids": ["codex", "claude_code"], "apply": True},
    )

    assert "sync_instructions" in tool_names
    assert received == [
        SyncInstructionsCommand(host_ids=["codex", "claude_code"], apply=True, origin="mcp")
    ]
    assert result.structured_content == {
        "ok": True,
        "operation": "host_sync",
        "scope": "project",
        "data": {
            "host_ids": ["codex", "claude_code"],
            "instruction_targets": ["AGENTS.md", "CLAUDE.md"],
            "planned_changes": [
                {"target": "agents_md", "action": "create", "path": "AGENTS.md"},
                {"target": "claude_md", "action": "create", "path": "CLAUDE.md"},
            ],
            "manual_steps": [],
            "validation_status": "success",
            "audit_reference": "audit-1",
            "snapshot_reference": "snapshot-1",
            "timestamp": "2026-05-29T12:00:00Z",
        },
        "warnings": [],
    }


@pytest.mark.anyio
async def test_claude_code_host_check_tool_returns_devex_contract_with_warnings(
    tmp_path: Path,
) -> None:
    def host_check(command: ConfigureHostCommand) -> ConfigureHostResult:
        assert command.host_id == "claude_code"
        assert command.apply is False
        return ConfigureHostResult(
            host_id="claude_code",
            instruction_targets=["claude_md"],
            planned_changes=[],
            manual_steps=["Remova a duplicacao manualmente antes de aplicar setup."],
            validation_status="warning",
            audit_reference="not-applied",
            snapshot_reference="planned",
            timestamp="2026-05-29T00:00:00Z",
            warnings=["Instrucao duplicada em AGENTS.md e CLAUDE.md: Use relative paths."],
        )

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: initialized_status(),
            context=lambda _command: context_result(),
            host_setup=host_check,
            host_check=host_check,
        ),
        project_root=tmp_path,
    )

    result = await server.call_tool("host_check", {"host_id": "claude_code"})

    payload = result.structured_content
    assert payload is not None
    assert payload["operation"] == "host_check"
    assert payload["data"]["host_id"] == "claude_code"
    assert payload["data"]["instruction_targets"] == ["claude_md"]
    assert payload["data"]["manual_steps"] == [
        "Remova a duplicacao manualmente antes de aplicar setup."
    ]
    assert payload["data"]["snapshot_reference"] == "planned"
    assert payload["warnings"] == [
        "Instrucao duplicada em AGENTS.md e CLAUDE.md: Use relative paths."
    ]


@pytest.mark.anyio
async def test_mcp_errors_are_sanitized_without_absolute_paths_or_secret_values(
    tmp_path: Path,
) -> None:
    secret = "sk-test-secret-value"  # noqa: S105 - sentinel used to verify redaction.

    def status_use_case(_command: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        raise SecretDetectedError(f"Secret detected at {tmp_path}: {secret}")

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(status=status_use_case, context=lambda _command: context_result()),
        project_root=tmp_path,
    )

    result = await server.call_tool("status", {})
    payload = result.structured_content
    assert payload is not None
    error_payload = payload.get("structuredContent", payload)

    assert payload.get("isError", True) is True
    assert error_payload["ok"] is False
    assert error_payload["error"]["code"] == JSON_RPC_SECRET_DETECTED
    assert str(tmp_path) not in error_payload["error"]["data"]["detail"]
    assert secret not in error_payload["error"]["data"]["detail"]


@pytest.mark.anyio
async def test_bootstrap_server_uses_local_dependencies_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_network_access(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is not allowed during MCP bootstrap")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("socket.create_connection", fail_network_access)
    monkeypatch.setattr("socket.socket", fail_network_access)
    assert main(["init", "--format", "json"]) == 0

    server = build_server(tmp_path)
    result = await server.call_tool("status", {})
    payload = result.structured_content
    assert payload is not None

    assert payload["ok"] is True
    assert payload["operation"] == "status"
    assert payload["data"]["initialized"] is True
    assert payload["data"]["active_rules_count"] == 0
    assert payload["data"]["registered_skills_count"] == 0
