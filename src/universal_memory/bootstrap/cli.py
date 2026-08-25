from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from universal_memory.application.diagnostics import DoctorUseCase
from universal_memory.application.host import (
    ConfigureHostUseCase,
    SyncInstructionsUseCase,
)
from universal_memory.application.layout import MigrateProjectLayoutUseCase
from universal_memory.application.memory import (
    AssembleContextSummaryUseCase,
    ContextHygieneUseCase,
    GetMemoryStatusUseCase,
    ListFactsUseCase,
    PurgeFactUseCase,
    RememberFactUseCase,
)
from universal_memory.application.onboarding import (
    ExecuteAgentConnectionsUseCase,
    OfficialSkillInstallerPlannerAdapter,
    RegistrySignalAgentDetector,
    SessionBootstrapUseCase,
    default_agent_connection_planner,
)
from universal_memory.application.security import (
    ListAuditLogUseCase,
    ListSnapshotsUseCase,
    RollbackUseCase,
    SafeWriteUseCase,
)
from universal_memory.application.skills import (
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
from universal_memory.application.update import (
    UpdateBenchmarksUseCase,
    UpdateCheckUseCase,
    UpdateManagedSkillsUseCase,
    UpdateMigrateUseCase,
)
from universal_memory.domain import SnapshotFailedError
from universal_memory.domain.entities import (
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    Rule,
    RuleScope,
    RuleStatus,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.domain.entities.runtime import default_runtime_registry
from universal_memory.domain.ports import LatentSkillRepository, RuleRepository
from universal_memory.infrastructure.config import (
    LocalConfigValidationPort,
    LocalConnectionStatePort,
    LocalProjectLayoutPort,
)
from universal_memory.infrastructure.config.toml_loader import load_config
from universal_memory.infrastructure.onboarding import (
    DEFAULT_OFFICIAL_SKILL_MAPPINGS,
    LocalExternalActionAuditPort,
    LocalOfficialSkillConnectionStatePort,
    LocalOfficialSkillEnvironmentProbe,
    OfficialSkillExternalActionExecutor,
    OfficialSkillMappedAgentDetector,
    StaticOfficialSkillMappingPort,
)
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
from universal_memory.interfaces.cli import build_main
from universal_memory.interfaces.cli.message_catalog import DEFAULT_LOCALE, normalize_locale


class EmptyRuleRepository(RuleRepository):
    def read(self, id: str) -> Rule:
        raise KeyError(id)

    def list(self, scope: RuleScope | None = None, status: RuleStatus | None = None) -> list[Rule]:
        return []

    def write(self, entity: Rule) -> None:
        return None

    def delete(self, id: str) -> None:
        return None

    def migrate(self, target_version: int) -> None:
        return None


class EmptyLatentSkillRepository(LatentSkillRepository):
    def read(self, id: str) -> LatentSkill:
        raise KeyError(id)

    def list(
        self, scope: LatentSkillScope | None = None, status: LatentSkillStatus | None = None
    ) -> list[LatentSkill]:
        return []

    def write(self, entity: LatentSkill, *, origin: str = "repository") -> None:
        return None

    def delete(self, id: str) -> None:
        return None

    def migrate(self, target_version: int) -> None:
        return None


def main(argv: Sequence[str] | None = None) -> int:  # noqa: PLR0915
    project_root = Path.cwd()
    data_root = project_root / ".umem"
    layout_port = LocalProjectLayoutPort()
    audit_log_repository = LocalAuditLogRepository(
        project_root=project_root,
        data_root=data_root,
    )
    snapshot_repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
    safe_write_use_case = SafeWriteUseCase(
        project_root=project_root,
        secret_scanner=EntropySecretScanner(),
        snapshot_repository=snapshot_repository,
        audit_log_repository=audit_log_repository,
    )
    fact_repository = LocalFactRepository(
        project_root=project_root,
        data_root=data_root,
        safe_write_use_case=safe_write_use_case,
    )
    audit_list_use_case = ListAuditLogUseCase(audit_log_repository=audit_log_repository)
    manifest_file = data_root / "snapshots" / "manifest.json"
    manifest_rel_path = str(manifest_file.relative_to(project_root))
    snapshots_list_use_case = ListSnapshotsUseCase(
        snapshot_repository=snapshot_repository,
        manifest_path=manifest_rel_path,
    )
    rollback_use_case = RollbackUseCase(
        project_root=project_root,
        snapshot_repository=snapshot_repository,
        audit_log_repository=audit_log_repository,
    )
    rule_repository = LocalRuleRepository(
        project_root=project_root,
        data_root=data_root,
        safe_write_use_case=safe_write_use_case,
    )
    latent_skill_repository = LocalLatentSkillRepository(
        project_root=project_root,
        data_root=data_root,
        safe_write_use_case=safe_write_use_case,
    )
    agent_skill_repository = LocalAgentSkillRepository(
        project_root=project_root,
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
    facts_list_use_case = ListFactsUseCase(fact_repository=fact_repository)
    facts_purge_use_case = PurgeFactUseCase(fact_repository=fact_repository)
    facts_hygiene_use_case = ContextHygieneUseCase(fact_repository=fact_repository)
    context_use_case = AssembleContextSummaryUseCase(
        fact_repository=fact_repository,
        rule_repository=rule_repository,
        secret_scanner=EntropySecretScanner(),
        audit_log_repository=audit_log_repository,
        context_summary_repository=LocalContextSummaryRepository(
            project_root=project_root,
            data_root=data_root,
        ),
    )
    remember_use_case = RememberFactUseCase(
        fact_repository=fact_repository,
        safe_write_use_case=safe_write_use_case,
    )
    host_use_case = ConfigureHostUseCase(
        project_root=project_root,
        safe_write_use_case=safe_write_use_case,
        fact_repository=fact_repository,
    )
    runtime_registry = default_runtime_registry()
    official_connection_state = LocalOfficialSkillConnectionStatePort(
        project_root=project_root,
        safe_write_use_case=safe_write_use_case,
    )
    official_mapping_port = StaticOfficialSkillMappingPort(
        DEFAULT_OFFICIAL_SKILL_MAPPINGS,
        project_root=project_root,
        state_port=official_connection_state,
    )
    official_environment_probe = LocalOfficialSkillEnvironmentProbe(
        mapping_port=official_mapping_port
    )
    official_installer_planner = OfficialSkillInstallerPlannerAdapter(
        environment_port=official_environment_probe,
        agent_mapping_port=official_mapping_port,
    )
    connection_planner = default_agent_connection_planner(
        runtime_registry,
        detector=OfficialSkillMappedAgentDetector(
            delegate=RegistrySignalAgentDetector(),
            mapping_port=official_mapping_port,
        ),
        external_skill_installer=official_installer_planner,
    )
    connection_executor = ExecuteAgentConnectionsUseCase(
        host_setup_command=host_use_case.execute,
        host_check_command=host_use_case.execute,
        context_read_command=context_use_case.execute,
        connection_state_port=LocalConnectionStatePort(
            project_root=project_root,
            safe_write_use_case=safe_write_use_case,
        ),
        external_action_executor=OfficialSkillExternalActionExecutor(
            project_root=project_root,
            mapping_port=official_mapping_port,
            state_port=official_connection_state,
            audit_port=LocalExternalActionAuditPort(repository=audit_log_repository),
        ),
        known_runtime_ids=frozenset(
            runtime_id.value for runtime_id in runtime_registry.runtime_ids
        ),
    )
    doctor_use_case = DoctorUseCase(host_check_command=host_use_case.execute)
    host_sync_use_case = SyncInstructionsUseCase(
        project_root=project_root,
        safe_write_use_case=safe_write_use_case,
        rule_repository=rule_repository,
        fact_repository=fact_repository,
    )
    propose_skill_use_case = ProposeSkillUseCase(
        project_root=project_root,
        repository=latent_skill_repository,
        safe_write_use_case=safe_write_use_case,
    )
    track_latent_skill_use_case = TrackLatentSkillUseCase(
        repository=latent_skill_repository,
    )
    generate_skill_use_case = GenerateSkillUseCase(
        project_root=project_root,
        repository=latent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            latent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    create_skill_use_case = CreateSkillUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    sync_skills_use_case = SyncSkillsUseCase(
        project_root=project_root,
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
        project_root=project_root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    create_skill_draft_use_case = CreateSkillDraftUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
    )
    publish_skill_use_case = PublishSkillUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    share_skill_use_case = ShareSkillUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
    )
    validate_skill_use_case = ValidateSkillUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
    )
    adopt_skill_use_case = AdoptSkillUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    update_canonical_skill_use_case = UpdateCanonicalSkillUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            agent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    rename_skill_use_case = RenameSkillUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
    )
    cleanup_skill_use_case = CleanupSkillUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
    )
    repair_skills_use_case = RepairSkillsUseCase(
        project_root=project_root,
        repository=agent_skill_repository,
    )
    _activate_skill_use_case = ActivateSkillUseCase(
        project_root=project_root,
        repository=latent_skill_repository,
    )
    _deactivate_skill_use_case = DeactivateSkillUseCase(
        repository=latent_skill_repository,
        project_root=project_root,
        safe_write_use_case=safe_write_use_case,
    )
    _update_skill_use_case = UpdateSkillUseCase(
        project_root=project_root,
        repository=latent_skill_repository,
        safe_write_use_case=safe_write_use_case,
        global_safe_write_use_case=getattr(
            latent_skill_repository, "global_safe_write_use_case", None
        ),
    )
    list_skills_use_case = ListSkillsUseCase(
        project_root=project_root,
        repository=latent_skill_repository,
        agent_skill_repository=agent_skill_repository,
    )
    session_bootstrap_use_case = SessionBootstrapUseCase(
        status=status_use_case.execute,
        context=context_use_case.execute,
        list_skills=list_skills_use_case.execute,
    )
    recommend_skills_use_case = RecommendSkillsUseCase(repository=latent_skill_repository)
    get_skill_detail_use_case = GetSkillDetailUseCase(
        project_root=project_root,
        repository=latent_skill_repository,
        agent_skill_repository=agent_skill_repository,
    )
    update_check_use_case = UpdateCheckUseCase()
    update_managed_skills_use_case = UpdateManagedSkillsUseCase(
        safe_write_use_case=safe_write_use_case
    )
    update_migrate_use_case = UpdateMigrateUseCase(safe_write_use_case=safe_write_use_case)
    update_benchmarks_use_case = UpdateBenchmarksUseCase(
        safe_write_use_case=safe_write_use_case,
    )
    layout_migrate_use_case = MigrateProjectLayoutUseCase(
        project_root=project_root,
        safe_write_use_case=safe_write_use_case,
    )

    def locale_resolver() -> str:
        try:
            loaded = load_config(project_root)
        except Exception:
            return DEFAULT_LOCALE
        preferences = loaded.merged.get("preferences")
        if not isinstance(preferences, dict):
            return DEFAULT_LOCALE
        return normalize_locale(preferences.get("locale"))

    def rollback_preview(scope: SnapshotScope) -> Snapshot:
        snapshots = snapshot_repository.list(scope=scope, status=SnapshotStatus.created)
        if not snapshots:
            raise SnapshotFailedError(
                "No snapshot found for the requested scope. "
                "Hint: run a safe mutation before trying rollback."
            )

        def _normalize_datetime(dt: datetime) -> datetime:
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                return dt.replace(tzinfo=UTC)
            return dt

        return max(snapshots, key=lambda snapshot: _normalize_datetime(snapshot.timestamp))

    configured_main = build_main(
        layout_port=layout_port,
        config_validation_port=LocalConfigValidationPort(),
        audit_list_command=audit_list_use_case.execute,
        snapshots_list_command=snapshots_list_use_case.execute,
        rollback_command=rollback_use_case.execute,
        rollback_preview_command=rollback_preview,
        status_command=status_use_case.execute,
        bootstrap_command=session_bootstrap_use_case.execute,
        doctor_command=doctor_use_case.execute,
        context_command=context_use_case.execute,
        remember_command=remember_use_case.execute,
        facts_list_command=facts_list_use_case.execute,
        facts_purge_command=facts_purge_use_case.execute,
        facts_hygiene_command=facts_hygiene_use_case.execute,
        host_setup_command=host_use_case.execute,
        host_check_command=host_use_case.execute,
        host_sync_command=host_sync_use_case.execute,
        agent_connection_plan_command=connection_planner.plan,
        agent_connection_executor=connection_executor,
        propose_skill_command=propose_skill_use_case.execute,
        track_latent_skill_command=track_latent_skill_use_case.execute,
        generate_skill_command=generate_skill_use_case.execute,
        create_skill_command=create_skill_use_case.execute,
        create_skill_draft_command=create_skill_draft_use_case.execute,
        publish_skill_command=publish_skill_use_case.execute,
        share_skill_command=share_skill_use_case.execute,
        validate_skill_command=validate_skill_use_case.execute,
        adopt_skill_command=adopt_skill_use_case.execute,
        update_canonical_skill_command=update_canonical_skill_use_case.execute,
        rename_skill_command=rename_skill_use_case.execute,
        cleanup_skill_command=cleanup_skill_use_case.execute,
        repair_skills_command=repair_skills_use_case.execute,
        sync_skills_command=sync_skills_use_case.execute,
        promote_skill_recommendation_command=promote_skill_recommendation_use_case.execute,
        import_skill_command=import_skill_use_case.execute,
        recommend_skills_command=recommend_skills_use_case.execute,
        list_skills_command=list_skills_use_case.execute,
        get_skill_detail_command=get_skill_detail_use_case.execute,
        activate_skill_command=_activate_skill_use_case.execute,
        deactivate_skill_command=_deactivate_skill_use_case.execute,
        update_skill_command=_update_skill_use_case.execute,
        update_check_command=update_check_use_case.execute,
        update_managed_skills_command=update_managed_skills_use_case.execute,
        update_migrate_command=update_migrate_use_case.execute,
        update_benchmarks_command=update_benchmarks_use_case.execute,
        layout_migrate_command=layout_migrate_use_case.execute,
        locale_resolver=locale_resolver,
    )
    return configured_main(argv)
