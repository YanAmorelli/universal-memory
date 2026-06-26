import json
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.domain import StorageError
from universal_memory.domain.entities import AuditEvent, AuditEventScope
from universal_memory.infrastructure.security import LocalAuditLogRepository

CONCURRENT_EVENT_COUNT = 40


def make_audit_event(
    *,
    scope: AuditEventScope = AuditEventScope.project,
    created_at: datetime | None = None,
    action: str = "safe-write",
    result: str = "success",
) -> AuditEvent:
    timestamp = created_at or datetime.now(UTC)
    audit_reference = str(uuid4())
    return AuditEvent(
        id=audit_reference,
        created_at=timestamp,
        updated_at=timestamp,
        timestamp=timestamp,
        action=action,
        scope=scope,
        origin="test",
        result=result,
        snapshot_reference=str(uuid4()),
        audit_reference=audit_reference,
        status="logged",
    )


def test_write_appends_event_as_jsonl(tmp_path: Path) -> None:
    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
    event = make_audit_event()

    repository.write(event)

    events_path = tmp_path / ".umem" / "audit" / "events.jsonl"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["id"] == event.id
    assert payload["audit_reference"] == event.audit_reference
    assert payload["timestamp"].endswith("Z")
    assert repository.read(event.id) == event


def test_list_filters_by_scope_and_read_returns_events_ordered_by_timestamp(
    tmp_path: Path,
) -> None:
    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
    base = datetime(2026, 5, 26, tzinfo=UTC)
    older = make_audit_event(scope=AuditEventScope.project, created_at=base)
    global_event = make_audit_event(
        scope=AuditEventScope.global_, created_at=base + timedelta(minutes=1)
    )
    newer = make_audit_event(scope=AuditEventScope.project, created_at=base + timedelta(minutes=2))

    repository.write(newer)
    repository.write(global_event)
    repository.write(older)

    assert repository.list(scope=AuditEventScope.project) == [older, newer]
    assert repository.read(global_event.id) == global_event


def test_concurrent_writes_preserve_all_jsonl_events(tmp_path: Path) -> None:
    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
    events = [make_audit_event() for _ in range(CONCURRENT_EVENT_COUNT)]

    threads = [threading.Thread(target=repository.write, args=(event,)) for event in events]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    stored = repository.list(scope=AuditEventScope.project)
    assert {event.id for event in stored} == {event.id for event in events}
    assert (
        len((tmp_path / ".umem" / "audit" / "events.jsonl").read_text().splitlines())
        == CONCURRENT_EVENT_COUNT
    )


def test_write_fails_with_typed_error_when_lock_cannot_be_acquired(tmp_path: Path) -> None:
    repository = LocalAuditLogRepository(
        project_root=tmp_path,
        data_root=tmp_path / ".umem",
        lock_acquire_timeout_seconds=0.1,
    )
    lock_path = tmp_path / ".umem" / "audit" / "events.jsonl.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    try:
        with pytest.raises(StorageError, match="Failed to acquire lock"):
            repository.write(make_audit_event())
    finally:
        os.close(fd)
        os.unlink(lock_path)


def test_corrupted_log_skips_invalid_lines(tmp_path: Path) -> None:
    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
    events_path = tmp_path / ".umem" / "audit" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("{not-json}\n", encoding="utf-8")

    assert repository.list() == []


def test_unread_log_raises_typed_storage_error(tmp_path: Path) -> None:
    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
    events_path = tmp_path / ".umem" / "audit" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.mkdir()  # Causes OSError upon read

    with pytest.raises(StorageError, match="Failed to read audit log"):
        repository.list()
