from __future__ import annotations

import sys
import traceback
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP

from universal_memory.application.host import (
    ConfigureHostCommand,
    ConfigureHostResult,
    SyncInstructionsCommand,
    SyncInstructionsResult,
)
from universal_memory.application.memory import (
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
    GetMemoryStatusCommand,
    GetMemoryStatusResult,
    ListFactsCommand,
    ListFactsResult,
    PurgeFactCommand,
    PurgeFactResult,
    RememberFactCommand,
    RememberFactResult,
)
from universal_memory.application.onboarding.setup_project import SetupProjectResult
from universal_memory.application.security import (
    ListAuditLogCommand,
    ListAuditLogResult,
    ListSnapshotsCommand,
    ListSnapshotsResult,
    RollbackCommand,
    RollbackResult,
)
from universal_memory.application.skills import (
    ActivateSkillCommand,
    ActivateSkillResult,
    DeactivateSkillCommand,
    DeactivateSkillResult,
    GenerateSkillCommand,
    GenerateSkillResult,
    GetSkillDetailCommand,
    GetSkillDetailResult,
    ListSkillsCommand,
    ListSkillsResult,
    ProposeSkillCommand,
    ProposeSkillDecision,
    ProposeSkillResult,
    UpdateSkillCommand,
    UpdateSkillResult,
)
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEventScope,
    ContextSummaryScope,
    FactScope,
    FactStatus,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.interfaces import errors as interface_errors
from universal_memory.interfaces.errors import (
    error_descriptor,
    error_payload,
    json_rpc_error_payload,
    sanitize_error_detail,
)

JSON_RPC_SECRET_DETECTED = interface_errors.JSON_RPC_SECRET_DETECTED
JSON_RPC_SNAPSHOT_FAILED = interface_errors.JSON_RPC_SNAPSHOT_FAILED
JSON_RPC_VALIDATION_FAILED = interface_errors.JSON_RPC_VALIDATION_FAILED
JSON_RPC_FACT_NOT_FOUND = interface_errors.JSON_RPC_FACT_NOT_FOUND
JSON_RPC_INVALID_CONFIG = interface_errors.JSON_RPC_INVALID_CONFIG
JSON_RPC_STORAGE_ERROR = interface_errors.JSON_RPC_STORAGE_ERROR
JSON_RPC_UNEXPECTED_ERROR = interface_errors.JSON_RPC_UNEXPECTED_ERROR

DEFAULT_CONTEXT_MAX_SIZE_CHARS = 4000
TOKEN_ESTIMATE_CHARS = 4
SetupProjectCommandHandler = Callable[[Path], SetupProjectResult]
StatusCommandHandler = Callable[[GetMemoryStatusCommand], GetMemoryStatusResult]
ContextCommandHandler = Callable[[AssembleContextSummaryCommand], AssembleContextSummaryResult]
RememberCommandHandler = Callable[[RememberFactCommand], RememberFactResult]
ListFactsCommandHandler = Callable[[ListFactsCommand], ListFactsResult]
PurgeFactCommandHandler = Callable[[PurgeFactCommand], PurgeFactResult]
ListAuditLogCommandHandler = Callable[[ListAuditLogCommand], ListAuditLogResult]
ListSnapshotsCommandHandler = Callable[[ListSnapshotsCommand], ListSnapshotsResult]
RollbackCommandHandler = Callable[[RollbackCommand], RollbackResult]
ConfigureHostCommandHandler = Callable[[ConfigureHostCommand], ConfigureHostResult]
SyncInstructionsCommandHandler = Callable[[SyncInstructionsCommand], SyncInstructionsResult]
ProposeSkillCommandHandler = Callable[[ProposeSkillCommand], ProposeSkillResult]
GenerateSkillCommandHandler = Callable[[GenerateSkillCommand], GenerateSkillResult]
ListSkillsCommandHandler = Callable[[ListSkillsCommand], ListSkillsResult]
GetSkillDetailCommandHandler = Callable[[GetSkillDetailCommand], GetSkillDetailResult]
ActivateSkillCommandHandler = Callable[[ActivateSkillCommand], ActivateSkillResult]
DeactivateSkillCommandHandler = Callable[[DeactivateSkillCommand], DeactivateSkillResult]
UpdateSkillCommandHandler = Callable[[UpdateSkillCommand], UpdateSkillResult]
ToolResponse = dict[str, Any]


