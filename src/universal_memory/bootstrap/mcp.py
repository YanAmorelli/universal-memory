from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{6,}\b"),
    re.compile(r"\b[A-Za-z0-9_]*api[_-]?key[A-Za-z0-9_]*\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9_]*token[A-Za-z0-9_]*\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
)
_UNIX_ABSOLUTE_PATH = re.compile(r"(?<![\w.-])/(?:[^/\s:]+/)+[^/\s:]+")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"(?<![\w.-])(?:[a-zA-Z]:\\|\\\\)(?:[^\\\s:]+\\)+[^\\\s:]+")
_DEFAULT_RECOVERY_HINT = "Try again. If the problem persists, check the diagnostic logs."


def build_server(project_root: Path | None = None) -> FastMCP:  # noqa: PLR0915
    from universal_memory.application.diagnostics import DoctorUseCase  # noqa: PLC0415
    from universal_memory.application.host import (  # noqa: PLC0415
        ConfigureHostUseCase,
        SyncInstructionsUseCase,
    )
    from universal_memory.application.layout import MigrateProjectLayoutUseCase  # noqa: PLC0415
    from universal_memory.application.memory import (  # noqa: PLC0415
        AssembleContextSummaryUseCase,
        GetMemoryStatusUseCase,
        ListFactsUseCase,
        PurgeFactUseCase,
        RememberFactUseCase,
    )
    from universal_memory.application.onboarding import (  # noqa: PLC0415
        ExecuteAgentConnectionsUseCase,
        SessionBootstrapUseCase,
    )
    from universal_memory.application.onboarding.setup_project import setup_project  # noqa: PLC0415
    from universal_memory.application.security import (  # noqa: PLC0415
        ListAuditLogUseCase,
        SafeWriteUseCase,
    )
    from universal_memory.application.skills import (  # noqa: PLC0415
        ActivateSkillUseCase,
        AdoptSkillUseCase,
        CleanupSkillUseCase,
        CreateSkillDraftUseCase,
        CreateSkillUseCase,
        DeactivateSkillUseCase,
        GenerateSkillUseCase,
        GetSkillDetailUseCase,
        ImportSkillUseCase,
        ListSkillsUseCase,
        PromoteSkillRecommendationUseCase,
        ProposeSkillUseCase,
        PublishSkillUseCase,
        RecommendSkillsUseCase,
        RenameSkillUseCase,
        RepairSkillsUseCase,
        ShareSkillUseCase,
        SyncSkillsUseCase,
        TrackLatentSkillUseCase,
        UpdateCanonicalSkillUseCase,
        UpdateSkillUseCase,
        ValidateSkillUseCase,
    )
    from universal_memory.application.skills.native_skill_sync import (  # noqa: PLC0415
        NativeSkillSync,
    )
    from universal_memory.infrastructure.config import (  # noqa: PLC0415
        LocalConfigValidationPort,
        LocalProjectLayoutPort,
    )
    from universal_memory.infrastructure.security import (  # noqa: PLC0415
        EntropySecretScanner,
        LocalAuditLogRepository,
        LocalSnapshotRepository,
    )
    from universal_memory.infrastructure.storage import (  # noqa: PLC0415
        LocalAgentSkillRepository,
        LocalContextSummaryRepository,
        LocalFactRepository,
        LocalLatentSkillRepository,
        LocalRuleRepository,
    )
    from universal_memory.interfaces.mcp import (  # noqa: PLC0415
        MCPUseCases,
        configure_server,
        create_mcp_server,
    )

    try:
        root = project_root or Path.cwd()
    except Exception:
        root = Path(".")
    from universal_memory.bootstrap.project_memory import (  # noqa: PLC0415
        guard_project_operation,
        scoped_context_handler,
    )
    from universal_memory.bootstrap.project_snapshots import (  # noqa: PLC0415
        ProjectSnapshotCommands,
    )
    from universal_memory.infrastructure.config.project_roots import (  # noqa: PLC0415
        resolve_project_roots,
    )

    roots = resolve_project_roots(root)
    root = roots.memory_root
    for warning in roots.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    data_root = root / ".umem"
    layout_port = LocalProjectLayoutPort()
    audit_log_repository = LocalAuditLogRepository(project_root=root, data_root=data_root)
    snapshot_repository = LocalSnapshotRepository(project_root=root, data_root=data_root)
    secret_scanner = EntropySecretScanner()
    safe_write_use_case = SafeWriteUseCase(
        project_root=root,
        secret_scanner=secret_scanner,
        snapshot_repository=snapshot_repository,
        audit_log_repository=audit_log_repository,
    )
    fact_repository = LocalFactRepository(
        project_root=root,
        data_root=data_root,
        safe_write_use_case=safe_write_use_case,
    )
    rule_repository = LocalRuleRepository(
        project_root=root,
        data_root=data_root,
        safe_write_use_case=safe_write_use_case,
    )
    latent_skill_repository = LocalLatentSkillRepository(
        project_root=root,
        data_root=data_root,
        safe_write_use_case=safe_write_use_case,
    )
    agent_skill_repository = LocalAgentSkillRepository(
        project_root=root,
        data_root=data_root,
        safe_write_use_case=safe_write_use_case,
    )
    status_use_case = GetMemoryStatusUseCase(
        fact_repository=fact_repository,
        rule_repository=rule_repository,
        latent_skill_repository=latent_skill_repository,
        agent_skill_repository=agent_skill_repository,
        layout_port=layout_port,
        audit_log_repository=audit_log_repository,
        data_root=data_root,
    )
    context_use_case = AssembleContextSummaryUseCase(
        fact_repository=fact_repository,
        rule_repository=rule_repository,
        secret_scanner=secret_scanner,
        audit_log_repository=audit_log_repository,
        context_summary_repository=LocalContextSummaryRepository(
            project_root=root,
            data_root=data_root,
        ),
    )
    context_handler = scoped_context_handler(context_use_case, fact_repository.global_data_root)
    remember_use_case = RememberFactUseCase(
        fact_repository=fact_repository,
        safe_write_use_case=safe_write_use_case,
    )
    facts_list_use_case = ListFactsUseCase(fact_repository=fact_repository)
    facts_purge_use_case = PurgeFactUseCase(fact_repository=fact_repository)
    audit_list_use_case = ListAuditLogUseCase(audit_log_repository=audit_log_repository)
    host_safe_write = SafeWriteUseCase(
        project_root=roots.project_root,
        secret_scanner=secret_scanner,
        snapshot_repository=LocalSnapshotRepository(
            project_root=roots.project_root,
            data_root=roots.project_root / ".umem",
        ),
        audit_log_repository=audit_log_repository,
    )
    snapshot_commands = ProjectSnapshotCommands(safe_write_use_case, host_safe_write)
    host_use_case = ConfigureHostUseCase(
        project_root=roots.project_root,
        safe_write_use_case=host_safe_write,
        fact_repository=fact_repository,
    )
    connection_executor = ExecuteAgentConnectionsUseCase(
        host_setup_command=host_use_case.execute,
        host_check_command=host_use_case.execute,
        context_read_command=context_handler,
    )
    doctor_use_case = DoctorUseCase(host_check_command=host_use_case.execute)
    host_sync_use_case = SyncInstructionsUseCase(
        project_root=roots.project_root,
        safe_write_use_case=host_safe_write,
        rule_repository=rule_repository,
        fact_repository=fact_repository,
    )
    native_skill_sync = NativeSkillSync(
        project_root=roots.project_root,
        canonical_root=root,
        safe_write_use_case=host_safe_write,
    )
    propose_skill_use_case = ProposeSkillUseCase(
        project_root=root,
        repository=latent_skill_repository,
        safe_write_use_case=safe_write_use_case,
    )
    track_latent_skill_use_case = TrackLatentSkillUseCase(
        repository=latent_skill_repository,
    )
    generate_skill_use_case = GenerateSkillUseCase(
        native_skill_sync=native_skill_sync,
        project_root=root,
        repository=latent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            latent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    create_skill_use_case = CreateSkillUseCase(
        native_skill_sync=native_skill_sync,
        project_root=root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    sync_skills_use_case = SyncSkillsUseCase(
        native_skill_sync=native_skill_sync,
        project_root=root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    promote_skill_recommendation_use_case = PromoteSkillRecommendationUseCase(
        recommendation_repository=latent_skill_repository,
        create_skill_use_case=create_skill_use_case,
    )
    import_skill_use_case = ImportSkillUseCase(
        native_skill_sync=native_skill_sync,
        project_root=root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    create_skill_draft_use_case = CreateSkillDraftUseCase(
        project_root=root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
    )
    publish_skill_use_case = PublishSkillUseCase(
        native_skill_sync=native_skill_sync,
        project_root=root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    share_skill_use_case = ShareSkillUseCase(
        project_root=root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
    )
    validate_skill_use_case = ValidateSkillUseCase(
        project_root=root,
        repository=agent_skill_repository,
    )
    adopt_skill_use_case = AdoptSkillUseCase(
        project_root=root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    update_canonical_skill_use_case = UpdateCanonicalSkillUseCase(
        native_skill_sync=native_skill_sync,
        project_root=root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    rename_skill_use_case = RenameSkillUseCase(project_root=root, repository=agent_skill_repository)
    cleanup_skill_use_case = CleanupSkillUseCase(
        project_root=root, repository=agent_skill_repository
    )
    repair_skills_use_case = RepairSkillsUseCase(
        project_root=root, repository=agent_skill_repository
    )
    _activate_skill_use_case = ActivateSkillUseCase(
        project_root=root,
        repository=latent_skill_repository,
    )
    _deactivate_skill_use_case = DeactivateSkillUseCase(
        native_skill_sync=native_skill_sync,
        repository=latent_skill_repository,
        project_root=root,
        safe_write_use_case=safe_write_use_case,
    )
    _update_skill_use_case = UpdateSkillUseCase(
        native_skill_sync=native_skill_sync,
        project_root=root,
        repository=latent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            latent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    list_skills_use_case = ListSkillsUseCase(
        project_root=root,
        repository=latent_skill_repository,
        agent_skill_repository=agent_skill_repository,
    )
    session_bootstrap_use_case = SessionBootstrapUseCase(
        status=status_use_case.execute,
        context=context_handler,
        list_skills=list_skills_use_case.execute,
    )
    recommend_skills_use_case = RecommendSkillsUseCase(repository=latent_skill_repository)
    get_skill_detail_use_case = GetSkillDetailUseCase(
        project_root=root,
        repository=latent_skill_repository,
        agent_skill_repository=agent_skill_repository,
    )
    layout_migrate_use_case = MigrateProjectLayoutUseCase(
        project_root=root,
        safe_write_use_case=safe_write_use_case,
    )

    def initialize_project(project_root: Path, *, layout: str = "legacy"):
        return setup_project(
            project_root,
            layout_port=layout_port,
            config_validation_port=LocalConfigValidationPort(),
            layout=layout,
        )

    def guarded(handler):
        return guard_project_operation(handler, root)

    return configure_server(
        create_mcp_server(),
        MCPUseCases(
            initialize_project=initialize_project,
            execute_agent_connections=connection_executor,
            status=status_use_case.execute,
            bootstrap=guarded(session_bootstrap_use_case.execute),
            doctor=doctor_use_case.execute,
            context=guarded(context_handler),
            remember=guarded(remember_use_case.execute),
            list_facts=facts_list_use_case.execute,
            purge_fact=guarded(facts_purge_use_case.execute),
            list_audit_events=audit_list_use_case.execute,
            list_snapshots=snapshot_commands.list,
            rollback_scope=guarded(snapshot_commands.rollback),
            host_setup=guarded(host_use_case.execute),
            host_check=guarded(host_use_case.execute),
            sync_instructions=guarded(host_sync_use_case.execute),
            propose_skill=guarded(propose_skill_use_case.execute),
            track_latent_skill=guarded(track_latent_skill_use_case.execute),
            generate_skill=guarded(generate_skill_use_case.execute),
            create_skill=guarded(create_skill_use_case.execute),
            create_skill_draft=guarded(create_skill_draft_use_case.execute),
            publish_skill=guarded(publish_skill_use_case.execute),
            share_skill=guarded(share_skill_use_case.execute),
            validate_skill=validate_skill_use_case.execute,
            adopt_skill=guarded(adopt_skill_use_case.execute),
            update_canonical_skill=guarded(update_canonical_skill_use_case.execute),
            rename_skill=guarded(rename_skill_use_case.execute),
            cleanup_skill=guarded(cleanup_skill_use_case.execute),
            repair_skills=guarded(repair_skills_use_case.execute),
            sync_skills=guarded(sync_skills_use_case.execute),
            promote_skill_recommendation=guarded(promote_skill_recommendation_use_case.execute),
            import_skill=guarded(import_skill_use_case.execute),
            recommend_skills=recommend_skills_use_case.execute,
            list_skills=list_skills_use_case.execute,
            get_skill_detail=get_skill_detail_use_case.execute,
            activate_skill=guarded(_activate_skill_use_case.execute),
            deactivate_skill=guarded(_deactivate_skill_use_case.execute),
            update_skill=guarded(_update_skill_use_case.execute),
            migrate_project_layout=guarded(layout_migrate_use_case.execute),
        ),
        project_root=roots.project_root,
        memory_root=root,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if any(arg in {"-h", "--help"} for arg in args):
        print("Usage: umem-mcp [--help]")
        print()
        print("Run the Universal Memory MCP server over stdio.")
        print("Troubleshoot environment issues with: umem doctor")
        return

    try:
        build_server().run()
    except Exception as error:
        _write_startup_failure(error)
        raise SystemExit(1) from None


def _write_startup_failure(error: Exception) -> None:
    lines = (
        f"Universal Memory MCP startup failed: {_safe_error_detail(error)}",
        f"Recovery hint: {_safe_recovery_hint(error)}",
    )
    try:
        print(*lines, sep="\n", file=sys.stderr)
    except OSError:
        return


def _safe_error_detail(error: Exception) -> str:
    if isinstance(error, ImportError):
        return _fallback_sanitize_error_detail(error)
    try:
        from universal_memory.interfaces.errors import sanitize_error_detail  # noqa: PLC0415

        return sanitize_error_detail(error)
    except Exception:
        return _fallback_sanitize_error_detail(error)


def _safe_recovery_hint(error: Exception) -> str:
    try:
        from universal_memory.interfaces.errors import recovery_hint  # noqa: PLC0415

        return recovery_hint(error)
    except Exception:
        return _DEFAULT_RECOVERY_HINT


def _fallback_sanitize_error_detail(error: Exception) -> str:
    try:
        detail = str(error)
    except Exception:
        return "Unexpected error."
    detail = _UNIX_ABSOLUTE_PATH.sub("<path>", detail)
    detail = _WINDOWS_ABSOLUTE_PATH.sub("<path>", detail)
    for pattern in _SECRET_PATTERNS:
        detail = pattern.sub("<secret>", detail)
    return detail[:240] or "Unexpected error."


if __name__ == "__main__":
    main()
