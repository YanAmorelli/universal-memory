from __future__ import annotations

import sys
import traceback
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP

from universal_memory.application.diagnostics import (
    DoctorCommand,
    DoctorResult,
)
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
    AdoptSkillCommand,
    AdoptSkillResult,
    CleanupSkillCommand,
    CleanupSkillResult,
    CreateSkillCommand,
    CreateSkillDraftCommand,
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
    ProposeSkillDecision,
    ProposeSkillResult,
    PublishSkillCommand,
    PublishSkillResult,
    RecommendSkillsCommand,
    RecommendSkillsResult,
    RenameSkillCommand,
    RenameSkillResult,
    RepairSkillsCommand,
    RepairSkillsResult,
    SyncSkillsCommand,
    SyncSkillsResult,
    TrackLatentSkillCommand,
    TrackLatentSkillResult,
    UpdateCanonicalSkillCommand,
    UpdateCanonicalSkillResult,
    UpdateSkillCommand,
    UpdateSkillResult,
    ValidateSkillCommand,
    ValidateSkillResult,
)
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEventScope,
    ContextSummaryScope,
    FactScope,
    FactStatus,
    LatentSkillScope,
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
DoctorCommandHandler = Callable[[DoctorCommand], DoctorResult]
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
TrackLatentSkillCommandHandler = Callable[[TrackLatentSkillCommand], TrackLatentSkillResult]
GenerateSkillCommandHandler = Callable[[GenerateSkillCommand], GenerateSkillResult]
CreateSkillCommandHandler = Callable[[CreateSkillCommand], CreateSkillResult]
CreateSkillDraftCommandHandler = Callable[[CreateSkillDraftCommand], DraftSkillResult]
PublishSkillCommandHandler = Callable[[PublishSkillCommand], PublishSkillResult]
ValidateSkillCommandHandler = Callable[[ValidateSkillCommand], ValidateSkillResult]
AdoptSkillCommandHandler = Callable[[AdoptSkillCommand], AdoptSkillResult]
UpdateCanonicalSkillCommandHandler = Callable[
    [UpdateCanonicalSkillCommand], UpdateCanonicalSkillResult
]
RenameSkillCommandHandler = Callable[[RenameSkillCommand], RenameSkillResult]
CleanupSkillCommandHandler = Callable[[CleanupSkillCommand], CleanupSkillResult]
RepairSkillsCommandHandler = Callable[[RepairSkillsCommand], RepairSkillsResult]
PromoteSkillRecommendationCommandHandler = Callable[
    [PromoteSkillRecommendationCommand], PromoteSkillRecommendationResult
]
ImportSkillCommandHandler = Callable[[ImportSkillCommand], ImportSkillResult]
RecommendSkillsCommandHandler = Callable[[RecommendSkillsCommand], RecommendSkillsResult]
SyncSkillsCommandHandler = Callable[[SyncSkillsCommand], SyncSkillsResult]
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
    doctor: DoctorCommandHandler = _missing_use_case
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
    track_latent_skill: TrackLatentSkillCommandHandler = _missing_use_case
    generate_skill: GenerateSkillCommandHandler = _missing_use_case
    create_skill: CreateSkillCommandHandler = _missing_use_case
    create_skill_draft: CreateSkillDraftCommandHandler = _missing_use_case
    publish_skill: PublishSkillCommandHandler = _missing_use_case
    validate_skill: ValidateSkillCommandHandler = _missing_use_case
    adopt_skill: AdoptSkillCommandHandler = _missing_use_case
    update_canonical_skill: UpdateCanonicalSkillCommandHandler = _missing_use_case
    rename_skill: RenameSkillCommandHandler = _missing_use_case
    cleanup_skill: CleanupSkillCommandHandler = _missing_use_case
    repair_skills: RepairSkillsCommandHandler = _missing_use_case
    promote_skill_recommendation: PromoteSkillRecommendationCommandHandler = _missing_use_case
    import_skill: ImportSkillCommandHandler = _missing_use_case
    recommend_skills: RecommendSkillsCommandHandler = _missing_use_case
    sync_skills: SyncSkillsCommandHandler = _missing_use_case
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

    def require_project_initialized() -> None:
        result = use_cases.status(GetMemoryStatusCommand(project_root=root))
        if not result.initialized:
            raise ValidationFailedError(
                "Project memory is not initialized. Call initialize_project first."
            )

    def project_initialized() -> bool:
        return use_cases.status(GetMemoryStatusCommand(project_root=root)).initialized

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

    @server.tool(name="doctor")
    def doctor() -> ToolResponse:
        """Run read-only environment diagnostics for Universal Memory."""
        try:
            result = use_cases.doctor(DoctorCommand(project_root=root))
            return _doctor_success_envelope(result)
        except Exception as error:
            return _mcp_tool_error(error, operation="doctor", scope="environment")

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
            if context_scope is ContextSummaryScope.project:
                require_project_initialized()
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
            if fact_scope is FactScope.project:
                require_project_initialized()
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
            if fact_scope is None or fact_scope is FactScope.project:
                require_project_initialized()
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
            if fact_scope is None or fact_scope is FactScope.project:
                require_project_initialized()
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
            if audit_scope is AuditEventScope.project:
                require_project_initialized()
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
            if snapshot_scope is SnapshotScope.project:
                require_project_initialized()
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
            if snapshot_scope is SnapshotScope.project:
                require_project_initialized()
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
            require_project_initialized()
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
            require_project_initialized()
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
            require_project_initialized()
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
        decision: Literal["yes", "y", "always", "no", "n"] | None = None,
    ) -> ToolResponse:
        """Review or decide a latent skill proposal.

        If `decision` is omitted, returns the suggested name, scope, purpose,
        evidence, and explicit choices for a follow-up call.
        """
        try:
            require_project_initialized()
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

    @server.tool(name="track_latent_skill")
    def track_latent_skill(
        name: str,
        description: str,
        scope: Literal["project", "global"] = "project",
        evidence_summary: str = "Manual user invocation via MCP.",
        tags: list[str] | None = None,
    ) -> ToolResponse:
        """Explicitly track or increment recurrence for a latent skill opportunity."""
        try:
            latent_scope = _latent_skill_scope(scope)
            if latent_scope is LatentSkillScope.project:
                require_project_initialized()
            result = use_cases.track_latent_skill(
                TrackLatentSkillCommand(
                    name=name,
                    description=description,
                    scope=latent_scope,
                    origin="mcp",
                    evidence_summary=evidence_summary,
                    tags=tags or [],
                )
            )
            skill = result.latent_skill
            return _success_envelope(
                operation="skills.track",
                scope=skill.scope.value,
                data={
                    "latent_skill": {
                        "id": skill.id,
                        "name": skill.name,
                        "description": skill.description,
                        "scope": skill.scope.value,
                        "status": skill.status.value,
                        "recurrence_count": skill.recurrence_count,
                        "metadata": skill.metadata,
                        "created_at": format_utc_iso(skill.created_at),
                        "updated_at": format_utc_iso(skill.updated_at),
                    },
                    "matched_existing": result.matched_existing,
                    "audit_reference": result.audit_reference,
                    "snapshot_reference": result.snapshot_reference,
                },
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.track", scope=_raw_scope(scope))

    @server.tool(name="generate_skill")
    def generate_skill(
        latent_skill_id: str,
        update_existing: bool = False,
    ) -> ToolResponse:
        """Generate the physical Agent Skill structure for an approved latent skill."""
        try:
            require_project_initialized()
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

    @server.tool(name="create_skill")
    def create_skill(  # noqa: PLR0913
        name: str,
        description: str,
        scope: Literal["project", "global"] = "project",
        slug: str | None = None,
        sync: bool = False,
        triggers: list[str] | None = None,
        raw_markdown: str | None = None,
        targets: list[str] | None = None,
    ) -> ToolResponse:
        """Create a canonical Agent Skill without native sync unless sync is explicit."""
        try:
            latent_scope = _latent_skill_scope(scope)
            if latent_scope is LatentSkillScope.project:
                require_project_initialized()
            result = use_cases.create_skill(
                CreateSkillCommand(
                    name=name.strip(),
                    description=description.strip(),
                    scope=latent_scope,
                    origin="mcp",
                    triggers=_normalize_triggers(triggers) or [],
                    raw_markdown=raw_markdown,
                    slug=slug,
                    sync=sync,
                    targets=targets,
                )
            )
            return _success_envelope(
                operation="skills.create",
                scope=result.latent_skill.scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.create", scope=_raw_scope(scope))

    @server.tool(name="create_skill_draft")
    def create_skill_draft(  # noqa: PLR0913
        name: str,
        description: str,
        scope: Literal["project", "global"] = "project",
        slug: str | None = None,
        triggers: list[str] | None = None,
        raw_markdown: str | None = None,
    ) -> ToolResponse:
        """Create an editable draft skill without canonical publish or native runtime writes."""
        try:
            latent_scope = _latent_skill_scope(scope)
            if latent_scope is LatentSkillScope.project:
                require_project_initialized()
            result = use_cases.create_skill_draft(
                CreateSkillDraftCommand(
                    name=name.strip(),
                    description=description.strip(),
                    scope=latent_scope,
                    origin="mcp",
                    slug=slug,
                    triggers=_normalize_triggers(triggers) or [],
                    raw_markdown=raw_markdown,
                )
            )
            return _success_envelope(
                operation="skills.draft.create",
                scope=latent_scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.draft.create", scope=_raw_scope(scope))

    @server.tool(name="validate_skill")
    def validate_skill(
        skill_or_path: str,
        scope: Literal["project", "global"] | None = None,
    ) -> ToolResponse:
        """Validate a draft, canonical skill, or local skill path without mutating files."""
        try:
            result = use_cases.validate_skill(
                ValidateSkillCommand(
                    skill_or_path=skill_or_path,
                    scope=_latent_skill_scope_optional(scope),
                )
            )
            return _success_envelope(
                operation="skills.validate",
                scope=_raw_scope(scope) if scope else "project",
                data=result.to_payload(),
                warnings=result.report.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.validate", scope="project")

    @server.tool(name="publish_skill")
    def publish_skill(
        draft_or_path: str,
        slug: str | None = None,
        sync: bool = False,
        targets: list[str] | None = None,
    ) -> ToolResponse:
        """Publish a validated draft as canonical and optionally sync native targets."""
        try:
            require_project_initialized()
            result = use_cases.publish_skill(
                PublishSkillCommand(
                    draft_or_path=draft_or_path,
                    origin="mcp",
                    slug=slug,
                    sync=sync,
                    targets=targets,
                )
            )
            return _success_envelope(
                operation="skills.publish",
                scope=result.agent_skill.scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.publish", scope="project")

    @server.tool(name="promote_skill_recommendation")
    def promote_skill_recommendation(
        recommendation_id: str,
        edits: dict[str, Any] | None = None,
        targets: list[str] | None = None,
    ) -> ToolResponse:
        """Promote an approved latent skill candidate into a canonical Agent Skill."""
        try:
            initialized = project_initialized()
            edits = edits or {}
            result = use_cases.promote_skill_recommendation(
                PromoteSkillRecommendationCommand(
                    recommendation_id=recommendation_id,
                    origin="mcp",
                    name=_optional_str(edits.get("name")),
                    description=_optional_str(edits.get("description")),
                    triggers=_normalize_triggers(edits.get("triggers")),
                    targets=targets,
                    project_initialized=initialized,
                )
            )
            return _success_envelope(
                operation="skills.promote",
                scope=result.promoted_recommendation.scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(
                _map_skill_mutation_error(error, recommendation_id),
                operation="skills.promote",
                scope="project",
            )

    @server.tool(name="sync_skills")
    def sync_skills(
        skill_id_or_name: str | None = None,
        targets: list[str] | None = None,
        drift_decision: Literal["keep", "overwrite"] = "keep",
        check_gitignore: bool = False,
    ) -> ToolResponse:
        """Synchronize canonical Agent Skills into native targets with optional git warnings."""
        try:
            require_project_initialized()
            if drift_decision not in {"keep", "overwrite"}:
                raise ValidationFailedError("drift_decision must be 'keep' or 'overwrite'.")
            result = use_cases.sync_skills(
                SyncSkillsCommand(
                    skill_id_or_name=skill_id_or_name.strip() if skill_id_or_name else None,
                    targets=targets,
                    drift_decision=drift_decision,
                    origin="mcp",
                    check_gitignore=check_gitignore,
                )
            )
            return _success_envelope(
                operation="skills.sync",
                scope="all",
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.sync", scope="all")

    @server.tool(name="import_skill")
    def import_skill(
        path: str,
        scope: Literal["project", "global"] = "project",
        replace_native: bool = False,
        sync_after_import: bool = False,
    ) -> ToolResponse:
        """Import an existing native or local Agent Skill directory into canonical UMEM storage."""
        try:
            latent_scope = _latent_skill_scope(scope)
            if latent_scope is LatentSkillScope.project:
                require_project_initialized()
            result = use_cases.import_skill(
                ImportSkillCommand(
                    path=path,
                    scope=latent_scope,
                    origin="mcp",
                    replace_native=replace_native,
                    sync_after_import=sync_after_import,
                )
            )
            return _success_envelope(
                operation="skills.import",
                scope=result.latent_skill.scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.import", scope=_raw_scope(scope))

    @server.tool(name="adopt_skill")
    def adopt_skill(
        path: str,
        scope: Literal["project", "global"] = "project",
        slug: str | None = None,
        replace_native: bool = False,
        sync_after_adopt: bool = False,
    ) -> ToolResponse:
        """Adopt an existing skill directory into UMEM without creating duplicate slugs."""
        try:
            latent_scope = _latent_skill_scope(scope)
            if latent_scope is LatentSkillScope.project:
                require_project_initialized()
            result = use_cases.adopt_skill(
                AdoptSkillCommand(
                    path=path,
                    scope=latent_scope,
                    origin="mcp",
                    slug=slug,
                    replace_native=replace_native,
                    sync_after_adopt=sync_after_adopt,
                )
            )
            return _success_envelope(
                operation="skills.adopt",
                scope=result.agent_skill.scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.adopt", scope=_raw_scope(scope))

    @server.tool(name="update_canonical_skill")
    def update_canonical_skill(
        skill_id_or_name: str,
        raw_markdown: str,
        sync: bool = False,
        drift_decision: Literal["keep", "overwrite"] = "keep",
    ) -> ToolResponse:
        """Update canonical skill content with validation and optional native sync."""
        try:
            require_project_initialized()
            result = use_cases.update_canonical_skill(
                UpdateCanonicalSkillCommand(
                    skill_id_or_name=skill_id_or_name,
                    origin="mcp",
                    raw_markdown=raw_markdown,
                    sync=sync,
                    drift_decision=drift_decision,
                )
            )
            return _success_envelope(
                operation="skills.canonical.update",
                scope=result.agent_skill.scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.canonical.update", scope="project")

    @server.tool(name="rename_skill")
    def rename_skill(skill_id_or_name: str, slug: str) -> ToolResponse:
        """Rename a canonical skill slug while blocking unmanaged destination conflicts."""
        try:
            require_project_initialized()
            result = use_cases.rename_skill(
                RenameSkillCommand(
                    skill_id_or_name=skill_id_or_name,
                    slug=slug,
                    origin="mcp",
                )
            )
            return _success_envelope(
                operation="skills.rename",
                scope=result.agent_skill.scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.rename", scope="project")

    @server.tool(name="cleanup_skill")
    def cleanup_skill(
        skill_id_or_name: str,
        targets: bool = True,
        dry_run: bool = True,
    ) -> ToolResponse:
        """Plan or apply managed-only native target cleanup for a canonical skill."""
        try:
            require_project_initialized()
            result = use_cases.cleanup_skill(
                CleanupSkillCommand(
                    skill_id_or_name=skill_id_or_name,
                    origin="mcp",
                    targets=targets,
                    dry_run=dry_run,
                )
            )
            return _success_envelope(
                operation="skills.cleanup",
                scope="project",
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.cleanup", scope="project")

    @server.tool(name="repair_skills")
    def repair_skills(
        remove_orphan_targets: bool = False,
        dry_run: bool = True,
    ) -> ToolResponse:
        """Plan or apply managed-only repair for orphan native skill targets."""
        try:
            require_project_initialized()
            result = use_cases.repair_skills(
                RepairSkillsCommand(
                    origin="mcp",
                    remove_orphan_targets=remove_orphan_targets,
                    dry_run=dry_run,
                )
            )
            return _success_envelope(
                operation="skills.repair",
                scope="project",
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.repair", scope="project")

    @server.tool(name="list_skills")
    def list_skills() -> ToolResponse:
        """List registered skills and candidates without mutating local state."""
        try:
            require_project_initialized()
            result = use_cases.list_skills(ListSkillsCommand())
            return _success_envelope(
                operation="skills.list",
                scope="all",
                data=result.to_payload(),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.list", scope="all")

    @server.tool(name="recommend_skills")
    def recommend_skills(
        scope: Literal["project", "global", "all"] = "project",
        min_recurrence: int | None = None,
        dry_run: bool = True,
    ) -> ToolResponse:
        """Review read-only latent skill recommendations captured by explicit skills.track evidence.

        This never promotes, imports, syncs, creates, or mutates skills. `dry_run` is accepted
        for API clarity; non-read-only behavior is not supported.
        """
        try:
            _ = dry_run
            latent_scope = _latent_skill_scope_optional_all(scope)
            if latent_scope is None or latent_scope is LatentSkillScope.project:
                require_project_initialized()
            result = use_cases.recommend_skills(
                RecommendSkillsCommand(scope=latent_scope, min_recurrence=min_recurrence)
            )
            return _success_envelope(
                operation="skills.recommend",
                scope=latent_scope.value if latent_scope is not None else "all",
                data=result.to_payload(),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.recommend", scope=_raw_scope(scope))

    @server.tool(name="get_skill_detail")
    def get_skill_detail(name_or_id: str) -> ToolResponse:
        """Inspect metadata and triggers for one registered skill."""
        try:
            require_project_initialized()
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
            require_project_initialized()
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
            require_project_initialized()
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
            require_project_initialized()
            result = use_cases.update_skill(
                UpdateSkillCommand(
                    latent_skill_id=latent_skill_id,
                    origin="mcp",
                    name=name.strip() if name is not None else None,
                    description=description.strip() if description is not None else None,
                    triggers=_normalize_triggers(triggers),
                    raw_markdown=raw_markdown,
                    native_drift_decision="keep",
                )
            )
            return _success_envelope(
                operation="skills.update",
                scope=result.latent_skill.scope.value,
                data=_skill_mutation_payload(result),
                warnings=result.warnings,
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
            "installed_version": result.installed_version,
            "recommended_action": result.recommended_action,
        }

    return {
        "initialized": True,
        "project_path": result.project_path,
        "installed_version": result.installed_version,
        "fact_counts": result.fact_counts,
        "active_rules_count": result.active_rules_count,
        "registered_skills_count": result.registered_skills_count,
        "approximate_size_bytes": result.approximate_size_bytes,
        "last_health_check": result.last_health_check,
        "host_validation": result.host_validation,
    }


def _doctor_success_envelope(result: DoctorResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "operation": "doctor",
        "scope": "environment",
        "data": result.to_payload(),
        "warnings": [],
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


def _normalize_triggers(triggers: object) -> list[str] | None:
    if triggers is None:
        return None
    if isinstance(triggers, list):
        values = triggers
    elif isinstance(triggers, tuple | set):
        values = list(triggers)
    else:
        values = [triggers]
    return [str(trigger).strip() for trigger in values if str(trigger).strip()]


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip()


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


def _latent_skill_scope(value: Literal["project", "global"]) -> LatentSkillScope:
    normalized = str(value).lower()
    if normalized == "global":
        return LatentSkillScope.global_
    if normalized == "project":
        return LatentSkillScope.project
    raise ValidationFailedError("scope must be 'project' or 'global'.")


def _latent_skill_scope_optional_all(
    value: Literal["project", "global", "all"],
) -> LatentSkillScope | None:
    normalized = str(value).lower()
    if normalized == "all":
        return None
    if normalized == "global":
        return LatentSkillScope.global_
    if normalized == "project":
        return LatentSkillScope.project
    raise ValidationFailedError("scope must be 'project', 'global', or 'all'.")


def _latent_skill_scope_optional(
    value: Literal["project", "global"] | None,
) -> LatentSkillScope | None:
    if value is None:
        return None
    return _latent_skill_scope(value)


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
    if normalized in {"y", "yes"}:
        return ProposeSkillDecision.yes
    if normalized == "always":
        return ProposeSkillDecision.always
    if normalized in {"n", "no"}:
        return ProposeSkillDecision.no
    raise ValidationFailedError("decision must be 'yes', 'always' or 'no'.")


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
            f"Latent skill '{latent_skill_id}' not found in the repository."
        )
    return error


def _error_code(error: Exception) -> int:
    return error_descriptor(error).json_rpc_code


def _error_message(error: Exception) -> str:
    return error_descriptor(error).mcp_message


def _sanitize_error_detail(error: Exception) -> str:
    return sanitize_error_detail(error)
