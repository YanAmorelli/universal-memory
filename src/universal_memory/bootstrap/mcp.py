from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from universal_memory.application.diagnostics import DoctorUseCase
from universal_memory.application.host import (
    ConfigureHostUseCase,
    SyncInstructionsUseCase,
)
from universal_memory.application.memory import (
    AssembleContextSummaryUseCase,
    GetMemoryStatusUseCase,
    ListFactsUseCase,
    PurgeFactUseCase,
    RememberFactUseCase,
)
from universal_memory.application.onboarding.setup_project import setup_project
from universal_memory.application.security import (
    ListAuditLogUseCase,
    ListSnapshotsUseCase,
    RollbackUseCase,
    SafeWriteUseCase,
)
from universal_memory.application.skills import (
    ActivateSkillUseCase,
    CreateSkillUseCase,
    DeactivateSkillUseCase,
    GenerateSkillUseCase,
    GetSkillDetailUseCase,
    ImportSkillUseCase,
    ListSkillsUseCase,
    PromoteSkillRecommendationUseCase,
    ProposeSkillUseCase,
    RecommendSkillsUseCase,
    SyncSkillsUseCase,
    TrackLatentSkillUseCase,
    UpdateSkillUseCase,
)
from universal_memory.infrastructure.config import LocalConfigValidationPort, LocalProjectLayoutPort
from universal_memory.infrastructure.security import (
    EntropySecretScanner,
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)
from universal_memory.infrastructure.storage import (
    LocalAgentSkillRepository,
    LocalContextSummaryRepository,
    LocalFactRepository,
    LocalLatentSkillRepository,
    LocalRuleRepository,
)
from universal_memory.interfaces.mcp import MCPUseCases, configure_server, create_mcp_server


def build_server(project_root: Path | None = None) -> FastMCP:
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

    def initialize_project(project_root: Path):
        return setup_project(
            project_root,
            layout_port=layout_port,
            config_validation_port=LocalConfigValidationPort(),
        )

    return configure_server(
        create_mcp_server(),
        MCPUseCases(
            initialize_project=initialize_project,
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
            sync_skills=sync_skills_use_case.execute,
            promote_skill_recommendation=promote_skill_recommendation_use_case.execute,
            import_skill=import_skill_use_case.execute,
            recommend_skills=recommend_skills_use_case.execute,
            list_skills=list_skills_use_case.execute,
            get_skill_detail=get_skill_detail_use_case.execute,
            activate_skill=_activate_skill_use_case.execute,
            deactivate_skill=_deactivate_skill_use_case.execute,
            update_skill=_update_skill_use_case.execute,
        ),
        project_root=root,
    )


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
