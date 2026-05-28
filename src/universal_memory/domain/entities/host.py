from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from universal_memory.domain.entities.base import BaseEntity
from universal_memory.domain.entities.instruction_target import InstructionTargetType


class HostName(StrEnum):
    codex = "codex"
    claude_code = "claude_code"


class Host(BaseEntity):
    model_config = ConfigDict(extra="forbid")

    name: HostName
    supported_targets: list[InstructionTargetType] = Field(min_length=1)
    mcp_config_method: str
    read_validation_method: str
    write_validation_method: str
    rollback_behavior: str
    audit_event_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("supported_targets")
    @classmethod
    def validate_supported_targets_unique(
        cls, value: list[InstructionTargetType]
    ) -> list[InstructionTargetType]:
        if len(value) != len(set(value)):
            raise ValueError("supported_targets must not contain duplicate targets")
        return value

    @field_validator(
        "mcp_config_method",
        "read_validation_method",
        "write_validation_method",
        "rollback_behavior",
        "audit_event_type",
    )
    @classmethod
    def validate_non_blank_operational_method(cls, value: str, info) -> str:
        stripped = value.strip()
        if stripped == "":
            raise ValueError(f"{info.field_name} must not be blank")
        return stripped

