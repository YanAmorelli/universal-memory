from datetime import datetime
from enum import StrEnum

from pydantic import field_validator

from universal_memory.domain.entities.base import (
    BaseEntity,
    validate_utc_datetime,
    validate_uuid_v4_string,
)


class AuditEventScope(StrEnum):
    global_ = "global"
    project = "project"


class AuditEvent(BaseEntity):
    timestamp: datetime
    action: str
    scope: AuditEventScope
    origin: str
    result: str
    snapshot_reference: str
    audit_reference: str
    status: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_utc(cls, value: datetime) -> datetime:
        return validate_utc_datetime(value)

    @field_validator("snapshot_reference", "audit_reference")
    @classmethod
    def validate_references(cls, value: str) -> str:
        return validate_uuid_v4_string(value)
