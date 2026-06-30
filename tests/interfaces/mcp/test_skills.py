from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from universal_memory.application.memory import GetMemoryStatusResult
from universal_memory.application.skills import (
    ActivateSkillCommand,
    ActivateSkillResult,
    CreateSkillCommand,
    CreateSkillResult,
    DeactivateSkillCommand,
    DeactivateSkillResult,
    ImportSkillCommand,
    ImportSkillResult,
    PromoteSkillRecommendationCommand,
    PromoteSkillRecommendationResult,
    RecommendSkillsCommand,
    RecommendSkillsResult,
    SkillRecommendationItem,
    SyncSkillResult,
    SyncSkillsCommand,
    SyncSkillsResult,
    TrackLatentSkillCommand,
    TrackLatentSkillResult,
    UpdateSkillCommand,
    UpdateSkillResult,
)
from universal_memory.domain import SecretDetectedError, StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
)
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
        rollback_hint="Use scoped rollback to restore the previous snapshot.",
    )


def create_result() -> CreateSkillResult:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id=SKILL_ID,
        created_at=now,
        updated_at=now,
        name="Launch Funnel Operator",
        slug="launch-funnel-operator",
        description="Operate launch funnel: CTAs and UTMs.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/launch-funnel-operator/SKILL.md",
        origin="mcp",
        audit_reference="audit-create",
        content_hash="hash-1",
        native_installations=[],
        metadata={"triggers": ["when creating launch schedules"], "creation_flow": "direct"},
    )
    return CreateSkillResult(
        agent_skill=skill,
        slug="launch-funnel-operator",
        skill_dir=".umem/skills/launch-funnel-operator",
        skill_file=".umem/skills/launch-funnel-operator/SKILL.md",
        created_paths=[".umem/skills/launch-funnel-operator/SKILL.md"],
        affected_paths=[".umem/skills/launch-funnel-operator/SKILL.md"],
        audit_reference="audit-create",
        snapshot_reference="snapshot-create",
    )


def promote_result() -> PromoteSkillRecommendationResult:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    source = LatentSkill(
        id=SKILL_ID,
        created_at=now,
        updated_at=now,
        name="Launch Funnel Operator",
        description="Operate launch funnel: CTAs and UTMs.",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.proposed,
        recurrence_count=3,
        metadata={"triggers": ["when creating launch schedules"]},
    )
    promoted = source.model_copy(
        update={
            "status": LatentSkillStatus.active,
            "metadata": {
                "promotion": {
                    "promoted_skill_id": SKILL_ID,
                    "promoted_at": "2026-05-29T12:00:00Z",
                }
            },
        }
    )
    create = create_result()
    create = CreateSkillResult(
        agent_skill=create.agent_skill.model_copy(update={"source_recommendation_id": SKILL_ID}),
        slug=create.slug,
        skill_dir=create.skill_dir,
        skill_file=create.skill_file,
        created_paths=create.created_paths,
        affected_paths=create.affected_paths,
        audit_reference=create.audit_reference,
        snapshot_reference=create.snapshot_reference,
        native_installations=create.native_installations,
        warnings=create.warnings,
    )
    return PromoteSkillRecommendationResult(
        create_result=create,
        source_recommendation=source,
        promoted_recommendation=promoted,
        audit_reference="audit-promote",
        snapshot_reference="snapshot-promote",
    )


def sync_result() -> SyncSkillsResult:
    return SyncSkillsResult(
        skills=[
            SyncSkillResult(
                skill_id=SKILL_ID,
                name="Launch Funnel Operator",
                scope="project",
                status="active",
                canonical_path=".umem/skills/launch-funnel-operator/SKILL.md",
                affected_paths=[".opencode/skills/launch-funnel-operator/SKILL.md"],
                removed_paths=[".opencode/skills/launch-funnel-operator/references/old.md"],
                targets=[
                    {
                        "runtime": "opencode",
                        "path": ".opencode/skills/launch-funnel-operator",
                        "status": "synced",
                        "drift_detected": False,
                        "canonical_hash": "canonical",
                        "target_hash": "target",
                        "hash_algorithm": "manifest_tree_sha256",
                        "audit_reference": "audit-sync",
                        "snapshot_reference": "snapshot-sync",
                        "affected_paths": ["SKILL.md"],
                        "removed_paths": ["references/old.md"],
                    }
                ],
                audit_reference="audit-sync",
                snapshot_reference="snapshot-sync",
            )
        ],
        affected_paths=[".opencode/skills/launch-funnel-operator/SKILL.md"],
        removed_paths=[".opencode/skills/launch-funnel-operator/references/old.md"],
        audit_reference="audit-sync",
        snapshot_reference="snapshot-sync",
    )


