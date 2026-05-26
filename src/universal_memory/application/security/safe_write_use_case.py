from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from uuid import uuid4

from universal_memory.domain import SecretDetectedError
from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.domain.ports import AuditLogRepository, SecretScannerPort, SnapshotRepository


@dataclass(frozen=True, slots=True)
class SafeWriteCommand:
    relative_path: str
    content: str
    scope: AuditEventScope
    origin: str
    action: str


@dataclass(frozen=True, slots=True)
class SafeWriteResult:
    relative_path: str
    audit_reference: str
    snapshot_reference: str


class SafeWriteUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        secret_scanner: SecretScannerPort,
        snapshot_repository: SnapshotRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self.project_root = project_root.resolve()
        self.secret_scanner = secret_scanner
        self.snapshot_repository = snapshot_repository
        self.audit_log_repository = audit_log_repository

    def execute(self, command: SafeWriteCommand) -> SafeWriteResult:
        relative_path = self._validate_relative_path(command.relative_path)

        try:
            self.secret_scanner.scan(command.content, origin=command.origin)
        except SecretDetectedError:
            try:
                dummy_snapshot_ref = str(uuid4())
                self._record_audit(
                    command,
                    snapshot_reference=dummy_snapshot_ref,
                    result="blocked",
                    status="blocked",
                )
            except Exception as audit_err:
                audit_err.add_note("Audit failure suppressed during secret block")
            raise

        target_path = self._resolve_target(relative_path)
        try:
            previous_bytes = target_path.read_bytes() if target_path.exists() else b""
        except OSError:
            previous_bytes = b""

        try:
            snapshot = self._snapshot_for(command, relative_path, previous_bytes)
            self.snapshot_repository.write(snapshot)
        except Exception:
            try:
                dummy_snapshot_ref = str(uuid4())
                self._record_audit(
                    command,
                    snapshot_reference=dummy_snapshot_ref,
                    result="failure",
                    status="failed",
                )
            except Exception as audit_err:
                audit_err.add_note("Audit failure suppressed during snapshot failure")
            raise

        try:
            self._atomic_write(target_path, command.content)
        except BaseException:
            try:
                self._record_audit(
                    command,
                    snapshot_reference=snapshot.id,
                    result="failure",
                    status="failed",
                )
            except Exception as audit_error:
                audit_error.add_note("Audit failure suppressed to preserve write exception")
            raise

        try:
            event = self._record_audit(
                command,
                snapshot_reference=snapshot.id,
                result="success",
                status="logged",
            )
            audit_ref = event.audit_reference
        except Exception as audit_exc:
            print(
                f"CRITICAL COMPLIANCE WARNING: Atomic write succeeded for {relative_path}, "
                f"but audit logging failed: {audit_exc}. This write is UNAUDITED.",
                file=sys.stderr,
            )
            audit_ref = "UNAUDITED"

        return SafeWriteResult(
            relative_path=relative_path,
            audit_reference=audit_ref,
            snapshot_reference=snapshot.id,
        )

    def _validate_relative_path(self, value: str) -> str:
        normalized = value.replace("\\", "/")
        path = PurePosixPath(normalized)
        if not value or path.is_absolute() or ".." in path.parts:
            raise ValueError("relative_path must be relative and must not contain traversal")
        return path.as_posix()

    def _resolve_target(self, relative_path: str) -> Path:
        target_path = self.project_root / relative_path
        try:
            target_path.resolve().relative_to(self.project_root)
        except ValueError as exc:
            raise ValueError("relative_path must resolve inside project_root") from exc
        if target_path.exists() and not target_path.is_file():
            raise ValueError("relative_path must target a file")
        return target_path

    def _snapshot_for(
        self,
        command: SafeWriteCommand,
        relative_path: str,
        previous_bytes: bytes,
    ) -> Snapshot:
        timestamp = datetime.now(UTC)
        snapshot_scope = (
            SnapshotScope.global_
            if command.scope == AuditEventScope.global_
            else SnapshotScope.project
        )
        return Snapshot(
            id=str(uuid4()),
            created_at=timestamp,
            updated_at=timestamp,
            timestamp=timestamp,
            scope=snapshot_scope,
            origin=command.origin,
            action=command.action,
            relative_path=relative_path,
            hash=sha256(previous_bytes).hexdigest(),
            status=SnapshotStatus.created,
        )

    def _atomic_write(self, target_path: Path, content: str) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_name(f"{target_path.name}.{uuid4()}.tmp")
        try:
            temp_path.write_text(content, encoding="utf-8")
            os.replace(temp_path, target_path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise

    def _record_audit(
        self,
        command: SafeWriteCommand,
        *,
        snapshot_reference: str,
        result: str,
        status: str | None = None,
    ) -> AuditEvent:
        timestamp = datetime.now(UTC)
        audit_reference = str(uuid4())
        resolved_status = status or ("logged" if result == "success" else "failed")
        event = AuditEvent(
            id=audit_reference,
            created_at=timestamp,
            updated_at=timestamp,
            timestamp=timestamp,
            action=command.action,
            scope=command.scope,
            origin=command.origin,
            result=result,
            snapshot_reference=snapshot_reference,
            audit_reference=audit_reference,
            status=resolved_status,
        )
        self.audit_log_repository.write(event)
        return event
