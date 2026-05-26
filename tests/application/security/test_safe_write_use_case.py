from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path

import pytest

from universal_memory.application.security.safe_write_use_case import (
    SafeWriteCommand,
    SafeWriteUseCase,
)
from universal_memory.domain import SecretDetectedError, SnapshotFailedError
from universal_memory.domain.entities import AuditEvent, AuditEventScope, Snapshot
from universal_memory.domain.ports import AuditLogRepository, SecretScannerPort, SnapshotRepository


class RecordingScanner(SecretScannerPort):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.scanned: list[str] = []

    def scan(self, content: str, *, origin: str | None = None) -> None:
        self.scanned.append(f"{origin}:{content}")
        if self.error is not None:
            raise self.error


class RecordingSnapshotRepository(SnapshotRepository):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.written: list[Snapshot] = []

    def read(self, id: str) -> Snapshot:
        raise KeyError(id)

    def list(self, scope=None, status=None) -> list[Snapshot]:
        return self.written

    def write(self, entity: Snapshot) -> None:
        if self.error is not None:
            raise self.error
        self.written.append(entity)

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


def build_use_case(
    *,
    project_root: Path,
    scanner: RecordingScanner | None = None,
    snapshots: RecordingSnapshotRepository | None = None,
    audit: RecordingAuditRepository | None = None,
) -> tuple[
    SafeWriteUseCase,
    RecordingScanner,
    RecordingSnapshotRepository,
    RecordingAuditRepository,
]:
    resolved_scanner = scanner or RecordingScanner()
    resolved_snapshots = snapshots or RecordingSnapshotRepository()
    resolved_audit = audit or RecordingAuditRepository()
    return (
        SafeWriteUseCase(
            project_root=project_root,
            secret_scanner=resolved_scanner,
            snapshot_repository=resolved_snapshots,
            audit_log_repository=resolved_audit,
        ),
        resolved_scanner,
        resolved_snapshots,
        resolved_audit,
    )


def test_safe_write_validates_scans_snapshots_writes_atomically_and_audits_success(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
    previous = b"old state\n"
    target.parent.mkdir(parents=True)
    target.write_bytes(previous)
    use_case, scanner, snapshots, audit = build_use_case(project_root=tmp_path)

    result = use_case.execute(
        SafeWriteCommand(
            relative_path=".umem/memory/facts.jsonl",
            content="new state\n",
            scope=AuditEventScope.project,
            origin="cli",
            action="remember_fact",
        )
    )

    assert scanner.scanned == ["cli:new state\n"]
    assert target.read_text(encoding="utf-8") == "new state\n"
    assert snapshots.written[0].relative_path == ".umem/memory/facts.jsonl"
    assert snapshots.written[0].hash == sha256(previous).hexdigest()
    assert audit.written[0].result == "success"
    assert audit.written[0].snapshot_reference == snapshots.written[0].id
    assert result.audit_reference == audit.written[0].audit_reference
    assert not list(target.parent.glob("*.tmp"))


def test_secret_detection_aborts_before_snapshot_or_write(tmp_path: Path) -> None:
    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
    target.parent.mkdir(parents=True)
    target.write_text("old state\n", encoding="utf-8")
    use_case, _scanner, snapshots, audit = build_use_case(
        project_root=tmp_path,
        scanner=RecordingScanner(SecretDetectedError("blocked", metadata={"span": (0, 6)})),
    )

    with pytest.raises(SecretDetectedError):
        use_case.execute(
            SafeWriteCommand(
                relative_path=".umem/memory/facts.jsonl",
                content="secret",
                scope=AuditEventScope.project,
                origin="cli",
                action="remember_fact",
            )
        )

    assert target.read_text(encoding="utf-8") == "old state\n"
    assert snapshots.written == []
    assert len(audit.written) == 1
    assert audit.written[0].result == "blocked"
    assert audit.written[0].status == "blocked"


def test_snapshot_failure_aborts_before_touching_original_file(tmp_path: Path) -> None:
    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
    target.parent.mkdir(parents=True)
    target.write_text("old state\n", encoding="utf-8")
    use_case, _scanner, _snapshots, audit = build_use_case(
        project_root=tmp_path,
        snapshots=RecordingSnapshotRepository(SnapshotFailedError("snapshot unavailable")),
    )

    with pytest.raises(SnapshotFailedError):
        use_case.execute(
            SafeWriteCommand(
                relative_path=".umem/memory/facts.jsonl",
                content="new state\n",
                scope=AuditEventScope.project,
                origin="cli",
                action="remember_fact",
            )
        )

    assert target.read_text(encoding="utf-8") == "old state\n"
    assert len(audit.written) == 1
    assert audit.written[0].result == "failure"
    assert audit.written[0].status == "failed"


def test_atomic_write_failure_cleans_temp_file_and_audits_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
    target.parent.mkdir(parents=True)
    target.write_text("old state\n", encoding="utf-8")
    use_case, _scanner, snapshots, audit = build_use_case(project_root=tmp_path)

    def fail_replace(source: Path | str, destination: Path | str) -> None:
        source_path = Path(source)
        if source_path.suffix == ".tmp":
            raise OSError("disk full")
        os.replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="disk full"):
        use_case.execute(
            SafeWriteCommand(
                relative_path=".umem/memory/facts.jsonl",
                content="new state\n",
                scope=AuditEventScope.project,
                origin="cli",
                action="remember_fact",
            )
        )

    assert target.read_text(encoding="utf-8") == "old state\n"
    assert snapshots.written
    assert audit.written[0].result == "failure"
    assert audit.written[0].status == "failed"
    assert not list(target.parent.glob("*.tmp"))


def test_rejects_absolute_or_traversal_paths(tmp_path: Path) -> None:
    use_case, _scanner, snapshots, audit = build_use_case(project_root=tmp_path)

    with pytest.raises(ValueError, match="relative_path"):
        use_case.execute(
            SafeWriteCommand(
                relative_path="../outside.txt",
                content="content",
                scope=AuditEventScope.project,
                origin="cli",
                action="write",
            )
        )

    assert snapshots.written == []
    assert audit.written == []
