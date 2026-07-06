from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from universal_memory.application.diagnostics import DoctorCheck, DoctorResult
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
from universal_memory.application.skills import (
    ActivateSkillCommand,
    ActivateSkillResult,
    AdoptSkillResult,
    CleanupPlan,
    CleanupSkillResult,
    CreateSkillCommand,
    CreateSkillResult,
    DeactivateSkillCommand,
    DeactivateSkillResult,
    DraftSkillResult,
    GenerateSkillCommand,
    GenerateSkillResult,
    GetSkillDetailCommand,
    GetSkillDetailResult,
    ImportSkillCommand,
    ImportSkillResult,
    ListSkillsCommand,
    ListSkillsResult,
    PromoteSkillRecommendationCommand,
    PromoteSkillRecommendationResult,
    ProposeSkillCommand,
    ProposeSkillResult,
    PublishSkillResult,
    RecommendSkillsCommand,
    RecommendSkillsResult,
    RenameSkillResult,
    RepairSkillsResult,
    ShareSkillResult,
    SkillListItem,
    SkillRecommendationItem,
    SkillValidationReport,
    SyncSkillResult,
    SyncSkillsCommand,
    SyncSkillsResult,
    TrackLatentSkillCommand,
    TrackLatentSkillResult,
    UpdateCanonicalSkillResult,
    UpdateSkillCommand,
    UpdateSkillResult,
    ValidateSkillResult,
)
from universal_memory.domain import StorageError
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
    "inspect_project_layout": {},
    "status": {},
    "doctor": {},
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
    "propose_skill": {"latent_skill_id": FACT_ID, "decision": "yes"},
    "create_skill": {
        "name": "TDD recorrente",
        "description": "Usuario pede ciclo red green refactor",
        "triggers": ["red green refactor"],
    },
    "create_skill_draft": {
        "name": "Draft Helper",
        "description": "Draft skill.",
        "triggers": ["draft"],
    },
    "validate_skill": {"skill_or_path": "tdd-recorrente"},
    "publish_skill": {"draft_or_path": "draft-helper"},
    "share_skill": {
        "skill_id_or_name": "use-universal-memory",
        "category": "operational",
        "confirm_operational": True,
    },
    "import_skill": {
        "path": "native/tdd-recorrente/SKILL.md",
        "replace_native": True,
        "sync_after_import": True,
    },
    "adopt_skill": {"path": ".umem/skills/tdd-recorrente", "slug": "tdd-recorrente"},
    "update_canonical_skill": {
        "skill_id_or_name": "tdd-recorrente",
        "raw_markdown": "---\nname: TDD recorrente\ndescription: Usuario pede ciclo\n---\n",
    },
    "rename_skill": {"skill_id_or_name": "tdd-recorrente", "slug": "tdd-renamed"},
    "cleanup_skill": {"skill_id_or_name": "tdd-recorrente", "dry_run": True},
    "repair_skills": {"remove_orphan_targets": True, "dry_run": True},
    "promote_skill_recommendation": {"recommendation_id": FACT_ID, "targets": []},
    "generate_skill": {"latent_skill_id": FACT_ID},
    "sync_skills": {"skill_id_or_name": "TDD recorrente", "targets": ["opencode"]},
    "list_skills": {},
    "recommend_skills": {"scope": "project", "dry_run": True},
    "get_skill_detail": {"name_or_id": "TDD recorrente"},
    "activate_skill": {"latent_skill_id": FACT_ID},
    "deactivate_skill": {"latent_skill_id": FACT_ID},
    "update_skill": {
        "latent_skill_id": FACT_ID,
        "name": "TDD recorrente",
        "description": "Usuario pede ciclo red green refactor",
        "triggers": ["red green refactor"],
    },
    "track_latent_skill": {
        "name": "TDD recorrente",
        "description": "Usuario pede ciclo red green refactor",
    },
    "migrate_project_layout": {"target_layout": "shared", "dry_run": True},
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
        "layout",
        "shared_root",
        "operational_root",
        "shared_paths",
        "operational_paths",
    },
    "inspect_project_layout": {
        "operation",
        "layout",
        "shared_root",
        "operational_root",
        "precedence",
        "warnings",
        "recommended_actions",
        "git_status_available",
        "ignored_shared_paths",
        "tracked_operational_paths",
        "overlaps",
    },
    "migrate_project_layout": {
        "operation",
        "source_layout",
        "target_layout",
        "dry_run",
        "copied",
        "already_shared",
        "skipped",
        "conflicts",
        "remaining_local",
        "affected_paths",
        "next_steps",
        "warnings",
    },
    "status": {
        "initialized",
        "project_path",
        "installed_version",
        "fact_counts",
        "active_rules_count",
        "registered_skills_count",
        "approximate_size_bytes",
        "last_health_check",
        "host_validation",
        "layout",
        "shared_root",
        "operational_root",
        "path_counts",
    },
    "doctor": {"checks", "summary"},
    "context": {
        "project_summary",
        "universal_preferences",
        "active_rules",
        "source_fact_ids",
        "truncated",
        "token_estimate",
        "last_read_at",
    },
    "remember_fact": {
        "fact_id",
        "scope",
        "status",
        "tags",
        "visibility",
        "storage_path",
        "created_at",
        "audit_reference",
    },
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
    "generate_skill": {
        "skill_id",
        "name",
        "slug",
        "skill_dir",
        "skill_file",
        "created_paths",
        "affected_paths",
        "audit_reference",
        "snapshot_reference",
        "native_installations",
        "collision_detected",
        "suggested_slug",
    },
    "create_skill": {
        "skill_id",
        "name",
        "slug",
        "skill_dir",
        "skill_file",
        "created_paths",
        "affected_paths",
        "audit_reference",
        "snapshot_reference",
        "native_installations",
        "visibility",
        "category",
        "canonical_skill",
    },
    "create_skill_draft": {
        "skill_id",
        "name",
        "slug",
        "draft_path",
        "affected_paths",
        "audit_reference",
        "snapshot_reference",
        "warnings",
    },
    "validate_skill": {"validation"},
    "publish_skill": {
        "skill_id",
        "name",
        "slug",
        "skill_dir",
        "skill_file",
        "affected_paths",
        "audit_reference",
        "snapshot_reference",
        "native_installations",
        "validation",
        "canonical_skill",
        "visibility",
        "category",
    },
    "share_skill": {
        "skill_id",
        "name",
        "slug",
        "skill_dir",
        "skill_file",
        "old_canonical_path",
        "new_canonical_path",
        "affected_paths",
        "audit_reference",
        "snapshot_reference",
        "recommended_actions",
        "canonical_skill",
        "visibility",
        "category",
    },
    "import_skill": {
        "skill_id",
        "name",
        "slug",
        "skill_dir",
        "skill_file",
        "created_paths",
        "affected_paths",
        "audit_reference",
        "snapshot_reference",
        "native_installations",
        "native_installations_note",
        "canonical_skill",
        "visibility",
        "category",
    },
    "adopt_skill": {
        "skill_id",
        "name",
        "slug",
        "skill_dir",
        "skill_file",
        "adopted_source",
        "affected_paths",
        "audit_reference",
        "snapshot_reference",
        "native_installations",
        "warnings",
        "canonical_skill",
        "visibility",
        "category",
    },
    "update_canonical_skill": {
        "skill_id",
        "name",
        "slug",
        "skill_file",
        "affected_paths",
        "audit_reference",
        "snapshot_reference",
        "native_installations",
        "warnings",
        "validation",
        "canonical_skill",
    },
    "rename_skill": {
        "skill_id",
        "name",
        "slug",
        "old_path",
        "new_path",
        "affected_paths",
        "warnings",
        "audit_reference",
        "snapshot_reference",
        "canonical_skill",
    },
    "cleanup_skill": {"plan", "removed_paths", "warnings"},
    "repair_skills": {"plans", "removed_paths", "warnings"},
    "promote_skill_recommendation": {
        "skill_id",
        "name",
        "slug",
        "skill_dir",
        "skill_file",
        "created_paths",
        "affected_paths",
        "audit_reference",
        "snapshot_reference",
        "native_installations",
        "visibility",
        "category",
        "canonical_skill",
        "source_recommendation_id",
        "promotion",
    },
    "sync_skills": {
        "skills",
        "affected_paths",
        "removed_paths",
        "audit_reference",
        "snapshot_reference",
    },
    "list_skills": {"skills"},
    "recommend_skills": {
        "recommendations",
        "thresholds",
        "evidence_sources",
        "limitations",
    },
    "get_skill_detail": {
        "name",
        "scope",
        "status",
        "relative_path",
        "triggers",
        "audit_reference",
        "references_loaded",
    },
    "activate_skill": {
        "latent_skill",
        "skill_file",
        "audit_reference",
        "snapshot_reference",
    },
    "deactivate_skill": {
        "latent_skill",
        "audit_reference",
        "snapshot_reference",
    },
    "update_skill": {
        "latent_skill",
        "skill_file",
        "audit_reference",
        "snapshot_reference",
    },
    "track_latent_skill": {
        "latent_skill",
        "matched_existing",
        "audit_reference",
        "snapshot_reference",
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
        "layout": str,
        "shared_root": (str, type(None)),
        "operational_root": str,
        "shared_paths": list,
        "operational_paths": list,
    },
    "inspect_project_layout": {
        "operation": str,
        "layout": str,
        "shared_root": str,
        "operational_root": str,
        "precedence": str,
        "warnings": list,
        "recommended_actions": list,
        "git_status_available": bool,
        "ignored_shared_paths": list,
        "tracked_operational_paths": list,
        "overlaps": list,
    },
    "migrate_project_layout": {
        "operation": str,
        "source_layout": str,
        "target_layout": str,
        "dry_run": bool,
        "copied": list,
        "already_shared": list,
        "skipped": list,
        "conflicts": list,
        "remaining_local": list,
        "affected_paths": list,
        "next_steps": list,
        "warnings": list,
    },
    "status": {
        "initialized": bool,
        "project_path": str,
        "installed_version": str,
        "fact_counts": dict,
        "active_rules_count": int,
        "registered_skills_count": int,
        "approximate_size_bytes": int,
        "last_health_check": str,
        "host_validation": dict,
        "layout": str,
        "shared_root": str,
        "operational_root": str,
        "path_counts": dict,
    },
    "doctor": {
        "checks": list,
        "summary": dict,
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
        "visibility": (str, type(None)),
        "storage_path": (str, type(None)),
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
    "generate_skill": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "skill_dir": str,
        "skill_file": str,
        "created_paths": list,
        "affected_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "collision_detected": bool,
        "suggested_slug": (str, type(None)),
    },
    "create_skill": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "skill_dir": str,
        "skill_file": str,
        "created_paths": list,
        "affected_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "native_installations": list,
        "visibility": (str, type(None)),
        "category": (str, type(None)),
        "canonical_skill": dict,
    },
    "create_skill_draft": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "draft_path": str,
        "affected_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "warnings": list,
    },
    "validate_skill": {"validation": dict},
    "publish_skill": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "skill_dir": str,
        "skill_file": str,
        "affected_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "native_installations": list,
        "validation": dict,
        "canonical_skill": dict,
        "visibility": (str, type(None)),
        "category": (str, type(None)),
    },
    "share_skill": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "skill_dir": str,
        "skill_file": str,
        "old_canonical_path": str,
        "new_canonical_path": str,
        "affected_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "recommended_actions": list,
        "canonical_skill": dict,
        "visibility": (str, type(None)),
        "category": (str, type(None)),
    },
    "import_skill": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "skill_dir": str,
        "skill_file": str,
        "created_paths": list,
        "affected_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "native_installations": list,
        "canonical_skill": dict,
        "visibility": (str, type(None)),
        "category": (str, type(None)),
    },
    "adopt_skill": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "skill_dir": str,
        "skill_file": str,
        "adopted_source": str,
        "affected_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "native_installations": list,
        "warnings": list,
        "canonical_skill": dict,
        "visibility": (str, type(None)),
        "category": (str, type(None)),
    },
    "update_canonical_skill": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "skill_file": str,
        "affected_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "native_installations": list,
        "warnings": list,
        "validation": dict,
        "canonical_skill": dict,
    },
    "rename_skill": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "old_path": str,
        "new_path": str,
        "affected_paths": list,
        "warnings": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "canonical_skill": dict,
    },
    "cleanup_skill": {"plan": dict, "removed_paths": list, "warnings": list},
    "repair_skills": {"plans": list, "removed_paths": list, "warnings": list},
    "promote_skill_recommendation": {
        "skill_id": str,
        "name": str,
        "slug": str,
        "skill_dir": str,
        "skill_file": str,
        "created_paths": list,
        "affected_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
        "native_installations": list,
        "visibility": str,
        "category": str,
        "canonical_skill": dict,
        "source_recommendation_id": str,
        "promotion": dict,
    },
    "sync_skills": {
        "skills": list,
        "affected_paths": list,
        "removed_paths": list,
        "audit_reference": str,
        "snapshot_reference": str,
    },
    "list_skills": {"skills": list},
    "recommend_skills": {
        "recommendations": list,
        "thresholds": dict,
        "evidence_sources": list,
        "limitations": list,
    },
    "get_skill_detail": {
        "name": str,
        "scope": str,
        "status": str,
        "relative_path": (str, type(None)),
        "triggers": list,
        "audit_reference": str,
        "references_loaded": bool,
    },
    "activate_skill": {
        "latent_skill": dict,
        "skill_file": str,
        "audit_reference": str,
        "snapshot_reference": str,
    },
    "deactivate_skill": {
        "latent_skill": dict,
        "audit_reference": str,
        "snapshot_reference": str,
    },
    "update_skill": {
        "latent_skill": dict,
        "skill_file": str,
        "audit_reference": str,
        "snapshot_reference": str,
    },
    "track_latent_skill": {
        "latent_skill": dict,
        "matched_existing": bool,
        "audit_reference": str,
        "snapshot_reference": str,
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
async def test_mcp_compliance_doctor_payload_includes_shared_layout_checks(tmp_path: Path) -> None:
    result = DoctorResult(
        checks=[
            DoctorCheck(
                name="project_layout_mode",
                status="success",
                detail="Shared project layout is active.",
            ),
            DoctorCheck(
                name="shared_root_visibility",
                status="warning",
                error="Shared paths are ignored: umem/",
                recovery_hint="Update ignore rules so umem/ shared content is reviewable.",
            ),
            DoctorCheck(
                name="operational_root_privacy",
                status="warning",
                error="Operational paths are tracked: .umem/audit/events.jsonl",
                recovery_hint="Remove operational .umem paths from Git tracking.",
            ),
            DoctorCheck(
                name="layout_overlaps",
                status="warning",
                error="Legacy/shared overlaps detected: skill:review-helper",
                recovery_hint=(
                    "Shared content takes precedence; remove or migrate shadowed legacy records."
                ),
            ),
        ]
    )
    server = configure_server(
        create_mcp_server(),
        replace(mcp_use_cases(tmp_path), doctor=lambda _command: result),
        project_root=tmp_path,
    )

    response = await server.call_tool("doctor", {})
    payload = response.structured_content

    assert payload is not None
    assert payload["ok"] is True
    assert payload["data"]["summary"] == {
        "total_checks": 4,
        "passed": 1,
        "warnings": 3,
        "failed": 0,
    }
    checks = {check["name"]: check for check in payload["data"]["checks"]}
    assert set(checks) == {
        "project_layout_mode",
        "shared_root_visibility",
        "operational_root_privacy",
        "layout_overlaps",
    }
    assert checks["shared_root_visibility"]["status"] == "warning"
    assert checks["layout_overlaps"]["recovery_hint"].startswith("Shared content takes precedence")


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


@pytest.mark.anyio
async def test_mcp_initialize_project_accepts_shared_layout(tmp_path: Path) -> None:
    seen: list[str] = []

    def initialize_project(project_root: Path, *, layout: str = "legacy") -> SetupProjectResult:
        seen.append(layout)
        return SetupProjectResult(
            project_path=project_root,
            config_path=project_root / ".umem" / "config.toml",
            memory_path=project_root / ".umem" / "memory",
            audit_path=project_root / ".umem" / "audit" / "events.jsonl",
            snapshots_path=project_root / ".umem" / "snapshots",
            skills_path=project_root / ".umem" / "skills",
            benchmarks_path=project_root / ".umem" / "benchmarks",
            created=True,
            created_paths=[".umem/config.toml", "umem/project.toml"],
            existing_paths=[],
            already_initialized=False,
            layout="shared",
            shared_root=Path("umem"),
            operational_root=Path(".umem"),
            shared_paths=["umem/project.toml", "umem/memory", "umem/skills"],
            operational_paths=[".umem/config.toml", ".umem/memory"],
        )

    use_cases = mcp_use_cases(tmp_path)
    use_cases = replace(use_cases, initialize_project=initialize_project)
    server = configure_server(create_mcp_server(), use_cases, project_root=tmp_path)

    payload = (
        await server.call_tool("initialize_project", {"layout": "shared"})
    ).structured_content

    assert payload is not None
    assert payload["ok"] is True
    assert payload["data"]["layout"] == "shared"
    assert payload["data"]["shared_root"] == "umem"
    assert payload["data"]["operational_root"] == ".umem"
    assert payload["data"]["shared_paths"] == ["umem/project.toml", "umem/memory", "umem/skills"]
    assert seen == ["shared"]


@pytest.mark.anyio
async def test_mcp_migrate_project_layout_accepts_dry_run_and_apply(tmp_path: Path) -> None:
    seen: list[bool] = []

    def migrate(command) -> dict[str, Any]:
        seen.append(command.dry_run)
        return migration_payload(dry_run=command.dry_run)

    use_cases = replace(mcp_use_cases(tmp_path), migrate_project_layout=migrate)
    server = configure_server(create_mcp_server(), use_cases, project_root=tmp_path)

    dry_run_payload = (
        await server.call_tool(
            "migrate_project_layout",
            {"target_layout": "shared", "dry_run": True},
        )
    ).structured_content
    apply_payload = (
        await server.call_tool(
            "migrate_project_layout",
            {"target_layout": "shared", "dry_run": False},
        )
    ).structured_content

    assert dry_run_payload is not None
    assert apply_payload is not None
    assert dry_run_payload["operation"] == "layout.migrate"
    assert dry_run_payload["data"]["dry_run"] is True
    assert apply_payload["data"]["dry_run"] is False
    assert seen == [True, False]


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
        doctor=lambda _command: doctor_result(),
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
        create_skill=create_skill_result,
        create_skill_draft=create_skill_draft_result,
        validate_skill=validate_skill_result,
        publish_skill=publish_skill_result,
        share_skill=share_skill_result,
        import_skill=import_skill_result,
        adopt_skill=adopt_skill_result,
        update_canonical_skill=update_canonical_skill_result,
        rename_skill=rename_skill_result,
        cleanup_skill=cleanup_skill_result,
        repair_skills=repair_skills_result,
        promote_skill_recommendation=promote_skill_recommendation_result,
        generate_skill=generate_skill_result,
        sync_skills=sync_skills_result,
        list_skills=list_skills_result,
        recommend_skills=recommend_skills_result,
        get_skill_detail=get_skill_detail_result,
        activate_skill=activate_skill_result,
        deactivate_skill=deactivate_skill_result,
        update_skill=update_skill_result,
        track_latent_skill=track_latent_skill_result,
        migrate_project_layout=lambda command: migration_payload(dry_run=command.dry_run),
    )


