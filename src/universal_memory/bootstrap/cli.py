from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from universal_memory.application.security import (
    ListAuditLogUseCase,
    ListSnapshotsUseCase,
    RollbackUseCase,
)
from universal_memory.domain import SnapshotFailedError
from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
from universal_memory.infrastructure.config import (
    LocalConfigValidationPort,
    LocalProjectLayoutPort,
)
from universal_memory.infrastructure.security import (
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)
from universal_memory.interfaces.cli import build_main


def main(argv: Sequence[str] | None = None) -> int:
    project_root = Path.cwd()
    data_root = project_root / ".umem"
    audit_list_use_case = ListAuditLogUseCase(
        audit_log_repository=LocalAuditLogRepository(
            project_root=project_root,
            data_root=data_root,
        )
    )
    manifest_file = data_root / "snapshots" / "manifest.json"
    manifest_rel_path = str(manifest_file.relative_to(project_root))
    snapshots_list_use_case = ListSnapshotsUseCase(
        snapshot_repository=LocalSnapshotRepository(project_root=project_root, data_root=data_root),
        manifest_path=manifest_rel_path,
    )
    snapshot_repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
    rollback_use_case = RollbackUseCase(
        project_root=project_root,
        snapshot_repository=snapshot_repository,
        audit_log_repository=LocalAuditLogRepository(
            project_root=project_root,
            data_root=data_root,
        ),
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
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        audit_list_command=audit_list_use_case.execute,
        snapshots_list_command=snapshots_list_use_case.execute,
        rollback_command=rollback_use_case.execute,
        rollback_preview_command=rollback_preview,
    )
    return configured_main(argv)
