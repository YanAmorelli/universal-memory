from enum import StrEnum

from pydantic import field_validator

from universal_memory.domain.entities.base import BaseEntity, validate_uuid_v4_string


class ContextSummaryScope(StrEnum):
    global_ = "global"
    project = "project"


class ContextSummary(BaseEntity):
    project_summary: str
    universal_preferences: str
    active_rules: str
    audit_reference: str
    status: str
    scope: ContextSummaryScope

    @field_validator("audit_reference")
    @classmethod
    def validate_audit_reference(cls, value: str) -> str:
        return validate_uuid_v4_string(value)