def migration_payload(*, dry_run: bool) -> dict[str, Any]:
    data = {
        "operation": "layout.migrate",
        "source_layout": "legacy",
        "target_layout": "shared",
        "dry_run": dry_run,
        "copied": [
            {
                "kind": "fact",
                "id": "fact-1",
                "reason": "copied",
                "path": "umem/memory/facts.jsonl",
            }
        ],
        "already_shared": [],
        "skipped": [],
        "conflicts": [],
        "remaining_local": [],
        "affected_paths": ["umem/project.toml", "umem/memory/facts.jsonl"],
        "next_steps": [],
        "warnings": [],
    }
    return {"operation": "layout.migrate", "scope": "project", "data": data, "warnings": []}


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


def track_latent_skill_result(command: TrackLatentSkillCommand) -> TrackLatentSkillResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    skill = LatentSkill(
        id=FACT_ID,
        created_at=now,
        updated_at=now,
        name=command.name,
        description=command.description,
        scope=command.scope,
        status=LatentSkillStatus.proposed,
        recurrence_count=1,
        metadata={
            "tags": command.tags,
            "evidence": [{"origin": "mcp", "summary": command.evidence_summary}],
        },
    )
    return TrackLatentSkillResult(
        latent_skill=skill,
        matched_existing=False,
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def list_skills_result(_command: ListSkillsCommand) -> ListSkillsResult:
    return ListSkillsResult(
        skills=[
            SkillListItem(
                name="TDD recorrente",
                scope="project",
                status="active",
                relative_path=".umem/skills/tdd-recorrente/SKILL.md",
                created_at="2026-05-28T12:00:00Z",
                updated_at="2026-05-28T12:00:00Z",
                origin="cli",
                audit_reference="audit-1",
            )
        ]
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


def get_skill_detail_result(_command: GetSkillDetailCommand) -> GetSkillDetailResult:
    return GetSkillDetailResult(
        name="TDD recorrente",
        scope="project",
        status="active",
        relative_path=".umem/skills/tdd-recorrente/SKILL.md",
        triggers=["red green refactor"],
        audit_reference="audit-1",
        references_loaded=False,
    )


def generate_skill_result(command: GenerateSkillCommand) -> GenerateSkillResult:
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


def create_skill_result(command: CreateSkillCommand) -> CreateSkillResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    agent_skill = AgentSkill(
        id=FACT_ID,
        created_at=now,
        updated_at=now,
        name=command.name,
        slug="tdd-recorrente",
        description=command.description,
        scope=command.scope,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/tdd-recorrente/SKILL.md",
        origin="mcp",
        audit_reference="audit-1",
        content_hash="hash-1",
        metadata={
            "visibility": command.visibility or "private",
            "category": command.category,
        },
    )
    return CreateSkillResult(
        agent_skill=agent_skill,
        slug="tdd-recorrente",
        skill_dir=".umem/skills/tdd-recorrente",
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        created_paths=[".umem/skills/tdd-recorrente/SKILL.md"],
        affected_paths=[".umem/skills/tdd-recorrente/SKILL.md"],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def validation_report() -> SkillValidationReport:
    return SkillValidationReport(
        subject="tdd-recorrente",
        status="pass",
        checks=[],
        affected_paths=[".umem/skills/tdd-recorrente/SKILL.md"],
        recommended_next_steps=["Skill is ready."],
    )


def create_skill_draft_result(command: object) -> DraftSkillResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    agent_skill = AgentSkill(
        id=FACT_ID,
        created_at=now,
        updated_at=now,
        name=getattr(command, "name", "Draft Helper"),
        slug="draft-helper",
        description=getattr(command, "description", "Draft skill."),
        scope=getattr(command, "scope", LatentSkillScope.project),
        status=AgentSkillStatus.draft,
        canonical_path=".umem/drafts/skills/draft-helper/SKILL.md",
        origin="mcp",
        audit_reference="audit-1",
        content_hash="hash-1",
    )
    return DraftSkillResult(
        agent_skill=agent_skill,
        slug="draft-helper",
        draft_path=".umem/drafts/skills/draft-helper/SKILL.md",
        affected_paths=[".umem/drafts/skills/draft-helper/SKILL.md"],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def validate_skill_result(_command: object) -> ValidateSkillResult:
    return ValidateSkillResult(report=validation_report())


def publish_skill_result(_command: object) -> PublishSkillResult:
    create = create_skill_result(
        CreateSkillCommand(
            name="Draft Helper",
            description="Draft skill.",
            scope=LatentSkillScope.project,
            origin="mcp",
        )
    )
    return PublishSkillResult(
        agent_skill=create.agent_skill,
        slug=create.slug,
        skill_dir=create.skill_dir,
        skill_file=create.skill_file,
        affected_paths=create.affected_paths,
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
        validation=validation_report(),
    )


def share_skill_result(_command: object) -> ShareSkillResult:
    create = create_skill_result(
        CreateSkillCommand(
            name="Use Universal Memory",
            description="Operational bootstrap guidance.",
            scope=LatentSkillScope.project,
            origin="mcp",
            slug="use-universal-memory",
            category="operational",
        )
    )
    skill = create.agent_skill.model_copy(
        update={
            "canonical_path": "umem/skills/use-universal-memory/SKILL.md",
            "metadata": {"visibility": "shared", "category": "operational"},
        }
    )
    return ShareSkillResult(
        agent_skill=skill,
        old_canonical_path=".umem/skills/use-universal-memory/SKILL.md",
        new_canonical_path="umem/skills/use-universal-memory/SKILL.md",
        affected_paths=[
            "umem/skills/use-universal-memory/SKILL.md",
            "umem/project.toml",
        ],
        audit_reference="audit-share",
        snapshot_reference="snapshot-share",
        recommended_actions=["Review umem/project.toml and commit the shared skill."],
    )


def import_skill_result(command: ImportSkillCommand) -> ImportSkillResult:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    agent_skill = AgentSkill(
        id=FACT_ID,
        created_at=now,
        updated_at=now,
        name="Imported Skill",
        slug="imported-skill",
        description="Imported from native skill directory.",
        scope=command.scope,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/imported-skill/SKILL.md",
        origin="mcp",
        audit_reference="audit-1",
        content_hash="hash-1",
    )
    return ImportSkillResult(
        agent_skill=agent_skill,
        slug="imported-skill",
        skill_dir=".umem/skills/imported-skill",
        skill_file=".umem/skills/imported-skill/SKILL.md",
        created_paths=[".umem/skills/imported-skill/SKILL.md"],
        affected_paths=[".umem/skills/imported-skill/SKILL.md"],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def adopt_skill_result(command: object) -> AdoptSkillResult:
    imported = import_skill_result(
        ImportSkillCommand(
            path=getattr(command, "path", ".umem/skills/tdd-recorrente"),
            scope=getattr(command, "scope", LatentSkillScope.project),
            origin="mcp",
        )
    )
    return AdoptSkillResult(
        agent_skill=imported.agent_skill,
        slug=imported.slug,
        skill_dir=imported.skill_dir,
        skill_file=imported.skill_file,
        adopted_source=".umem/skills/tdd-recorrente",
        affected_paths=imported.affected_paths,
        audit_reference=imported.audit_reference,
        snapshot_reference=imported.snapshot_reference,
    )


def update_canonical_skill_result(_command: object) -> UpdateCanonicalSkillResult:
    create = create_skill_result(
        CreateSkillCommand(
            name="TDD recorrente",
            description="Usuario pede ciclo red green refactor",
            scope=LatentSkillScope.project,
            origin="mcp",
        )
    )
    return UpdateCanonicalSkillResult(
        agent_skill=create.agent_skill,
        skill_file=create.skill_file,
        validation=validation_report(),
        affected_paths=create.affected_paths,
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def rename_skill_result(_command: object) -> RenameSkillResult:
    create = create_skill_result(
        CreateSkillCommand(
            name="TDD recorrente",
            description="Usuario pede ciclo red green refactor",
            scope=LatentSkillScope.project,
            origin="mcp",
        )
    )
    renamed = create.agent_skill.model_copy(update={"slug": "tdd-renamed"})
    return RenameSkillResult(
        agent_skill=renamed,
        old_path=".umem/skills/tdd-recorrente/SKILL.md",
        new_path=".umem/skills/tdd-renamed/SKILL.md",
        affected_paths=[
            ".umem/skills/tdd-recorrente/SKILL.md",
            ".umem/skills/tdd-renamed/SKILL.md",
        ],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def cleanup_skill_result(_command: object) -> CleanupSkillResult:
    plan = CleanupPlan(
        skill="tdd-recorrente",
        mode="targets",
        dry_run=True,
        removable_paths=[".agents/skills/tdd-recorrente"],
    )
    return CleanupSkillResult(plan=plan)


def repair_skills_result(_command: object) -> RepairSkillsResult:
    plan = CleanupPlan(
        skill="all",
        mode="orphan-targets",
        dry_run=True,
        removable_paths=[".agents/skills/orphan"],
    )
    return RepairSkillsResult(plans=[plan])


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
                skill_id=FACT_ID,
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
