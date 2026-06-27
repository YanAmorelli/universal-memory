from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from universal_memory.domain import StorageError
from universal_memory.domain.entities import AuditEvent, AuditEventScope
from universal_memory.domain.ports import AuditLogRepository

STALE_LOCK_SECONDS = 10.0
LOCK_ACQUIRE_TIMEOUT_SECONDS = 10.0
LOCK_RETRY_DELAY_SECONDS = 0.05


class LocalAuditLogRepository(AuditLogRepository):
    def __init__(
        self,
        *,
        project_root: Path,
        data_root: Path,
        lock_acquire_timeout_seconds: float = LOCK_ACQUIRE_TIMEOUT_SECONDS,
    ) -> None:
        self.project_root = project_root
        self.data_root = data_root
        self.audit_root = self.data_root / "audit"
        self.events_path = self.audit_root / "events.jsonl"
        self.lock_acquire_timeout_seconds = lock_acquire_timeout_seconds

    @contextmanager
    def _lock(self) -> Generator[None, None, None]:
        lock_path = self.events_path.with_suffix(".jsonl.lock")
        self.audit_root.mkdir(parents=True, exist_ok=True)

        # Break stale locks older than 10 seconds
        if lock_path.exists():
            try:
                mtime = os.path.getmtime(lock_path)
                if time.time() - mtime > STALE_LOCK_SECONDS:
                    lock_path.unlink(missing_ok=True)
            except OSError:
                pass

        deadline = time.monotonic() + self.lock_acquire_timeout_seconds
        acquired = False
        fd: int | None = None
        try:
            while time.monotonic() <= deadline:
                try:
                    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    acquired = True
                    break
                except FileExistsError:
                    time.sleep(LOCK_RETRY_DELAY_SECONDS)
            if not acquired:
                raise StorageError("Failed to acquire lock on audit log")
            yield
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if acquired:
                try:
                    os.unlink(lock_path)
                except OSError:
                    pass

    def read(self, id: str) -> AuditEvent:
        for event in self._load_events():
            if event.id == id:
                return event
        raise StorageError(f"Audit event not found: {id}")

    def list(self, scope: AuditEventScope | None = None) -> list[AuditEvent]:
        events = self._load_events()
        if scope is not None:
            events = [event for event in events if event.scope == scope]
        return sorted(events, key=lambda event: self._normalize_datetime(event.timestamp))

    def write(self, entity: AuditEvent) -> None:
        payload = self._render_event(entity)
        try:
            with self._lock():
                with self.events_path.open("a", encoding="utf-8") as stream:
                    stream.write(f"{payload}\n")
                    stream.flush()
                    os.fsync(stream.fileno())
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to write audit log") from exc

    def migrate(self, target_version: int) -> None:
        if target_version != 1:
            raise StorageError(f"Unsupported audit repository schema version: {target_version}")

    def _load_events(self) -> list[AuditEvent]:
        if not self.events_path.exists():
            return []
        try:
            with self._lock():
                events: list[AuditEvent] = []
                for line in self.events_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        events.append(AuditEvent.model_validate(json.loads(line)))
                    except (json.JSONDecodeError, ValidationError) as line_exc:
                        print(f"Skipping corrupt audit log line: {line_exc}", file=sys.stderr)
                return events
        except (OSError, StorageError) as exc:
            if isinstance(exc, StorageError):
                raise
            raise StorageError("Failed to read audit log") from exc

    @classmethod
    def _render_event(cls, entity: AuditEvent) -> str:
        payload = entity.model_dump(mode="json")
        normalized = cls._normalize_payload(payload)
        return json.dumps(normalized, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _normalize_payload(cls, data: object) -> object:
        if isinstance(data, dict):
            return {k: cls._normalize_payload(v) for k, v in data.items()}
        if isinstance(data, list):
            return [cls._normalize_payload(item) for item in data]
        if isinstance(data, str) and data.endswith("+00:00"):
            return data.removesuffix("+00:00") + "Z"
        return data

    @staticmethod
    def _normalize_datetime(dt: datetime) -> datetime:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=UTC)
        return dt
