from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.application.security.rollback_use_case import (
    RollbackCommand,
    RollbackUseCase,
)
from universal_memory.domain import SnapshotFailedError
from universal_memory.domain.entities import (
    AuditEvent,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.domain.ports import AuditLogRepository, SnapshotRepository


class RecordingSnapshotRepository(SnapshotRepository):
    def __init__(self, snapshots: list[Snapshot], content_by_id: dict[str, bytes]) -> None:
        self.snapshots = snapshots
        self.content_by_id = content_by_id

    def read(self, id: str) -> Snapshot:
        for snapshot in self.snapshots:
            if snapshot.id == id:
                return snapshot
        raise KeyError(id)

    def get_content(self, id: str) -> bytes:
        return self.content_by_id[id]

    def list(self, scope=None, status=None) -> list[Snapshot]:
        snapshots = self.snapshots
        if scope is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.scope == scope]
        if status is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.status == status]
        return snapshots

    def write(self, entity: Snapshot) -> None:
        self.snapshots.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


class RecordingAuditRepository(AuditLogRepository):
    def __init__(self) -> None:
        self.written: list[AuditEvent] = []

    def read(self, id: str) -> AuditEvent:
        for event in self.written:
            if event.id == id:
                return event
        raise KeyError(id)

    def list(self, scope=None) -> list[AuditEvent]:
        return self.written

    def write(self, entity: AuditEvent) -> None:
        self.written.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


def make_snapshot(
    *,
    content: bytes,
    created_at: datetime,
    scope: SnapshotScope = SnapshotScope.project,
    relative_path: str = ".umem/memory/facts.jsonl",
    action: str = "safe_write",
) -> Snapshot:
    return Snapshot(
        id=str(uuid4()),
        created_at=created_at,
        updated_at=created_at,
        timestamp=created_at,
        scope=scope,
        origin="cli",
        action=action,
        relative_path=relative_path,
        hash=sha256(content).hexdigest(),
        status=SnapshotStatus.created,
    )


def test_rollback_restores_latest_snapshot_for_scope_and_audits_success(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"current state\n")
    base_time = datetime(2026, 5, 26, tzinfo=UTC)
    older = make_snapshot(content=b"older state\n", created_at=base_time)
    newer = make_snapshot(content=b"restored state\n", created_at=base_time + timedelta(minutes=2))
    global_snapshot = make_snapshot(
        content=b"global state\n",
        created_at=base_time + timedelta(minutes=5),
        scope=SnapshotScope.global_,
    )
    snapshots = RecordingSnapshotRepository(
        [global_snapshot, older, newer],
        {
            older.id: b"older state\n",
            newer.id: b"restored state\n",
            global_snapshot.id: b"global state\n",
        },
    )
    audit = RecordingAuditRepository()
    use_case = RollbackUseCase(
        project_root=tmp_path,
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )

    result = use_case.execute(
        RollbackCommand(scope=SnapshotScope.project, origin="cli", action="rollback")
    )

    assert target.read_bytes() == b"restored state\n"
    assert result.scope == SnapshotScope.project
    assert result.snapshot_reference == newer.id
    assert result.restored_paths == [".umem/memory/facts.jsonl"]
    assert result.audit_reference == audit.written[0].audit_reference
    assert audit.written[0].action == "rollback"
    assert audit.written[0].result == "success"
    assert audit.written[0].status == "logged"
    assert audit.written[0].snapshot_reference == newer.id
    assert not list(target.parent.glob("*.tmp"))


def test_rollback_without_snapshots_raises_domain_error_without_side_effects(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"current state\n")
    audit = RecordingAuditRepository()
    use_case = RollbackUseCase(
        project_root=tmp_path,
        snapshot_repository=RecordingSnapshotRepository([], {}),
        audit_log_repository=audit,
    )

    with pytest.raises(SnapshotFailedError, match="Nenhum snapshot"):
        use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))

    assert target.read_bytes() == b"current state\n"
    assert audit.written == []


def test_rollback_blocks_hash_mismatch_before_write_and_audits_failure(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"current state\n")
    timestamp = datetime(2026, 5, 26, tzinfo=UTC)
    snapshot = make_snapshot(content=b"expected state\n", created_at=timestamp)
    audit = RecordingAuditRepository()
    use_case = RollbackUseCase(
        project_root=tmp_path,
        snapshot_repository=RecordingSnapshotRepository(
            [snapshot],
            {snapshot.id: b"corrupted state\n"},
        ),
        audit_log_repository=audit,
    )

    with pytest.raises(SnapshotFailedError, match="integridade"):
        use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))

    assert target.read_bytes() == b"current state\n"
    assert len(audit.written) == 1
    assert audit.written[0].result == "failure"
    assert audit.written[0].status == "failed"
    assert audit.written[0].snapshot_reference == snapshot.id


def test_rollback_is_offline_and_has_no_network_dependency(tmp_path: Path) -> None:
    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"current state\n")
    snapshot = make_snapshot(
        content=b"offline restore\n",
        created_at=datetime(2026, 5, 26, tzinfo=UTC),
    )
    use_case = RollbackUseCase(
        project_root=tmp_path,
        snapshot_repository=RecordingSnapshotRepository(
            [snapshot],
            {snapshot.id: b"offline restore\n"},
        ),
        audit_log_repository=RecordingAuditRepository(),
    )

    result = use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))

    assert result.snapshot_reference == snapshot.id
    assert target.read_bytes() == b"offline restore\n"


def test_rollback_restores_deleted_target_file(tmp_path: Path) -> None:
    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
    snapshot = make_snapshot(
        content=b"restored from deletion\n",
        created_at=datetime(2026, 5, 26, tzinfo=UTC),
    )
    use_case = RollbackUseCase(
        project_root=tmp_path,
        snapshot_repository=RecordingSnapshotRepository(
            [snapshot],
            {snapshot.id: b"restored from deletion\n"},
        ),
        audit_log_repository=RecordingAuditRepository(),
    )

    result = use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))

    assert result.snapshot_reference == snapshot.id
    assert target.read_bytes() == b"restored from deletion\n"
