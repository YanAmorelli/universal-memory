from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from universal_memory.application.skills import RecommendSkillsCommand, RecommendSkillsUseCase
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.domain.ports import LatentSkillRepository

IDS = {
    "skill-1": "11111111-1111-4111-8111-111111111111",
    "candidate-1": "22222222-2222-4222-8222-222222222222",
    "ignored": "33333333-3333-4333-8333-333333333333",
    "active": "44444444-4444-4444-8444-444444444444",
    "missing-evidence": "55555555-5555-4555-8555-555555555555",
    "global": "66666666-6666-4666-8666-666666666666",
    "eligible": "77777777-7777-4777-8777-777777777777",
    "higher-recurrence": "88888888-8888-4888-8888-888888888888",
}
DEFAULT_MIN_RECURRENCE = 2


class ReadOnlyLatentSkillRepository(LatentSkillRepository):
    def __init__(self, skills: list[LatentSkill] | None = None) -> None:
        self.skills = skills or []
        self.write_called = False
        self.delete_called = False

    def read(self, id: str) -> LatentSkill:
        raise AssertionError(f"read should not be called: {id}")

    def list(
        self,
        scope: LatentSkillScope | None = None,
        status: LatentSkillStatus | None = None,
    ) -> list[LatentSkill]:
        skills = self.skills
        if scope is not None:
            skills = [skill for skill in skills if skill.scope == scope]
        if status is not None:
            skills = [skill for skill in skills if skill.status == status]
        return skills

    def write(self, entity: LatentSkill, *, origin: str = "repository") -> None:
        self.write_called = True
        raise AssertionError("recommendations must be read-only")

    def delete(self, id: str) -> None:
        self.delete_called = True
        raise AssertionError("recommendations must be read-only")

    def migrate(self, target_version: int) -> None:
        return None


def make_skill(  # noqa: PLR0913
    *,
    id: str = "skill-1",
    name: str = "TDD Recorrente",
    scope: LatentSkillScope = LatentSkillScope.project,
    status: LatentSkillStatus = LatentSkillStatus.proposed,
    recurrence_count: int = 2,
    evidence: list[str] | None = None,
    tags: list[str] | None = None,
) -> LatentSkill:
    now = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
    evidence_summaries = ["one", "two"] if evidence is None else evidence
    return LatentSkill(
        id=IDS[id],
        created_at=now,
        updated_at=now + timedelta(minutes=5),
        name=name,
        description=f"Descricao de {name}",
        scope=scope,
        status=status,
        recurrence_count=recurrence_count,
        metadata={
            "tags": tags or ["tdd"],
            "evidence": [{"origin": "cli", "summary": summary} for summary in evidence_summaries],
        },
    )


def test_recommend_skills_empty_returns_policy_and_limitation() -> None:
    repository = ReadOnlyLatentSkillRepository()

    result = RecommendSkillsUseCase(repository=repository).execute(RecommendSkillsCommand())

    assert result.to_payload() == {
        "recommendations": [],
        "thresholds": {"min_recurrence": 2, "min_evidence_summaries": 2},
        "evidence_sources": [
            {
                "source": "latent_skills",
                "description": (
                    "Curated evidence summaries explicitly recorded by `umem skills track`."
                ),
            }
        ],
        "limitations": [
            "First implementation only evaluates explicit `skills track` latent records; "
            "facts, audit events, host feedback, prompts, logs, transcripts, native skill files, "
            "and memory fact text are not scanned."
        ],
    }
    assert repository.write_called is False
    assert repository.delete_called is False


def test_recommend_skills_returns_actionable_candidate() -> None:
    candidate = make_skill(id="candidate-1", evidence=["first", "second"], tags=["tdd", "story"])

    payload = (
        RecommendSkillsUseCase(repository=ReadOnlyLatentSkillRepository([candidate]))
        .execute(RecommendSkillsCommand())
        .to_payload()
    )

    recommendation = payload["recommendations"][0]
    assert recommendation["id"] == IDS["candidate-1"]
    assert recommendation["name"] == "TDD Recorrente"
    assert recommendation["description"] == "Descricao de TDD Recorrente"
    assert recommendation["scope"] == "project"
    assert recommendation["status"] == "proposed"
    assert recommendation["recurrence_count"] == DEFAULT_MIN_RECURRENCE
    assert recommendation["evidence_summaries"] == ["first", "second"]
    assert recommendation["tags"] == ["story", "tdd"]
    assert recommendation["confidence"] > 0
    assert "minimum recurrence threshold 2" in " ".join(recommendation["reasons"])
    assert recommendation["recommended_action"] == f"umem skills promote {IDS['candidate-1']}"


def test_recommend_skills_default_threshold_excludes_low_recurrence() -> None:
    candidate = make_skill(recurrence_count=1, evidence=["first"])

    result = RecommendSkillsUseCase(repository=ReadOnlyLatentSkillRepository([candidate])).execute(
        RecommendSkillsCommand()
    )

    assert result.recommendations == []
    assert result.thresholds["min_recurrence"] == DEFAULT_MIN_RECURRENCE


def test_recommend_skills_min_recurrence_override_allows_single_evidence() -> None:
    candidate = make_skill(recurrence_count=1, evidence=["first"])

    result = RecommendSkillsUseCase(repository=ReadOnlyLatentSkillRepository([candidate])).execute(
        RecommendSkillsCommand(min_recurrence=1)
    )

    assert len(result.recommendations) == 1
    assert "minimum recurrence threshold 1" in " ".join(result.recommendations[0].reasons)


def test_recommend_skills_min_recurrence_three_keeps_default_evidence_threshold() -> None:
    candidate = make_skill(
        id="higher-recurrence",
        recurrence_count=3,
        evidence=["first", "second"],
    )

    result = RecommendSkillsUseCase(repository=ReadOnlyLatentSkillRepository([candidate])).execute(
        RecommendSkillsCommand(min_recurrence=3)
    )

    assert result.thresholds == {"min_recurrence": 3, "min_evidence_summaries": 2}
    assert [item.id for item in result.recommendations] == [IDS["higher-recurrence"]]
    reasons = " ".join(result.recommendations[0].reasons)
    assert "minimum recurrence threshold 3" in reasons
    assert "minimum evidence threshold 2" in reasons


def test_recommend_skills_excludes_ignored_active_missing_evidence_and_other_scope() -> None:
    skills = [
        make_skill(id="ignored", status=LatentSkillStatus.ignored),
        make_skill(id="active", status=LatentSkillStatus.active),
        make_skill(id="missing-evidence", evidence=[]),
        make_skill(id="global", scope=LatentSkillScope.global_),
        make_skill(id="eligible"),
    ]

    result = RecommendSkillsUseCase(repository=ReadOnlyLatentSkillRepository(skills)).execute(
        RecommendSkillsCommand(scope=LatentSkillScope.project)
    )

    assert [item.id for item in result.recommendations] == [IDS["eligible"]]


def test_recommend_skills_rejects_min_recurrence_below_one() -> None:
    with pytest.raises(ValidationFailedError, match="min_recurrence must be at least 1"):
        RecommendSkillsUseCase(repository=ReadOnlyLatentSkillRepository()).execute(
            RecommendSkillsCommand(min_recurrence=0)
        )
