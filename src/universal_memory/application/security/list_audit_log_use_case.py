from __future__ import annotations

from dataclasses import dataclass

from universal_memory.domain.entities import AuditEvent, AuditEventScope
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.domain.ports import AuditLogRepository


@dataclass(frozen=True, slots=True)
class ListAuditLogCommand:
    scope: AuditEventScope | None = None


@dataclass(frozen=True, slots=True)
class AuditLogEntry:
    timestamp: str
    action: str
    scope: str
    origin: str
    result: str
    snapshot_reference: str
    audit_reference: str


@dataclass(frozen=True, slots=True)
class ListAuditLogResult:
    events: list[AuditLogEntry]


class ListAuditLogUseCase:
    def __init__(self, *, audit_log_repository: AuditLogRepository) -> None:
        self.audit_log_repository = audit_log_repository

    def execute(self, command: ListAuditLogCommand) -> ListAuditLogResult:
        events = self.audit_log_repository.list(scope=command.scope)
        return ListAuditLogResult(events=[self._entry_for(event) for event in events])

    def _entry_for(self, event: AuditEvent) -> AuditLogEntry:
        return AuditLogEntry(
            timestamp=format_utc_iso(event.timestamp),
            action=event.action,
            scope=event.scope.value,
            origin=event.origin,
            result=event.result,
            snapshot_reference=event.snapshot_reference,
            audit_reference=event.audit_reference,
        )

