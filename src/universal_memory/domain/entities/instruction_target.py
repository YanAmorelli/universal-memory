from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Self

from pydantic import ConfigDict, Field, field_validator, model_validator

from universal_memory.domain.entities.base import BaseEntity


class InstructionTargetType(StrEnum):
    agents_md = "agents_md"
    claude_md = "claude_md"


class InstructionClassification(StrEnum):
    shared_policy = "shared_policy"
    provider_delta = "provider_delta"
    scoped_rule = "scoped_rule"
    canonical_doc = "canonical_doc"


class InstructionTargetOwnership(StrEnum):
    single_writer = "single_writer"
    delta_consumer = "delta_consumer"


class InstructionTarget(BaseEntity):
    model_config = ConfigDict(extra="forbid")

    name: InstructionTargetType
    relative_path: str
    ownership: InstructionTargetOwnership
    supported_classifications: list[InstructionClassification] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("supported_classifications")
    @classmethod
    def validate_classifications_unique(
        cls, value: list[InstructionClassification]
    ) -> list[InstructionClassification]:
        if len(value) != len(set(value)):
            raise ValueError("supported_classifications must not contain duplicate classifications")
        return value

    @field_validator("relative_path")
    @classmethod
    def validate_safe_relative_path(cls, value: str) -> str:
        if "\\" in value:
            raise ValueError("relative_path must not contain backslashes")
        path = PurePosixPath(value)
        if value == "" or path.is_absolute() or ".." in path.parts:
            raise ValueError("relative_path must be a safe relative path")
        return value

    @model_validator(mode="after")
    def validate_target_contract(self) -> Self:
        target_constraints = {
            InstructionTargetType.agents_md: {
                "relative_path": "AGENTS.md",
                "ownership": InstructionTargetOwnership.single_writer,
                "forbidden_classifications": set(),
            },
            InstructionTargetType.claude_md: {
                "relative_path": "CLAUDE.md",
                "ownership": InstructionTargetOwnership.delta_consumer,
                "forbidden_classifications": {InstructionClassification.shared_policy},
            },
        }

        constraints = target_constraints.get(self.name)
        if constraints:
            expected_path = constraints["relative_path"]
            if self.relative_path != expected_path:
                raise ValueError(f"{self.name} target must write {expected_path}")

            expected_ownership = constraints["ownership"]
            if self.ownership != expected_ownership:
                raise ValueError(
                    f"{self.name} target must have {expected_ownership.value} ownership"
                )

            forbidden = constraints["forbidden_classifications"]
            for classification in self.supported_classifications:
                if classification in forbidden:
                    raise ValueError(
                        f"{self.name} target must not duplicate {classification.value} content"
                    )

        return self
