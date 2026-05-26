import json
import os
import threading
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.domain import SnapshotFailedError
from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
from universal_memory.infrastructure.security import LocalSnapshotRepository


def make_snapshot(
    *,
    relative_path: str = "memory/facts.jsonl",
    content: bytes = b"previous state\n",
    scope: SnapshotScope = SnapshotScope.project,
    created_at: datetime | None = None,
) -> Snapshot:
    timestamp = created_at or datetime.now(UTC)
    return Snapshot(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        timestamp=timestamp,
        scope=scope,
        action="test-write",
        relative_path=relative_path,
        hash=sha256(content).hexdigest(),
        status=SnapshotStatus.created,
    )


def test_write_copies_existing_file_and_records_manifest_metadata(tmp_path: Path) -> None:
    project_root = tmp_path / "workspace"
    data_root = project_root / ".umem"
    original = project_root / "memory" / "facts.jsonl"
    content = b"previous state\n"
    original.parent.mkdir(parents=True)
    original.write_bytes(content)
    repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
    snapshot = make_snapshot(content=content)

    repository.write(snapshot)

    copied_file = data_root / "snapshots" / "files" / snapshot.id
    assert copied_file.read_bytes() == content
    stored = repository.read(snapshot.id)
    assert stored == snapshot
    assert repository.list(scope=SnapshotScope.project, status=SnapshotStatus.created) == [snapshot]


def test_write_records_initial_creation_without_physical_copy(tmp_path: Path) -> None:
    project_root = tmp_path / "workspace"
    repository = LocalSnapshotRepository(
        project_root=project_root, data_root=project_root / ".umem"
    )
    snapshot = make_snapshot(relative_path="memory/new-file.jsonl", content=b"")

    repository.write(snapshot)

    assert repository.read(snapshot.id) == snapshot
    assert not (project_root / ".umem" / "snapshots" / "files" / snapshot.id).exists()


def test_write_aborts_with_snapshot_failed_error_when_physical_copy_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = tmp_path / "workspace"
    data_root = project_root / ".umem"
    original = project_root / "memory" / "facts.jsonl"
    content = b"previous state\n"
    original.parent.mkdir(parents=True)
    original.write_bytes(content)
    repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
    snapshot = make_snapshot(content=content)

    def fail_write_bytes(self: Path, data: bytes) -> int:
        if self.name.endswith(".tmp"):
            raise OSError("disk full")
        return len(data)

    monkeypatch.setattr(Path, "write_bytes", fail_write_bytes)

    with pytest.raises(SnapshotFailedError, match="Failed to create snapshot"):
        repository.write(snapshot)

    assert not (data_root / "snapshots" / "manifest.json").exists()
    assert not (data_root / "snapshots" / "files" / snapshot.id).exists()


def test_write_rejects_hash_mismatch_before_recording_manifest(tmp_path: Path) -> None:
    project_root = tmp_path / "workspace"
    data_root = project_root / ".umem"
    original = project_root / "memory" / "facts.jsonl"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"changed state\n")
    repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
    snapshot = make_snapshot(content=b"previous state\n")

    with pytest.raises(SnapshotFailedError, match="hash mismatch"):
        repository.write(snapshot)

    assert not (data_root / "snapshots" / "manifest.json").exists()


def test_write_retains_only_five_newest_snapshots_per_scope_and_removes_old_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "workspace"
    data_root = project_root / ".umem"
    original = project_root / "memory" / "facts.jsonl"
    content = b"previous state\n"
    original.parent.mkdir(parents=True)
    original.write_bytes(content)
    repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
    base_time = datetime(2026, 5, 26, tzinfo=UTC)
    snapshots = [
        make_snapshot(content=content, created_at=base_time + timedelta(minutes=offset))
        for offset in range(7)
    ]

    for snapshot in snapshots:
        repository.write(snapshot)

    retained = repository.list(scope=SnapshotScope.project)
    assert [snapshot.id for snapshot in retained] == [snapshot.id for snapshot in snapshots[2:]]
    assert all(
        (data_root / "snapshots" / "files" / snapshot.id).exists()
        for snapshot in snapshots[2:]
    )
    assert all(
        not (data_root / "snapshots" / "files" / snapshot.id).exists()
        for snapshot in snapshots[:2]
    )


def test_retention_deletes_old_files_only_after_new_manifest_is_confirmed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = tmp_path / "workspace"
    data_root = project_root / ".umem"
    original = project_root / "memory" / "facts.jsonl"
    content = b"previous state\n"
    original.parent.mkdir(parents=True)
    original.write_bytes(content)
    repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
    base_time = datetime(2026, 5, 26, tzinfo=UTC)
    snapshots = [
        make_snapshot(content=content, created_at=base_time + timedelta(minutes=offset))
        for offset in range(6)
    ]
    observed_manifest_ids_before_unlink: list[list[str]] = []
    original_unlink = Path.unlink

    def observe_manifest_before_unlink(self: Path, *, missing_ok: bool = False) -> None:
        if self.parent == data_root / "snapshots" / "files":
            observed_manifest_ids_before_unlink.append(
                [snapshot.id for snapshot in repository.list(scope=SnapshotScope.project)]
            )
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", observe_manifest_before_unlink)

    for snapshot in snapshots:
        repository.write(snapshot)

    assert observed_manifest_ids_before_unlink
    assert observed_manifest_ids_before_unlink[-1] == [snapshot.id for snapshot in snapshots[1:]]


def test_write_prevents_symlink_path_traversal(tmp_path: Path) -> None:
    project_root = tmp_path / "workspace"
    data_root = project_root / ".umem"
    project_root.mkdir(parents=True)

    # File outside the project root
    outside_file = tmp_path / "outside.txt"
    outside_file.write_bytes(b"sensitive content")

    # Symlink inside the project pointing outside
    symlink_path = project_root / "memory" / "exploit.txt"
    symlink_path.parent.mkdir(parents=True, exist_ok=True)
    symlink_path.symlink_to(outside_file)

    repository = LocalSnapshotRepository(
        project_root=project_root, data_root=data_root
    )
    snapshot = make_snapshot(relative_path="memory/exploit.txt", content=b"sensitive content")

    with pytest.raises(SnapshotFailedError, match="path traversal detected"):
        repository.write(snapshot)


def test_write_validates_schema_version(tmp_path: Path) -> None:
    project_root = tmp_path / "workspace"
    data_root = project_root / ".umem"
    repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)

    manifest_path = data_root / "snapshots" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"schema_version": 2, "snapshots": []}), encoding="utf-8")

    snapshot = make_snapshot(relative_path="memory/facts.jsonl", content=b"")
    with pytest.raises(SnapshotFailedError, match="Failed to create snapshot"):
        repository.write(snapshot)


def test_timezone_normalization_safety() -> None:
    expected_hour = 12
    naive_dt = datetime(2026, 5, 26, expected_hour, 0, 0)
    normalized = LocalSnapshotRepository._normalize_datetime(naive_dt)
    assert normalized.tzinfo == UTC
    assert normalized.hour == expected_hour


def test_concurrency_lock_prevents_clash(tmp_path: Path) -> None:
    project_root = tmp_path / "workspace"
    data_root = project_root / ".umem"
    repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)

    lock_path = data_root / "snapshots" / "manifest.json.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    def write_snapshot():
        snapshot = make_snapshot(relative_path="memory/facts.jsonl", content=b"")
        with pytest.raises(SnapshotFailedError, match="Failed to acquire lock"):
            repository.write(snapshot)

    t = threading.Thread(target=write_snapshot)
    t.start()
    t.join()

    os.close(fd)
    os.unlink(lock_path)