def _missing_use_case(_command: Any) -> Any:
    msg = "MCP use case dependency was not configured."
    raise RuntimeError(msg)


@dataclass(frozen=True, slots=True)
class MCPUseCases:
    status: StatusCommandHandler
    context: ContextCommandHandler
    initialize_project: SetupProjectCommandHandler = _missing_use_case
    remember: RememberCommandHandler = _missing_use_case
    list_facts: ListFactsCommandHandler = _missing_use_case
    purge_fact: PurgeFactCommandHandler = _missing_use_case
    list_audit_events: ListAuditLogCommandHandler = _missing_use_case
    list_snapshots: ListSnapshotsCommandHandler = _missing_use_case
    rollback_scope: RollbackCommandHandler = _missing_use_case
    host_setup: ConfigureHostCommandHandler = _missing_use_case
    host_check: ConfigureHostCommandHandler = _missing_use_case
    sync_instructions: SyncInstructionsCommandHandler = _missing_use_case
    propose_skill: ProposeSkillCommandHandler = _missing_use_case
    generate_skill: GenerateSkillCommandHandler = _missing_use_case
    list_skills: ListSkillsCommandHandler = _missing_use_case
    get_skill_detail: GetSkillDetailCommandHandler = _missing_use_case
    activate_skill: ActivateSkillCommandHandler = _missing_use_case
    deactivate_skill: DeactivateSkillCommandHandler = _missing_use_case
    update_skill: UpdateSkillCommandHandler = _missing_use_case


def create_mcp_server(name: str = "universal-memory") -> FastMCP:
    return FastMCP(name)


