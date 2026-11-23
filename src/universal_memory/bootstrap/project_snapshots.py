"""Keep recovery bound to the root that originally owned each safe write."""

import os
from datetime import UTC, datetime
from pathlib import PurePosixPath

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
from universal_memory.infrastructure.config.project_layout import resolve_project_layout


class ProjectSnapshotCommands:
    def __init__(self, memory: SafeWriteUseCase, host: SafeWriteUseCase) -> None:
        self.writers = [memory] if memory.project_root == host.project_root else [memory, host]
        self.project_root = host.project_root
        self.state_prefixes = {PurePosixPath(".umem"), PurePosixPath("umem")}
        for writer in self.writers:
            layout = resolve_project_layout(writer.project_root)
            self.state_prefixes.update(
                PurePosixPath(root.relative_to(writer.project_root).as_posix())
                for root in (layout.operational_root_path, layout.shared_root_path)
            )

    def _eligible(self, writer: SafeWriteUseCase, relative_path: str) -> bool:
        if len(self.writers) == 1:
            return True
        # Local state snapshots belong to orphaned memory. Conversely, host
        # backups in the main manifest belong to that checkout's host files.
        is_state = any(
            PurePosixPath(relative_path).is_relative_to(prefix) for prefix in self.state_prefixes
        )
        return is_state == (writer is self.writers[0])

    def _latest(self, scope: SnapshotScope) -> tuple[Snapshot, SafeWriteUseCase]:
        candidates = [
            (snapshot, writer)
            for writer in self.writers
            for snapshot in writer.snapshot_repository.list(
                scope=scope,
                status=SnapshotStatus.created,
            )
            if self._eligible(writer, snapshot.relative_path)
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
        snapshot, writer = self._latest(command.scope)
        return RollbackUseCase(
            project_root=writer.project_root,
            snapshot_repository=writer.snapshot_repository,
            audit_log_repository=writer.audit_log_repository,
        ).execute(command, snapshot_id=snapshot.id)

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
            entries.extend(
                entry for entry in result.snapshots if self._eligible(writer, entry.relative_path)
            )
        return ListSnapshotsResult(snapshots=sorted(entries, key=lambda entry: entry.timestamp))
