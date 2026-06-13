from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.domain.ports import LatentSkillRepository

DEFAULT_MIN_RECURRENCE = 2
DEFAULT_MIN_EVIDENCE_SUMMARIES = 2
LATENT_SKILLS_LIMITATION = (
    "First implementation only evaluates explicit `skills track` latent records; "
    "facts, audit events, host feedback, prompts, logs, transcripts, native skill files, "
    "and memory fact text are not scanned."
)


@dataclass(frozen=True, slots=True)
class RecommendSkillsCommand:
    scope: LatentSkillScope | None = LatentSkillScope.project
    min_recurrence: int | None = None


@dataclass(frozen=True, slots=True)
class SkillRecommendationItem:
    id: str
    name: str
    description: str
    scope: str
    status: str
    recurrence_count: int
    evidence_summaries: list[str]
    tags: list[str]
    confidence: float
    reasons: list[str]
    recommended_action: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "scope": self.scope,
            "status": self.status,
            "recurrence_count": self.recurrence_count,
            "evidence_summaries": self.evidence_summaries,
            "tags": self.tags,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "recommended_action": self.recommended_action,
        }


@dataclass(frozen=True, slots=True)
class RecommendSkillsResult:
    recommendations: list[SkillRecommendationItem]
    thresholds: dict[str, int]
    evidence_sources: list[dict[str, str]]
    limitations: list[str]

    def to_payload(self) -> dict[str, Any]:
        return {
            "recommendations": [item.to_payload() for item in self.recommendations],
            "thresholds": self.thresholds,
            "evidence_sources": self.evidence_sources,
            "limitations": self.limitations,
        }


class RecommendSkillsUseCase:
    def __init__(self, *, repository: LatentSkillRepository) -> None:
        self.repository = repository

    def execute(self, command: RecommendSkillsCommand) -> RecommendSkillsResult:
        min_recurrence = self._min_recurrence(command.min_recurrence)
        min_evidence_summaries = self._min_evidence_summaries(min_recurrence)
        recommendations = [
            self._item_for(
                skill,
                min_recurrence=min_recurrence,
                min_evidence_summaries=min_evidence_summaries,
            )
            for skill in self.repository.list(scope=command.scope)
            if self._is_actionable(
                skill,
                min_recurrence=min_recurrence,
                min_evidence_summaries=min_evidence_summaries,
            )
        ]
        recommendations.sort(key=lambda item: (-item.confidence, item.name.casefold(), item.id))
        return RecommendSkillsResult(
            recommendations=recommendations,
            thresholds={
                "min_recurrence": min_recurrence,
                "min_evidence_summaries": min_evidence_summaries,
            },
            evidence_sources=[
                {
                    "source": "latent_skills",
                    "description": (
                        "Curated evidence summaries explicitly recorded by `umem skills track`."
                    ),
                }
            ],
            limitations=[LATENT_SKILLS_LIMITATION],
        )

    @staticmethod
    def _min_recurrence(value: int | None) -> int:
        min_recurrence = DEFAULT_MIN_RECURRENCE if value is None else value
        if min_recurrence < 1:
            raise ValidationFailedError("min_recurrence must be at least 1.")
        return min_recurrence

    @staticmethod
    def _min_evidence_summaries(min_recurrence: int) -> int:
        return min(min_recurrence, DEFAULT_MIN_EVIDENCE_SUMMARIES)

    def _is_actionable(
        self,
        skill: LatentSkill,
        *,
        min_recurrence: int,
        min_evidence_summaries: int,
    ) -> bool:
        if skill.status != LatentSkillStatus.proposed:
            return False
        if skill.recurrence_count < min_recurrence:
            return False
        return len(self._evidence_summaries(skill)) >= min_evidence_summaries

    def _item_for(
        self,
        skill: LatentSkill,
        *,
        min_recurrence: int,
        min_evidence_summaries: int,
    ) -> SkillRecommendationItem:
        evidence_summaries = self._evidence_summaries(skill)
        tags = self._tags(skill)
        return SkillRecommendationItem(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            scope=skill.scope.value,
            status=skill.status.value,
            recurrence_count=skill.recurrence_count,
            evidence_summaries=evidence_summaries,
            tags=tags,
            confidence=self._confidence(skill, evidence_summaries=evidence_summaries, tags=tags),
            reasons=self._reasons(
                skill,
                evidence_summaries=evidence_summaries,
                tags=tags,
                min_recurrence=min_recurrence,
                min_evidence_summaries=min_evidence_summaries,
            ),
            recommended_action=f"umem skills promote {skill.id}",
        )

    @staticmethod
    def _evidence_summaries(skill: LatentSkill) -> list[str]:
        evidence = (skill.metadata or {}).get("evidence", [])
        if not isinstance(evidence, list):
            return []
        summaries: list[str] = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            summary = item.get("summary")
            if not isinstance(summary, str):
                continue
            cleaned = summary.strip()
            if cleaned:
                summaries.append(cleaned)
        return summaries

    @staticmethod
    def _tags(skill: LatentSkill) -> list[str]:
        tags = (skill.metadata or {}).get("tags", [])
        if not isinstance(tags, list):
            return []
        return sorted({str(tag).strip() for tag in tags if str(tag).strip()})

    @staticmethod
    def _confidence(
        skill: LatentSkill,
        *,
        evidence_summaries: list[str],
        tags: list[str],
    ) -> float:
        score = 0.4
        score += min(skill.recurrence_count, 5) * 0.08
        score += min(len(evidence_summaries), 5) * 0.08
        if tags:
            score += 0.05
        return round(min(score, 0.95), 2)

    @staticmethod
    def _reasons(
        skill: LatentSkill,
        *,
        evidence_summaries: list[str],
        tags: list[str],
        min_recurrence: int,
        min_evidence_summaries: int,
    ) -> list[str]:
        reasons = [
            "status is proposed and actionable",
            (
                f"recurrence_count {skill.recurrence_count} meets minimum "
                f"recurrence threshold {min_recurrence}"
            ),
            (
                f"{len(evidence_summaries)} curated evidence summaries meet "
                f"minimum evidence threshold {min_evidence_summaries}"
            ),
        ]
        if tags:
            reasons.append(f"tags: {', '.join(tags)}")
        return reasons