def configure_server(  # noqa: PLR0915
    server: FastMCP,
    use_cases: MCPUseCases,
    *,
    project_root: Path | None = None,
) -> FastMCP:
    root = project_root or Path.cwd()

    @server.tool(name="initialize_project")
    def initialize_project() -> ToolResponse:
        """Initialize the local Universal Memory project layout."""
        try:
            result = use_cases.initialize_project(root)
            return _success_envelope(
                operation="init",
                scope="project",
                data=_init_payload(result, root),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="init", scope="project")

    @server.tool(name="status")
    def status() -> ToolResponse:
        """Expose local cognitive persistence memory initialization and health check status.

        Returns initialization state, fact counts, active rules, registered skills,
        approximate size, host validations, and recommended actions.
        """
        try:
            result = use_cases.status(GetMemoryStatusCommand(project_root=root))
            return _success_envelope(
                operation="status",
                scope="project",
                data=_status_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="status", scope="project")

    @server.tool(name="context")
    def context(
        scope: Literal["project", "global"] = "project",
        max_size_chars: int = DEFAULT_CONTEXT_MAX_SIZE_CHARS,
        agent_session_key: str | None = None,
    ) -> ToolResponse:
        """Assemble the active cognitive memory context for AI agent operations.

        Retrieves and compiles project-specific or global context facts, preferences,
        and rules formatted in Markdown, optimized for injection into system prompts.
        """
        try:
            context_scope = _context_scope(scope)
            result = use_cases.context(
                AssembleContextSummaryCommand(
                    scope=context_scope,
                    max_size_chars=max_size_chars,
                    agent_session_key=agent_session_key,
                )
            )
            return _success_envelope(
                operation="context",
                scope=context_scope.value,
                data=_context_payload(result, max_size_chars=max_size_chars),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="context", scope=_raw_scope(scope))

    @server.tool(name="remember_fact")
    def remember_fact(
        content: str,
        scope: Literal["project", "global"] = "project",
        tags: list[str] | None = None,
    ) -> ToolResponse:
        """Persist a memory fact through the shared safe mutation pipeline."""
        try:
            fact_scope = _fact_scope(scope)
            result = use_cases.remember(
                RememberFactCommand(
                    content=content,
                    scope=fact_scope,
                    source="mcp",
                    tags=tags or [],
                    origin="mcp",
                )
            )
            return _success_envelope(
                operation="remember",
                scope=fact_scope.value,
                data=_remember_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="remember", scope=_raw_scope(scope))

    @server.tool(name="list_facts")
    def list_facts(
        scope: Literal["project", "global"] | None = None,
        status: Literal["active", "stale", "archived", "purged"] = "active",
    ) -> ToolResponse:
        """List memory facts with optional scope and status filters."""
        try:
            fact_scope = _fact_scope_optional(scope)
            result = use_cases.list_facts(
                ListFactsCommand(scope=fact_scope, status=FactStatus(status))
            )
            return _success_envelope(
                operation="facts.list",
                scope=fact_scope.value if fact_scope is not None else "all",
                data={"facts": [_fact_payload(fact) for fact in result.facts]},
            )
        except Exception as error:
            return _mcp_tool_error(
                error,
                operation="facts.list",
                scope=_raw_scope(scope) if scope is not None else "all",
            )

    @server.tool(name="purge_fact")
    def purge_fact(
        id: str | None = None,
        scope: Literal["project", "global"] | None = None,
        confirm: bool = False,
    ) -> ToolResponse:
        """Purge one fact by id or all facts in a scope through the shared use case.

        Requires `confirm=True` to execute.
        """
        try:
            if not confirm:
                raise ValidationFailedError(
                    "Purging facts is destructive and requires explicit confirmation. "
                    "Please call this tool with confirm=True."
                )
            fact_scope = _fact_scope_optional(scope)
            result = use_cases.purge_fact(PurgeFactCommand(id=id, scope=fact_scope, origin="mcp"))
            return _success_envelope(
                operation="facts.purge",
                scope=fact_scope.value if fact_scope is not None else "fact",
                data=_purge_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(
                error,
                operation="facts.purge",
                scope=_raw_scope(scope) if scope is not None else "fact",
            )

    @server.tool(name="list_audit_events")
    def list_audit_events(
        scope: Literal["project", "global"] = "project",
    ) -> ToolResponse:
        """List audit events for a scope."""
        try:
            audit_scope = _audit_scope(scope)
            result = use_cases.list_audit_events(ListAuditLogCommand(scope=audit_scope))
            return _success_envelope(
                operation="audit.list",
                scope=audit_scope.value,
                data={"events": [_entry_dict(event) for event in result.events]},
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="audit.list", scope=_raw_scope(scope))

    @server.tool(name="list_snapshots")
    def list_snapshots(
        scope: Literal["project", "global"] = "project",
    ) -> ToolResponse:
        """List created snapshots for a scope."""
        try:
            snapshot_scope = _snapshot_scope(scope)
            result = use_cases.list_snapshots(
                ListSnapshotsCommand(scope=snapshot_scope, status=SnapshotStatus.created)
            )
            return _success_envelope(
                operation="snapshots.list",
                scope=snapshot_scope.value,
                data={"snapshots": [_entry_dict(snapshot) for snapshot in result.snapshots]},
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="snapshots.list", scope=_raw_scope(scope))

    @server.tool(name="rollback_scope")
    def rollback_scope(
        scope: Literal["project", "global"] = "project",
        confirm: bool = False,
    ) -> ToolResponse:
        """Rollback the latest created snapshot for a scope.

        Requires `confirm=True` to execute.
        """
        try:
            if not confirm:
                raise ValidationFailedError(
                    "Rolling back a scope is destructive and requires explicit confirmation. "
                    "Please call this tool with confirm=True."
                )
            snapshot_scope = _snapshot_scope(scope)
            result = use_cases.rollback_scope(RollbackCommand(scope=snapshot_scope, origin="mcp"))
            return _success_envelope(
                operation="rollback",
                scope=snapshot_scope.value,
                data=_rollback_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="rollback", scope=_raw_scope(scope))

    @server.tool(name="host_setup")
    def host_setup(
        host_id: str,
        force: bool = False,
        max_lines: int = 100,
        max_chars: int = 4000,
    ) -> ToolResponse:
        """Configure an agent host manifest through the safe mutation pipeline."""
        try:
            result = use_cases.host_setup(
                ConfigureHostCommand(
                    host_id=host_id,
                    apply=force,
                    max_managed_lines=max_lines,
                    max_managed_chars=max_chars,
                    origin="mcp",
                )
            )
            return _success_envelope(
                operation="host_setup",
                scope="project",
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="host_setup", scope="project")

    @server.tool(name="host_check")
    def host_check(
        host_id: str,
        max_lines: int = 100,
        max_chars: int = 4000,
    ) -> ToolResponse:
        """Validate an agent host manifest without mutating files."""
        try:
            result = use_cases.host_check(
                ConfigureHostCommand(
                    host_id=host_id,
                    apply=False,
                    check=True,
                    max_managed_lines=max_lines,
                    max_managed_chars=max_chars,
                    origin="mcp",
                )
            )
            return _success_envelope(
                operation="host_check",
                scope="project",
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="host_check", scope="project")

    @server.tool(name="sync_instructions")
    def sync_instructions(
        host_ids: list[str] | None = None,
        apply: bool = False,
    ) -> ToolResponse:
        """Synchronize approved active rules into supported instruction targets."""
        try:
            result = use_cases.sync_instructions(
                SyncInstructionsCommand(
                    host_ids=host_ids or ["codex", "claude_code"],
                    apply=apply,
                    origin="mcp",
                )
            )
            return _success_envelope(
                operation="host_sync",
                scope="project",
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="host_sync", scope="project")

    @server.tool(name="propose_skill")
    def propose_skill(
        latent_skill_id: str,
        decision: Literal["sim", "s", "sempre", "e", "nao", "não", "n"] | None = None,
    ) -> ToolResponse:
        """Review or decide a latent skill proposal.

        If `decision` is omitted, returns the suggested name, scope, purpose,
        evidence, and explicit choices for a follow-up call.
        """
        try:
            result = use_cases.propose_skill(
                ProposeSkillCommand(
                    latent_skill_id=latent_skill_id,
                    decision=_skill_decision(decision),
                    origin="mcp",
                )
            )
            return _success_envelope(
                operation="skills.propose",
                scope=result.latent_skill.scope.value,
                data=_skill_proposal_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.propose", scope="project")

    @server.tool(name="generate_skill")
    def generate_skill(
        latent_skill_id: str,
        update_existing: bool = False,
    ) -> ToolResponse:
        """Generate the physical Agent Skill structure for an approved latent skill."""
        try:
            result = use_cases.generate_skill(
                GenerateSkillCommand(
                    latent_skill_id=latent_skill_id,
                    origin="mcp",
                    update_existing=update_existing,
                )
            )
            return _success_envelope(
                operation="skills.generate",
                scope=result.latent_skill.scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.generate", scope="project")

    @server.tool(name="list_skills")
    def list_skills() -> ToolResponse:
        """List registered skills and candidates without mutating local state."""
        try:
            result = use_cases.list_skills(ListSkillsCommand())
            return _success_envelope(
                operation="skills.list",
                scope="all",
                data=result.to_payload(),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.list", scope="all")

    @server.tool(name="get_skill_detail")
    def get_skill_detail(name_or_id: str) -> ToolResponse:
        """Inspect metadata and triggers for one registered skill."""
        try:
            result = use_cases.get_skill_detail(GetSkillDetailCommand(name_or_id=name_or_id))
            return _success_envelope(
                operation="skills.detail",
                scope=result.scope,
                data=result.to_payload(),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.detail", scope="project")

    @server.tool(name="activate_skill")
    def activate_skill(latent_skill_id: str) -> ToolResponse:
        """Reactivate an ignored latent skill through the shared safe mutation pipeline."""
        try:
            result = use_cases.activate_skill(
                ActivateSkillCommand(latent_skill_id=latent_skill_id, origin="mcp")
            )
            return _success_envelope(
                operation="skills.activate",
                scope=result.latent_skill.scope.value,
                data=_skill_mutation_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(
                _map_skill_mutation_error(error, latent_skill_id),
                operation="skills.activate",
                scope="project",
            )

    @server.tool(name="deactivate_skill")
    def deactivate_skill(latent_skill_id: str) -> ToolResponse:
        """Deactivate an active latent skill without deleting its physical SKILL.md."""
        try:
            result = use_cases.deactivate_skill(
                DeactivateSkillCommand(latent_skill_id=latent_skill_id, origin="mcp")
            )
            return _success_envelope(
                operation="skills.deactivate",
                scope=result.latent_skill.scope.value,
                data=_skill_mutation_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(
                _map_skill_mutation_error(error, latent_skill_id),
                operation="skills.deactivate",
                scope="project",
            )

    @server.tool(name="update_skill")
    def update_skill(
        latent_skill_id: str,
        name: str | None = None,
        description: str | None = None,
        triggers: list[str] | None = None,
        raw_markdown: str | None = None,
    ) -> ToolResponse:
        """Update skill metadata or markdown through the shared safe mutation pipeline."""
        try:
            result = use_cases.update_skill(
                UpdateSkillCommand(
                    latent_skill_id=latent_skill_id,
                    origin="mcp",
                    name=name.strip() if name is not None else None,
                    description=description.strip() if description is not None else None,
                    triggers=_normalize_triggers(triggers),
                    raw_markdown=raw_markdown,
                )
            )
            return _success_envelope(
                operation="skills.update",
                scope=result.latent_skill.scope.value,
                data=_skill_mutation_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(
                _map_skill_mutation_error(error, latent_skill_id),
                operation="skills.update",
                scope="project",
            )

    return server


def _success_envelope(
    *,
    operation: str,
    scope: str,
    data: dict[str, Any],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": operation,
        "scope": scope,
        "data": data,
        "warnings": warnings or [],
    }


def _status_payload(result: GetMemoryStatusResult) -> dict[str, Any]:
    if not result.initialized:
        return {
            "initialized": False,
            "project_path": result.project_path,
            "recommended_action": result.recommended_action,
        }

    return {
        "initialized": True,
        "project_path": result.project_path,
        "fact_counts": result.fact_counts,
        "active_rules_count": result.active_rules_count,
        "registered_skills_count": result.registered_skills_count,
        "approximate_size_bytes": result.approximate_size_bytes,
        "last_health_check": result.last_health_check,
        "host_validation": result.host_validation,
    }


def _context_payload(
    result: AssembleContextSummaryResult,
    *,
    max_size_chars: int,
) -> dict[str, Any]:
    summary = result.context_summary
    markdown_size = len(result.context_markdown)
    return {
        "project_summary": summary.project_summary,
        "universal_preferences": summary.universal_preferences,
        "active_rules": summary.active_rules,
        "source_fact_ids": result.included_fact_ids,
        "truncated": markdown_size >= max_size_chars,
        "token_estimate": max(1, round(markdown_size / TOKEN_ESTIMATE_CHARS)),
        "last_read_at": format_utc_iso(summary.created_at),
    }


def _init_payload(result: SetupProjectResult, project_root: Path) -> dict[str, Any]:
    return {
        "project_path": _relative_path(result.project_path, project_root),
        "config_path": _relative_path(result.config_path, project_root),
        "memory_path": _relative_path(result.memory_path, project_root),
        "audit_path": _relative_path(result.audit_path, project_root),
        "snapshots_path": _relative_path(result.snapshots_path, project_root),
        "created": result.created_paths,
        "already_initialized": result.already_initialized,
        "audit_reference": "not-implemented-yet",
    }


def _remember_payload(result: RememberFactResult) -> dict[str, Any]:
    fact = result.fact
    return {
        "fact_id": fact.id,
        "scope": fact.scope.value,
        "status": fact.status.value,
        "tags": fact.tags,
        "created_at": format_utc_iso(fact.created_at),
        "audit_reference": result.audit_reference,
    }


def _fact_payload(fact: Any) -> dict[str, Any]:
    return {
        "id": fact.id,
        "content": fact.content,
        "scope": fact.scope.value,
        "source": fact.source,
        "status": fact.status.value,
        "recurrence_count": fact.recurrence_count,
        "tags": fact.tags,
        "metadata": fact.metadata,
        "created_at": format_utc_iso(fact.created_at),
        "updated_at": format_utc_iso(fact.updated_at),
    }


def _purge_payload(result: PurgeFactResult) -> dict[str, Any]:
    return {
        "purged_count": result.purged_count,
        "affected_ids": result.affected_ids,
        "audit_reference": result.audit_reference,
    }


def _rollback_payload(result: RollbackResult) -> dict[str, Any]:
    return {
        "scope": result.scope.value,
        "snapshot_reference": result.snapshot_reference,
        "restored_paths": result.restored_paths,
        "audit_reference": result.audit_reference,
    }


def _skill_proposal_payload(result: ProposeSkillResult) -> dict[str, Any]:
    return {
        "skill_id": result.latent_skill.id,
        "suggested_name": result.proposal["suggested_name"],
        "status": result.latent_skill.status.value,
        "accepted": result.accepted,
        "auto_approval_recorded": result.auto_approval_recorded,
        "audit_reference": result.audit_reference,
        "snapshot_reference": result.snapshot_reference,
        "choices": result.choices,
        "requires_decision": result.requires_decision,
        "evidence": result.proposal["evidence"],
    }


def _skill_mutation_payload(
    result: ActivateSkillResult | DeactivateSkillResult | UpdateSkillResult,
) -> dict[str, Any]:
    skill = result.latent_skill
    payload: dict[str, Any] = {
        "latent_skill": {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "status": skill.status.value,
            "scope": skill.scope.value,
            "triggers": _skill_triggers(skill),
        },
        "audit_reference": result.audit_reference,
        "snapshot_reference": result.snapshot_reference,
    }
    skill_file = getattr(result, "skill_file", None)
    if skill_file is not None:
        payload["skill_file"] = skill_file
    return payload


def _skill_triggers(skill: Any) -> list[str]:
    metadata = skill.metadata or {}
    raw_triggers = metadata.get("triggers") or []
    if isinstance(raw_triggers, list):
        return [str(trigger) for trigger in raw_triggers]
    return [str(raw_triggers)]


def _normalize_triggers(triggers: list[str] | None) -> list[str] | None:
    if triggers is None:
        return None
    return [trigger.strip() for trigger in triggers if trigger.strip()]


def _entry_dict(entry: Any) -> dict[str, Any]:
    if hasattr(entry, "model_dump"):
        return entry.model_dump()
    return asdict(entry)


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _context_scope(value: Literal["project", "global"]) -> ContextSummaryScope:
    normalized = str(value).lower()
    if normalized == "global":
        return ContextSummaryScope.global_
    if normalized == "project":
        return ContextSummaryScope.project
    raise ValidationFailedError("scope must be 'project' or 'global'.")


def _fact_scope(value: Literal["project", "global"]) -> FactScope:
    normalized = str(value).lower()
    if normalized == "global":
        return FactScope.global_
    if normalized == "project":
        return FactScope.project
    raise ValidationFailedError("scope must be 'project' or 'global'.")


def _fact_scope_optional(value: Literal["project", "global"] | None) -> FactScope | None:
    if value is None:
        return None
    return _fact_scope(value)


def _audit_scope(value: Literal["project", "global"]) -> AuditEventScope:
    normalized = str(value).lower()
    if normalized == "global":
        return AuditEventScope.global_
    if normalized == "project":
        return AuditEventScope.project
    raise ValidationFailedError("scope must be 'project' or 'global'.")


def _snapshot_scope(value: Literal["project", "global"]) -> SnapshotScope:
    normalized = str(value).lower()
    if normalized == "global":
        return SnapshotScope.global_
    if normalized == "project":
        return SnapshotScope.project
    raise ValidationFailedError("scope must be 'project' or 'global'.")


def _skill_decision(value: str | None) -> ProposeSkillDecision | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if normalized in {"s", "sim", "y", "yes"}:
        return ProposeSkillDecision.sim
    if normalized in {"e", "sempre", "always"}:
        return ProposeSkillDecision.sempre
    if normalized in {"n", "nao", "não", "no"}:
        return ProposeSkillDecision.nao
    raise ValidationFailedError("decision must be 'sim', 'sempre' or 'nao'.")


def _error_envelope(error: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "operation": "mcp",
        "scope": "project",
        "error": error_payload(error, message_locale="en"),
        "warnings": [],
    }


def _mcp_tool_error(error: Exception, *, operation: str, scope: str) -> dict[str, Any]:
    if _error_code(error) == JSON_RPC_UNEXPECTED_ERROR:
        traceback.print_exc(file=sys.stderr)
    else:
        print(f"{type(error).__name__}: {_sanitize_error_detail(error)}", file=sys.stderr)

    payload = json_rpc_error_payload(error)
    return {
        "ok": False,
        "operation": operation,
        "scope": scope,
        "data": {},
        "error": payload,
        "warnings": [],
    }


def _raw_scope(value: Any) -> str:
    return str(value).lower()


def _map_skill_mutation_error(error: Exception, latent_skill_id: str) -> Exception:
    if isinstance(error, StorageError) and str(error) == (
        f"Latent skill not found: {latent_skill_id}"
    ):
        return ValidationFailedError(
            f"Latent skill '{latent_skill_id}' nao encontrada no repositorio."
        )
    return error


def _error_code(error: Exception) -> int:
    return error_descriptor(error).json_rpc_code


def _error_message(error: Exception) -> str:
    return error_descriptor(error).mcp_message


def _sanitize_error_detail(error: Exception) -> str:
    return sanitize_error_detail(error)
