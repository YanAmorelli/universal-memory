from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from universal_memory.application.memory import GetMemoryStatusResult
from universal_memory.application.skills import (
    ActivateSkillCommand,
    ActivateSkillResult,
    DeactivateSkillCommand,
    DeactivateSkillResult,
    TrackLatentSkillCommand,
    TrackLatentSkillResult,
    UpdateSkillCommand,
    UpdateSkillResult,
)
from universal_memory.domain import SecretDetectedError, StorageError, ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.interfaces.mcp.server import (
    JSON_RPC_SECRET_DETECTED,
    JSON_RPC_STORAGE_ERROR,
    JSON_RPC_VALIDATION_FAILED,
    MCPUseCases,
    configure_server,
    create_mcp_server,
)

SKILL_ID = "11111111-1111-4111-8111-111111111111"
EXPECTED_MATCHED_RECURRENCE = 2


def make_skill(*, status: LatentSkillStatus = LatentSkillStatus.active) -> LatentSkill:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    return LatentSkill(
        id=SKILL_ID,
        created_at=now,
        updated_at=now,
        name="TDD Recorrente",
        description="Executa red green refactor",
        scope=LatentSkillScope.project,
        status=status,
        recurrence_count=4,
        metadata={"triggers": ["red green refactor"]},
    )


