from __future__ import annotations

import sys
import traceback
from collections.abc import Callable
from dataclasses import asdict, dataclass
from inspect import signature
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

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
from universal_memory.application.layout import (
    InspectProjectLayoutUseCase,
    MigrateProjectLayoutCommand,
    MigrateProjectLayoutUseCase,
)
from universal_memory.application.memory import (
    DEFAULT_CONTEXT_MAX_SIZE_CHARS,
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
from universal_memory.application.onboarding import (
    AgentConnectionExecution,
    AgentConnectionPlan,
    ExecuteAgentConnectionsUseCase,
    SessionBootstrapCommand,
    SessionBootstrapResult,
    default_agent_connection_planner,
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
    ShareSkillCommand,
    ShareSkillResult,
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
from universal_memory.domain.entities.runtime import default_runtime_registry
from universal_memory.infrastructure.config import LocalProjectLayoutPort
from universal_memory.interfaces import errors as interface_errors
from universal_memory.interfaces.errors import (
    error_descriptor,
    error_payload,
    json_rpc_error_payload,
    normalize_bootstrap_error,
    sanitize_error_detail,
)
from universal_memory.interfaces.payloads import (
    context_payload as _context_payload,
)
from universal_memory.interfaces.payloads import (
    session_bootstrap_payload,
)
from universal_memory.interfaces.payloads import (
    status_payload as _status_payload,
)

JSON_RPC_SECRET_DETECTED = interface_errors.JSON_RPC_SECRET_DETECTED
JSON_RPC_SNAPSHOT_FAILED = interface_errors.JSON_RPC_SNAPSHOT_FAILED
JSON_RPC_VALIDATION_FAILED = interface_errors.JSON_RPC_VALIDATION_FAILED
JSON_RPC_FACT_NOT_FOUND = interface_errors.JSON_RPC_FACT_NOT_FOUND
JSON_RPC_INVALID_CONFIG = interface_errors.JSON_RPC_INVALID_CONFIG
JSON_RPC_STORAGE_ERROR = interface_errors.JSON_RPC_STORAGE_ERROR
JSON_RPC_UNEXPECTED_ERROR = interface_errors.JSON_RPC_UNEXPECTED_ERROR

SetupProjectCommandHandler = Callable[..., SetupProjectResult]
StatusCommandHandler = Callable[[GetMemoryStatusCommand], GetMemoryStatusResult]
BootstrapCommandHandler = Callable[[SessionBootstrapCommand], SessionBootstrapResult]
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
ShareSkillCommandHandler = Callable[[ShareSkillCommand], ShareSkillResult]
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
LayoutMigrateCommandHandler = Callable[[MigrateProjectLayoutCommand], dict[str, Any]]


def _missing_use_case(_command: Any) -> Any:
    msg = "MCP use case dependency was not configured."
    raise RuntimeError(msg)


def _execute_initialize_project(
    command: SetupProjectCommandHandler,
    project_root: Path,
    *,
    layout: str,
) -> SetupProjectResult:
    try:
        sig = signature(command)
        if "layout" in sig.parameters:
            return command(project_root, layout=layout)
    except (TypeError, ValueError):
        pass
    return command(project_root)


@dataclass(frozen=True, slots=True)
class MCPUseCases:
    status: StatusCommandHandler
    context: ContextCommandHandler
    bootstrap: BootstrapCommandHandler = _missing_use_case
    doctor: DoctorCommandHandler = _missing_use_case
    initialize_project: SetupProjectCommandHandler = _missing_use_case
    execute_agent_connections: ExecuteAgentConnectionsUseCase | None = None
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
    share_skill: ShareSkillCommandHandler = _missing_use_case
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
    migrate_project_layout: LayoutMigrateCommandHandler = _missing_use_case


def create_mcp_server(name: str = "universal-memory") -> FastMCP:
    return FastMCP(
        name,
        instructions=(
            "Universal Memory manages local project/global facts, context, host "
            "instructions, and Agent Skills. Start a session with bootstrap; inspect only "
            "relevant skill details. Tools run with the server process filesystem "
            "permissions. No server account, API key, or remote-service rate limit is "
            "required. Tools operate locally except initialize_project, which can invoke "
            "the official skill installer over the network. Local repositories may use "
            "storage lock files during reads. Context assembly and host validation also "
            "persist summaries/audit records as disclosed by their tools. Success returns "
            "ok, operation, scope, data, warnings; failure returns a sanitized error "
            "envelope. Inspect ok and warnings. Annotations describe every supported mode, "
            "including optional apply/overwrite modes, not just safe defaults. Do not "
            "blindly retry mutations after an uncertain result."
        ),
    )


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

    @server.tool(
        name="initialize_project",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True
        ),
    )
    def initialize_project(
        layout: Annotated[
            Literal["legacy", "shared"],
            Field(
                description=(
                    "Project storage layout: legacy keeps content under .umem; "
                    "shared uses visible umem content plus private operational "
                    "storage. Defaults to legacy."
                )
            ),
        ] = "legacy",
    ) -> ToolResponse:
        """Initialize local project memory and configure detected agent connections. Use for a new
        workspace; use inspect_project_layout to inspect storage or migrate_project_layout to
        share existing legacy content. Creates project storage and managed host configuration
        and may install the official skill through npx, requiring Node.js and network access
        when that bridge is selected. Existing managed content is reconciled rather than blindly
        replaced. Returns initialization details, connection execution results, warnings, and
        manual fallback steps; inspect them before retrying. Repeated calls may run connection
        validation again.
        """
        try:
            result = _execute_initialize_project(use_cases.initialize_project, root, layout=layout)
            payload = _init_payload(result, root)
            plan = default_agent_connection_planner(default_runtime_registry()).plan(root)
            executor = use_cases.execute_agent_connections or ExecuteAgentConnectionsUseCase(
                host_setup_command=use_cases.host_setup,
                host_check_command=use_cases.host_check,
                context_read_command=use_cases.context,
                known_runtime_ids=frozenset(
                    runtime_id.value for runtime_id in default_runtime_registry().runtime_ids
                ),
            )
            execution = executor.execute(
                plan,
                accepted=True,
                origin="mcp_init",
                persist_connections=False,
            )
            payload.update(_mcp_connection_plan_payload(plan, execution=execution))
            return _success_envelope(
                operation="init",
                scope="project",
                data=payload,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="init", scope="project")

    @server.tool(
        name="status",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def status() -> ToolResponse:
        """Inspect project initialization, fact counts, storage size, registered skills, and host
        validation status. Use before initialization or to diagnose whether context can be
        loaded; use doctor for environment diagnostics and bootstrap for session startup. Does
        not change memory records or configure hosts. Returns status and recommended actions,
        including initialized=false for an uninitialized project.
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

    @server.tool(
        name="bootstrap",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def bootstrap() -> ToolResponse:
        """Load status, project context, and the skill catalog once at session startup. Use instead
        of separate status, context, and list_skills calls; use get_skill_detail only for
        relevant catalog entries. Requires initialized project memory for context loading.
        Persists the compiled context summary and audit event; repeated calls create fresh
        records. Does not install skills or synchronize hosts. Returns status, context, and
        skills on success or an error envelope if a step fails.
        """
        try:
            result = use_cases.bootstrap(SessionBootstrapCommand(project_root=root))
            return _success_envelope(
                operation="bootstrap",
                scope="project",
                data=session_bootstrap_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(
                normalize_bootstrap_error(error),
                operation="bootstrap",
                scope="project",
            )

    @server.tool(
        name="inspect_project_layout",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def inspect_layout() -> ToolResponse:
        """Inspect which local project storage layout and roots are active, including migration
        warnings. Use before initialize_project or migrate_project_layout when layout is
        uncertain. Does not initialize, copy, or remove project content and requires no
        initialized project. Returns the layout report, storage paths, and warnings.
        """
        try:
            result = InspectProjectLayoutUseCase(
                project_root=root,
                layout_port=LocalProjectLayoutPort(),
            ).execute()
            report = result["data"]
            return _success_envelope(
                operation=result["operation"],
                scope="project",
                data=report,
                warnings=report["warnings"],
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="layout.status", scope="project")

    @server.tool(
        name="migrate_project_layout",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def migrate_project_layout(  # noqa: PLR0913
        target_layout: Annotated[
            Literal["shared"],
            Field(
                description=(
                    "Destination layout. Only shared is supported. Applying migration "
                    "removes migrated/already-shared facts from the legacy facts file; "
                    "private/global/conflicting facts remain."
                )
            ),
        ] = "shared",
        dry_run: Annotated[
            bool,
            Field(
                description=(
                    "true (default) previews without modifying content. false applies "
                    "shared writes and rewrites the legacy facts file to remove "
                    "migrated/already-shared facts."
                )
            ),
        ] = True,
        include: Annotated[
            list[Literal["facts", "rules", "skills"]] | None,
            Field(
                description=(
                    "Content kinds to migrate. Omitted or empty selects facts, rules, and skills."
                )
            ),
        ] = None,
        private_fact_ids: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Fact IDs to retain privately instead of copying into shared "
                    "content; omitted or empty excludes none explicitly."
                )
            ),
        ] = None,
        private_skill_slugs: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Skill slugs to retain privately; omitted or empty excludes none explicitly."
                )
            ),
        ] = None,
        shared_operational_skill_slugs: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Explicit operational skill slugs allowed into shared content; "
                    "omitted or empty grants no such exceptions."
                )
            ),
        ] = None,
    ) -> ToolResponse:
        """Preview or migrate selected legacy project facts, rules, and skills into shared
        repository storage. Use to expose curated existing content; initialize_project creates
        new storage and share_skill shares one skill. Requires legacy content and filesystem
        access. dry_run=true previews without modifying content. false writes shared content and
        migration state, then rewrites the legacy facts file to remove migrated or already-
        shared facts; private, global, and conflicting facts remain local. Writes use the safe
        snapshot/audit pipeline. Returns the migration plan/results and warnings. Review private
        exclusions and source changes before applying: shared content can become visible to
        repository collaborators.
        """
        try:
            command_handler = use_cases.migrate_project_layout
            if command_handler is _missing_use_case:
                command_handler = MigrateProjectLayoutUseCase(project_root=root).execute
            result = command_handler(
                MigrateProjectLayoutCommand(
                    target_layout=target_layout,
                    dry_run=dry_run,
                    include=tuple(include or ["facts", "rules", "skills"]),
                    private_fact_ids=tuple(private_fact_ids or []),
                    private_skill_slugs=tuple(private_skill_slugs or []),
                    shared_operational_skill_slugs=tuple(shared_operational_skill_slugs or []),
                )
            )
            return _success_envelope(
                operation=result["operation"],
                scope="project",
                data=result["data"],
                warnings=result.get("warnings", []),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="layout.migrate", scope="project")

    @server.tool(
        name="doctor",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def doctor() -> ToolResponse:
        """Inspect Python, storage, project layout, and supported host integration health. Use for
        diagnostic checks; use host_setup to change configuration. Does not repair or install
        anything and can inspect an uninitialized environment. Returns named checks with
        success/failure details and recovery guidance.
        """
        try:
            result = use_cases.doctor(DoctorCommand(project_root=root))
            return _doctor_success_envelope(result)
        except Exception as error:
            return _mcp_tool_error(error, operation="doctor", scope="environment")

    @server.tool(
        name="context",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def context(
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
        max_size_chars: Annotated[
            int,
            Field(
                description=(
                    "Maximum compiled Markdown length in characters, including "
                    "headings. Defaults to 4000; values below the 110-character "
                    "template minimum fail."
                )
            ),
        ] = DEFAULT_CONTEXT_MAX_SIZE_CHARS,
        agent_session_key: Annotated[
            str | None,
            Field(
                description=(
                    "Optional caller session correlation key included in the audit "
                    "event. Omitted leaves it unset; do not include secrets."
                )
            ),
        ] = None,
    ) -> ToolResponse:
        """Compile active facts, preferences, and rules into prompt-ready Markdown within a
        character budget. Use for agent context; use list_facts to inspect individual records.
        Project scope requires initialized project memory; global scope excludes project
        content. Persists a generated summary and audit event, so repeated calls create new
        records even with identical arguments. Returns context_markdown, included fact IDs, size
        information, and the summary metadata.
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

    @server.tool(
        name="remember_fact",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def remember_fact(
        content: Annotated[
            str,
            Field(
                description=(
                    "Curated durable fact text to persist. Secret detection can "
                    "reject sensitive content; do not submit credentials or raw "
                    "logs."
                )
            ),
        ],
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
        tags: Annotated[
            list[str] | None,
            Field(description="Optional classification tags. Omitted or empty adds no tags."),
        ] = None,
        visibility: Annotated[
            Literal["shared", "private"] | None,
            Field(
                description=(
                    "Project content visibility: shared for repository content, "
                    "private for operational storage. Omitted follows "
                    "layout/category policy; global content cannot be shared."
                )
            ),
        ] = None,
    ) -> ToolResponse:
        """Save a curated durable memory fact, with optional tags and visibility. Use for a learned
        preference or project decision; use track_latent_skill for repeated workflow evidence
        and list_facts for inspection. Project scope requires initialization. Writes a fact
        through the safe mutation pipeline with audit/snapshot references; repeated calls may
        add records rather than update an existing fact. Returns the stored fact and write
        references. Do not store secrets or raw conversation logs.
        """
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
                    visibility=visibility,
                )
            )
            return _success_envelope(
                operation="remember",
                scope=fact_scope.value,
                data=_remember_payload(result),
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="remember", scope=_raw_scope(scope))

    @server.tool(
        name="list_facts",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def list_facts(
        scope: Annotated[
            Literal["project", "global"] | None,
            Field(
                description=(
                    "Select project or global facts; omitted searches both. Project"
                    " and combined reads require project initialization."
                )
            ),
        ] = None,
        status: Annotated[
            Literal["active", "stale", "archived", "purged"],
            Field(
                description=(
                    "Fact lifecycle filter; defaults to active. stale, archived, "
                    "and purged inspect those record states instead."
                )
            ),
        ] = "active",
        visibility: Annotated[
            Literal["shared", "private", "all"],
            Field(
                description=(
                    "Filter shared, private, or all content; defaults to all "
                    "visible to this local process."
                )
            ),
        ] = "all",
    ) -> ToolResponse:
        """Inspect individual memory facts filtered by scope, lifecycle status, and visibility. Use
        for record IDs and metadata; use context for compiled prompt context. Project or
        combined scope requires initialized project memory. Does not change fact records.
        Returns a facts array; omitted scope searches both project and global records, while
        omitted status selects active records.
        """
        try:
            fact_scope = _fact_scope_optional(scope)
            if fact_scope is None or fact_scope is FactScope.project:
                require_project_initialized()
            result = use_cases.list_facts(
                ListFactsCommand(scope=fact_scope, status=FactStatus(status), visibility=visibility)
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

    @server.tool(
        name="purge_fact",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def purge_fact(
        id: Annotated[
            str | None,
            Field(
                description=(
                    "Exact fact ID from list_facts. Selects one fact; omit when "
                    "purging an entire explicit scope. Cannot be combined with "
                    "scope."
                )
            ),
        ] = None,
        scope: Annotated[
            Literal["project", "global"] | None,
            Field(
                description=(
                    "Explicit project/global scope to purge in full when id is "
                    "omitted. Cannot be combined with id; omitting both is "
                    "rejected."
                )
            ),
        ] = None,
        confirm: Annotated[
            bool,
            Field(
                description=(
                    "Explicit destructive-operation authorization. Defaults to "
                    "false, which rejects the operation without applying it."
                )
            ),
        ] = False,
    ) -> ToolResponse:
        """Destructively remove one fact by ID or all facts in an explicitly selected scope. Use
        list_facts first to identify intended records; use context only for reading.
        confirm=true is mandatory; false rejects without purging. Supply id or scope, not both;
        omitting both is rejected. Project or unscoped ID lookup requires initialization. The
        configured repository uses safe writes for recovery; inspect list_snapshots and
        list_audit_events rather than assuming the response contains a snapshot ID. Returns
        purged_count, affected_ids, and an audit marker. Repeating a purge may fail if the fact
        no longer exists.
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

    @server.tool(
        name="list_audit_events",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def list_audit_events(
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
    ) -> ToolResponse:
        """Read audit events for one memory scope to investigate prior operations and recovery
        references. Use list_snapshots to inspect recoverable snapshots instead. Project scope
        requires initialization. Does not create audit events or change recorded history.
        Returns an events array with the recorded operation details.
        """
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

    @server.tool(
        name="list_snapshots",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def list_snapshots(
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
    ) -> ToolResponse:
        """Read created recovery snapshots in one scope. Use before rollback_scope to inspect
        available recovery points; list_audit_events provides operation history. Project scope
        requires initialization. Does not create or restore snapshots. Returns the created
        snapshots array; already consumed snapshots are excluded.
        """
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

    @server.tool(
        name="rollback_scope",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def rollback_scope(
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
        confirm: Annotated[
            bool,
            Field(
                description=(
                    "Explicit destructive-operation authorization. Defaults to "
                    "false, which rejects the operation without applying it."
                )
            ),
        ] = False,
    ) -> ToolResponse:
        """Restore the latest created snapshot in a scope, replacing current state covered by that
        snapshot. Use list_snapshots and list_audit_events before choosing recovery.
        confirm=true is required; false rejects without restoring. Project scope requires
        initialization. Returns restored state references and rollback details. Destructive and
        not idempotent: a second call can select a different snapshot, so inspect results before
        retrying.
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

    @server.tool(
        name="host_setup",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def host_setup(
        host_id: Annotated[
            str,
            Field(
                description=(
                    "Supported host registry ID, for example codex or claude_code; "
                    "use the ID rather than a display name."
                )
            ),
        ],
        force: Annotated[
            bool,
            Field(
                description=(
                    "Apply managed host configuration when true. Defaults to false "
                    "for planning; does not bypass unmanaged-content protections."
                )
            ),
        ] = False,
        max_lines: Annotated[
            int,
            Field(
                description=(
                    "Maximum managed instruction block length in lines. Defaults to"
                    " 100; used together with max_chars and host policy limits."
                )
            ),
        ] = 100,
        max_chars: Annotated[
            int,
            Field(
                description=(
                    "Maximum managed instruction block length in characters. "
                    "Defaults to 4000; both line and character limits apply."
                )
            ),
        ] = 4000,
    ) -> ToolResponse:
        """Plan or apply managed instruction configuration for a supported agent host. Use after
        project initialization; use host_check to validate an existing configuration and
        sync_instructions to refresh active rules. force=false returns a plan; force=true
        applies managed changes through the snapshot/audit pipeline. It does not mean
        unrestricted overwrite of unmanaged files. Returns planned changes, validation, manual
        steps, warnings, and write references.
        """
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

    @server.tool(
        name="host_check",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def host_check(
        host_id: Annotated[
            str,
            Field(
                description=(
                    "Supported host registry ID, for example codex or claude_code; "
                    "use the ID rather than a display name."
                )
            ),
        ],
        max_lines: Annotated[
            int,
            Field(
                description=(
                    "Maximum managed instruction block length in lines. Defaults to"
                    " 100; used together with max_chars and host policy limits."
                )
            ),
        ] = 100,
        max_chars: Annotated[
            int,
            Field(
                description=(
                    "Maximum managed instruction block length in characters. "
                    "Defaults to 4000; both line and character limits apply."
                )
            ),
        ] = 4000,
    ) -> ToolResponse:
        """Validate an existing agent host instruction manifest and record the validation result.
        Use after host_setup or to diagnose host readability; use doctor for broader
        diagnostics. Requires initialized project memory. Does not rewrite the host manifest,
        but writes an audit event, so repeated checks create new audit records. Returns
        validation status, checks/manual guidance, warnings, and audit reference.
        """
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

    @server.tool(
        name="sync_instructions",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def sync_instructions(
        host_ids: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Host registry IDs to synchronize. Omitted or empty selects "
                    "codex and claude_code."
                )
            ),
        ] = None,
        apply: Annotated[
            bool,
            Field(
                description=(
                    "Write managed instruction changes when true; defaults to false for a preview."
                )
            ),
        ] = False,
    ) -> ToolResponse:
        """Plan or apply active-rule synchronization into selected agent instruction targets. Use
        after changing approved rules; use sync_skills for native skill directories and
        host_setup for initial host configuration. Requires initialized project memory.
        apply=false previews; true writes managed instruction blocks with recovery/audit
        references. Returns planned changes, validation, warnings, and manual steps; does not
        grant permission to overwrite unrelated host content.
        """
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

    @server.tool(
        name="propose_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def propose_skill(
        latent_skill_id: Annotated[
            str,
            Field(
                description=(
                    "Exact latent candidate ID returned by track_latent_skill, "
                    "list_skills, or recommend_skills; not a canonical skill slug "
                    "or file path."
                )
            ),
        ],
        decision: Annotated[
            Literal["yes", "y", "always", "no", "n"] | None,
            Field(
                description=(
                    "Omit to review only; yes/y accepts, no/n ignores, and always "
                    "accepts while recording future approval policy."
                )
            ),
        ] = None,
    ) -> ToolResponse:
        """Review a tracked latent workflow candidate or record a decision about it. Use after
        track_latent_skill or recommend_skills; use create_skill for an explicitly requested new
        canonical skill. Requires initialized project memory and a latent candidate ID. Omitted
        decision returns a proposal and follow-up choices; yes/y accepts, no/n ignores, and
        always also records future approval policy. Decisions mutate candidate state through the
        safe pipeline. Returns candidate, proposal, decision requirements, and write references;
        inspect state before repeating a decision.
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

    @server.tool(
        name="track_latent_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def track_latent_skill(
        name: Annotated[
            str,
            Field(
                description=(
                    "Nonempty human-readable skill name. Used for display and "
                    "candidate matching; not a file path."
                )
            ),
        ],
        description: Annotated[
            str,
            Field(
                description=(
                    "Nonempty description of the reusable workflow purpose; "
                    "distinguish it from neighboring skills."
                )
            ),
        ],
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
        evidence_summary: Annotated[
            str,
            Field(
                description=(
                    "Sanitized summary of this recurring workflow observation. "
                    "Defaults to Manual user invocation via MCP.; provide specific "
                    "curated evidence without secrets or transcripts."
                )
            ),
        ] = "Manual user invocation via MCP.",
        tags: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional workflow classification tags used in candidate "
                    "matching and merged on recurrence. Omitted or empty adds no "
                    "tags."
                )
            ),
        ] = None,
    ) -> ToolResponse:
        """Record curated evidence of a repeated workflow and create or increment a matching latent
        skill candidate. Use only for recurring workflow observations; use remember_fact for
        preferences and create_skill for an explicit new skill request. Project scope requires
        initialization. Matching proposed/active candidates gain recurrence and evidence;
        otherwise a proposed candidate is created. Not idempotent: every call counts another
        observation. Does not publish or generate skill files. Returns latent_skill,
        matched_existing, and audit/snapshot references. Use recommend_skills or propose_skill
        next; never submit secrets, raw logs, or transcripts as evidence.
        """
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

    @server.tool(
        name="generate_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def generate_skill(
        latent_skill_id: Annotated[
            str,
            Field(
                description=(
                    "Exact latent candidate ID returned by track_latent_skill, "
                    "list_skills, or recommend_skills; not a canonical skill slug "
                    "or file path."
                )
            ),
        ],
        update_existing: Annotated[
            bool,
            Field(
                description=(
                    "Permit updating an existing generated skill when true. "
                    "Defaults to false; native drift protections still apply."
                )
            ),
        ] = False,
    ) -> ToolResponse:
        """Generate physical Agent Skill content for an approved latent candidate. Use after
        proposal approval; use create_skill for new canonical content without a latent candidate
        and publish_skill for a draft. Requires initialized project memory and an eligible
        latent ID. Writes skill content, native copies for enabled runtimes, and related state;
        update_existing=true permits updating existing generated content while retaining native
        drift protections. Returns generation details, paths, warnings, and write references.
        Review existing content before enabling updates or retrying.
        """
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

    @server.tool(
        name="create_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def create_skill(  # noqa: PLR0913
        name: Annotated[
            str,
            Field(
                description=(
                    "Nonempty human-readable skill name. Used for display and "
                    "candidate matching; not a file path."
                )
            ),
        ],
        description: Annotated[
            str,
            Field(
                description=(
                    "Nonempty description of the reusable workflow purpose; "
                    "distinguish it from neighboring skills."
                )
            ),
        ],
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
        slug: Annotated[
            str | None,
            Field(
                description=(
                    "Canonical directory slug. Omitted derives from the name where "
                    "supported; use a portable skill slug rather than a path."
                )
            ),
        ] = None,
        sync: Annotated[
            bool,
            Field(
                description=(
                    "Synchronize native runtime copies after the canonical write "
                    "when true. Defaults to false, which only writes canonical "
                    "content."
                )
            ),
        ] = False,
        triggers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Phrases or situations that should select the skill. Without "
                    "raw_markdown, omitted/empty triggers render the skill name as the file"
                    " trigger; supplied Markdown provides its frontmatter triggers."
                )
            ),
        ] = None,
        raw_markdown: Annotated[
            str | None,
            Field(
                description=(
                    "Complete SKILL.md Markdown including valid frontmatter when "
                    "supplied; validated before content is written. Omitted lets "
                    "creation build content from metadata."
                )
            ),
        ] = None,
        targets: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Native runtime registry IDs for synchronization. Omitted uses "
                    "the workflow default targets; an empty list requests no "
                    "explicit targets."
                )
            ),
        ] = None,
        visibility: Annotated[
            Literal["shared", "private"] | None,
            Field(
                description=(
                    "Project content visibility: shared for repository content, "
                    "private for operational storage. Omitted follows "
                    "layout/category policy; global content cannot be shared."
                )
            ),
        ] = None,
        category: Annotated[
            Literal["user-facing", "operational"],
            Field(
                description=(
                    "user-facing for reusable team content; operational for "
                    "internal workflows. Defaults to user-facing and participates "
                    "in visibility policy."
                )
            ),
        ] = "user-facing",
    ) -> ToolResponse:
        """Create a new canonical Agent Skill from a name, purpose, triggers, and optional
        Markdown. Use for an explicit new skill request; use import_skill for an external/native
        directory, adopt_skill for existing canonical content, or create_skill_draft for an
        editable draft. Project scope requires initialization. Writes canonical content and
        registration; sync=false avoids native copies, true also synchronizes selected targets.
        Returns skill metadata, paths, warnings, and write references. Repeated calls may
        conflict with an existing slug; use update_canonical_skill to edit it.
        """
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
                    visibility=visibility,
                    category=category,
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

    @server.tool(
        name="create_skill_draft",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def create_skill_draft(  # noqa: PLR0913
        name: Annotated[
            str,
            Field(
                description=(
                    "Nonempty human-readable skill name. Used for display and "
                    "candidate matching; not a file path."
                )
            ),
        ],
        description: Annotated[
            str,
            Field(
                description=(
                    "Nonempty description of the reusable workflow purpose; "
                    "distinguish it from neighboring skills."
                )
            ),
        ],
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
        slug: Annotated[
            str | None,
            Field(
                description=(
                    "Canonical directory slug. Omitted derives from the name where "
                    "supported; use a portable skill slug rather than a path."
                )
            ),
        ] = None,
        triggers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Trigger phrases for generated draft content. Without raw_markdown, "
                    "omitted/empty triggers render the skill name as the default trigger; "
                    "supplied raw Markdown takes precedence."
                )
            ),
        ] = None,
        raw_markdown: Annotated[
            str | None,
            Field(
                description=(
                    "Complete SKILL.md Markdown including valid frontmatter when "
                    "supplied; validated before content is written. Omitted lets "
                    "creation build content from metadata."
                )
            ),
        ] = None,
    ) -> ToolResponse:
        """Create an editable skill draft without canonical publication or native runtime writes.
        Use when content needs review; use create_skill for direct canonical creation. Project
        scope requires initialization. Writes the draft file and registration with
        snapshot/audit references. An existing unregistered file at the same draft path can be
        overwritten without confirmation; only registered slug collisions are rejected. Inspect
        the draft destination first. When generating Markdown, omitted/empty triggers default to
        the skill name. Returns draft metadata, paths, validation information, and warnings.
        Validate with validate_skill before publish_skill.
        """
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

    @server.tool(
        name="validate_skill",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def validate_skill(
        skill_or_path: Annotated[
            str,
            Field(
                description=(
                    "Registered skill selector, draft slug, or local SKILL.md "
                    "file/directory path to validate."
                )
            ),
        ],
        scope: Annotated[
            Literal["project", "global"] | None,
            Field(
                description=(
                    "Optional scope for selector lookup. Omitted lets the validator"
                    " resolve the draft/path or registered skill."
                )
            ),
        ] = None,
    ) -> ToolResponse:
        """Validate a draft, registered canonical skill, or local skill file/directory without
        publishing or changing skill content. Use before publish_skill or after editing a skill;
        get_skill_detail reads registered metadata. Accepts an ID/name or path and does not
        require project initialization at this interface. Returns a validation report with
        errors and warnings; inspect the report rather than treating a successful tool envelope
        as proof that the skill is valid.
        """
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

    @server.tool(
        name="publish_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def publish_skill(  # noqa: PLR0913
        draft_or_path: Annotated[
            str,
            Field(
                description=(
                    "Existing draft slug or local draft file/directory path to "
                    "publish; canonical destinations are validated for conflicts."
                )
            ),
        ],
        slug: Annotated[
            str | None,
            Field(
                description=(
                    "Canonical directory slug. Omitted derives from the name where "
                    "supported; use a portable skill slug rather than a path."
                )
            ),
        ] = None,
        sync: Annotated[
            bool,
            Field(
                description=(
                    "Synchronize native runtime copies after the canonical write "
                    "when true. Defaults to false, which only writes canonical "
                    "content."
                )
            ),
        ] = False,
        targets: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Native runtime registry IDs for synchronization. Omitted uses "
                    "the workflow default targets; an empty list requests no "
                    "explicit targets."
                )
            ),
        ] = None,
        visibility: Annotated[
            Literal["shared", "private"] | None,
            Field(
                description=(
                    "Project content visibility: shared for repository content, "
                    "private for operational storage. Omitted follows "
                    "layout/category policy; global content cannot be shared."
                )
            ),
        ] = None,
        category: Annotated[
            Literal["user-facing", "operational"],
            Field(
                description=(
                    "user-facing for reusable team content; operational for "
                    "internal workflows. Defaults to user-facing and participates "
                    "in visibility policy."
                )
            ),
        ] = "user-facing",
    ) -> ToolResponse:
        """Validate and publish an existing draft into canonical skill storage. Use after
        create_skill_draft and validate_skill; use update_canonical_skill to edit an already
        published skill. Requires initialized project memory. Writes canonical content and
        registration; sync=false leaves native targets untouched, true also synchronizes
        selected targets. Returns skill metadata, published paths, warnings, and write
        references. Publication can conflict with an existing slug; inspect before retrying.
        """
        try:
            require_project_initialized()
            result = use_cases.publish_skill(
                PublishSkillCommand(
                    draft_or_path=draft_or_path,
                    origin="mcp",
                    slug=slug,
                    sync=sync,
                    targets=targets,
                    visibility=visibility,
                    category=category,
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

    @server.tool(
        name="share_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def share_skill(
        skill_id_or_name: Annotated[
            str,
            Field(
                description=(
                    "Active canonical skill ID, slug, or unambiguous display name. "
                    "Use list_skills to resolve it; not a latent candidate ID."
                )
            ),
        ],
        category: Annotated[
            Literal["user-facing", "operational"],
            Field(
                description=(
                    "user-facing for reusable team content; operational for "
                    "internal workflows. Defaults to user-facing and participates "
                    "in visibility policy."
                )
            ),
        ] = "user-facing",
        confirm_operational: Annotated[
            bool,
            Field(
                description=(
                    "Explicit permission to share operational content. Defaults to "
                    "false; required for operational sharing."
                )
            ),
        ] = False,
    ) -> ToolResponse:
        """Copy an existing project skill into shared repository content for collaboration. Use for
        deliberate sharing; use sync_skills to distribute native copies without changing
        visibility. Requires initialized project memory and a resolvable project skill. Writes
        shared content and updates registration. Existing shared files at matching destination
        paths can be overwritten without a destination-conflict check or an overwrite
        confirmation; there is no preview mode. Sharing operational content additionally
        requires confirm_operational=true. Writes use the safe snapshot/audit pipeline. Returns
        the shared skill, paths, warnings, and write references. Inspect existing destination
        files and remove private information before calling. Re-sharing an already-shared skill
        can update registration and policy again.
        """
        try:
            require_project_initialized()
            result = use_cases.share_skill(
                ShareSkillCommand(
                    skill_id_or_name=skill_id_or_name,
                    category=category,
                    confirm_operational=confirm_operational,
                    origin="mcp",
                )
            )
            return _success_envelope(
                operation="skills.share",
                scope=result.agent_skill.scope.value,
                data=result.to_payload(),
                warnings=result.warnings,
            )
        except Exception as error:
            return _mcp_tool_error(error, operation="skills.share", scope="project")

    @server.tool(
        name="promote_skill_recommendation",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def promote_skill_recommendation(
        recommendation_id: Annotated[
            str,
            Field(
                description=(
                    "Latent recommendation ID returned by recommend_skills; use an "
                    "eligible candidate rather than a canonical slug."
                )
            ),
        ],
        edits: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional promotion overrides: name and description strings and"
                    " triggers as a string/list. Omitted or empty keeps recommended"
                    " metadata."
                )
            ),
        ] = None,
        targets: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Runtime selectors passed to canonical creation; this promotion does "
                    "not enable native sync. Use sync_skills afterward for native "
                    "installation."
                )
            ),
        ] = None,
    ) -> ToolResponse:
        """Promote a proposed, not previously promoted latent recommendation into a canonical Agent
        Skill. Use after reviewing recommend_skills; this call itself performs promotion. Use
        propose_skill followed by generate_skill for the separate approval/generation flow, or
        publish_skill for drafts. Project-scoped promotion requires initialized memory. Writes
        canonical content, changes the recommendation to active, and records promotion metadata.
        targets alone does not enable native synchronization; use sync_skills afterward. Returns
        promoted recommendation, skill metadata, paths, warnings, and write references. Repeated
        promotion of the same candidate is rejected.
        """
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

    @server.tool(
        name="sync_skills",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def sync_skills(
        skill_id_or_name: Annotated[
            str | None,
            Field(
                description=(
                    "Canonical skill ID, slug, or unambiguous name. Omitted or "
                    "blank synchronizes all active canonical skills."
                )
            ),
        ] = None,
        targets: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Native runtime registry IDs for synchronization. Omitted uses "
                    "the workflow default targets; an empty list requests no "
                    "explicit targets."
                )
            ),
        ] = None,
        drift_decision: Annotated[
            Literal["keep", "overwrite"],
            Field(
                description=(
                    "keep preserves changed native copies; overwrite permits "
                    "replacing managed divergent copies. Defaults to keep."
                )
            ),
        ] = "keep",
        check_gitignore: Annotated[
            bool,
            Field(
                description=(
                    "Include warnings about native target gitignore coverage when "
                    "true. Defaults to false; does not edit .gitignore."
                )
            ),
        ] = False,
    ) -> ToolResponse:
        """Synchronize one or all active canonical skills into native runtime directories. Use
        after canonical content changes; use sync_instructions for host instruction blocks and
        import_skill to bring external content into UMEM. Requires initialized project memory.
        Writes native copies; drift_decision=keep preserves divergent native content, overwrite
        permits replacement of managed divergent copies. Returns per-skill synchronization
        results and warnings, optionally including gitignore checks. Repeated sync can still
        create audit records; review drift before overwriting.
        """
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

    @server.tool(
        name="import_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def import_skill(  # noqa: PLR0913
        path: Annotated[
            str,
            Field(
                description=(
                    "Existing local skill directory or SKILL.md path. Relative "
                    "paths resolve from the project; the source must contain valid "
                    "skill content."
                )
            ),
        ],
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
        replace_native: Annotated[
            bool,
            Field(
                description=(
                    "Allow replacement of a native source with a managed canonical "
                    "copy when true. Defaults to false to preserve the source."
                )
            ),
        ] = False,
        sync_after_import: Annotated[
            bool,
            Field(
                description=(
                    "Synchronize native targets after import when true. Defaults to false."
                )
            ),
        ] = False,
        visibility: Annotated[
            Literal["shared", "private"] | None,
            Field(
                description=(
                    "Project content visibility: shared for repository content, "
                    "private for operational storage. Omitted follows "
                    "layout/category policy; global content cannot be shared."
                )
            ),
        ] = None,
        category: Annotated[
            Literal["user-facing", "operational"],
            Field(
                description=(
                    "user-facing for reusable team content; operational for "
                    "internal workflows. Defaults to user-facing and participates "
                    "in visibility policy."
                )
            ),
        ] = "user-facing",
    ) -> ToolResponse:
        """Import an existing native or local skill directory into canonical UMEM storage. Use for
        external skill content; use adopt_skill to register an existing canonical directory or
        create_skill for new content. Project scope requires initialization. Copies content and
        registers the skill; optional replacement/synchronization can alter native files.
        Defaults preserve native source content and avoid post-import sync. Returns imported
        skill metadata, paths, warnings, and write references. Repeated imports can conflict
        with an existing canonical destination.
        """
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
                    visibility=visibility,
                    category=category,
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

    @server.tool(
        name="adopt_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def adopt_skill(  # noqa: PLR0913
        path: Annotated[
            str,
            Field(
                description=(
                    "Existing local skill directory or SKILL.md path. Relative "
                    "paths resolve from the project; the source must contain valid "
                    "skill content."
                )
            ),
        ],
        scope: Annotated[
            Literal["project", "global"],
            Field(
                description=(
                    "Storage scope: project uses this workspace; global uses user "
                    "memory. Defaults to project."
                )
            ),
        ] = "project",
        slug: Annotated[
            str | None,
            Field(
                description=(
                    "Canonical directory slug. Omitted derives from the name where "
                    "supported; use a portable skill slug rather than a path."
                )
            ),
        ] = None,
        replace_native: Annotated[
            bool,
            Field(
                description=(
                    "Allow replacement of a native source with a managed canonical "
                    "copy when true. Defaults to false to preserve the source."
                )
            ),
        ] = False,
        sync_after_adopt: Annotated[
            bool,
            Field(
                description=(
                    "Synchronize native targets after adoption when true. Defaults to false."
                )
            ),
        ] = False,
        visibility: Annotated[
            Literal["shared", "private"] | None,
            Field(
                description=(
                    "Project content visibility: shared for repository content, "
                    "private for operational storage. Omitted follows "
                    "layout/category policy; global content cannot be shared."
                )
            ),
        ] = None,
        category: Annotated[
            Literal["user-facing", "operational"],
            Field(
                description=(
                    "user-facing for reusable team content; operational for "
                    "internal workflows. Defaults to user-facing and participates "
                    "in visibility policy."
                )
            ),
        ] = "user-facing",
    ) -> ToolResponse:
        """Register an existing canonical skill directory in UMEM while avoiding duplicate slugs.
        Use for unregistered canonical content; use import_skill for an external/native source
        or create_skill for new content. Project scope requires initialization. May reconcile
        canonical location and registration; optional native replacement and synchronization can
        change native copies. Defaults avoid native replacement/sync. Returns adopted skill
        metadata, paths, warnings, and write references; inspect conflicts before repeating.
        """
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
                    visibility=visibility,
                    category=category,
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

    @server.tool(
        name="update_canonical_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def update_canonical_skill(
        skill_id_or_name: Annotated[
            str,
            Field(
                description=(
                    "Active canonical skill ID, slug, or unambiguous display name. "
                    "Use list_skills to resolve it; not a latent candidate ID."
                )
            ),
        ],
        raw_markdown: Annotated[
            str,
            Field(
                description=(
                    "Complete replacement canonical SKILL.md Markdown including "
                    "valid frontmatter; required and validated before writing."
                )
            ),
        ],
        sync: Annotated[
            bool,
            Field(
                description=(
                    "Synchronize native runtime copies after the canonical write "
                    "when true. Defaults to false, which only writes canonical "
                    "content."
                )
            ),
        ] = False,
        drift_decision: Annotated[
            Literal["keep", "overwrite"],
            Field(
                description=(
                    "keep preserves changed native copies; overwrite permits "
                    "replacing managed divergent copies. Defaults to keep."
                )
            ),
        ] = "keep",
    ) -> ToolResponse:
        """Validate and replace Markdown content for an existing canonical skill. Use for canonical
        edits; use update_skill for latent metadata or rename_skill for a slug change. Requires
        initialized project memory and an active canonical selector. Writes canonical content
        through the safe pipeline; sync=true also updates native targets subject to
        drift_decision. Returns skill metadata, changed paths, warnings, and write references.
        Repeated calls can create audit/snapshot records even when content matches.
        """
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

    @server.tool(
        name="rename_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def rename_skill(
        skill_id_or_name: Annotated[
            str,
            Field(
                description=(
                    "Active canonical skill ID, slug, or unambiguous display name. "
                    "Use list_skills to resolve it; not a latent candidate ID."
                )
            ),
        ],
        slug: Annotated[
            str,
            Field(
                description=(
                    "Required new canonical directory slug; unmanaged destination "
                    "conflicts are rejected."
                )
            ),
        ],
    ) -> ToolResponse:
        """Rename an existing canonical skill slug and reconcile managed locations. Use for
        identity/path changes; use update_canonical_skill to edit content. Requires initialized
        project memory and an active canonical selector. Moves managed skill content and updates
        registration while rejecting unmanaged destination conflicts. Returns renamed skill
        metadata, paths, warnings, and write references. The old slug may no longer resolve
        after success; inspect before retrying.
        """
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

    @server.tool(
        name="cleanup_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def cleanup_skill(
        skill_id_or_name: Annotated[
            str,
            Field(
                description=(
                    "Active canonical skill ID, slug, or unambiguous display name. "
                    "Use list_skills to resolve it; not a latent candidate ID."
                )
            ),
        ],
        targets: Annotated[
            bool,
            Field(
                description=(
                    "Compatibility flag, default true. Currently ignored by cleanup"
                    " execution: false does not disable native target removal; use "
                    "dry_run=true to preview."
                )
            ),
        ] = True,
        dry_run: Annotated[
            bool,
            Field(
                description=(
                    "true (default) reports removable and blocked native targets; "
                    "false deletes removable managed native copies without deleting"
                    " canonical content."
                )
            ),
        ] = True,
    ) -> ToolResponse:
        """Preview or remove managed native copies for one active canonical skill. Use when
        cleaning that skill's installed runtime copies; use repair_skills for orphan targets
        across the project and deactivate_skill for latent candidate state. Requires initialized
        project memory and a canonical ID, slug, or unambiguous name. dry_run=true lists
        removable/blocked paths; false deletes removable native directories. Keeps canonical
        content and blocks targets without suitable managed manifests. targets is a
        compatibility flag and currently does not disable cleanup. Returns plan, removed_paths,
        and warnings. No cleanup snapshot is created; restore native copies with sync_skills if
        needed.
        """
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

    @server.tool(
        name="repair_skills",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def repair_skills(
        remove_orphan_targets: Annotated[
            bool,
            Field(
                description=(
                    "Select orphan native target cleanup when true. Defaults to "
                    "false, selecting no repair action even if dry_run=false."
                )
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            Field(
                description=(
                    "true (default) previews selected orphan target removal; false "
                    "deletes selected orphan targets. remove_orphan_targets must "
                    "also be true."
                )
            ),
        ] = True,
    ) -> ToolResponse:
        """Preview or remove orphan managed native skill targets across the project. Use for stale
        installations; use cleanup_skill to inspect one registered skill. Requires initialized
        project memory. remove_orphan_targets=false selects no action; true discovers orphan
        targets. dry_run=true previews, false deletes discovered targets. Returns plans,
        removed_paths, and warnings. Does not delete canonical skills or create a recovery
        snapshot; inspect the plan before applying.
        """
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

    @server.tool(
        name="list_skills",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def list_skills() -> ToolResponse:
        """Read the catalog of canonical skills, native installation state, and latent candidates.
        Use at startup through bootstrap or to find skill IDs; use get_skill_detail for one
        entry and recommend_skills for evidence-based candidates. Requires initialized project
        memory. Does not register, synchronize, or activate skills. Returns the catalog,
        recommendations, and metadata; unregistered directories remain unregistered.
        """
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

    @server.tool(
        name="recommend_skills",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def recommend_skills(
        scope: Annotated[
            Literal["project", "global", "all"],
            Field(
                description=(
                    "Candidate scope: project (default), global, or all. "
                    "Project/all requires project initialization."
                )
            ),
        ] = "project",
        min_recurrence: Annotated[
            int | None,
            Field(
                description=(
                    "Minimum tracked observation count, at least 1. Omitted uses 2; also "
                    "requires min(min_recurrence, 2) nonempty evidence entries. Duplicate "
                    "summary text counts separately; no distinctness check."
                )
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            Field(
                description=(
                    "Compatibility flag, default true. Both true and false remain "
                    "read-only; false does not enable promotion or writes."
                )
            ),
        ] = True,
    ) -> ToolResponse:
        """Review latent workflow recommendations from explicit track_latent_skill evidence. Use to
        choose candidates for proposal or promotion; use list_skills for the full catalog.
        Project/all scope requires initialized project memory. Read-only: does not promote,
        import, synchronize, create, or mutate skill records, even when dry_run=false. Uses
        recurrence plus nonempty curated evidence-entry thresholds (duplicate summaries count
        separately) rather than scanning facts, logs, or transcripts. Returns recommendations,
        thresholds, evidence sources, and limitations; inspect these before propose_skill or
        promote_skill_recommendation.
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

    @server.tool(
        name="get_skill_detail",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    def get_skill_detail(
        name_or_id: Annotated[
            str,
            Field(
                description=(
                    "Registered skill ID or unambiguous name/slug to inspect; "
                    "resolve candidates with list_skills."
                )
            ),
        ],
    ) -> ToolResponse:
        """Read metadata, triggers, content references, and installation state for one registered
        skill. Use after list_skills to inspect a relevant entry; use validate_skill to validate
        local content and recommend_skills to discover candidates. Requires initialized project
        memory. Does not activate, generate, or synchronize skills. Returns the matching skill
        details or an error when the selector is unresolved or ambiguous.
        """
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

    @server.tool(
        name="activate_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        ),
    )
    def activate_skill(
        latent_skill_id: Annotated[
            str,
            Field(
                description=(
                    "Exact latent candidate ID returned by track_latent_skill, "
                    "list_skills, or recommend_skills; not a canonical skill slug "
                    "or file path."
                )
            ),
        ],
    ) -> ToolResponse:
        """Reactivate an ignored latent skill candidate whose generated SKILL.md still exists and
        has valid frontmatter. Use to reverse candidate deactivation; use create_skill or
        publish_skill for canonical creation. Requires initialized project memory and a latent
        candidate ID in ignored state. Updates latent status with audit/snapshot references; it
        does not reinstall removed native files. Returns the candidate, skill_file, and mutation
        references. Use sync_skills separately for native copies where applicable; repeating
        activation fails once the candidate is active.
        """
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

    @server.tool(
        name="deactivate_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def deactivate_skill(
        latent_skill_id: Annotated[
            str,
            Field(
                description=(
                    "Exact latent candidate ID returned by track_latent_skill, "
                    "list_skills, or recommend_skills; not a canonical skill slug "
                    "or file path."
                )
            ),
        ],
    ) -> ToolResponse:
        """Mark an active latent skill candidate ignored and disable its recorded native
        installations according to runtime policy. Use to deactivate a latent workflow; use
        cleanup_skill for explicit native cleanup of a canonical skill. Requires initialized
        project memory and a latent ID in active state. Preserves canonical SKILL.md, but can
        remove native directories, replace them with disabled stubs, or preserve them according
        to host policy. Returns candidate and audit/snapshot references; removed directories do
        not necessarily have recovery snapshots. Repeating the call fails once ignored.
        activate_skill restores candidate state but does not reinstall native files.
        """
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

    @server.tool(
        name="update_skill",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )
    def update_skill(
        latent_skill_id: Annotated[
            str,
            Field(
                description=(
                    "Exact latent candidate ID returned by track_latent_skill, "
                    "list_skills, or recommend_skills; not a canonical skill slug "
                    "or file path."
                )
            ),
        ],
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Replacement latent skill display name. Omitted keeps the "
                    "existing name; a supplied name must be nonempty."
                )
            ),
        ] = None,
        description: Annotated[
            str | None,
            Field(
                description=(
                    "Replacement latent workflow purpose. Omitted keeps the "
                    "existing description; supplied text must be nonempty."
                )
            ),
        ] = None,
        triggers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Replacement trigger phrases. Omitted keeps existing triggers; "
                    "an empty list clears them."
                )
            ),
        ] = None,
        raw_markdown: Annotated[
            str | None,
            Field(
                description=(
                    "Complete replacement generated SKILL.md content, validated before "
                    "writing. Omitted regenerates the whole file from metadata and can "
                    "discard custom body content; supply edited full Markdown to retain it."
                )
            ),
        ] = None,
    ) -> ToolResponse:
        """Update metadata and rewrite generated Markdown for an existing latent skill. Use for
        latent candidate edits; use update_canonical_skill for direct canonical content
        replacement. Requires initialized project memory and a latent candidate ID. Omitted
        metadata values retain their stored fields, but omitting raw_markdown regenerates the
        entire SKILL.md from metadata and can discard a customized body even when no other edit
        is supplied. To retain custom content, read the existing file and supply complete edited
        raw_markdown with compatible frontmatter. Writes use the safe pipeline and may
        synchronize recorded native copies while preserving divergent native content. Returns
        candidate, warnings, and audit/snapshot references. Repeated calls can create additional
        audit records.
        """
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