def import_result() -> ImportSkillResult:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id=SKILL_ID,
        created_at=now,
        updated_at=now,
        name="Review Helper",
        slug="review-helper",
        description="Review code with focused checks.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/review-helper/SKILL.md",
        origin="mcp",
        audit_reference="audit-import",
        content_hash="hash-1",
        native_installations=[],
        metadata={"triggers": ["when reviewing code"], "creation_flow": "import"},
    )
    return ImportSkillResult(
        agent_skill=skill,
        slug="review-helper",
        skill_dir=".umem/skills/review-helper",
        skill_file=".umem/skills/review-helper/SKILL.md",
        created_paths=[".umem/skills/review-helper/SKILL.md"],
        affected_paths=[".umem/skills/review-helper/SKILL.md"],
        audit_reference="audit-import",
        snapshot_reference="snapshot-import",
    )


def recommend_result() -> RecommendSkillsResult:
    return RecommendSkillsResult(
        recommendations=[
            SkillRecommendationItem(
                id=SKILL_ID,
                name="TDD Recorrente",
                description="Executa red green refactor",
                scope="project",
                status="proposed",
                recurrence_count=2,
                evidence_summaries=["first", "second"],
                tags=["tdd"],
                confidence=0.77,
                reasons=["recurrence_count 2 meets minimum recurrence threshold 2"],
                recommended_action=f"umem skills promote {SKILL_ID}",
            )
        ],
        thresholds={"min_recurrence": 2, "min_evidence_summaries": 2},
        evidence_sources=[{"source": "latent_skills", "description": "Tracked latent records."}],
        limitations=["First implementation only evaluates explicit `skills track` latent records."],
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


def uninitialized_status() -> GetMemoryStatusResult:
    return GetMemoryStatusResult(
        initialized=False,
        project_path=".",
        fact_counts={},
        active_rules_count=0,
        registered_skills_count=0,
        approximate_size_bytes=0,
        last_health_check=None,
        host_validation={},
        recommended_action="Run initialize_project first.",
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
async def test_create_skill_tool_uses_mcp_origin_and_success_envelope(tmp_path: Path) -> None:
    seen: list[CreateSkillCommand] = []

    def create(command: CreateSkillCommand) -> CreateSkillResult:
        seen.append(command)
        return create_result()

    server = configure_server(
        create_mcp_server(),
        base_use_cases(create_skill=create),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool(
        "create_skill",
        {
            "name": " Launch Funnel Operator ",
            "description": " Operate launch funnel: CTAs and UTMs. ",
            "scope": "project",
            "triggers": [" when creating launch schedules ", ""],
            "visibility": "shared",
            "category": "user-facing",
        },
    )
    payload = result.structured_content
    assert payload is not None
    success_payload = payload.get("structuredContent", payload)

    assert "create_skill" in tool_names
    assert seen == [
        CreateSkillCommand(
            name="Launch Funnel Operator",
            description="Operate launch funnel: CTAs and UTMs.",
            scope=LatentSkillScope.project,
            origin="mcp",
            triggers=["when creating launch schedules"],
            raw_markdown=None,
            visibility="shared",
            category="user-facing",
        )
    ]
    assert success_payload["ok"] is True
    assert success_payload["operation"] == "skills.create"
    assert success_payload["data"]["skill_file"] == ".umem/skills/launch-funnel-operator/SKILL.md"


@pytest.mark.anyio
async def test_promote_skill_recommendation_tool_passes_edits_and_targets(
    tmp_path: Path,
) -> None:
    seen: list[PromoteSkillRecommendationCommand] = []

    def promote(command: PromoteSkillRecommendationCommand) -> PromoteSkillRecommendationResult:
        seen.append(command)
        return promote_result()

    server = configure_server(
        create_mcp_server(),
        base_use_cases(promote_skill_recommendation=promote),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool(
        "promote_skill_recommendation",
        {
            "recommendation_id": SKILL_ID,
            "edits": {
                "name": " Edited Review Operator ",
                "description": " Edited description. ",
                "triggers": [" edited trigger ", ""],
            },
            "targets": [],
        },
    )
    payload = result.structured_content
    assert payload is not None
    success_payload = payload.get("structuredContent", payload)

    assert "promote_skill_recommendation" in tool_names
    assert seen == [
        PromoteSkillRecommendationCommand(
            recommendation_id=SKILL_ID,
            origin="mcp",
            name="Edited Review Operator",
            description="Edited description.",
            triggers=["edited trigger"],
            targets=[],
            project_initialized=True,
        )
    ]
    assert success_payload["ok"] is True
    assert success_payload["operation"] == "skills.promote"
    assert success_payload["data"]["source_recommendation_id"] == SKILL_ID


@pytest.mark.anyio
async def test_promote_skill_recommendation_tool_maps_missing_to_validation(
    tmp_path: Path,
) -> None:
    def promote(_command: PromoteSkillRecommendationCommand) -> PromoteSkillRecommendationResult:
        raise StorageError(f"Latent skill not found: {SKILL_ID}")

    server = configure_server(
        create_mcp_server(),
        base_use_cases(promote_skill_recommendation=promote),
        project_root=tmp_path,
    )

    result = await server.call_tool("promote_skill_recommendation", {"recommendation_id": SKILL_ID})
    payload = result.structured_content
    assert payload is not None
    error_payload = payload.get("structuredContent", payload)
    assert error_payload["ok"] is False
    assert error_payload["error"]["code"] == JSON_RPC_VALIDATION_FAILED


@pytest.mark.anyio
async def test_promote_global_skill_recommendation_does_not_require_project_initialized(
    tmp_path: Path,
) -> None:
    seen: list[PromoteSkillRecommendationCommand] = []

    def promote(command: PromoteSkillRecommendationCommand) -> PromoteSkillRecommendationResult:
        seen.append(command)
        result = promote_result()
        return PromoteSkillRecommendationResult(
            create_result=CreateSkillResult(
                agent_skill=result.create_result.agent_skill.model_copy(
                    update={"scope": LatentSkillScope.global_}
                ),
                slug=result.create_result.slug,
                skill_dir="skills/launch-funnel-operator",
                skill_file="skills/launch-funnel-operator/SKILL.md",
                created_paths=["skills/launch-funnel-operator/SKILL.md"],
                affected_paths=["skills/launch-funnel-operator/SKILL.md"],
                audit_reference=result.create_result.audit_reference,
                snapshot_reference=result.create_result.snapshot_reference,
                native_installations=result.create_result.native_installations,
                warnings=result.create_result.warnings,
            ),
            source_recommendation=result.source_recommendation.model_copy(
                update={"scope": LatentSkillScope.global_}
            ),
            promoted_recommendation=result.promoted_recommendation.model_copy(
                update={"scope": LatentSkillScope.global_}
            ),
            audit_reference=result.audit_reference,
            snapshot_reference=result.snapshot_reference,
        )

    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: uninitialized_status(),
            context=cast(Any, lambda _command: None),
            promote_skill_recommendation=promote,
        ),
        project_root=tmp_path,
    )

    result = await server.call_tool("promote_skill_recommendation", {"recommendation_id": SKILL_ID})
    payload = result.structured_content
    assert payload is not None
    success_payload = payload.get("structuredContent", payload)

    assert success_payload["ok"] is True
    assert success_payload["scope"] == "global"
    assert seen == [
        PromoteSkillRecommendationCommand(
            recommendation_id=SKILL_ID,
            origin="mcp",
            project_initialized=False,
        )
    ]


@pytest.mark.anyio
async def test_sync_skills_tool_uses_mcp_origin_and_success_envelope(tmp_path: Path) -> None:
    seen: list[SyncSkillsCommand] = []

    def sync(command: SyncSkillsCommand) -> SyncSkillsResult:
        seen.append(command)
        return sync_result()

    server = configure_server(
        create_mcp_server(),
        base_use_cases(sync_skills=sync),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool(
        "sync_skills",
        {
            "skill_id_or_name": "Launch Funnel Operator",
            "targets": ["opencode"],
            "drift_decision": "keep",
        },
    )
    payload = result.structured_content
    assert payload is not None
    success_payload = payload.get("structuredContent", payload)

    assert "sync_skills" in tool_names
    assert seen == [
        SyncSkillsCommand(
            skill_id_or_name="Launch Funnel Operator",
            targets=["opencode"],
            drift_decision="keep",
            origin="mcp",
        )
    ]
    assert success_payload["ok"] is True
    assert success_payload["operation"] == "skills.sync"
    assert success_payload["data"]["removed_paths"] == [
        ".opencode/skills/launch-funnel-operator/references/old.md"
    ]
    assert success_payload["data"]["skills"][0]["removed_paths"] == [
        ".opencode/skills/launch-funnel-operator/references/old.md"
    ]
    assert success_payload["data"]["skills"][0]["targets"][0]["removed_paths"] == [
        "references/old.md"
    ]
    assert (
        success_payload["data"]["skills"][0]["targets"][0]["hash_algorithm"]
        == "manifest_tree_sha256"
    )
    assert success_payload["data"]["skills"][0]["targets"][0]["status"] == "synced"


@pytest.mark.anyio
async def test_import_skill_tool_uses_mcp_origin_and_success_envelope(tmp_path: Path) -> None:
    seen: list[ImportSkillCommand] = []

    def import_skill(command: ImportSkillCommand) -> ImportSkillResult:
        seen.append(command)
        return import_result()

    server = configure_server(
        create_mcp_server(),
        base_use_cases(import_skill=import_skill),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool(
        "import_skill",
        {
            "path": "native/review-helper/SKILL.md",
            "scope": "project",
            "replace_native": True,
            "sync_after_import": True,
        },
    )
    payload = result.structured_content
    assert payload is not None
    success_payload = payload.get("structuredContent", payload)

    assert "import_skill" in tool_names
    assert seen == [
        ImportSkillCommand(
            path="native/review-helper/SKILL.md",
            scope=LatentSkillScope.project,
            origin="mcp",
            replace_native=True,
            sync_after_import=True,
        )
    ]
    assert success_payload["ok"] is True
    assert success_payload["operation"] == "skills.import"
    assert success_payload["data"]["skill_file"] == ".umem/skills/review-helper/SKILL.md"


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
async def test_recommend_skills_tool_delegates_to_use_case(tmp_path: Path) -> None:
    seen: list[RecommendSkillsCommand] = []

    def recommend(command: RecommendSkillsCommand) -> RecommendSkillsResult:
        seen.append(command)
        return recommend_result()

    server = configure_server(
        create_mcp_server(),
        base_use_cases(recommend_skills=recommend),
        project_root=tmp_path,
    )

    tool_names = {tool.name for tool in await server.list_tools()}
    result = await server.call_tool(
        "recommend_skills",
        {"scope": "project", "min_recurrence": 1, "dry_run": True},
    )
    payload = result.structured_content
    assert payload is not None
    success_payload = payload.get("structuredContent", payload)

    assert "recommend_skills" in tool_names
    assert seen == [RecommendSkillsCommand(scope=LatentSkillScope.project, min_recurrence=1)]
    assert success_payload["operation"] == "skills.recommend"
    assert success_payload["scope"] == "project"
    assert success_payload["data"] == recommend_result().to_payload()


@pytest.mark.anyio
async def test_recommend_skills_tool_supports_all_scope_and_validation_errors(
    tmp_path: Path,
) -> None:
    seen: list[RecommendSkillsCommand] = []

    def recommend(command: RecommendSkillsCommand) -> RecommendSkillsResult:
        seen.append(command)
        raise ValidationFailedError("min_recurrence must be at least 1.")

    server = configure_server(
        create_mcp_server(),
        base_use_cases(recommend_skills=recommend),
        project_root=tmp_path,
    )

    result = await server.call_tool("recommend_skills", {"scope": "all", "min_recurrence": 0})
    payload = result.structured_content
    assert payload is not None
    error_payload = payload.get("structuredContent", payload)

    assert seen == [RecommendSkillsCommand(scope=None, min_recurrence=0)]
    assert error_payload["ok"] is False
    assert error_payload["operation"] == "skills.recommend"
    assert error_payload["error"]["code"] == JSON_RPC_VALIDATION_FAILED


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
