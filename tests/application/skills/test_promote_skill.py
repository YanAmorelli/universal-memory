from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tests.application.skills.test_generate_skill import (
    RecordingAuditRepository,
    RecordingScanner,
    RecordingSnapshotRepository,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    CreateSkillUseCase,
    ListSkillsCommand,
    ListSkillsUseCase,
    PromoteSkillRecommendationCommand,
    PromoteSkillRecommendationUseCase,
)
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.infrastructure.storage import (
    LocalAgentSkillRepository,
    LocalLatentSkillRepository,
)

RECOMMENDATION_ID = "11111111-1111-4111-8111-111111111111"


def make_recommendation(
    *,
    status: LatentSkillStatus = LatentSkillStatus.proposed,
    metadata: dict[str, object] | None = None,
) -> LatentSkill:
    now = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
    return LatentSkill(
        id=RECOMMENDATION_ID,
        created_at=now,
        updated_at=now,
        name="Review Operator",
        description="Review code changes before handoff.",
        scope=LatentSkillScope.project,
        status=status,
        recurrence_count=3,
        metadata=metadata or {"triggers": ["review code changes"]},
    )


def make_use_case(tmp_path: Path):
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    latent_repository = LocalLatentSkillRepository(
        project_root=tmp_path,
        safe_write_use_case=safe_write,
    )
    agent_repository = LocalAgentSkillRepository(
        project_root=tmp_path,
        safe_write_use_case=safe_write,
    )
    use_case = PromoteSkillRecommendationUseCase(
        recommendation_repository=latent_repository,
        create_skill_use_case=CreateSkillUseCase(
            project_root=tmp_path,
            repository=agent_repository,
            safe_write_use_case=safe_write,
        ),
    )
    return use_case, latent_repository, agent_repository


def test_promote_recommendation_creates_canonical_skill_and_marks_source(tmp_path: Path) -> None:
    use_case, latent_repository, agent_repository = make_use_case(tmp_path)
    latent_repository.write(make_recommendation(), origin="test")

    result = use_case.execute(
        PromoteSkillRecommendationCommand(recommendation_id=RECOMMENDATION_ID, origin="test")
    )

    stored_skill = agent_repository.read(result.create_result.agent_skill.id)
    promoted = latent_repository.read(RECOMMENDATION_ID)
    payload = result.to_payload()

    assert stored_skill.source_recommendation_id == RECOMMENDATION_ID
    assert stored_skill.metadata["creation_flow"] == "promotion"
    assert stored_skill.metadata["recommendation_flow"] is True
    assert promoted.status == LatentSkillStatus.active
    assert promoted.metadata["promotion"]["promoted_skill_id"] == stored_skill.id
    assert payload["source_recommendation_id"] == RECOMMENDATION_ID
    assert payload["canonical_skill"]["source_recommendation_id"] == RECOMMENDATION_ID
    assert (tmp_path / ".umem" / "skills" / "review-operator" / "SKILL.md").is_file()


