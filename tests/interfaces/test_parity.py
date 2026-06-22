from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from universal_memory.application.diagnostics import DoctorCheck, DoctorResult
from universal_memory.application.memory import (
    AssembleContextSummaryResult,
    GetMemoryStatusResult,
    ListFactsResult,
    PurgeFactResult,
    RememberFactCommand,
    RememberFactResult,
)
from universal_memory.application.onboarding import SetupProjectResult
from universal_memory.application.security import (
    AuditLogEntry,
    ListAuditLogResult,
    ListSnapshotsResult,
    RollbackResult,
    SnapshotEntry,
)
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
    ProposeSkillCommand,
    ProposeSkillDecision,
    ProposeSkillResult,
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
from universal_memory.domain import SecretDetectedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    ContextSummary,
    ContextSummaryScope,
    Fact,
    FactScope,
    FactStatus,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
)
from universal_memory.interfaces.cli.init_command import create_typer_app
from universal_memory.interfaces.cli.init_command import main as cli_main
from universal_memory.interfaces.mcp.server import (
    JSON_RPC_SECRET_DETECTED,
    MCPUseCases,
    configure_server,
    create_mcp_server,
)

FACT_ID = "11111111-1111-4111-8111-111111111111"
SECRET_SENTINEL = "sk-test-secret-value"  # noqa: S105 - sentinel used to verify redaction.

PARITY_EXCLUSIONS = {
    # Epic 5 backlog: host adapters and host checks are not implemented yet.
    "check_host",
    # Epic 6 backlog: skill registry use cases are not implemented yet.
    "list_skills",
    # Future rules capability: no business use case exists in the current implementation.
    "propose_rule",
}

PARITY_MATRIX = {
    "init": "initialize_project",
    "status": "status",
    "doctor": "doctor",
    "context": "context",
    "remember": "remember_fact",
    "facts.list": "list_facts",
    "facts.purge": "purge_fact",
    "facts.hygiene": None,
    "audit.list": "list_audit_events",
    "snapshots.list": "list_snapshots",
    "rollback": "rollback_scope",
    "host.setup_check": "check_host",
    "skills.propose": "propose_skill",
    "skills.track": "track_latent_skill",
    "skills.create": "create_skill",
    "skills.promote": "promote_skill_recommendation",
    "skills.sync": "sync_skills",
    "skills.import": "import_skill",
    "skills.list": "list_skills",
    "skills.recommend": "recommend_skills",
    "skills.activate": "activate_skill",
    "skills.deactivate": "deactivate_skill",
    "skills.update": "update_skill",
    "rules.propose": "propose_rule",
}


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


