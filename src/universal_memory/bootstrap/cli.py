from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from universal_memory.application.host import ConfigureHostUseCase, SyncInstructionsUseCase
from universal_memory.application.memory import (
    AssembleContextSummaryUseCase,
    ContextHygieneUseCase,
    GetMemoryStatusUseCase,
    ListFactsUseCase,
    PurgeFactUseCase,
    RememberFactUseCase,
)
from universal_memory.application.security import (
    ListAuditLogUseCase,
    ListSnapshotsUseCase,
    RollbackUseCase,
    SafeWriteUseCase,
)
from universal_memory.application.skills import (
    GenerateSkillUseCase,
    GetSkillDetailUseCase,
    ListSkillsUseCase,
    ProposeSkillUseCase,
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
from universal_memory.domain.ports import LatentSkillRepository, RuleRepository
from universal_memory.infrastructure.config import (
    LocalConfigValidationPort,
    LocalProjectLayoutPort,
)
from universal_memory.infrastructure.security import (
    EntropySecretScanner,
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)
from universal_memory.infrastructure.storage import (
    LocalContextSummaryRepository,
    LocalFactRepository,
    LocalLatentSkillRepository,
    LocalRuleRepository,
)
from universal_memory.interfaces.cli import build_main


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

    def write(self, entity: LatentSkill) -> None:
        return None

    def delete(self, id: str) -> None:
        return None

    def migrate(self, target_version: int) -> None:
        return None


def main(argv: Sequence[str] | None = None) -> int:
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
    status_use_case = GetMemoryStatusUseCase(
        fact_repository=fact_repository,
        rule_repository=rule_repository,
        latent_skill_repository=latent_skill_repository,
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
    host_sync_use_case = SyncInstructionsUseCase(
        project_root=project_root,
        safe_write_use_case=safe_write_use_case,
        rule_repository=rule_repository,
    )
    propose_skill_use_case = ProposeSkillUseCase(
        project_root=project_root,
        repository=latent_skill_repository,
        safe_write_use_case=safe_write_use_case,
    )
    generate_skill_use_case = GenerateSkillUseCase(
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
    )
    get_skill_detail_use_case = GetSkillDetailUseCase(
        project_root=project_root,
        repository=latent_skill_repository,
    )

    def rollback_preview(scope: SnapshotScope) -> Snapshot:
        snapshots = snapshot_repository.list(scope=scope, status=SnapshotStatus.created)
        if not snapshots:
            raise SnapshotFailedError(
                "Nenhum snapshot encontrado para o escopo solicitado. "
                "Hint: execute uma mutacao segura antes de tentar rollback."
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
        context_command=context_use_case.execute,
        remember_command=remember_use_case.execute,
        facts_list_command=facts_list_use_case.execute,
        facts_purge_command=facts_purge_use_case.execute,
        facts_hygiene_command=facts_hygiene_use_case.execute,
        host_setup_command=host_use_case.execute,
        host_check_command=host_use_case.execute,
        host_sync_command=host_sync_use_case.execute,
        propose_skill_command=propose_skill_use_case.execute,
        generate_skill_command=generate_skill_use_case.execute,
        list_skills_command=list_skills_use_case.execute,
        get_skill_detail_command=get_skill_detail_use_case.execute,
    )
    return configured_main(argv)
