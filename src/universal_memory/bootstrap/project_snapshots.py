"""Keep recovery bound to the root that originally owned each safe write."""

import os
from datetime import UTC, datetime

from universal_memory.application.security import (
    ListSnapshotsCommand,
    ListSnapshotsResult,
    ListSnapshotsUseCase,
    RollbackCommand,
    RollbackResult,
    RollbackUseCase,
    SafeWriteUseCase,
)
from universal_memory.domain import SnapshotFailedError
from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus


class ProjectSnapshotCommands:
    def __init__(self, memory: SafeWriteUseCase, host: SafeWriteUseCase) -> None:
        self.writers = [memory] if memory.project_root == host.project_root else [memory, host]
        self.project_root = host.project_root

    def _latest(self, scope: SnapshotScope) -> tuple[Snapshot, SafeWriteUseCase]:
        candidates = [
            (snapshot, writer)
            for writer in self.writers
            for snapshot in writer.snapshot_repository.list(
                scope=scope,
                status=SnapshotStatus.created,
            )
        ]
        if not candidates:
            raise SnapshotFailedError(
                "No snapshot found for the requested scope. "
                "Hint: run a safe mutation before trying rollback."
            )

        def timestamp(item: tuple[Snapshot, SafeWriteUseCase]) -> datetime:
            value = item[0].timestamp
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value

        return max(candidates, key=timestamp)

    def preview(self, scope: SnapshotScope) -> Snapshot:
        return self._latest(scope)[0]

    def rollback(self, command: RollbackCommand) -> RollbackResult:
        _, writer = self._latest(command.scope)
        return RollbackUseCase(
            project_root=writer.project_root,
            snapshot_repository=writer.snapshot_repository,
            audit_log_repository=writer.audit_log_repository,
        ).execute(command)

    def list(self, command: ListSnapshotsCommand) -> ListSnapshotsResult:
        entries = []
        for writer in self.writers:
            result = ListSnapshotsUseCase(
                snapshot_repository=writer.snapshot_repository,
                manifest_path=os.path.relpath(
                    writer.project_root / ".umem/snapshots/manifest.json",
                    self.project_root,
                ),
            ).execute(command)
            entries.extend(result.snapshots)
        return ListSnapshotsResult(snapshots=sorted(entries, key=lambda entry: entry.timestamp))