def test_promote_recommendation_applies_approved_edits(tmp_path: Path) -> None:
    use_case, latent_repository, agent_repository = make_use_case(tmp_path)
    latent_repository.write(make_recommendation(), origin="test")

    result = use_case.execute(
        PromoteSkillRecommendationCommand(
            recommendation_id=RECOMMENDATION_ID,
            origin="test",
            name="Edited Review Operator",
            description="Edited review instructions.",
            triggers=[" edited trigger ", ""],
        )
    )

    stored_skill = agent_repository.read(result.create_result.agent_skill.id)
    markdown = (tmp_path / ".umem" / "skills" / "edited-review-operator" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert stored_skill.name == "Edited Review Operator"
    assert stored_skill.description == "Edited review instructions."
    assert stored_skill.metadata["triggers"] == ["edited trigger"]
    assert 'name: "Edited Review Operator"' in markdown


def test_promote_recommendation_can_skip_native_targets(tmp_path: Path) -> None:
    use_case, latent_repository, _agent_repository = make_use_case(tmp_path)
    latent_repository.write(make_recommendation(), origin="test")

    result = use_case.execute(
        PromoteSkillRecommendationCommand(
            recommendation_id=RECOMMENDATION_ID,
            origin="test",
            targets=[],
        )
    )

    assert result.create_result.native_installations == []
    assert not (tmp_path / ".opencode" / "skills" / "review-operator").exists()


def test_promote_rejects_ineligible_or_already_promoted_recommendations(tmp_path: Path) -> None:
    use_case, latent_repository, agent_repository = make_use_case(tmp_path)
    latent_repository.write(
        make_recommendation(status=LatentSkillStatus.ignored),
        origin="test",
    )

    try:
        use_case.execute(
            PromoteSkillRecommendationCommand(recommendation_id=RECOMMENDATION_ID, origin="test")
        )
    except ValidationFailedError as error:
        assert "must be proposed" in str(error)
    else:
        raise AssertionError("Expected ineligible recommendation to fail")

    assert agent_repository.list() == []


def test_promote_rejects_project_recommendation_when_project_uninitialized(
    tmp_path: Path,
) -> None:
    use_case, latent_repository, agent_repository = make_use_case(tmp_path)
    latent_repository.write(make_recommendation(), origin="test")

    try:
        use_case.execute(
            PromoteSkillRecommendationCommand(
                recommendation_id=RECOMMENDATION_ID,
                origin="mcp",
                project_initialized=False,
            )
        )
    except ValidationFailedError as error:
        assert "Project memory is not initialized" in str(error)
    else:
        raise AssertionError("Expected uninitialized project promotion to fail")

    assert agent_repository.list() == []


def test_promote_failure_after_canonical_create_leaves_traceable_provenance(
    tmp_path: Path,
) -> None:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    recommendation = make_recommendation()
    agent_repository = LocalAgentSkillRepository(
        project_root=tmp_path,
        safe_write_use_case=safe_write,
    )

    class FailingLatentRepository(LocalLatentSkillRepository):
        def read(self, id: str) -> LatentSkill:
            if id == recommendation.id:
                return recommendation
            return super().read(id)

        def write(self, entity: LatentSkill, *, origin: str = "repository"):
            raise StorageError("simulated latent promotion write failure")

    use_case = PromoteSkillRecommendationUseCase(
        recommendation_repository=FailingLatentRepository(
            project_root=tmp_path,
            safe_write_use_case=safe_write,
        ),
        create_skill_use_case=CreateSkillUseCase(
            project_root=tmp_path,
            repository=agent_repository,
            safe_write_use_case=safe_write,
        ),
    )

    try:
        use_case.execute(
            PromoteSkillRecommendationCommand(recommendation_id=RECOMMENDATION_ID, origin="test")
        )
    except StorageError as error:
        assert "simulated latent promotion write failure" in str(error)
    else:
        raise AssertionError("Expected latent write failure")

    stored = agent_repository.list()[0]
    assert stored.source_recommendation_id == RECOMMENDATION_ID
    assert stored.metadata["promotion"]["source_recommendation_id"] == RECOMMENDATION_ID


def test_list_skills_exposes_provenance_and_hides_promoted_recommendation(tmp_path: Path) -> None:
    use_case, latent_repository, agent_repository = make_use_case(tmp_path)
    latent_repository.write(make_recommendation(), origin="test")
    promoted = use_case.execute(
        PromoteSkillRecommendationCommand(recommendation_id=RECOMMENDATION_ID, origin="test")
    )

    payload = (
        ListSkillsUseCase(
            project_root=tmp_path,
            repository=latent_repository,
            agent_skill_repository=agent_repository,
        )
        .execute(ListSkillsCommand())
        .to_payload()
    )

    assert payload["skills"][0]["source_recommendation_id"] == RECOMMENDATION_ID
    assert payload["recommendations"] == []
    assert promoted.promoted_recommendation.metadata["promotion"]["promoted_skill_id"]
