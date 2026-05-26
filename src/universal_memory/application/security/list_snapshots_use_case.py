from __future__ import annotations

from dataclasses import dataclass

from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.domain.ports import SnapshotRepository


@dataclass(frozen=True, slots=True)
class ListSnapshotsCommand:
    scope: SnapshotScope | None = None
    status: SnapshotStatus | None = None


@dataclass(frozen=True, slots=True)
class SnapshotEntry:
    timestamp: str
    scope: str
    origin: str
    action: str
    relative_path: str
    hash: str
    manifest_path: str


@dataclass(frozen=True, slots=True)
class ListSnapshotsResult:
    snapshots: list[SnapshotEntry]


class ListSnapshotsUseCase:
    def __init__(
        self,
        *,
        snapshot_repository: SnapshotRepository,
        manifest_path: str = ".umem/snapshots/manifest.json",
    ) -> None:
        self.snapshot_repository = snapshot_repository
        self.manifest_path = manifest_path

    def execute(self, command: ListSnapshotsCommand) -> ListSnapshotsResult:
        snapshots = self.snapshot_repository.list(scope=command.scope, status=command.status)
        return ListSnapshotsResult(
            snapshots=[self._entry_for(snapshot, self.manifest_path) for snapshot in snapshots]
        )

    def _entry_for(self, snapshot: Snapshot, manifest_path: str) -> SnapshotEntry:
        return SnapshotEntry(
            timestamp=format_utc_iso(snapshot.timestamp),
            scope=snapshot.scope.value,
            origin=snapshot.origin,
            action=snapshot.action,
            relative_path=snapshot.relative_path,
            hash=snapshot.hash,
            manifest_path=manifest_path,
        )
