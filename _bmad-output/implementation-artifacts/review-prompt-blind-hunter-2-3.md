# Blind Hunter Review Prompt

Você é o Blind Hunter. Revise o diff abaixo sem contexto adicional do projeto. Procure bugs, regressões comportamentais, suposições quebradas, inconsistências internas, APIs mal definidas, problemas de idempotência, riscos de manutenção e lacunas de teste. Produza apenas findings acionáveis em Markdown.

Para cada finding:
- Título de uma linha
- Severidade: high, medium ou low
- Evidência objetiva no diff
- Impacto concreto

## Diff

```diff
diff --git a/src/universal_memory/application/security/__init__.py b/src/universal_memory/application/security/__init__.py
new file mode 100644
index 0000000..9e9e8b8
--- /dev/null
+++ b/src/universal_memory/application/security/__init__.py
@@ -0,0 +1,9 @@
+"""Security use cases for universal-memory."""
+
+from universal_memory.application.security.safe_write_use_case import (
+    SafeWriteCommand,
+    SafeWriteResult,
+    SafeWriteUseCase,
+)
+
+__all__ = ["SafeWriteCommand", "SafeWriteResult", "SafeWriteUseCase"]
diff --git a/src/universal_memory/application/security/safe_write_use_case.py b/src/universal_memory/application/security/safe_write_use_case.py
new file mode 100644
index 0000000..510429c
--- /dev/null
+++ b/src/universal_memory/application/security/safe_write_use_case.py
@@ -0,0 +1,148 @@
+from __future__ import annotations
+
+import os
+from dataclasses import dataclass
+from datetime import UTC, datetime
+from hashlib import sha256
+from pathlib import Path, PurePosixPath
+from uuid import uuid4
+
+from universal_memory.domain.entities import (
+    AuditEvent,
+    AuditEventScope,
+    Snapshot,
+    SnapshotScope,
+    SnapshotStatus,
+)
+from universal_memory.domain.ports import AuditLogRepository, SecretScannerPort, SnapshotRepository
+
+
+@dataclass(frozen=True, slots=True)
+class SafeWriteCommand:
+    relative_path: str
+    content: str
+    scope: AuditEventScope
+    origin: str
+    action: str
+
+
+@dataclass(frozen=True, slots=True)
+class SafeWriteResult:
+    relative_path: str
+    audit_reference: str
+    snapshot_reference: str
+
+
+class SafeWriteUseCase:
+    def __init__(
+        self,
+        *,
+        project_root: Path,
+        secret_scanner: SecretScannerPort,
+        snapshot_repository: SnapshotRepository,
+        audit_log_repository: AuditLogRepository,
+    ) -> None:
+        self.project_root = project_root.resolve()
+        self.secret_scanner = secret_scanner
+        self.snapshot_repository = snapshot_repository
+        self.audit_log_repository = audit_log_repository
+
+    def execute(self, command: SafeWriteCommand) -> SafeWriteResult:
+        relative_path = self._validate_relative_path(command.relative_path)
+        self.secret_scanner.scan(command.content, origin=command.origin)
+
+        target_path = self._resolve_target(relative_path)
+        previous_bytes = target_path.read_bytes() if target_path.exists() else b""
+        snapshot = self._snapshot_for(command, relative_path, previous_bytes)
+        self.snapshot_repository.write(snapshot)
+
+        try:
+            self._atomic_write(target_path, command.content)
+        except OSError:
+            try:
+                self._record_audit(command, snapshot_reference=snapshot.id, result="failure")
+            except Exception as audit_error:
+                audit_error.add_note("Audit failure suppressed to preserve write exception")
+            raise
+
+        event = self._record_audit(command, snapshot_reference=snapshot.id, result="success")
+        return SafeWriteResult(
+            relative_path=relative_path,
+            audit_reference=event.audit_reference,
+            snapshot_reference=snapshot.id,
+        )
+
+    def _validate_relative_path(self, value: str) -> str:
+        path = PurePosixPath(value)
+        if not value or path.is_absolute() or ".." in path.parts:
+            raise ValueError("relative_path must be relative and must not contain traversal")
+        return path.as_posix()
+
+    def _resolve_target(self, relative_path: str) -> Path:
+        target_path = self.project_root / relative_path
+        try:
+            target_path.resolve().relative_to(self.project_root)
+        except ValueError as exc:
+            raise ValueError("relative_path must resolve inside project_root") from exc
+        if target_path.exists() and not target_path.is_file():
+            raise ValueError("relative_path must target a file")
+        return target_path
+
+    def _snapshot_for(
+        self,
+        command: SafeWriteCommand,
+        relative_path: str,
+        previous_bytes: bytes,
+    ) -> Snapshot:
+        timestamp = datetime.now(UTC)
+        snapshot_scope = (
+            SnapshotScope.global_
+            if command.scope == AuditEventScope.global_
+            else SnapshotScope.project
+        )
+        return Snapshot(
+            id=str(uuid4()),
+            created_at=timestamp,
+            updated_at=timestamp,
+            timestamp=timestamp,
+            scope=snapshot_scope,
+            action=command.action,
+            relative_path=relative_path,
+            hash=sha256(previous_bytes).hexdigest(),
+            status=SnapshotStatus.created,
+        )
+
+    def _atomic_write(self, target_path: Path, content: str) -> None:
+        target_path.parent.mkdir(parents=True, exist_ok=True)
+        temp_path = target_path.with_name(f"{target_path.name}.{uuid4()}.tmp")
+        try:
+            temp_path.write_text(content, encoding="utf-8")
+            os.replace(temp_path, target_path)
+        except OSError:
+            temp_path.unlink(missing_ok=True)
+            raise
+
+    def _record_audit(
+        self,
+        command: SafeWriteCommand,
+        *,
+        snapshot_reference: str,
+        result: str,
+    ) -> AuditEvent:
+        timestamp = datetime.now(UTC)
+        audit_reference = str(uuid4())
+        event = AuditEvent(
+            id=audit_reference,
+            created_at=timestamp,
+            updated_at=timestamp,
+            timestamp=timestamp,
+            action=command.action,
+            scope=command.scope,
+            origin=command.origin,
+            result=result,
+            snapshot_reference=snapshot_reference,
+            audit_reference=audit_reference,
+            status="logged" if result == "success" else "failed",
+        )
+        self.audit_log_repository.write(event)
+        return event
diff --git a/src/universal_memory/domain/__init__.py b/src/universal_memory/domain/__init__.py
index e3f4621..431e487 100644
--- a/src/universal_memory/domain/__init__.py
+++ b/src/universal_memory/domain/__init__.py
@@ -33,6 +33,7 @@ from universal_memory.domain.ports import (
     LatentSkillRepository,
     ProjectLayoutPort,
     RuleRepository,
+    SecretScannerPort,
     SnapshotRepository,
 )
 from universal_memory.domain.project_layout import ProjectLayoutResult
@@ -62,6 +63,7 @@ __all__ = [
     "RuleScope",
     "RuleStatus",
     "SecretDetectedError",
+    "SecretScannerPort",
     "Snapshot",
     "SnapshotFailedError",
     "SnapshotRepository",
diff --git a/src/universal_memory/infrastructure/security/__init__.py b/src/universal_memory/infrastructure/security/__init__.py
index e5a231c..af9edb1 100644
--- a/src/universal_memory/infrastructure/security/__init__.py
+++ b/src/universal_memory/infrastructure/security/__init__.py
@@ -1,8 +1,11 @@
 """Offline security scanners for persistence guardrails."""
 
 from universal_memory.infrastructure.security.entropy_secret_scanner import EntropySecretScanner
+from universal_memory.infrastructure.security.local_audit_log_repository import (
+    LocalAuditLogRepository,
+)
 from universal_memory.infrastructure.security.local_snapshot_repository import (
     LocalSnapshotRepository,
 )
 
-__all__ = ["EntropySecretScanner", "LocalSnapshotRepository"]
+__all__ = ["EntropySecretScanner", "LocalAuditLogRepository", "LocalSnapshotRepository"]
diff --git a/src/universal_memory/infrastructure/security/local_audit_log_repository.py b/src/universal_memory/infrastructure/security/local_audit_log_repository.py
new file mode 100644
index 0000000..9d72e93
--- /dev/null
+++ b/src/universal_memory/infrastructure/security/local_audit_log_repository.py
@@ -0,0 +1,111 @@
+from __future__ import annotations
+
+import json
+import os
+import time
+from collections.abc import Generator
+from contextlib import contextmanager
+from datetime import UTC, datetime
+from pathlib import Path
+
+from pydantic import ValidationError
+
+from universal_memory.domain import StorageError
+from universal_memory.domain.entities import AuditEvent, AuditEventScope
+from universal_memory.domain.ports import AuditLogRepository
+
+
+class LocalAuditLogRepository(AuditLogRepository):
+    def __init__(self, *, project_root: Path, data_root: Path) -> None:
+        self.project_root = project_root
+        self.data_root = data_root
+        self.audit_root = self.data_root / "audit"
+        self.events_path = self.audit_root / "events.jsonl"
+
+    @contextmanager
+    def _lock(self) -> Generator[None, None, None]:
+        lock_path = self.events_path.with_suffix(".jsonl.lock")
+        self.audit_root.mkdir(parents=True, exist_ok=True)
+
+        max_attempts = 20
+        delay = 0.1
+        acquired = False
+        fd: int | None = None
+        try:
+            for _ in range(max_attempts):
+                try:
+                    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
+                    acquired = True
+                    break
+                except FileExistsError:
+                    time.sleep(delay)
+            if not acquired:
+                raise StorageError("Failed to acquire lock on audit log")
+            yield
+        finally:
+            if fd is not None:
+                try:
+                    os.close(fd)
+                except OSError:
+                    pass
+            if acquired:
+                try:
+                    os.unlink(lock_path)
+                except OSError:
+                    pass
+
+    def read(self, id: str) -> AuditEvent:
+        for event in self._load_events():
+            if event.id == id:
+                return event
+        raise StorageError(f"Audit event not found: {id}")
+
+    def list(self, scope: AuditEventScope | None = None) -> list[AuditEvent]:
+        events = self._load_events()
+        if scope is not None:
+            events = [event for event in events if event.scope == scope]
+        return sorted(events, key=lambda event: self._normalize_datetime(event.timestamp))
+
+    def write(self, entity: AuditEvent) -> None:
+        payload = self._render_event(entity)
+        try:
+            with self._lock():
+                with self.events_path.open("a", encoding="utf-8") as stream:
+                    stream.write(f"{payload}\n")
+                    stream.flush()
+                    os.fsync(stream.fileno())
+        except StorageError:
+            raise
+        except OSError as exc:
+            raise StorageError("Failed to write audit log") from exc
+
+    def migrate(self, target_version: int) -> None:
+        if target_version != 1:
+            raise StorageError(f"Unsupported audit repository schema version: {target_version}")
+
+    def _load_events(self) -> list[AuditEvent]:
+        if not self.events_path.exists():
+            return []
+        try:
+            events: list[AuditEvent] = []
+            for line in self.events_path.read_text(encoding="utf-8").splitlines():
+                if not line.strip():
+                    continue
+                events.append(AuditEvent.model_validate(json.loads(line)))
+            return events
+        except (OSError, json.JSONDecodeError, ValidationError) as exc:
+            raise StorageError("Failed to read audit log") from exc
+
+    @staticmethod
+    def _render_event(entity: AuditEvent) -> str:
+        payload = entity.model_dump(mode="json")
+        for key, value in payload.items():
+            if isinstance(value, str) and value.endswith("+00:00"):
+                payload[key] = value.removesuffix("+00:00") + "Z"
+        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
+
+    @staticmethod
+    def _normalize_datetime(dt: datetime) -> datetime:
+        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
+            return dt.replace(tzinfo=UTC)
+        return dt
diff --git a/tests/application/security/test_safe_write_use_case.py b/tests/application/security/test_safe_write_use_case.py
new file mode 100644
index 0000000..b13da7a
--- /dev/null
+++ b/tests/application/security/test_safe_write_use_case.py
@@ -0,0 +1,224 @@
+from __future__ import annotations
+
+import os
+from hashlib import sha256
+from pathlib import Path
+
+import pytest
+
+from universal_memory.application.security.safe_write_use_case import (
+    SafeWriteCommand,
+    SafeWriteUseCase,
+)
+from universal_memory.domain import SecretDetectedError, SnapshotFailedError
+from universal_memory.domain.entities import AuditEvent, AuditEventScope, Snapshot
+from universal_memory.domain.ports import AuditLogRepository, SecretScannerPort, SnapshotRepository
+
+
+class RecordingScanner(SecretScannerPort):
+    def __init__(self, error: Exception | None = None) -> None:
+        self.error = error
+        self.scanned: list[str] = []
+
+    def scan(self, content: str, *, origin: str | None = None) -> None:
+        self.scanned.append(f"{origin}:{content}")
+        if self.error is not None:
+            raise self.error
+
+
+class RecordingSnapshotRepository(SnapshotRepository):
+    def __init__(self, error: Exception | None = None) -> None:
+        self.error = error
+        self.written: list[Snapshot] = []
+
+    def read(self, id: str) -> Snapshot:
+        raise KeyError(id)
+
+    def list(self, scope=None, status=None) -> list[Snapshot]:
+        return self.written
+
+    def write(self, entity: Snapshot) -> None:
+        if self.error is not None:
+            raise self.error
+        self.written.append(entity)
+
+    def migrate(self, target_version: int) -> None:
+        return None
+
+
+class RecordingAuditRepository(AuditLogRepository):
+    def __init__(self) -> None:
+        self.written: list[AuditEvent] = []
+
+    def read(self, id: str) -> AuditEvent:
+        for event in self.written:
+            if event.id == id:
+                return event
+        raise KeyError(id)
+
+    def list(self, scope=None) -> list[AuditEvent]:
+        return self.written
+
+    def write(self, entity: AuditEvent) -> None:
+        self.written.append(entity)
+
+    def migrate(self, target_version: int) -> None:
+        return None
+
+
+def build_use_case(
+    *,
+    project_root: Path,
+    scanner: RecordingScanner | None = None,
+    snapshots: RecordingSnapshotRepository | None = None,
+    audit: RecordingAuditRepository | None = None,
+) -> tuple[
+    SafeWriteUseCase,
+    RecordingScanner,
+    RecordingSnapshotRepository,
+    RecordingAuditRepository,
+]:
+    resolved_scanner = scanner or RecordingScanner()
+    resolved_snapshots = snapshots or RecordingSnapshotRepository()
+    resolved_audit = audit or RecordingAuditRepository()
+    return (
+        SafeWriteUseCase(
+            project_root=project_root,
+            secret_scanner=resolved_scanner,
+            snapshot_repository=resolved_snapshots,
+            audit_log_repository=resolved_audit,
+        ),
+        resolved_scanner,
+        resolved_snapshots,
+        resolved_audit,
+    )
+
+
+def test_safe_write_validates_scans_snapshots_writes_atomically_and_audits_success(
+    tmp_path: Path,
+) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    previous = b"old state\n"
+    target.parent.mkdir(parents=True)
+    target.write_bytes(previous)
+    use_case, scanner, snapshots, audit = build_use_case(project_root=tmp_path)
+
+    result = use_case.execute(
+        SafeWriteCommand(
+            relative_path=".umem/memory/facts.jsonl",
+            content="new state\n",
+            scope=AuditEventScope.project,
+            origin="cli",
+            action="remember_fact",
+        )
+    )
+
+    assert scanner.scanned == ["cli:new state\n"]
+    assert target.read_text(encoding="utf-8") == "new state\n"
+    assert snapshots.written[0].relative_path == ".umem/memory/facts.jsonl"
+    assert snapshots.written[0].hash == sha256(previous).hexdigest()
+    assert audit.written[0].result == "success"
+    assert audit.written[0].snapshot_reference == snapshots.written[0].id
+    assert result.audit_reference == audit.written[0].audit_reference
+    assert not list(target.parent.glob("*.tmp"))
+
+
+def test_secret_detection_aborts_before_snapshot_or_write(tmp_path: Path) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_text("old state\n", encoding="utf-8")
+    use_case, _scanner, snapshots, audit = build_use_case(
+        project_root=tmp_path,
+        scanner=RecordingScanner(SecretDetectedError("blocked", metadata={"span": (0, 6)})),
+    )
+
+    with pytest.raises(SecretDetectedError):
+        use_case.execute(
+            SafeWriteCommand(
+                relative_path=".umem/memory/facts.jsonl",
+                content="secret",
+                scope=AuditEventScope.project,
+                origin="cli",
+                action="remember_fact",
+            )
+        )
+
+    assert target.read_text(encoding="utf-8") == "old state\n"
+    assert snapshots.written == []
+    assert audit.written == []
+
+
+def test_snapshot_failure_aborts_before_touching_original_file(tmp_path: Path) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_text("old state\n", encoding="utf-8")
+    use_case, _scanner, _snapshots, audit = build_use_case(
+        project_root=tmp_path,
+        snapshots=RecordingSnapshotRepository(SnapshotFailedError("snapshot unavailable")),
+    )
+
+    with pytest.raises(SnapshotFailedError):
+        use_case.execute(
+            SafeWriteCommand(
+                relative_path=".umem/memory/facts.jsonl",
+                content="new state\n",
+                scope=AuditEventScope.project,
+                origin="cli",
+                action="remember_fact",
+            )
+        )
+
+    assert target.read_text(encoding="utf-8") == "old state\n"
+    assert audit.written == []
+
+
+def test_atomic_write_failure_cleans_temp_file_and_audits_failure(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_text("old state\n", encoding="utf-8")
+    use_case, _scanner, snapshots, audit = build_use_case(project_root=tmp_path)
+
+    def fail_replace(source: Path | str, destination: Path | str) -> None:
+        source_path = Path(source)
+        if source_path.suffix == ".tmp":
+            raise OSError("disk full")
+        os.replace(source, destination)
+
+    monkeypatch.setattr(os, "replace", fail_replace)
+
+    with pytest.raises(OSError, match="disk full"):
+        use_case.execute(
+            SafeWriteCommand(
+                relative_path=".umem/memory/facts.jsonl",
+                content="new state\n",
+                scope=AuditEventScope.project,
+                origin="cli",
+                action="remember_fact",
+            )
+        )
+
+    assert target.read_text(encoding="utf-8") == "old state\n"
+    assert snapshots.written
+    assert audit.written[0].result == "failure"
+    assert audit.written[0].status == "failed"
+    assert not list(target.parent.glob("*.tmp"))
+
+
+def test_rejects_absolute_or_traversal_paths(tmp_path: Path) -> None:
+    use_case, _scanner, snapshots, audit = build_use_case(project_root=tmp_path)
+
+    with pytest.raises(ValueError, match="relative_path"):
+        use_case.execute(
+            SafeWriteCommand(
+                relative_path="../outside.txt",
+                content="content",
+                scope=AuditEventScope.project,
+                origin="cli",
+                action="write",
+            )
+        )
+
+    assert snapshots.written == []
+    assert audit.written == []
diff --git a/tests/infrastructure/security/test_local_audit_log_repository.py b/tests/infrastructure/security/test_local_audit_log_repository.py
new file mode 100644
index 0000000..b65c909
--- /dev/null
+++ b/tests/infrastructure/security/test_local_audit_log_repository.py
@@ -0,0 +1,117 @@
+import json
+import os
+import threading
+from datetime import UTC, datetime, timedelta
+from pathlib import Path
+from uuid import uuid4
+
+import pytest
+
+from universal_memory.domain import StorageError
+from universal_memory.domain.entities import AuditEvent, AuditEventScope
+from universal_memory.infrastructure.security import LocalAuditLogRepository
+
+CONCURRENT_EVENT_COUNT = 40
+
+
+def make_audit_event(
+    *,
+    scope: AuditEventScope = AuditEventScope.project,
+    created_at: datetime | None = None,
+    action: str = "safe-write",
+    result: str = "success",
+) -> AuditEvent:
+    timestamp = created_at or datetime.now(UTC)
+    audit_reference = str(uuid4())
+    return AuditEvent(
+        id=audit_reference,
+        created_at=timestamp,
+        updated_at=timestamp,
+        timestamp=timestamp,
+        action=action,
+        scope=scope,
+        origin="test",
+        result=result,
+        snapshot_reference=str(uuid4()),
+        audit_reference=audit_reference,
+        status="logged",
+    )
+
+
+def test_write_appends_event_as_jsonl(tmp_path: Path) -> None:
+    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
+    event = make_audit_event()
+
+    repository.write(event)
+
+    events_path = tmp_path / ".umem" / "audit" / "events.jsonl"
+    lines = events_path.read_text(encoding="utf-8").splitlines()
+    assert len(lines) == 1
+    payload = json.loads(lines[0])
+    assert payload["id"] == event.id
+    assert payload["audit_reference"] == event.audit_reference
+    assert payload["timestamp"].endswith("Z")
+    assert repository.read(event.id) == event
+
+
+def test_list_filters_by_scope_and_read_returns_events_ordered_by_timestamp(
+    tmp_path: Path,
+) -> None:
+    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
+    base = datetime(2026, 5, 26, tzinfo=UTC)
+    older = make_audit_event(scope=AuditEventScope.project, created_at=base)
+    global_event = make_audit_event(
+        scope=AuditEventScope.global_, created_at=base + timedelta(minutes=1)
+    )
+    newer = make_audit_event(
+        scope=AuditEventScope.project, created_at=base + timedelta(minutes=2)
+    )
+
+    repository.write(newer)
+    repository.write(global_event)
+    repository.write(older)
+
+    assert repository.list(scope=AuditEventScope.project) == [older, newer]
+    assert repository.read(global_event.id) == global_event
+
+
+def test_concurrent_writes_preserve_all_jsonl_events(tmp_path: Path) -> None:
+    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
+    events = [make_audit_event() for _ in range(CONCURRENT_EVENT_COUNT)]
+
+    threads = [threading.Thread(target=repository.write, args=(event,)) for event in events]
+    for thread in threads:
+        thread.start()
+    for thread in threads:
+        thread.join()
+
+    stored = repository.list(scope=AuditEventScope.project)
+    assert {event.id for event in stored} == {event.id for event in events}
+    assert (
+        len((tmp_path / ".umem" / "audit" / "events.jsonl").read_text().splitlines())
+        == CONCURRENT_EVENT_COUNT
+    )
+
+
+def test_write_fails_with_typed_error_when_lock_cannot_be_acquired(tmp_path: Path) -> None:
+    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
+    lock_path = tmp_path / ".umem" / "audit" / "events.jsonl.lock"
+    lock_path.parent.mkdir(parents=True, exist_ok=True)
+    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
+
+    try:
+        with pytest.raises(StorageError, match="Failed to acquire lock"):
+            repository.write(make_audit_event())
+    finally:
+        os.close(fd)
+        os.unlink(lock_path)
+
+
+def test_corrupted_log_raises_typed_storage_error(tmp_path: Path) -> None:
+    repository = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")
+    events_path = tmp_path / ".umem" / "audit" / "events.jsonl"
+    events_path.parent.mkdir(parents=True, exist_ok=True)
+    events_path.write_text("{not-json}\n", encoding="utf-8")
+
+    with pytest.raises(StorageError, match="Failed to read audit log"):
+        repository.list()
diff --git a/tests/interfaces/test_adapter_mutation_guardrails.py b/tests/interfaces/test_adapter_mutation_guardrails.py
new file mode 100644
index 0000000..8a44bec
--- /dev/null
+++ b/tests/interfaces/test_adapter_mutation_guardrails.py
@@ -0,0 +1,38 @@
+import ast
+from pathlib import Path
+
+DIRECT_MUTATION_CALLS = {
+    "open",
+    "replace",
+    "rename",
+    "write",
+    "write_bytes",
+    "write_text",
+}
+
+
+def test_interface_adapters_do_not_bypass_safe_write_use_case_for_mutations() -> None:
+    interface_files = [
+        path
+        for path in Path("src/universal_memory/interfaces").rglob("*.py")
+        if "__pycache__" not in path.parts
+    ]
+
+    violations: list[str] = []
+    for path in interface_files:
+        tree = ast.parse(path.read_text(encoding="utf-8"))
+        for node in ast.walk(tree):
+            if isinstance(node, ast.Call):
+                name = _call_name(node.func)
+                if name in DIRECT_MUTATION_CALLS:
+                    violations.append(f"{path}:{node.lineno}:{name}")
+
+    assert violations == []
+
+
+def _call_name(node: ast.expr) -> str | None:
+    if isinstance(node, ast.Name):
+        return node.id
+    if isinstance(node, ast.Attribute):
+        return node.attr
+    return None
```
