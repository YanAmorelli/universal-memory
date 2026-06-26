from __future__ import annotations

from pathlib import Path

import pytest

from tests.application.skills.conftest import write_valid_skill_tree
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    AdoptSkillCommand,
    AdoptSkillUseCase,
    GetSkillDetailCommand,
    GetSkillDetailUseCase,
    ListSkillsCommand,
    ListSkillsUseCase,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkillScope
from universal_memory.infrastructure.storage import (
    LocalAgentSkillRepository,
    LocalLatentSkillRepository,
)


def test_adopt_existing_canonical_directory_registers_in_place(
    tmp_path: Path,
    skill_safe_write: SafeWriteUseCase,
    agent_skill_repository: LocalAgentSkillRepository,
) -> None:
    source = write_valid_skill_tree(tmp_path)

    result = AdoptSkillUseCase(
        project_root=tmp_path,
        repository=agent_skill_repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        AdoptSkillCommand(
            path=source,
            scope=LatentSkillScope.project,
            origin="test",
            slug="review-helper",
        )
    )

    stored = agent_skill_repository.read(result.agent_skill.id)
    assert stored.slug == "review-helper"
    assert stored.canonical_path == ".umem/skills/review-helper/SKILL.md"
    assert result.affected_paths == [".umem/skills/review-helper/SKILL.md"]
    assert not (tmp_path / ".umem" / "skills" / "review-helper-1").exists()


def test_list_and_detail_surface_valid_unregistered_directory_with_adoption_guidance(
    tmp_path: Path,
    skill_safe_write: SafeWriteUseCase,
    agent_skill_repository: LocalAgentSkillRepository,
) -> None:
    write_valid_skill_tree(tmp_path)
    latent_repository = LocalLatentSkillRepository(
        project_root=tmp_path, safe_write_use_case=skill_safe_write
    )

    list_payload = (
        ListSkillsUseCase(
            project_root=tmp_path,
            repository=latent_repository,
            agent_skill_repository=agent_skill_repository,
        )
        .execute(ListSkillsCommand())
        .to_payload()
    )
    detail_payload = (
        GetSkillDetailUseCase(
            project_root=tmp_path,
            repository=latent_repository,
            agent_skill_repository=agent_skill_repository,
        )
        .execute(GetSkillDetailCommand(name_or_id="review-helper"))
        .to_payload()
    )

    assert list_payload["skills"][0]["status"] == "unregistered"
    assert list_payload["skills"][0]["recommended_action"] == (
        "umem skills adopt .umem/skills/review-helper --slug review-helper"
    )
    assert detail_payload["status"] == "unregistered"
    assert detail_payload["recommended_action"] == (
        "umem skills adopt .umem/skills/review-helper --slug review-helper"
    )


def test_adopt_slug_conflict_is_blocked(
    tmp_path: Path,
    skill_safe_write: SafeWriteUseCase,
    agent_skill_repository: LocalAgentSkillRepository,
) -> None:
    first = write_valid_skill_tree(tmp_path)
    use_case = AdoptSkillUseCase(
        project_root=tmp_path,
        repository=agent_skill_repository,
        safe_write_use_case=skill_safe_write,
    )
    use_case.execute(
        AdoptSkillCommand(
            path=first,
            scope=LatentSkillScope.project,
            origin="test",
            slug="review-helper",
        )
    )
    second = write_valid_skill_tree(tmp_path, "review-helper-copy", name="Review Helper Copy")

    with pytest.raises(ValidationFailedError, match="Skill slug already exists"):
        use_case.execute(
            AdoptSkillCommand(
                path=second,
                scope=LatentSkillScope.project,
                origin="test",
                slug="review-helper",
            )
        )
