from collections.abc import Sequence
from pathlib import Path

from universal_memory.application.security import ListAuditLogUseCase, ListSnapshotsUseCase
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
        snapshot_repository=LocalSnapshotRepository(
            project_root=project_root,
            data_root=data_root,
        ),
        manifest_path=manifest_rel_path,
    )
    configured_main = build_main(
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        audit_list_command=audit_list_use_case.execute,
        snapshots_list_command=snapshots_list_use_case.execute,
    )
    return configured_main(argv)