def activate_result() -> ActivateSkillResult:
    return ActivateSkillResult(
        latent_skill=make_skill(status=LatentSkillStatus.active),
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def deactivate_result() -> DeactivateSkillResult:
    return DeactivateSkillResult(
        latent_skill=make_skill(status=LatentSkillStatus.ignored),
        audit_reference="audit-2",
        snapshot_reference="snapshot-2",
    )


def update_result() -> UpdateSkillResult:
    return UpdateSkillResult(
        latent_skill=make_skill(status=LatentSkillStatus.active),
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        audit_reference="audit-3",
        snapshot_reference="snapshot-3",
        rollback_hint="Use rollback por escopo para restaurar o snapshot anterior.",
    )


def initialized_status() -> GetMemoryStatusResult:
    return GetMemoryStatusResult(
        initialized=True,
        project_path=".",
        fact_counts={},
        active_rules_count=0,
        registered_skills_count=0,
        approximate_size_bytes=0,
        last_health_check=None,
        host_validation={},
        recommended_action=None,
    )


def base_use_cases(**overrides):
    return MCPUseCases(
        status=cast(Any, lambda _command: initialized_status()),
        context=cast(Any, lambda _command: None),
        **overrides,
    )


@pytest.mark.anyio
async def test_activate_skill_tool_uses_mcp_origin_and_success_envelope(tmp_path: Path) -> None:
    seen: list[ActivateSkillCommand] = []

    def activate(command: ActivateSkillCommand) -> ActivateSkillResult:
        seen.append(command)
        return activate_result()

    server = configure_server(
        create_mcp_server(),
        base_use_cases(activate_skill=activate),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool("activate_skill", {"latent_skill_id": SKILL_ID})

    assert "activate_skill" in tool_names
    assert seen == [ActivateSkillCommand(latent_skill_id=SKILL_ID, origin="mcp")]
    assert result.structured_content == {
        "ok": True,
        "operation": "skills.activate",
        "scope": "project",
        "data": {
            "latent_skill": {
                "id": SKILL_ID,
                "name": "TDD Recorrente",
                "description": "Executa red green refactor",
                "status": "active",
                "scope": "project",
                "triggers": ["red green refactor"],
            },
            "skill_file": ".umem/skills/tdd-recorrente/SKILL.md",
            "audit_reference": "audit-1",
            "snapshot_reference": "snapshot-1",
        },
        "warnings": [],
    }


@pytest.mark.anyio
async def test_deactivate_skill_tool_uses_mcp_origin(tmp_path: Path) -> None:
    seen: list[DeactivateSkillCommand] = []

    def deactivate(command: DeactivateSkillCommand) -> DeactivateSkillResult:
        seen.append(command)
        return deactivate_result()

    server = configure_server(
        create_mcp_server(),
        base_use_cases(deactivate_skill=deactivate),
        project_root=tmp_path,
    )

    result = await server.call_tool("deactivate_skill", {"latent_skill_id": SKILL_ID})

    assert seen == [DeactivateSkillCommand(latent_skill_id=SKILL_ID, origin="mcp")]
    assert result.structured_content is not None
    assert result.structured_content["operation"] == "skills.deactivate"
    assert result.structured_content["data"]["latent_skill"]["status"] == "ignored"


@pytest.mark.anyio
async def test_update_skill_tool_passes_optional_metadata(tmp_path: Path) -> None:
    seen: list[UpdateSkillCommand] = []

    def update(command: UpdateSkillCommand) -> UpdateSkillResult:
        seen.append(command)
        return update_result()

    server = configure_server(
        create_mcp_server(),
        base_use_cases(update_skill=update),
        project_root=tmp_path,
    )

    result = await server.call_tool(
        "update_skill",
        {
            "latent_skill_id": SKILL_ID,
            "name": "Nome Novo",
            "description": "Descricao Nova",
            "triggers": ["trigger A", "trigger B"],
            "raw_markdown": "---\nname: Nome Novo\n---\n",
        },
    )

    assert seen == [
        UpdateSkillCommand(
            latent_skill_id=SKILL_ID,
            origin="mcp",
            name="Nome Novo",
            description="Descricao Nova",
            triggers=["trigger A", "trigger B"],
            raw_markdown="---\nname: Nome Novo\n---\n",
            native_drift_decision="keep",
        )
    ]
    assert result.structured_content is not None
    assert result.structured_content["operation"] == "skills.update"
    assert result.structured_content["data"]["audit_reference"] == "audit-3"


@pytest.mark.anyio
async def test_update_skill_tool_normalizes_inputs_like_cli(tmp_path: Path) -> None:
    seen: list[UpdateSkillCommand] = []

    def update(command: UpdateSkillCommand) -> UpdateSkillResult:
        seen.append(command)
        return update_result()

    server = configure_server(
        create_mcp_server(),
        base_use_cases(update_skill=update),
        project_root=tmp_path,
    )

    await server.call_tool(
        "update_skill",
        {
            "latent_skill_id": SKILL_ID,
            "name": "  Nome Novo  ",
            "description": "  Descricao Nova  ",
            "triggers": [" trigger A ", "", "  ", "trigger B"],
        },
    )

    assert seen == [
        UpdateSkillCommand(
            latent_skill_id=SKILL_ID,
            origin="mcp",
            name="Nome Novo",
            description="Descricao Nova",
            triggers=["trigger A", "trigger B"],
            raw_markdown=None,
            native_drift_decision="keep",
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (ValidationFailedError("invalid status"), JSON_RPC_VALIDATION_FAILED),
        (SecretDetectedError("blocked sk-test-secret-value"), JSON_RPC_SECRET_DETECTED),
        (StorageError("disk unavailable"), JSON_RPC_STORAGE_ERROR),
    ],
)
async def test_skill_tool_errors_are_json_rpc_safe(
    tmp_path: Path,
    error: Exception,
    expected_code: int,
) -> None:
    def activate(_command: ActivateSkillCommand) -> ActivateSkillResult:
        raise error

    server = configure_server(
        create_mcp_server(),
        base_use_cases(activate_skill=activate),
        project_root=tmp_path,
    )

    result = await server.call_tool("activate_skill", {"latent_skill_id": SKILL_ID})
    payload = result.structured_content
    assert payload is not None
    error_payload = payload.get("structuredContent", payload)

    assert payload.get("isError", True) is True
    assert error_payload["ok"] is False
    assert error_payload["operation"] == "skills.activate"
    assert error_payload["scope"] == "project"
    assert error_payload["warnings"] == []
    assert error_payload["error"]["code"] == expected_code
    assert "sk-test-secret-value" not in error_payload["error"]["data"]["detail"]


@pytest.mark.anyio
async def test_missing_skill_maps_storage_not_found_to_validation_failed(tmp_path: Path) -> None:
    def activate(_command: ActivateSkillCommand) -> ActivateSkillResult:
        raise StorageError(f"Latent skill not found: {SKILL_ID}")

    server = configure_server(
        create_mcp_server(),
        base_use_cases(activate_skill=activate),
        project_root=tmp_path,
    )

    result = await server.call_tool("activate_skill", {"latent_skill_id": SKILL_ID})
    payload = result.structured_content

    assert payload is not None
    error_payload = payload.get("structuredContent", payload)
    assert error_payload["error"]["code"] == JSON_RPC_VALIDATION_FAILED


def track_result(
    *,
    scope: LatentSkillScope = LatentSkillScope.project,
    matched_existing: bool = False,
) -> TrackLatentSkillResult:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    skill = LatentSkill(
        id=SKILL_ID,
        created_at=now,
        updated_at=now,
        name="TDD Recorrente",
        description="Executa red green refactor",
        scope=scope,
        status=LatentSkillStatus.proposed,
        recurrence_count=1 if not matched_existing else 2,
        metadata={"tags": ["tdd"], "evidence": [{"origin": "mcp", "summary": "test"}]},
    )
    return TrackLatentSkillResult(
        latent_skill=skill,
        matched_existing=matched_existing,
        audit_reference="audit-track",
        snapshot_reference="snapshot-track",
    )


@pytest.mark.anyio
async def test_track_latent_skill_tool_uses_mcp_origin_and_success_envelope(tmp_path: Path) -> None:
    seen: list[TrackLatentSkillCommand] = []

    def track(command: TrackLatentSkillCommand) -> TrackLatentSkillResult:
        seen.append(command)
        return track_result(matched_existing=False)

    server = configure_server(
        create_mcp_server(),
        base_use_cases(track_latent_skill=track),
        project_root=tmp_path,
    )

    result = await server.call_tool(
        "track_latent_skill",
        {
            "name": "TDD Recorrente",
            "description": "Executa red green refactor",
            "scope": "project",
            "evidence_summary": "test",
            "tags": ["tdd"],
        },
    )
    payload = result.structured_content
    assert payload is not None
    success_payload = payload.get("structuredContent", payload)

    assert payload.get("isError", False) is False
    assert seen == [
        TrackLatentSkillCommand(
            name="TDD Recorrente",
            description="Executa red green refactor",
            scope=LatentSkillScope.project,
            origin="mcp",
            evidence_summary="test",
            tags=["tdd"],
        )
    ]
    assert success_payload["ok"] is True
    assert success_payload["operation"] == "skills.track"
    assert success_payload["data"]["latent_skill"]["id"] == SKILL_ID
    assert success_payload["data"]["matched_existing"] is False


@pytest.mark.anyio
async def test_track_latent_skill_tool_surfaces_existing_match(tmp_path: Path) -> None:
    server = configure_server(
        create_mcp_server(),
        base_use_cases(track_latent_skill=lambda _command: track_result(matched_existing=True)),
        project_root=tmp_path,
    )

    result = await server.call_tool(
        "track_latent_skill",
        {
            "name": "TDD Recorrente",
            "description": "Executa red green refactor",
        },
    )
    payload = result.structured_content
    assert payload is not None
    success_payload = payload.get("structuredContent", payload)

    assert success_payload["data"]["matched_existing"] is True
    assert (
        success_payload["data"]["latent_skill"]["recurrence_count"] == EXPECTED_MATCHED_RECURRENCE
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (ValidationFailedError("invalid track input"), JSON_RPC_VALIDATION_FAILED),
        (SecretDetectedError("blocked password=123"), JSON_RPC_SECRET_DETECTED),
        (StorageError("disk unavailable"), JSON_RPC_STORAGE_ERROR),
    ],
)
async def test_track_latent_skill_tool_errors_are_json_rpc_safe(
    tmp_path: Path,
    error: Exception,
    expected_code: int,
) -> None:
    def track(_command: TrackLatentSkillCommand) -> TrackLatentSkillResult:
        raise error

    server = configure_server(
        create_mcp_server(),
        base_use_cases(track_latent_skill=track),
        project_root=tmp_path,
    )

    result = await server.call_tool(
        "track_latent_skill",
        {
            "name": "TDD Recorrente",
            "description": "password=123",
        },
    )
    payload = result.structured_content
    assert payload is not None
    error_payload = payload.get("structuredContent", payload)

    assert payload.get("isError", True) is True
    assert error_payload["ok"] is False
    assert error_payload["operation"] == "skills.track"
    assert error_payload["scope"] == "project"
    assert error_payload["error"]["code"] == expected_code
    assert "password=123" not in error_payload["error"]["data"]["detail"]


@pytest.mark.anyio
async def test_track_latent_skill_tool_error_uses_requested_global_scope() -> None:
    def track(_command: TrackLatentSkillCommand) -> TrackLatentSkillResult:
        raise StorageError("global store unavailable")

    server = configure_server(
        create_mcp_server(),
        base_use_cases(track_latent_skill=track),
        project_root=Path("/missing-project"),
    )

    result = await server.call_tool(
        "track_latent_skill",
        {
            "name": "TDD Recorrente",
            "description": "Executa red green refactor",
            "scope": "global",
        },
    )
    payload = result.structured_content
    assert payload is not None
    error_payload = payload.get("structuredContent", payload)

    assert error_payload["ok"] is False
    assert error_payload["scope"] == "global"
    assert error_payload["error"]["code"] == JSON_RPC_STORAGE_ERROR