def doctor_result() -> DoctorResult:
    return DoctorResult(
        checks=[
            DoctorCheck(
                name="python_version",
                status="success",
                detail="Python 3.12.13",
            )
        ]
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


def cli_app_command_names() -> set[str]:
    app = create_typer_app(
        setup_project_command=setup_result,
        status_command=lambda _command: status_result(),
        doctor_command=lambda _command: doctor_result(),
        context_command=lambda _command: context_result(),
        remember_command=lambda _command: RememberFactResult(
            fact=fact_fixture(),
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        ),
        facts_list_command=lambda _command: ListFactsResult(facts=[]),
        facts_purge_command=lambda _command: PurgeFactResult(0, [], "audit-1"),
        audit_list_command=lambda _command: ListAuditLogResult(events=[]),
        snapshots_list_command=lambda _command: ListSnapshotsResult(snapshots=[]),
        rollback_command=lambda command: RollbackResult(
            scope=command.scope,
            snapshot_reference="snapshot-1",
            restored_paths=[".umem/memory/facts.jsonl"],
            audit_reference="audit-1",
        ),
        rollback_preview_command=lambda _scope: pytest.fail("preview not used by parity listing"),
    )
    return {
        command.name or (command.callback.__name__.replace("_", ".") if command.callback else "")
        for command in app.registered_commands
    } | {
        f"{group.name}.{command.name}"
        for group in app.registered_groups
        if group.typer_instance is not None
        for command in group.typer_instance.registered_commands
    }


@pytest.mark.anyio
async def test_public_cli_capabilities_have_matching_mcp_tools() -> None:
    cli_names = cli_app_command_names()
    server = configure_server(create_mcp_server(), mcp_use_cases())
    mcp_names = {tool.name for tool in await server.list_tools()}

    for cli_capability, mcp_tool in PARITY_MATRIX.items():
        if mcp_tool is None or mcp_tool in PARITY_EXCLUSIONS:
            continue
        assert cli_capability in cli_names
        assert mcp_tool in mcp_names


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("cli_args", "mcp_tool", "mcp_args"),
    [
        (["init", "--format", "json"], "initialize_project", {}),
        (["status", "--format", "json"], "status", {}),
        (["doctor", "--format", "json"], "doctor", {}),
        (["context", "--format", "json"], "context", {}),
        (
            ["remember", "Use respostas concisas.", "--format", "json"],
            "remember_fact",
            {"content": "Use respostas concisas."},
        ),
        (["facts", "list", "--format", "json"], "list_facts", {}),
        (
            ["facts", "purge", "--id", FACT_ID, "--yes", "--format", "json"],
            "purge_fact",
            {"id": FACT_ID, "confirm": True},
        ),
        (["audit", "list", "--format", "json"], "list_audit_events", {}),
        (["snapshots", "list", "--format", "json"], "list_snapshots", {}),
        (["rollback", "--yes", "--format", "json"], "rollback_scope", {"confirm": True}),
        (
            [
                "skills",
                "create",
                "--name",
                "TDD recorrente",
                "--description",
                "Usuario pede ciclo red green refactor",
                "--scope",
                "project",
                "--trigger",
                "red green refactor",
                "--format",
                "json",
            ],
            "create_skill",
            {
                "name": "TDD recorrente",
                "description": "Usuario pede ciclo red green refactor",
                "scope": "project",
                "triggers": ["red green refactor"],
            },
        ),
        (
            [
                "skills",
                "import",
                "native/review-helper/SKILL.md",
                "--scope",
                "project",
                "--replace-native",
                "--format",
                "json",
            ],
            "import_skill",
            {
                "path": "native/review-helper/SKILL.md",
                "scope": "project",
                "replace_native": True,
            },
        ),
        (
            [
                "skills",
                "import",
                "native/review-helper/SKILL.md",
                "--scope",
                "project",
                "--sync",
                "--format",
                "json",
            ],
            "import_skill",
            {
                "path": "native/review-helper/SKILL.md",
                "scope": "project",
                "sync_after_import": True,
            },
        ),
        (
            [
                "skills",
                "propose",
                "11111111-1111-4111-8111-111111111111",
                "--yes",
                "--format",
                "json",
            ],
            "propose_skill",
            {"latent_skill_id": "11111111-1111-4111-8111-111111111111", "decision": "yes"},
        ),
        (
            [
                "skills",
                "promote",
                "11111111-1111-4111-8111-111111111111",
                "--yes",
                "--name",
                "TDD recorrente",
                "--description",
                "Usuario pede ciclo red green refactor",
                "--trigger",
                "red green refactor",
                "--format",
                "json",
            ],
            "promote_skill_recommendation",
            {
                "recommendation_id": "11111111-1111-4111-8111-111111111111",
                "edits": {
                    "name": "TDD recorrente",
                    "description": "Usuario pede ciclo red green refactor",
                    "triggers": ["red green refactor"],
                },
            },
        ),
        (
            [
                "skills",
                "activate",
                "11111111-1111-4111-8111-111111111111",
                "--format",
                "json",
            ],
            "activate_skill",
            {"latent_skill_id": "11111111-1111-4111-8111-111111111111"},
        ),
        (
            [
                "skills",
                "deactivate",
                "11111111-1111-4111-8111-111111111111",
                "--format",
                "json",
            ],
            "deactivate_skill",
            {"latent_skill_id": "11111111-1111-4111-8111-111111111111"},
        ),
        (
            [
                "skills",
                "update",
                "11111111-1111-4111-8111-111111111111",
                "--name",
                "TDD recorrente",
                "--description",
                "Usuario pede ciclo red green refactor",
                "--trigger",
                "red green refactor",
                "--format",
                "json",
            ],
            "update_skill",
            {
                "latent_skill_id": "11111111-1111-4111-8111-111111111111",
                "name": "TDD recorrente",
                "description": "Usuario pede ciclo red green refactor",
                "triggers": ["red green refactor"],
            },
        ),
        (
            [
                "skills",
                "sync",
                "TDD recorrente",
                "--target",
                "opencode",
                "--format",
                "json",
            ],
            "sync_skills",
            {
                "skill_id_or_name": "TDD recorrente",
                "targets": ["opencode"],
                "drift_decision": "keep",
            },
        ),
        (
            ["skills", "recommend", "--scope", "project", "--format", "json"],
            "recommend_skills",
            {"scope": "project", "dry_run": True},
        ),
        (
            [
                "skills",
                "track",
                "--name",
                "TDD recorrente",
                "--description",
                "Usuario pede ciclo red green refactor",
                "--scope",
                "project",
                "--tag",
                "red green refactor",
                "--format",
                "json",
            ],
            "track_latent_skill",
            {
                "name": "TDD recorrente",
                "description": "Usuario pede ciclo red green refactor",
                "scope": "project",
                "tags": ["red green refactor"],
            },
        ),
    ],
)
async def test_cli_and_mcp_json_data_keys_match_for_public_capabilities(  # noqa: PLR0913
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cli_args: list[str],
    mcp_tool: str,
    mcp_args: dict[str, Any],
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(cli_args, **cli_use_cases(tmp_path))
    cli_payload = json.loads(capsys.readouterr().out)
    server = configure_server(create_mcp_server(), mcp_use_cases(tmp_path), project_root=tmp_path)
    mcp_payload = (await server.call_tool(mcp_tool, mcp_args)).structured_content

    assert exit_code == 0
    assert mcp_payload is not None
    assert_contract_data_equivalent(cli_payload["data"], mcp_payload["data"], capability=mcp_tool)


@pytest.mark.anyio
async def test_import_cli_and_mcp_json_data_keys_match_without_other_skill_capabilities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    cli_exit_code = cli_main(
        [
            "skills",
            "import",
            "native/review-helper/SKILL.md",
            "--scope",
            "project",
            "--replace-native",
            "--format",
            "json",
        ],
        import_skill_command=import_skill_result,
    )
    cli_payload = json.loads(capsys.readouterr().out)
    server = configure_server(
        create_mcp_server(),
        MCPUseCases(
            status=lambda _command: status_result(),
            context=lambda _command: context_result(),
            import_skill=import_skill_result,
        ),
        project_root=tmp_path,
    )
    mcp_payload = (
        await server.call_tool(
            "import_skill",
            {
                "path": "native/review-helper/SKILL.md",
                "scope": "project",
                "replace_native": True,
            },
        )
    ).structured_content

    assert cli_exit_code == 0
    assert mcp_payload is not None
    assert_contract_data_equivalent(
        cli_payload["data"], mcp_payload["data"], capability="import_skill"
    )


@pytest.mark.anyio
async def test_mcp_domain_errors_use_json_rpc_codes_and_sanitized_detail(tmp_path: Path) -> None:
    def remember_error(_command: RememberFactCommand) -> RememberFactResult:
        raise SecretDetectedError(f"blocked {tmp_path}: {SECRET_SENTINEL}")

    use_cases = replace(mcp_use_cases(tmp_path), remember=remember_error)
    server = configure_server(create_mcp_server(), use_cases, project_root=tmp_path)

    payload = (await server.call_tool("remember_fact", {"content": "secret"})).structured_content

    assert payload is not None
    error_payload = payload.get("structuredContent", payload)
    assert payload.get("isError", True) is True
    assert error_payload["ok"] is False
    assert error_payload["error"]["code"] == JSON_RPC_SECRET_DETECTED
    assert str(tmp_path) not in error_payload["error"]["data"]["detail"]
    assert SECRET_SENTINEL not in error_payload["error"]["data"]["detail"]


def cli_use_cases(project_root: Path) -> dict[str, Any]:
    return {
        "setup_project_command": lambda _root: setup_result(project_root),
        "status_command": lambda _command: status_result(),
        "doctor_command": lambda _command: doctor_result(),
        "context_command": lambda _command: context_result(),
        "remember_command": lambda _command: RememberFactResult(
            fact=fact_fixture(),
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        ),
        "facts_list_command": lambda _command: ListFactsResult(facts=[fact_fixture()]),
        "facts_purge_command": lambda _command: PurgeFactResult(1, ["fact-1"], "audit-1"),
        "audit_list_command": lambda _command: ListAuditLogResult(events=[audit_entry_fixture()]),
        "snapshots_list_command": lambda _command: ListSnapshotsResult(
            snapshots=[snapshot_entry_fixture()]
        ),
        "rollback_command": lambda command: RollbackResult(
            scope=command.scope,
            snapshot_reference="snapshot-1",
            restored_paths=[".umem/memory/facts.jsonl"],
            audit_reference="audit-1",
        ),
        "rollback_preview_command": lambda _scope: object(),
        "propose_skill_command": propose_skill_result,
        "track_latent_skill_command": track_latent_skill_result,
        "create_skill_command": create_skill_result,
        "promote_skill_recommendation_command": promote_skill_recommendation_result,
        "sync_skills_command": sync_skills_result,
        "import_skill_command": import_skill_result,
        "recommend_skills_command": recommend_skills_result,
        "activate_skill_command": activate_skill_result,
        "deactivate_skill_command": deactivate_skill_result,
        "update_skill_command": update_skill_result,
    }


def mcp_use_cases(project_root: Path | None = None) -> MCPUseCases:
    root = project_root or Path(".")
    return MCPUseCases(
        initialize_project=lambda _project_root: setup_result(root),
        status=lambda _command: status_result(),
        doctor=lambda _command: doctor_result(),
        context=lambda _command: context_result(),
        remember=lambda _command: RememberFactResult(
            fact=fact_fixture(),
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        ),
        list_facts=lambda _command: ListFactsResult(facts=[fact_fixture()]),
        purge_fact=lambda _command: PurgeFactResult(1, ["fact-1"], "audit-1"),
        list_audit_events=lambda _command: ListAuditLogResult(events=[audit_entry_fixture()]),
        list_snapshots=lambda _command: ListSnapshotsResult(snapshots=[snapshot_entry_fixture()]),
        rollback_scope=lambda command: RollbackResult(
            scope=command.scope,
            snapshot_reference="snapshot-1",
            restored_paths=[".umem/memory/facts.jsonl"],
            audit_reference="audit-1",
        ),
        propose_skill=propose_skill_result,
        track_latent_skill=track_latent_skill_result,
        create_skill=create_skill_result,
        promote_skill_recommendation=promote_skill_recommendation_result,
        sync_skills=sync_skills_result,
        import_skill=import_skill_result,
        recommend_skills=recommend_skills_result,
        activate_skill=activate_skill_result,
        deactivate_skill=deactivate_skill_result,
        update_skill=update_skill_result,
    )


def track_latent_skill_result(command: TrackLatentSkillCommand) -> TrackLatentSkillResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    skill = LatentSkill(
        id="11111111-1111-4111-8111-111111111111",
        created_at=now,
        updated_at=now,
        name=command.name,
        description=command.description,
        scope=command.scope,
        status=LatentSkillStatus.proposed,
        recurrence_count=1,
        metadata={"tags": command.tags},
    )
    return TrackLatentSkillResult(
        latent_skill=skill,
        matched_existing=False,
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
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
        status=LatentSkillStatus.active
        if command.decision != ProposeSkillDecision.nao
        else LatentSkillStatus.ignored,
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
        accepted=command.decision in {ProposeSkillDecision.sim, ProposeSkillDecision.sempre},
        auto_approval_recorded=command.decision == ProposeSkillDecision.sempre,
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def create_skill_result(command: CreateSkillCommand) -> CreateSkillResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id="11111111-1111-4111-8111-111111111111",
        created_at=now,
        updated_at=now,
        name=command.name,
        slug="tdd-recorrente",
        description=command.description,
        scope=command.scope,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/tdd-recorrente/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"triggers": command.triggers or [], "creation_flow": "direct"},
    )
    return CreateSkillResult(
        agent_skill=skill,
        slug="tdd-recorrente",
        skill_dir=".umem/skills/tdd-recorrente",
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        created_paths=[".umem/skills/tdd-recorrente/SKILL.md"],
        affected_paths=[".umem/skills/tdd-recorrente/SKILL.md"],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def promote_skill_recommendation_result(
    command: PromoteSkillRecommendationCommand,
) -> PromoteSkillRecommendationResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    source = LatentSkill(
        id=command.recommendation_id,
        created_at=now,
        updated_at=now,
        name=command.name or "TDD recorrente",
        description=command.description or "Usuario pede ciclo red green refactor",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.proposed,
        recurrence_count=3,
        metadata={"triggers": command.triggers or ["red green refactor"]},
    )
    create = create_skill_result(
        CreateSkillCommand(
            name=source.name,
            description=source.description,
            scope=source.scope,
            origin=command.origin,
            triggers=command.triggers,
            targets=command.targets,
            source_recommendation_id=command.recommendation_id,
        )
    )
    create = CreateSkillResult(
        agent_skill=create.agent_skill.model_copy(
            update={"source_recommendation_id": command.recommendation_id}
        ),
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
    promoted = source.model_copy(
        update={
            "status": LatentSkillStatus.active,
            "metadata": {
                "promotion": {
                    "promoted_skill_id": create.agent_skill.id,
                    "promoted_at": "2026-05-28T12:00:00Z",
                }
            },
        }
    )
    return PromoteSkillRecommendationResult(
        create_result=create,
        source_recommendation=source,
        promoted_recommendation=promoted,
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def sync_skills_result(command: SyncSkillsCommand) -> SyncSkillsResult:
    return SyncSkillsResult(
        skills=[
            SyncSkillResult(
                skill_id="11111111-1111-4111-8111-111111111111",
                name=command.skill_id_or_name or "TDD recorrente",
                scope="project",
                status="active",
                canonical_path=".umem/skills/tdd-recorrente/SKILL.md",
                affected_paths=[".opencode/skills/tdd-recorrente/SKILL.md"],
                targets=[
                    {
                        "runtime": "opencode",
                        "path": ".opencode/skills/tdd-recorrente",
                        "status": "synced",
                        "drift_detected": False,
                        "canonical_hash": "canonical",
                        "target_hash": "target",
                        "audit_reference": "audit-1",
                        "snapshot_reference": "snapshot-1",
                        "affected_paths": ["SKILL.md"],
                    }
                ],
                audit_reference="audit-1",
                snapshot_reference="snapshot-1",
            )
        ],
        affected_paths=[".opencode/skills/tdd-recorrente/SKILL.md"],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def import_skill_result(command: ImportSkillCommand) -> ImportSkillResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id="11111111-1111-4111-8111-111111111111",
        created_at=now,
        updated_at=now,
        name="Imported Skill",
        slug="imported-skill",
        description="Imported from native skill directory.",
        scope=command.scope,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/imported-skill/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"triggers": [], "creation_flow": "import"},
    )
    return ImportSkillResult(
        agent_skill=skill,
        slug="imported-skill",
        skill_dir=".umem/skills/imported-skill",
        skill_file=".umem/skills/imported-skill/SKILL.md",
        created_paths=[".umem/skills/imported-skill/SKILL.md"],
        affected_paths=[".umem/skills/imported-skill/SKILL.md"],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def recommend_skills_result(_command: RecommendSkillsCommand) -> RecommendSkillsResult:
    return RecommendSkillsResult(
        recommendations=[
            SkillRecommendationItem(
                id=FACT_ID,
                name="TDD recorrente",
                description="Usuario pede ciclo red green refactor",
                scope="project",
                status="proposed",
                recurrence_count=2,
                evidence_summaries=["first", "second"],
                tags=["tdd"],
                confidence=0.77,
                reasons=["recurrence_count 2 meets minimum recurrence threshold 2"],
                recommended_action=f"umem skills promote {FACT_ID}",
            )
        ],
        thresholds={"min_recurrence": 2, "min_evidence_summaries": 2},
        evidence_sources=[{"source": "latent_skills", "description": "Tracked latent records."}],
        limitations=["First implementation only evaluates explicit `skills track` latent records."],
    )


def mutation_skill(
    command: ActivateSkillCommand | DeactivateSkillCommand | UpdateSkillCommand,
) -> LatentSkill:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    status = (
        LatentSkillStatus.ignored
        if isinstance(command, DeactivateSkillCommand)
        else LatentSkillStatus.active
    )
    return LatentSkill(
        id=command.latent_skill_id,
        created_at=now,
        updated_at=now,
        name=getattr(command, "name", None) or "TDD recorrente",
        description=getattr(command, "description", None)
        or "Usuario pede ciclo red green refactor",
        scope=LatentSkillScope.project,
        status=status,
        recurrence_count=3,
        metadata={"triggers": getattr(command, "triggers", None) or ["red green refactor"]},
    )


def activate_skill_result(command: ActivateSkillCommand) -> ActivateSkillResult:
    return ActivateSkillResult(
        latent_skill=mutation_skill(command),
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def deactivate_skill_result(command: DeactivateSkillCommand) -> DeactivateSkillResult:
    return DeactivateSkillResult(
        latent_skill=mutation_skill(command),
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def update_skill_result(command: UpdateSkillCommand) -> UpdateSkillResult:
    return UpdateSkillResult(
        latent_skill=mutation_skill(command),
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def audit_entry_fixture() -> AuditLogEntry:
    return AuditLogEntry(
        timestamp="2026-05-28T12:00:00Z",
        action="remember_fact",
        scope="project",
        origin="test",
        result="success",
        snapshot_reference="snapshot-1",
        audit_reference="audit-1",
    )


def snapshot_entry_fixture() -> SnapshotEntry:
    return SnapshotEntry(
        timestamp="2026-05-28T12:00:00Z",
        scope="project",
        origin="test",
        action="remember_fact",
        relative_path=".umem/memory/facts.jsonl",
        hash="abc123",
        manifest_path=".umem/snapshots/manifest.json",
    )


def assert_contract_data_equivalent(
    cli_data: dict[str, Any],
    mcp_data: dict[str, Any],
    *,
    capability: str,
) -> None:
    assert set(cli_data) == set(mcp_data), (
        f"{capability}: data keys differ; "
        f"missing_in_mcp={sorted(set(cli_data) - set(mcp_data))} "
        f"extra_in_mcp={sorted(set(mcp_data) - set(cli_data))}"
    )
    _assert_contract_shape(cli_data, mcp_data, path=capability)


def _assert_contract_shape(left: Any, right: Any, *, path: str) -> None:
    assert type(left) is type(right), (
        f"{path}: type mismatch; CLI={type(left).__name__}, MCP={type(right).__name__}"
    )
    if isinstance(left, dict):
        assert set(left) == set(right), (
            f"{path}: object keys differ; "
            f"missing_in_mcp={sorted(set(left) - set(right))} "
            f"extra_in_mcp={sorted(set(right) - set(left))}"
        )
        for key in sorted(left):
            _assert_contract_shape(left[key], right[key], path=f"{path}.{key}")
        return
    if isinstance(left, list):
        assert len(left) == len(right), (
            f"{path}: list length differs; CLI={len(left)}, MCP={len(right)}"
        )
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            _assert_contract_shape(left_item, right_item, path=f"{path}[{index}]")
        return
    assert left == right, f"{path}: value mismatch; CLI={left!r}, MCP={right!r}"


@pytest.mark.anyio
async def test_mcp_destructive_mutations_require_confirm_flag(tmp_path: Path) -> None:
    server = configure_server(create_mcp_server(), mcp_use_cases(tmp_path), project_root=tmp_path)

    # Calling without confirm=True should return a validation error envelope
    purge_payload = (await server.call_tool("purge_fact", {"confirm": False})).structured_content
    assert purge_payload is not None
    purge_error = purge_payload.get("structuredContent", purge_payload)
    assert purge_payload.get("isError", True) is True
    assert purge_error["ok"] is False
    assert "destructive" in purge_error["error"]["data"]["detail"]

    rollback_res = await server.call_tool("rollback_scope", {"confirm": False})
    rollback_payload = rollback_res.structured_content
    assert rollback_payload is not None
    rollback_error = rollback_payload.get("structuredContent", rollback_payload)
    assert rollback_payload.get("isError", True) is True
    assert rollback_error["ok"] is False
    assert "destructive" in rollback_error["error"]["data"]["detail"]
