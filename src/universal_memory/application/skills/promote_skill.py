from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.skills.create_skill import (
    CreateSkillCommand,
    CreateSkillResult,
    CreateSkillUseCase,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillStatus
from universal_memory.domain.ports import LatentSkillRepository


@dataclass(frozen=True, slots=True)
class PromoteSkillRecommendationCommand:
    recommendation_id: str
    origin: str
    name: str | None = None
    description: str | None = None
    triggers: list[str] | None = None
    targets: list[str] | None = None
    project_initialized: bool | None = None


@dataclass(frozen=True, slots=True)
class PromoteSkillRecommendationResult:
    create_result: CreateSkillResult
    source_recommendation: LatentSkill
    promoted_recommendation: LatentSkill
    audit_reference: str
    snapshot_reference: str

    @property
    def warnings(self) -> list[str]:
        return self.create_result.warnings

    def to_payload(self) -> dict[str, Any]:
        payload = self.create_result.to_payload()
        payload["source_recommendation_id"] = self.source_recommendation.id
        payload["promotion"] = {
            "source_recommendation_id": self.source_recommendation.id,
            "promoted_skill_id": self.create_result.agent_skill.id,
            "promoted_recommendation_status": self.promoted_recommendation.status.value,
            "promoted_at": self.promoted_recommendation.metadata["promotion"]["promoted_at"],
        }
        payload["audit_reference"] = self.audit_reference
        payload["snapshot_reference"] = self.snapshot_reference
        return payload


class _PromoteSkillRecommendationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    recommendation_id: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    name: str | None = None
    description: str | None = None
    triggers: list[str] | None = None
    targets: list[str] | None = None
    project_initialized: bool | None = None


class PromoteSkillRecommendationUseCase:
    def __init__(
        self,
        *,
        recommendation_repository: LatentSkillRepository,
        create_skill_use_case: CreateSkillUseCase,
    ) -> None:
        self.recommendation_repository = recommendation_repository
        self.create_skill_use_case = create_skill_use_case

    def execute(
        self,
        command: PromoteSkillRecommendationCommand,
    ) -> PromoteSkillRecommendationResult:
        validated = _PromoteSkillRecommendationSchema.model_validate(command)
        recommendation = self.recommendation_repository.read(validated.recommendation_id)
        self._validate_eligible(recommendation)
        if validated.project_initialized is False and recommendation.scope.value == "project":
            raise ValidationFailedError(
                "Project memory is not initialized. Call initialize_project first."
            )

        name = (validated.name if validated.name is not None else recommendation.name).strip()
        description = (
            validated.description
            if validated.description is not None
            else recommendation.description
        ).strip()
        triggers = (
            _normalize_triggers(validated.triggers)
            if validated.triggers is not None
            else _recommendation_triggers(recommendation)
        )
        create_result = self.create_skill_use_case.execute(
            CreateSkillCommand(
                name=name,
                description=description,
                scope=recommendation.scope,
                origin=validated.origin,
                triggers=triggers,
                targets=validated.targets,
                source_recommendation_id=recommendation.id,
                metadata={
                    "creation_flow": "promotion",
                    "recommendation_flow": True,
                    "promotion": {
                        "source_recommendation_id": recommendation.id,
                        "source_recommendation_status": recommendation.status.value,
                    },
                },
            )
        )
        promoted = self._promoted_recommendation(
            recommendation,
            promoted_skill_id=create_result.agent_skill.id,
            canonical_path=create_result.skill_file,
            origin=validated.origin,
        )
        write_result = self.recommendation_repository.write(promoted, origin=validated.origin)

        audit_references = [create_result.audit_reference]
        snapshot_references = [create_result.snapshot_reference]
        if write_result is not None:
            audit_references.append(write_result.audit_reference)
            snapshot_references.append(write_result.snapshot_reference)
        return PromoteSkillRecommendationResult(
            create_result=create_result,
            source_recommendation=recommendation,
            promoted_recommendation=promoted,
            audit_reference=", ".join(ref for ref in audit_references if ref),
            snapshot_reference=", ".join(ref for ref in snapshot_references if ref),
        )

    @staticmethod
    def _validate_eligible(recommendation: LatentSkill) -> None:
        promotion = (recommendation.metadata or {}).get("promotion")
        if isinstance(promotion, dict) and promotion.get("promoted_skill_id"):
            raise ValidationFailedError(f"Latent skill {recommendation.id} was already promoted.")
        if recommendation.status != LatentSkillStatus.proposed:
            raise ValidationFailedError(
                f"Latent skill {recommendation.id} must be proposed before promotion."
            )

    @staticmethod
    def _promoted_recommendation(
        recommendation: LatentSkill,
        *,
        promoted_skill_id: str,
        canonical_path: str,
        origin: str,
    ) -> LatentSkill:
        now = datetime.now(UTC)
        metadata = dict(recommendation.metadata or {})
        metadata["promotion"] = {
            "promoted_skill_id": promoted_skill_id,
            "source_recommendation_id": recommendation.id,
            "canonical_path": canonical_path,
            "origin": origin,
            "promoted_at": now.isoformat().replace("+00:00", "Z"),
        }
        return recommendation.model_copy(
            update={
                "status": LatentSkillStatus.active,
                "updated_at": now,
                "metadata": metadata,
            }
        )


def _recommendation_triggers(recommendation: LatentSkill) -> list[str]:
    metadata = recommendation.metadata or {}
    return _normalize_triggers(metadata.get("triggers") or metadata.get("tags") or [])


def _normalize_triggers(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        values = value
    elif isinstance(value, tuple | set):
        values = list(value)
    else:
        values = [value]
    return [str(item).strip() for item in values if str(item).strip()]