def _doctor_success_envelope(result: DoctorResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "operation": "doctor",
        "scope": "environment",
        "data": result.to_payload(),
        "warnings": [],
    }


def _init_payload(result: SetupProjectResult, project_root: Path) -> dict[str, Any]:
    payload = {
        "project_path": _relative_path(result.project_path, project_root),
        "config_path": _relative_path(result.config_path, project_root),
        "memory_path": _relative_path(result.memory_path, project_root),
        "audit_path": _relative_path(result.audit_path, project_root),
        "snapshots_path": _relative_path(result.snapshots_path, project_root),
        "created": result.created_paths,
        "already_initialized": result.already_initialized,
        "audit_reference": "not-implemented-yet",
    }
    payload.update(
        {
            "layout": result.layout,
            "shared_root": (
                _relative_path(result.shared_root, project_root)
                if result.shared_root is not None
                else None
            ),
            "operational_root": _relative_path(result.operational_root, project_root),
            "shared_paths": result.shared_paths or [],
            "operational_paths": result.operational_paths or [],
        }
    )
    return payload


def _mcp_connection_plan_payload(
    plan: AgentConnectionPlan,
    *,
    execution: AgentConnectionExecution,
) -> dict[str, Any]:
    payload = plan.to_payload()
    payload.update(
        {
            "validation_results": execution.validation_results,
            "connection_results": execution.connection_results,
            "audit_references": execution.audit_references,
            "persisted_connections": list(execution.persisted_connections),
        }
    )
    return payload


def _remember_payload(result: RememberFactResult) -> dict[str, Any]:
    fact = result.fact
    return {
        "fact_id": fact.id,
        "scope": fact.scope.value,
        "status": fact.status.value,
        "tags": fact.tags,
        "visibility": fact.metadata.get("visibility"),
        "storage_path": fact.metadata.get("storage_path"),
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
        "visibility": fact.metadata.get("visibility", "legacy"),
        "storage_path": fact.metadata.get("storage_path"),
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
