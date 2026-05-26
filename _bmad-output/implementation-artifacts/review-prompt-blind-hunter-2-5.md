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
index 3a86e40..63b50a7 100644
--- a/src/universal_memory/application/security/__init__.py
+++ b/src/universal_memory/application/security/__init__.py
@@ -12,6 +12,11 @@ from universal_memory.application.security.list_snapshots_use_case import (
     ListSnapshotsUseCase,
     SnapshotEntry,
 )
+from universal_memory.application.security.rollback_use_case import (
+    RollbackCommand,
+    RollbackResult,
+    RollbackUseCase,
+)
 from universal_memory.application.security.safe_write_use_case import (
     SafeWriteCommand,
     SafeWriteResult,
@@ -26,6 +31,9 @@ __all__ = [
     "ListSnapshotsCommand",
     "ListSnapshotsResult",
     "ListSnapshotsUseCase",
+    "RollbackCommand",
+    "RollbackResult",
+    "RollbackUseCase",
     "SafeWriteCommand",
     "SafeWriteResult",
     "SafeWriteUseCase",
diff --git a/src/universal_memory/application/security/rollback_use_case.py b/src/universal_memory/application/security/rollback_use_case.py
new file mode 100644
index 0000000..c141156
--- /dev/null
+++ b/src/universal_memory/application/security/rollback_use_case.py
@@ -0,0 +1,156 @@
+from __future__ import annotations
+
+import os
+from dataclasses import dataclass
+from datetime import UTC, datetime
+from hashlib import sha256
+from pathlib import Path
+from uuid import uuid4
+
+from universal_memory.domain import SnapshotFailedError
+from universal_memory.domain.entities import (
+    AuditEvent,
+    AuditEventScope,
+    Snapshot,
+    SnapshotScope,
+    SnapshotStatus,
+)
+from universal_memory.domain.ports import AuditLogRepository, SnapshotRepository
+
+
+@dataclass(frozen=True, slots=True)
+class RollbackCommand:
+    scope: SnapshotScope
+    origin: str
+    action: str = "rollback"
+
+
+@dataclass(frozen=True, slots=True)
+class RollbackResult:
+    scope: SnapshotScope
+    snapshot_reference: str
+    restored_paths: list[str]
+    audit_reference: str
+
+
+class RollbackUseCase:
+    def __init__(
+        self,
+        *,
+        project_root: Path,
+        snapshot_repository: SnapshotRepository,
+        audit_log_repository: AuditLogRepository,
+    ) -> None:
+        self.project_root = project_root.resolve()
+        self.snapshot_repository = snapshot_repository
+        self.audit_log_repository = audit_log_repository
+
+    def execute(self, command: RollbackCommand) -> RollbackResult:
+        snapshots = self.snapshot_repository.list(
+            scope=command.scope,
+            status=SnapshotStatus.created,
+        )
+        if not snapshots:
+            raise SnapshotFailedError(
+                "Nenhum snapshot encontrado para o escopo solicitado. "
+                "Hint: execute uma mutacao segura antes de tentar rollback."
+            )
+
+        snapshot = max(snapshots, key=lambda item: self._normalize_datetime(item.timestamp))
+        content = self.snapshot_repository.get_content(snapshot.id)
+        actual_hash = sha256(content).hexdigest()
+        if actual_hash != snapshot.hash:
+            self._record_audit(
+                command,
+                snapshot_reference=snapshot.id,
+                result="failure",
+                status="failed",
+            )
+            raise SnapshotFailedError(
+                "Falha de integridade do snapshot: hash SHA-256 do backup fisico "
+                "nao corresponde ao manifesto. Hint: inspecione os snapshots e recrie "
+                "o estado a partir de um backup confiavel."
+            )
+
+        target_path = self._resolve_target(snapshot)
+        try:
+            self._atomic_write_bytes(target_path, content)
+        except BaseException:
+            self._record_audit(
+                command,
+                snapshot_reference=snapshot.id,
+                result="failure",
+                status="failed",
+            )
+            raise
+
+        event = self._record_audit(
+            command,
+            snapshot_reference=snapshot.id,
+            result="success",
+            status="logged",
+        )
+        return RollbackResult(
+            scope=command.scope,
+            snapshot_reference=snapshot.id,
+            restored_paths=[snapshot.relative_path],
+            audit_reference=event.audit_reference,
+        )
+
+    def _resolve_target(self, snapshot: Snapshot) -> Path:
+        target_path = self.project_root / snapshot.relative_path
+        try:
+            target_path.resolve().relative_to(self.project_root)
+        except ValueError as exc:
+            raise SnapshotFailedError("Snapshot target path escapes project root") from exc
+        if target_path.exists() and not target_path.is_file():
+            raise SnapshotFailedError("Snapshot target path is not a file")
+        return target_path
+
+    def _atomic_write_bytes(self, target_path: Path, content: bytes) -> None:
+        target_path.parent.mkdir(parents=True, exist_ok=True)
+        temp_path = target_path.with_name(f"{target_path.name}.{uuid4()}.tmp")
+        try:
+            temp_path.write_bytes(content)
+            os.replace(temp_path, target_path)
+        except BaseException:
+            temp_path.unlink(missing_ok=True)
+            raise
+
+    def _record_audit(
+        self,
+        command: RollbackCommand,
+        *,
+        snapshot_reference: str,
+        result: str,
+        status: str,
+    ) -> AuditEvent:
+        timestamp = datetime.now(UTC)
+        audit_reference = str(uuid4())
+        event = AuditEvent(
+            id=audit_reference,
+            created_at=timestamp,
+            updated_at=timestamp,
+            timestamp=timestamp,
+            action=command.action,
+            scope=self._audit_scope(command.scope),
+            origin=command.origin,
+            result=result,
+            snapshot_reference=snapshot_reference,
+            audit_reference=audit_reference,
+            status=status,
+        )
+        self.audit_log_repository.write(event)
+        return event
+
+    @staticmethod
+    def _audit_scope(scope: SnapshotScope) -> AuditEventScope:
+        if scope == SnapshotScope.global_:
+            return AuditEventScope.global_
+        return AuditEventScope.project
+
+    @staticmethod
+    def _normalize_datetime(dt: datetime) -> datetime:
+        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
+            return dt.replace(tzinfo=UTC)
+        return dt
diff --git a/src/universal_memory/bootstrap/cli.py b/src/universal_memory/bootstrap/cli.py
index 6dc6a24..8b5c336 100644
--- a/src/universal_memory/bootstrap/cli.py
+++ b/src/universal_memory/bootstrap/cli.py
@@ -1,7 +1,13 @@
 from collections.abc import Sequence
 from pathlib import Path
 
-from universal_memory.application.security import ListAuditLogUseCase, ListSnapshotsUseCase
+from universal_memory.application.security import (
+    ListAuditLogUseCase,
+    ListSnapshotsUseCase,
+    RollbackUseCase,
+)
+from universal_memory.domain import SnapshotFailedError
+from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
 from universal_memory.infrastructure.config import (
     LocalConfigValidationPort,
     LocalProjectLayoutPort,
@@ -25,16 +31,34 @@ def main(argv: Sequence[str] | None = None) -> int:
     manifest_file = data_root / "snapshots" / "manifest.json"
     manifest_rel_path = str(manifest_file.relative_to(project_root))
     snapshots_list_use_case = ListSnapshotsUseCase(
-        snapshot_repository=LocalSnapshotRepository(
+        snapshot_repository=LocalSnapshotRepository(project_root=project_root, data_root=data_root),
+        manifest_path=manifest_rel_path,
+    )
+    snapshot_repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
+    rollback_use_case = RollbackUseCase(
+        project_root=project_root,
+        snapshot_repository=snapshot_repository,
+        audit_log_repository=LocalAuditLogRepository(
             project_root=project_root,
             data_root=data_root,
         ),
-        manifest_path=manifest_rel_path,
     )
+
+    def rollback_preview(scope: SnapshotScope) -> Snapshot:
+        snapshots = snapshot_repository.list(scope=scope, status=SnapshotStatus.created)
+        if not snapshots:
+            raise SnapshotFailedError(
+                "Nenhum snapshot encontrado para o escopo solicitado. "
+                "Hint: execute uma mutacao segura antes de tentar rollback."
+            )
+        return max(snapshots, key=lambda snapshot: snapshot.timestamp)
+
     configured_main = build_main(
         layout_port=LocalProjectLayoutPort(),
         config_validation_port=LocalConfigValidationPort(),
         audit_list_command=audit_list_use_case.execute,
         snapshots_list_command=snapshots_list_use_case.execute,
+        rollback_command=rollback_use_case.execute,
+        rollback_preview_command=rollback_preview,
     )
     return configured_main(argv)
diff --git a/src/universal_memory/domain/ports/snapshot_repository.py b/src/universal_memory/domain/ports/snapshot_repository.py
index ffda3e3..8dcb50e 100644
--- a/src/universal_memory/domain/ports/snapshot_repository.py
+++ b/src/universal_memory/domain/ports/snapshot_repository.py
@@ -19,6 +19,21 @@ class SnapshotRepository(ABC):
         """
         ...
 
+    @abstractmethod
+    def get_content(self, id: str) -> bytes:
+        """Read the physical backup bytes associated with a snapshot ID.
+
+        Args:
+            id: The unique identifier of the snapshot backup file.
+
+        Returns:
+            The backed up file content.
+
+        Raises:
+            UniversalMemoryError: If the backup file cannot be read.
+        """
+        ...
+
     @abstractmethod
     def list(
         self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None
diff --git a/src/universal_memory/infrastructure/security/local_snapshot_repository.py b/src/universal_memory/infrastructure/security/local_snapshot_repository.py
index 061f7d6..f1fe476 100644
--- a/src/universal_memory/infrastructure/security/local_snapshot_repository.py
+++ b/src/universal_memory/infrastructure/security/local_snapshot_repository.py
@@ -84,6 +84,15 @@ class LocalSnapshotRepository(SnapshotRepository):
                 return snapshot
         raise StorageError(f"Snapshot not found: {id}")
 
+    def get_content(self, id: str) -> bytes:
+        backup_path = self.files_root / id
+        try:
+            return backup_path.read_bytes()
+        except FileNotFoundError as exc:
+            raise StorageError(f"Snapshot backup file not found: {id}") from exc
+        except OSError as exc:
+            raise StorageError(f"Failed to read snapshot backup file: {id}") from exc
+
     def list(
         self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None
     ) -> list[Snapshot]:
diff --git a/src/universal_memory/interfaces/cli/init_command.py b/src/universal_memory/interfaces/cli/init_command.py
index bb17fc7..45c2e0a 100644
--- a/src/universal_memory/interfaces/cli/init_command.py
+++ b/src/universal_memory/interfaces/cli/init_command.py
@@ -17,16 +17,20 @@ from universal_memory.application.security import (
     ListAuditLogResult,
     ListSnapshotsCommand,
     ListSnapshotsResult,
+    RollbackCommand,
+    RollbackResult,
 )
 from universal_memory.domain import (
     ConfigValidationPort,
     InvalidConfigError,
     ProjectLayoutPort,
+    SnapshotFailedError,
     StorageError,
     ValidationFailedError,
 )
 from universal_memory.domain.entities import (
     AuditEventScope,
+    Snapshot,
     SnapshotScope,
     SnapshotStatus,
 )
@@ -35,14 +39,18 @@ AUDIT_REFERENCE_PLACEHOLDER = "not-implemented-yet"
 SetupProjectCommand = Callable[[Path], SetupProjectResult]
 ListAuditLogCommandHandler = Callable[[ListAuditLogCommand], ListAuditLogResult]
 ListSnapshotsCommandHandler = Callable[[ListSnapshotsCommand], ListSnapshotsResult]
+RollbackCommandHandler = Callable[[RollbackCommand], RollbackResult]
+RollbackPreviewHandler = Callable[[SnapshotScope], Snapshot]
 
 
-def main(
+def main(  # noqa: PLR0913
     argv: Sequence[str] | None = None,
     *,
     setup_project_command: SetupProjectCommand | None = None,
     audit_list_command: ListAuditLogCommandHandler | None = None,
     snapshots_list_command: ListSnapshotsCommandHandler | None = None,
+    rollback_command: RollbackCommandHandler | None = None,
+    rollback_preview_command: RollbackPreviewHandler | None = None,
 ) -> int:
     parser = _build_parser()
     args = parser.parse_args(argv)
@@ -74,16 +82,33 @@ def main(
             scope=_snapshot_scope(args.scope),
         )
 
+    if args.command == "rollback":
+        if rollback_command is None:
+            msg = "CLI rollback_command dependency was not configured."
+            raise RuntimeError(msg)
+        if rollback_preview_command is None:
+            msg = "CLI rollback_preview_command dependency was not configured."
+            raise RuntimeError(msg)
+        return _run_rollback(
+            rollback_command,
+            rollback_preview_command=rollback_preview_command,
+            output_format=args.output_format,
+            scope=_snapshot_scope(args.scope),
+            yes=args.yes,
+        )
+
     parser.print_help()
     return 0
 
 
-def build_main(
+def build_main(  # noqa: PLR0913
     *,
     layout_port: ProjectLayoutPort,
     config_validation_port: ConfigValidationPort,
     audit_list_command: ListAuditLogCommandHandler,
     snapshots_list_command: ListSnapshotsCommandHandler,
+    rollback_command: RollbackCommandHandler,
+    rollback_preview_command: RollbackPreviewHandler,
 ) -> Callable[[Sequence[str] | None], int]:
     command = _build_setup_project_command(
         layout_port=layout_port,
@@ -96,6 +121,8 @@ def build_main(
             setup_project_command=command,
             audit_list_command=audit_list_command,
             snapshots_list_command=snapshots_list_command,
+            rollback_command=rollback_command,
+            rollback_preview_command=rollback_preview_command,
         )
 
     return configured_main
@@ -148,6 +175,27 @@ def _build_parser() -> argparse.ArgumentParser:
         help="Scope filter",
     )
 
+    rollback_parser = subparsers.add_parser("rollback", help="Restore latest snapshot")
+    rollback_parser.add_argument(
+        "--format",
+        choices=["human", "json"],
+        default="human",
+        dest="output_format",
+        help="Output format",
+    )
+    rollback_parser.add_argument(
+        "--scope",
+        choices=["project", "global"],
+        default="project",
+        help="Scope to roll back",
+    )
+    rollback_parser.add_argument(
+        "--yes",
+        "-y",
+        action="store_true",
+        help="Skip interactive confirmation",
+    )
+
     return parser
 
 
@@ -237,6 +285,40 @@ def _run_snapshots_list(
     return 0
 
 
+def _run_rollback(
+    command: RollbackCommandHandler,
+    *,
+    rollback_preview_command: RollbackPreviewHandler,
+    output_format: str,
+    scope: SnapshotScope,
+    yes: bool,
+) -> int:
+    try:
+        preview = rollback_preview_command(scope)
+        if output_format != "json":
+            print(_format_human_rollback_preview(preview))
+            if not yes:
+                answer = input("Deseja prosseguir com o rollback? [s/N]: ")
+                if answer.strip().lower() not in {"s", "sim", "y", "yes"}:
+                    print("Rollback cancelado.")
+                    return 1
+
+        result = command(RollbackCommand(scope=scope, origin="cli"))
+    except OSError as error:
+        _print_expected_error(StorageError(str(error)), output_format=output_format)
+        return 1
+    except (SnapshotFailedError, StorageError, ValidationFailedError) as error:
+        _print_expected_error(error, output_format=output_format)
+        return 1
+
+    if output_format == "json":
+        print(json.dumps(_rollback_success_envelope(result), sort_keys=True))
+    else:
+        print(_format_human_rollback_success(result))
+
+    return 0
+
+
 def _success_envelope(result: SetupProjectResult) -> dict[str, Any]:
     return {
         "ok": True,
@@ -271,6 +353,21 @@ def _snapshots_success_envelope(
     }
 
 
+def _rollback_success_envelope(result: RollbackResult) -> dict[str, Any]:
+    return {
+        "ok": True,
+        "operation": "rollback",
+        "scope": result.scope.value,
+        "data": {
+            "scope": result.scope.value,
+            "snapshot_reference": result.snapshot_reference,
+            "restored_paths": result.restored_paths,
+            "audit_reference": result.audit_reference,
+        },
+        "warnings": [],
+    }
+
+
 def _init_payload(result: SetupProjectResult) -> dict[str, Any]:
     return {
         "project_path": _path_to_posix(result.project_path),
@@ -347,6 +444,31 @@ def _format_human_snapshots_output(result: ListSnapshotsResult) -> str:
     return "\n".join(lines)
 
 
+def _format_human_rollback_preview(snapshot: Snapshot) -> str:
+    return "\n".join(
+        [
+            "Rollback selecionado:",
+            f"Escopo: {snapshot.scope.value}",
+            f"Snapshot: {snapshot.id}",
+            f"Timestamp: {snapshot.timestamp.isoformat()}",
+            f"Acao original: {snapshot.action}",
+            f"Arquivo: {snapshot.relative_path}",
+        ]
+    )
+
+
+def _format_human_rollback_success(result: RollbackResult) -> str:
+    return "\n".join(
+        [
+            "Rollback concluido.",
+            f"Escopo: {result.scope.value}",
+            f"Snapshot: {result.snapshot_reference}",
+            f"Arquivos restaurados: {', '.join(result.restored_paths)}",
+            f"Auditoria: {result.audit_reference}",
+        ]
+    )
+
+
 def _print_expected_error(error: Exception, output_format: str) -> None:
     code = _error_code(error)
     detail = str(error)
@@ -378,6 +500,8 @@ def _print_expected_error(error: Exception, output_format: str) -> None:
 
 
 def _error_code(error: Exception) -> str:
+    if isinstance(error, SnapshotFailedError):
+        return "snapshot_failed"
     if isinstance(error, InvalidConfigError):
         return "invalid_config"
     if isinstance(error, ValidationFailedError):
@@ -386,6 +510,8 @@ def _error_code(error: Exception) -> str:
 
 
 def _error_message(error: Exception) -> str:
+    if isinstance(error, SnapshotFailedError):
+        return "Falha de snapshot."
     if isinstance(error, InvalidConfigError):
         return "Configuracao invalida."
     if isinstance(error, ValidationFailedError):
diff --git a/tests/application/security/test_list_snapshots_use_case.py b/tests/application/security/test_list_snapshots_use_case.py
index afd4621..73f0a3d 100644
--- a/tests/application/security/test_list_snapshots_use_case.py
+++ b/tests/application/security/test_list_snapshots_use_case.py
@@ -20,6 +20,9 @@ class RecordingSnapshotRepository(SnapshotRepository):
     def read(self, id: str) -> Snapshot:
         raise KeyError(id)
 
+    def get_content(self, id: str) -> bytes:
+        raise KeyError(id)
+
     def list(
         self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None
     ) -> list[Snapshot]:
diff --git a/tests/application/security/test_rollback_use_case.py b/tests/application/security/test_rollback_use_case.py
new file mode 100644
index 0000000..6f84a64
--- /dev/null
+++ b/tests/application/security/test_rollback_use_case.py
@@ -0,0 +1,208 @@
+from __future__ import annotations
+
+from datetime import UTC, datetime, timedelta
+from hashlib import sha256
+from pathlib import Path
+from uuid import uuid4
+
+import pytest
+
+from universal_memory.application.security.rollback_use_case import (
+    RollbackCommand,
+    RollbackUseCase,
+)
+from universal_memory.domain import SnapshotFailedError
+from universal_memory.domain.entities import (
+    AuditEvent,
+    Snapshot,
+    SnapshotScope,
+    SnapshotStatus,
+)
+from universal_memory.domain.ports import AuditLogRepository, SnapshotRepository
+
+
+class RecordingSnapshotRepository(SnapshotRepository):
+    def __init__(self, snapshots: list[Snapshot], content_by_id: dict[str, bytes]) -> None:
+        self.snapshots = snapshots
+        self.content_by_id = content_by_id
+
+    def read(self, id: str) -> Snapshot:
+        for snapshot in self.snapshots:
+            if snapshot.id == id:
+                return snapshot
+        raise KeyError(id)
+
+    def get_content(self, id: str) -> bytes:
+        return self.content_by_id[id]
+
+    def list(self, scope=None, status=None) -> list[Snapshot]:
+        snapshots = self.snapshots
+        if scope is not None:
+            snapshots = [snapshot for snapshot in snapshots if snapshot.scope == scope]
+        if status is not None:
+            snapshots = [snapshot for snapshot in snapshots if snapshot.status == status]
+        return snapshots
+
+    def write(self, entity: Snapshot) -> None:
+        self.snapshots.append(entity)
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
+def make_snapshot(
+    *,
+    content: bytes,
+    created_at: datetime,
+    scope: SnapshotScope = SnapshotScope.project,
+    relative_path: str = ".umem/memory/facts.jsonl",
+    action: str = "safe_write",
+) -> Snapshot:
+    return Snapshot(
+        id=str(uuid4()),
+        created_at=created_at,
+        updated_at=created_at,
+        timestamp=created_at,
+        scope=scope,
+        origin="cli",
+        action=action,
+        relative_path=relative_path,
+        hash=sha256(content).hexdigest(),
+        status=SnapshotStatus.created,
+    )
+
+
+def test_rollback_restores_latest_snapshot_for_scope_and_audits_success(
+    tmp_path: Path,
+) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_bytes(b"current state\n")
+    base_time = datetime(2026, 5, 26, tzinfo=UTC)
+    older = make_snapshot(content=b"older state\n", created_at=base_time)
+    newer = make_snapshot(content=b"restored state\n", created_at=base_time + timedelta(minutes=2))
+    global_snapshot = make_snapshot(
+        content=b"global state\n",
+        created_at=base_time + timedelta(minutes=5),
+        scope=SnapshotScope.global_,
+    )
+    snapshots = RecordingSnapshotRepository(
+        [global_snapshot, older, newer],
+        {
+            older.id: b"older state\n",
+            newer.id: b"restored state\n",
+            global_snapshot.id: b"global state\n",
+        },
+    )
+    audit = RecordingAuditRepository()
+    use_case = RollbackUseCase(
+        project_root=tmp_path,
+        snapshot_repository=snapshots,
+        audit_log_repository=audit,
+    )
+
+    result = use_case.execute(
+        RollbackCommand(scope=SnapshotScope.project, origin="cli", action="rollback")
+    )
+
+    assert target.read_bytes() == b"restored state\n"
+    assert result.scope == SnapshotScope.project
+    assert result.snapshot_reference == newer.id
+    assert result.restored_paths == [".umem/memory/facts.jsonl"]
+    assert result.audit_reference == audit.written[0].audit_reference
+    assert audit.written[0].action == "rollback"
+    assert audit.written[0].result == "success"
+    assert audit.written[0].status == "logged"
+    assert audit.written[0].snapshot_reference == newer.id
+    assert not list(target.parent.glob("*.tmp"))
+
+
+def test_rollback_without_snapshots_raises_domain_error_without_side_effects(
+    tmp_path: Path,
+) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_bytes(b"current state\n")
+    audit = RecordingAuditRepository()
+    use_case = RollbackUseCase(
+        project_root=tmp_path,
+        snapshot_repository=RecordingSnapshotRepository([], {}),
+        audit_log_repository=audit,
+    )
+
+    with pytest.raises(SnapshotFailedError, match="Nenhum snapshot"):
+        use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))
+
+    assert target.read_bytes() == b"current state\n"
+    assert audit.written == []
+
+
+def test_rollback_blocks_hash_mismatch_before_write_and_audits_failure(
+    tmp_path: Path,
+) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_bytes(b"current state\n")
+    timestamp = datetime(2026, 5, 26, tzinfo=UTC)
+    snapshot = make_snapshot(content=b"expected state\n", created_at=timestamp)
+    audit = RecordingAuditRepository()
+    use_case = RollbackUseCase(
+        project_root=tmp_path,
+        snapshot_repository=RecordingSnapshotRepository(
+            [snapshot],
+            {snapshot.id: b"corrupted state\n"},
+        ),
+        audit_log_repository=audit,
+    )
+
+    with pytest.raises(SnapshotFailedError, match="integridade"):
+        use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))
+
+    assert target.read_bytes() == b"current state\n"
+    assert len(audit.written) == 1
+    assert audit.written[0].result == "failure"
+    assert audit.written[0].status == "failed"
+    assert audit.written[0].snapshot_reference == snapshot.id
+
+
+def test_rollback_is_offline_and_has_no_network_dependency(tmp_path: Path) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_bytes(b"current state\n")
+    snapshot = make_snapshot(
+        content=b"offline restore\n",
+        created_at=datetime(2026, 5, 26, tzinfo=UTC),
+    )
+    use_case = RollbackUseCase(
+        project_root=tmp_path,
+        snapshot_repository=RecordingSnapshotRepository(
+            [snapshot],
+            {snapshot.id: b"offline restore\n"},
+        ),
+        audit_log_repository=RecordingAuditRepository(),
+    )
+
+    result = use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))
+
+    assert result.snapshot_reference == snapshot.id
+    assert target.read_bytes() == b"offline restore\n"
diff --git a/tests/application/security/test_safe_write_use_case.py b/tests/application/security/test_safe_write_use_case.py
index f274d04..50fdf43 100644
--- a/tests/application/security/test_safe_write_use_case.py
+++ b/tests/application/security/test_safe_write_use_case.py
@@ -34,6 +34,9 @@ class RecordingSnapshotRepository(SnapshotRepository):
     def read(self, id: str) -> Snapshot:
         raise KeyError(id)
 
+    def get_content(self, id: str) -> bytes:
+        raise KeyError(id)
+
     def list(self, scope=None, status=None) -> list[Snapshot]:
         return self.written
 
diff --git a/tests/domain/test_ports.py b/tests/domain/test_ports.py
index 8d76505..1d85660 100644
--- a/tests/domain/test_ports.py
+++ b/tests/domain/test_ports.py
@@ -69,6 +69,7 @@ EXPECTED_METHODS: dict[PortType, MethodExpectations] = {
     },
     SnapshotRepository: {
         "read": (Snapshot, {"id": str}),
+        "get_content": (bytes, {"id": str}),
         "list": (list[Snapshot], {"scope": SnapshotScope | None, "status": SnapshotStatus | None}),
         "write": (type(None), {"entity": Snapshot}),
         "migrate": (type(None), {"target_version": int}),
diff --git a/tests/infrastructure/security/test_local_snapshot_repository.py b/tests/infrastructure/security/test_local_snapshot_repository.py
index 698f602..cffd26a 100644
--- a/tests/infrastructure/security/test_local_snapshot_repository.py
+++ b/tests/infrastructure/security/test_local_snapshot_repository.py
@@ -8,7 +8,7 @@ from uuid import uuid4
 
 import pytest
 
-from universal_memory.domain import SnapshotFailedError
+from universal_memory.domain import SnapshotFailedError, StorageError
 from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
 from universal_memory.infrastructure.security import LocalSnapshotRepository
 
@@ -53,6 +53,30 @@ def test_write_copies_existing_file_and_records_manifest_metadata(tmp_path: Path
     assert repository.list(scope=SnapshotScope.project, status=SnapshotStatus.created) == [snapshot]
 
 
+def test_get_content_reads_physical_backup_file(tmp_path: Path) -> None:
+    project_root = tmp_path / "workspace"
+    data_root = project_root / ".umem"
+    original = project_root / "memory" / "facts.jsonl"
+    content = b"previous state\n"
+    original.parent.mkdir(parents=True)
+    original.write_bytes(content)
+    repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
+    snapshot = make_snapshot(content=content)
+    repository.write(snapshot)
+
+    assert repository.get_content(snapshot.id) == content
+
+
+def test_get_content_raises_storage_error_when_backup_file_is_missing(tmp_path: Path) -> None:
+    project_root = tmp_path / "workspace"
+    repository = LocalSnapshotRepository(
+        project_root=project_root, data_root=project_root / ".umem"
+    )
+
+    with pytest.raises(StorageError, match="Snapshot backup file not found"):
+        repository.get_content(str(uuid4()))
+
+
 def test_write_records_initial_creation_without_physical_copy(tmp_path: Path) -> None:
     project_root = tmp_path / "workspace"
     repository = LocalSnapshotRepository(
@@ -238,4 +262,3 @@ def test_concurrency_lock_prevents_clash(tmp_path: Path) -> None:
 
     os.close(fd)
     os.unlink(lock_path)
-
diff --git a/tests/interfaces/cli/test_rollback_command.py b/tests/interfaces/cli/test_rollback_command.py
new file mode 100644
index 0000000..3132515
--- /dev/null
+++ b/tests/interfaces/cli/test_rollback_command.py
@@ -0,0 +1,143 @@
+from __future__ import annotations
+
+import json
+from datetime import UTC, datetime
+from hashlib import sha256
+from pathlib import Path
+from uuid import uuid4
+
+import pytest
+
+from universal_memory.__main__ import main
+from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
+from universal_memory.infrastructure.security import LocalSnapshotRepository
+
+
+def seed_snapshot(
+    project_root: Path,
+    *,
+    content: bytes = b"previous state\n",
+    scope: SnapshotScope = SnapshotScope.project,
+    relative_path: str = ".umem/memory/facts.jsonl",
+    action: str = "safe_write",
+) -> Snapshot:
+    target = project_root / relative_path
+    target.parent.mkdir(parents=True, exist_ok=True)
+    target.write_bytes(content)
+    timestamp = datetime(2026, 5, 26, tzinfo=UTC)
+    snapshot = Snapshot(
+        id=str(uuid4()),
+        created_at=timestamp,
+        updated_at=timestamp,
+        timestamp=timestamp,
+        scope=scope,
+        origin="cli",
+        action=action,
+        relative_path=relative_path,
+        hash=sha256(content).hexdigest(),
+        status=SnapshotStatus.created,
+    )
+    LocalSnapshotRepository(
+        project_root=project_root,
+        data_root=project_root / ".umem",
+    ).write(snapshot)
+    target.write_bytes(b"current state\n")
+    return snapshot
+
+
+def test_rollback_yes_restores_snapshot_and_prints_human_details(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    snapshot = seed_snapshot(tmp_path)
+
+    exit_code = main(["rollback", "--scope", "project", "--yes"])
+
+    captured = capsys.readouterr()
+    assert exit_code == 0
+    assert captured.err == ""
+    assert (tmp_path / ".umem" / "memory" / "facts.jsonl").read_bytes() == b"previous state\n"
+    assert "Rollback concluido" in captured.out
+    assert "Escopo: project" in captured.out
+    assert f"Snapshot: {snapshot.id}" in captured.out
+    assert "Acao original: safe_write" in captured.out
+    assert "Arquivo: .umem/memory/facts.jsonl" in captured.out
+
+
+def test_rollback_json_success_outputs_strict_envelope(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    snapshot = seed_snapshot(tmp_path)
+
+    exit_code = main(["rollback", "--scope", "project", "--format", "json", "--yes"])
+
+    captured = capsys.readouterr()
+    payload = json.loads(captured.out)
+    assert exit_code == 0
+    assert captured.err == ""
+    assert payload["ok"] is True
+    assert payload["operation"] == "rollback"
+    assert payload["scope"] == "project"
+    assert payload["warnings"] == []
+    assert payload["data"]["scope"] == "project"
+    assert payload["data"]["snapshot_reference"] == snapshot.id
+    assert payload["data"]["restored_paths"] == [".umem/memory/facts.jsonl"]
+    assert isinstance(payload["data"]["audit_reference"], str)
+
+
+def test_rollback_interactive_confirmation_accepts_yes(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    seed_snapshot(tmp_path)
+    prompts: list[str] = []
+    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "s")
+
+    exit_code = main(["rollback", "--scope", "project"])
+
+    assert exit_code == 0
+    assert prompts == ["Deseja prosseguir com o rollback? [s/N]: "]
+    assert (tmp_path / ".umem" / "memory" / "facts.jsonl").read_bytes() == b"previous state\n"
+    assert "Rollback concluido" in capsys.readouterr().out
+
+
+def test_rollback_interactive_confirmation_declines_without_writing(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    seed_snapshot(tmp_path)
+    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
+
+    exit_code = main(["rollback", "--scope", "project"])
+
+    captured = capsys.readouterr()
+    assert exit_code == 1
+    assert (tmp_path / ".umem" / "memory" / "facts.jsonl").read_bytes() == b"current state\n"
+    assert "Rollback cancelado" in captured.out
+
+
+def test_rollback_json_failure_uses_standard_error_envelope(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+
+    exit_code = main(["rollback", "--scope", "project", "--format", "json", "--yes"])
+
+    captured = capsys.readouterr()
+    payload = json.loads(captured.out)
+    assert exit_code == 1
+    assert captured.err == ""
+    assert payload["ok"] is False
+    assert payload["error"]["code"] == "snapshot_failed"
+    assert "Nenhum snapshot" in payload["error"]["detail"]
```
