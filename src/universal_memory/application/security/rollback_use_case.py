from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from universal_memory.domain import SnapshotFailedError
from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.domain.ports import AuditLogRepository, SnapshotRepository


@dataclass(frozen=True, slots=True)
class RollbackCommand:
    scope: SnapshotScope
    origin: str
    action: str = "rollback"


@dataclass(frozen=True, slots=True)
class RollbackResult:
    scope: SnapshotScope
    snapshot_reference: str
    restored_paths: list[str]
    audit_reference: str


class RollbackUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        snapshot_repository: SnapshotRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self.project_root = project_root.resolve()
        self.snapshot_repository = snapshot_repository
        self.audit_log_repository = audit_log_repository

    def execute(self, command: RollbackCommand) -> RollbackResult:
        snapshots = self.snapshot_repository.list(
            scope=command.scope,
            status=SnapshotStatus.created,
        )
        if not snapshots:
            raise SnapshotFailedError(
                "Nenhum snapshot encontrado para o escopo solicitado. "
                "Hint: execute uma mutacao segura antes de tentar rollback."
            )

        snapshot = max(snapshots, key=lambda item: self._normalize_datetime(item.timestamp))
        actual_hash = None
        try:
            content = self.snapshot_repository.get_content(snapshot.id)
            actual_hash = sha256(content).hexdigest()
            if actual_hash != snapshot.hash:
                raise SnapshotFailedError(
                    "Falha de integridade do snapshot: hash SHA-256 do backup fisico "
                    "nao corresponde ao manifesto. Hint: inspecione os snapshots e recrie "
                    "o estado a partir de um backup confiavel."
                )

            target_path = self._resolve_target(snapshot)
            self._atomic_write_bytes(target_path, content)
        except Exception as error:
            details = None
            if actual_hash is not None and actual_hash != snapshot.hash:
                details = f"Hash mismatch: expected {snapshot.hash}, computed {actual_hash}"
            elif isinstance(error, SnapshotFailedError):
                details = str(error)
            elif isinstance(error, OSError):
                details = f"OS error: {error}"

            try:
                self._record_audit(
                    command,
                    snapshot_reference=snapshot.id,
                    result="failure",
                    status="failed",
                    details=details,
                )
            except Exception as audit_error:
                audit_error.add_note("Audit failure suppressed to preserve rollback exception")
            raise

        event = self._record_audit(
            command,
            snapshot_reference=snapshot.id,
            result="success",
            status="logged",
        )
        return RollbackResult(
            scope=command.scope,
            snapshot_reference=snapshot.id,
            restored_paths=[snapshot.relative_path],
            audit_reference=event.audit_reference,
        )

    def _resolve_target(self, snapshot: Snapshot) -> Path:
        target_path = (self.project_root / snapshot.relative_path).resolve()
        try:
            target_path.relative_to(self.project_root.resolve())
        except ValueError as exc:
            raise SnapshotFailedError("Snapshot target path escapes project root") from exc
        if target_path.exists() and not target_path.is_file():
            raise SnapshotFailedError("Snapshot target path is not a file")
        return target_path

    def _atomic_write_bytes(self, target_path: Path, content: bytes) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_name(f"{target_path.name}.{uuid4()}.tmp")
        try:
            temp_path.write_bytes(content)
            if target_path.exists():
                try:
                    os.chmod(temp_path, target_path.stat().st_mode)
                except OSError:
                    pass
            os.replace(temp_path, target_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def _record_audit(
        self,
        command: RollbackCommand,
        *,
        snapshot_reference: str,
        result: str,
        status: str,
        details: str | None = None,
    ) -> AuditEvent:
        timestamp = datetime.now(UTC)
        audit_reference = str(uuid4())
        event = AuditEvent(
            id=audit_reference,
            created_at=timestamp,
            updated_at=timestamp,
            timestamp=timestamp,
            action=command.action,
            scope=self._audit_scope(command.scope),
            origin=command.origin,
            result=result,
            snapshot_reference=snapshot_reference,
            audit_reference=audit_reference,
            status=status,
            details=details,
        )
        self.audit_log_repository.write(event)
        return event

    @staticmethod
    def _audit_scope(scope: SnapshotScope) -> AuditEventScope:
        if scope == SnapshotScope.global_:
            return AuditEventScope.global_
        return AuditEventScope.project

    @staticmethod
    def _normalize_datetime(dt: datetime) -> datetime:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=UTC)
        return dt
