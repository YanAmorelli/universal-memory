from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from universal_memory.application.security.list_snapshots_use_case import (
    ListSnapshotsCommand,
    ListSnapshotsUseCase,
)
from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
from universal_memory.domain.ports import SnapshotRepository


class RecordingSnapshotRepository(SnapshotRepository):
    def __init__(self, snapshots: list[Snapshot] | None = None) -> None:
        self.snapshots = snapshots or []
        self.calls: list[tuple[SnapshotScope | None, SnapshotStatus | None]] = []

    def read(self, id: str) -> Snapshot:
        raise KeyError(id)

    def get_content(self, id: str) -> bytes:
        raise KeyError(id)

    def list(
        self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None
    ) -> list[Snapshot]:
        self.calls.append((scope, status))
        snapshots = self.snapshots
        if scope is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.scope == scope]
        if status is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.status == status]
        return sorted(snapshots, key=lambda snapshot: snapshot.timestamp)

    def write(self, entity: Snapshot) -> None:
        self.snapshots.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


def make_snapshot(  # noqa: PLR0913
    *,
    created_at: datetime,
    scope: SnapshotScope = SnapshotScope.project,
    status: SnapshotStatus = SnapshotStatus.created,
    action: str = "safe_write",
    origin: str = "cli",
    relative_path: str = ".umem/memory/facts.jsonl",
) -> Snapshot:
    return Snapshot(
        id=str(uuid4()),
        created_at=created_at,
        updated_at=created_at,
        timestamp=created_at,
        scope=scope,
        origin=origin,
        action=action,
        relative_path=relative_path,
        hash=sha256(b"previous").hexdigest(),
        status=status,
    )


def test_list_snapshots_returns_snapshots_ordered_with_required_fields() -> None:
    base = datetime(2026, 5, 26, tzinfo=UTC)
    newer = make_snapshot(created_at=base + timedelta(minutes=2), action="second")
    older = make_snapshot(created_at=base, action="first", relative_path="rules/global.toml")
    repository = RecordingSnapshotRepository([newer, older])
    use_case = ListSnapshotsUseCase(snapshot_repository=repository)

    result = use_case.execute(ListSnapshotsCommand())

    assert [snapshot.action for snapshot in result.snapshots] == ["first", "second"]
    assert result.snapshots[0].timestamp == "2026-05-26T00:00:00Z"
    assert result.snapshots[0].scope == "project"
    assert result.snapshots[0].origin == "cli"
    assert result.snapshots[0].relative_path == "rules/global.toml"
    assert result.snapshots[0].hash == older.hash
    assert result.snapshots[0].manifest_path == ".umem/snapshots/manifest.json"


def test_list_snapshots_filters_by_scope_and_status() -> None:
    base = datetime(2026, 5, 26, tzinfo=UTC)
    created_global = make_snapshot(
        created_at=base,
        scope=SnapshotScope.global_,
        status=SnapshotStatus.created,
    )
    restored_global = make_snapshot(
        created_at=base + timedelta(minutes=1),
        scope=SnapshotScope.global_,
        status=SnapshotStatus.restored,
    )
    repository = RecordingSnapshotRepository([created_global, restored_global])
    use_case = ListSnapshotsUseCase(snapshot_repository=repository)

    result = use_case.execute(
        ListSnapshotsCommand(scope=SnapshotScope.global_, status=SnapshotStatus.restored)
    )

    assert repository.calls == [(SnapshotScope.global_, SnapshotStatus.restored)]
    assert [snapshot.hash for snapshot in result.snapshots] == [restored_global.hash]
    assert result.snapshots[0].scope == "global"


def test_list_snapshots_returns_empty_list_when_data_does_not_exist() -> None:
    use_case = ListSnapshotsUseCase(snapshot_repository=RecordingSnapshotRepository())

    result = use_case.execute(ListSnapshotsCommand())

    assert result.snapshots == []
