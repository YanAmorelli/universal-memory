from __future__ import annotations

from pathlib import Path

import pytest

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    CreateSkillCommand,
    CreateSkillUseCase,
    RenameSkillCommand,
    RenameSkillUseCase,
)
from universal_memory.domain import StorageError
from universal_memory.domain.entities import LatentSkillScope
from universal_memory.infrastructure.storage import LocalAgentSkillRepository


def test_rename_skill_moves_canonical_path_and_updates_registry(
    tmp_path: Path,
    skill_safe_write: SafeWriteUseCase,
) -> None:
    repository = LocalAgentSkillRepository(
        project_root=tmp_path,
        safe_write_use_case=skill_safe_write,
    )
    created = CreateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        CreateSkillCommand(
            name="Review Helper",
            description="Review implementation changes safely.",
            scope=LatentSkillScope.project,
            origin="test",
            targets=[],
        )
    )

    result = RenameSkillUseCase(project_root=tmp_path, repository=repository).execute(
        RenameSkillCommand(
            skill_id_or_name=created.agent_skill.id,
            slug="review-operator",
            origin="test",
        )
    )

    assert result.old_path == ".umem/skills/review-helper/SKILL.md"
    assert result.new_path == ".umem/skills/review-operator/SKILL.md"
    assert not (tmp_path / ".umem" / "skills" / "review-helper").exists()
    assert (tmp_path / ".umem" / "skills" / "review-operator" / "SKILL.md").is_file()
    assert repository.read(created.agent_skill.id).slug == "review-operator"


def test_rename_skill_blocks_existing_destination_directory(
    tmp_path: Path,
    skill_safe_write: SafeWriteUseCase,
) -> None:
    repository = LocalAgentSkillRepository(
        project_root=tmp_path,
        safe_write_use_case=skill_safe_write,
    )
    created = CreateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        CreateSkillCommand(
            name="Review Helper",
            description="Review implementation changes safely.",
            scope=LatentSkillScope.project,
            origin="test",
            targets=[],
        )
    )
    (tmp_path / ".umem" / "skills" / "review-operator").mkdir()

    with pytest.raises(StorageError, match="Destination skill directory already exists"):
        RenameSkillUseCase(project_root=tmp_path, repository=repository).execute(
            RenameSkillCommand(
                skill_id_or_name=created.agent_skill.id,
                slug="review-operator",
                origin="test",
            )
        )
