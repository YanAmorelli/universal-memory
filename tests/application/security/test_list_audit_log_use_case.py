from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from universal_memory.application.security.list_audit_log_use_case import (
    ListAuditLogCommand,
    ListAuditLogUseCase,
)
from universal_memory.domain.entities import AuditEvent, AuditEventScope
from universal_memory.domain.ports import AuditLogRepository


class RecordingAuditRepository(AuditLogRepository):
    def __init__(self, events: list[AuditEvent] | None = None) -> None:
        self.events = events or []
        self.scopes: list[AuditEventScope | None] = []

    def read(self, id: str) -> AuditEvent:
        raise KeyError(id)

    def list(self, scope: AuditEventScope | None = None) -> list[AuditEvent]:
        self.scopes.append(scope)
        events = self.events
        if scope is not None:
            events = [event for event in events if event.scope == scope]
        return sorted(events, key=lambda event: event.timestamp)

    def write(self, entity: AuditEvent) -> None:
        self.events.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


def make_event(
    *,
    created_at: datetime,
    scope: AuditEventScope = AuditEventScope.project,
    action: str = "safe_write",
    origin: str = "cli",
    result: str = "success",
) -> AuditEvent:
    audit_reference = str(uuid4())
    return AuditEvent(
        id=audit_reference,
        created_at=created_at,
        updated_at=created_at,
        timestamp=created_at,
        action=action,
        scope=scope,
        origin=origin,
        result=result,
        snapshot_reference=str(uuid4()),
        audit_reference=audit_reference,
        status="logged",
    )


def test_list_audit_log_returns_events_ordered_with_required_fields() -> None:
    base = datetime(2026, 5, 26, tzinfo=UTC)
    newer = make_event(created_at=base + timedelta(minutes=2), action="second")
    older = make_event(created_at=base, action="first")
    repository = RecordingAuditRepository([newer, older])
    use_case = ListAuditLogUseCase(audit_log_repository=repository)

    result = use_case.execute(ListAuditLogCommand())

    assert [event.action for event in result.events] == ["first", "second"]
    assert result.events[0].timestamp == "2026-05-26T00:00:00Z"
    assert result.events[0].scope == "project"
    assert result.events[0].origin == "cli"
    assert result.events[0].result == "success"
    assert result.events[0].snapshot_reference == older.snapshot_reference
    assert result.events[0].audit_reference == older.audit_reference


def test_list_audit_log_filters_by_scope() -> None:
    base = datetime(2026, 5, 26, tzinfo=UTC)
    project_event = make_event(created_at=base, scope=AuditEventScope.project)
    global_event = make_event(created_at=base + timedelta(minutes=1), scope=AuditEventScope.global_)
    repository = RecordingAuditRepository([project_event, global_event])
    use_case = ListAuditLogUseCase(audit_log_repository=repository)

    result = use_case.execute(ListAuditLogCommand(scope=AuditEventScope.global_))

    assert repository.scopes == [AuditEventScope.global_]
    assert [event.audit_reference for event in result.events] == [global_event.audit_reference]
    assert result.events[0].scope == "global"


def test_list_audit_log_returns_empty_list_when_data_does_not_exist() -> None:
    use_case = ListAuditLogUseCase(audit_log_repository=RecordingAuditRepository())

    result = use_case.execute(ListAuditLogCommand())

    assert result.events == []
