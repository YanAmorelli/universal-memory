from __future__ import annotations

from pathlib import Path

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    CreateSkillDraftCommand,
    CreateSkillDraftUseCase,
    PublishSkillCommand,
    PublishSkillUseCase,
)
from universal_memory.domain.entities import AgentSkillStatus, LatentSkillScope
from universal_memory.infrastructure.storage import LocalAgentSkillRepository


def test_draft_create_writes_draft_without_native_sync(
    tmp_path: Path,
    skill_safe_write: SafeWriteUseCase,
) -> None:
    repository = LocalAgentSkillRepository(
        project_root=tmp_path,
        safe_write_use_case=skill_safe_write,
    )

    result = CreateSkillDraftUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        CreateSkillDraftCommand(
            name="Review Helper",
            description="Review implementation changes safely.",
            scope=LatentSkillScope.project,
            origin="test",
            triggers=["review changes"],
        )
    )

    stored = repository.read(result.agent_skill.id)
    assert stored.status == AgentSkillStatus.draft
    assert stored.draft_path == ".umem/drafts/skills/review-helper/SKILL.md"
    assert result.validation is not None
    assert not (tmp_path / ".agents" / "skills" / "review-helper").exists()


def test_publish_draft_validates_and_syncs_only_when_requested(
    tmp_path: Path,
    skill_safe_write: SafeWriteUseCase,
) -> None:
    repository = LocalAgentSkillRepository(
        project_root=tmp_path,
        safe_write_use_case=skill_safe_write,
    )
    draft = CreateSkillDraftUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        CreateSkillDraftCommand(
            name="Review Helper",
            description="Review implementation changes safely.",
            scope=LatentSkillScope.project,
            origin="test",
            triggers=["review changes"],
        )
    )
    publish = PublishSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    )

    canonical_only = publish.execute(
        PublishSkillCommand(draft_or_path=draft.agent_skill.id, origin="test")
    )
    assert canonical_only.validation.status == "pass"
    assert canonical_only.native_installations == []
    assert not (tmp_path / ".agents" / "skills" / "review-helper").exists()

    second_draft = CreateSkillDraftUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        CreateSkillDraftCommand(
            name="Sync Review Helper",
            description="Review implementation changes safely.",
            scope=LatentSkillScope.project,
            origin="test",
            triggers=["review changes"],
        )
    )
    synced = publish.execute(
        PublishSkillCommand(draft_or_path=second_draft.agent_skill.id, origin="test", sync=True)
    )
    assert synced.native_installations
    assert (tmp_path / ".agents" / "skills" / "sync-review-helper" / "SKILL.md").is_file()
