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
    )
    from universal_memory.application.onboarding.setup_project import setup_project  # noqa: PLC0415
    from universal_memory.application.security import (  # noqa: PLC0415
        ListAuditLogUseCase,
        ListSnapshotsUseCase,
        RollbackUseCase,
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
    remember_use_case = RememberFactUseCase(
        fact_repository=fact_repository,
        safe_write_use_case=safe_write_use_case,
    )
    facts_list_use_case = ListFactsUseCase(fact_repository=fact_repository)
    facts_purge_use_case = PurgeFactUseCase(fact_repository=fact_repository)
    audit_list_use_case = ListAuditLogUseCase(audit_log_repository=audit_log_repository)
    manifest_file = data_root / "snapshots" / "manifest.json"
    try:
        manifest_rel_path = str(manifest_file.relative_to(root))
    except ValueError:
        manifest_rel_path = manifest_file.as_posix()
    snapshots_list_use_case = ListSnapshotsUseCase(
        snapshot_repository=snapshot_repository,
        manifest_path=manifest_rel_path,
    )
    rollback_use_case = RollbackUseCase(
        project_root=root,
        snapshot_repository=snapshot_repository,
        audit_log_repository=audit_log_repository,
    )
    host_use_case = ConfigureHostUseCase(
        project_root=root,
        safe_write_use_case=safe_write_use_case,
        fact_repository=fact_repository,
    )
    connection_executor = ExecuteAgentConnectionsUseCase(
        host_setup_command=host_use_case.execute,
        host_check_command=host_use_case.execute,
        context_read_command=context_use_case.execute,
    )
    doctor_use_case = DoctorUseCase(host_check_command=host_use_case.execute)
    host_sync_use_case = SyncInstructionsUseCase(
        project_root=root,
        safe_write_use_case=safe_write_use_case,
        rule_repository=rule_repository,
        fact_repository=fact_repository,
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
        project_root=root,
        repository=latent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            latent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    create_skill_use_case = CreateSkillUseCase(
        project_root=root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    sync_skills_use_case = SyncSkillsUseCase(
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
        repository=latent_skill_repository,
        project_root=root,
        safe_write_use_case=safe_write_use_case,
    )
    _update_skill_use_case = UpdateSkillUseCase(
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

    return configure_server(
        create_mcp_server(),
        MCPUseCases(
            initialize_project=initialize_project,
            execute_agent_connections=connection_executor,
            status=status_use_case.execute,
            doctor=doctor_use_case.execute,
            context=context_use_case.execute,
            remember=remember_use_case.execute,
            list_facts=facts_list_use_case.execute,
            purge_fact=facts_purge_use_case.execute,
            list_audit_events=audit_list_use_case.execute,
            list_snapshots=snapshots_list_use_case.execute,
            rollback_scope=rollback_use_case.execute,
            host_setup=host_use_case.execute,
            host_check=host_use_case.execute,
            sync_instructions=host_sync_use_case.execute,
            propose_skill=propose_skill_use_case.execute,
            track_latent_skill=track_latent_skill_use_case.execute,
            generate_skill=generate_skill_use_case.execute,
            create_skill=create_skill_use_case.execute,
            create_skill_draft=create_skill_draft_use_case.execute,
            publish_skill=publish_skill_use_case.execute,
            share_skill=share_skill_use_case.execute,
            validate_skill=validate_skill_use_case.execute,
            adopt_skill=adopt_skill_use_case.execute,
            update_canonical_skill=update_canonical_skill_use_case.execute,
            rename_skill=rename_skill_use_case.execute,
            cleanup_skill=cleanup_skill_use_case.execute,
            repair_skills=repair_skills_use_case.execute,
            sync_skills=sync_skills_use_case.execute,
            promote_skill_recommendation=promote_skill_recommendation_use_case.execute,
            import_skill=import_skill_use_case.execute,
            recommend_skills=recommend_skills_use_case.execute,
            list_skills=list_skills_use_case.execute,
            get_skill_detail=get_skill_detail_use_case.execute,
            activate_skill=_activate_skill_use_case.execute,
            deactivate_skill=_deactivate_skill_use_case.execute,
            update_skill=_update_skill_use_case.execute,
            migrate_project_layout=layout_migrate_use_case.execute,
        ),
        project_root=root,
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
