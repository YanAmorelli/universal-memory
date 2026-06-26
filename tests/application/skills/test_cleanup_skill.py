from __future__ import annotations

from pathlib import Path

from tests.application.skills.conftest import sample_agent_skill
from universal_memory.application.skills import (
    CleanupSkillCommand,
    CleanupSkillUseCase,
    RepairSkillsCommand,
    RepairSkillsUseCase,
)
from universal_memory.infrastructure.storage import LocalAgentSkillRepository


def test_cleanup_dry_run_and_apply_remove_only_manifest_managed_targets(
    tmp_path: Path,
    agent_skill_repository: LocalAgentSkillRepository,
) -> None:
    managed = tmp_path / ".opencode" / "skills" / "review-helper" / "SKILL.md"
    unmanaged = tmp_path / ".agents" / "skills" / "review-helper" / "SKILL.md"
    managed.parent.mkdir(parents=True)
    unmanaged.parent.mkdir(parents=True)
    managed.write_text("managed\n", encoding="utf-8")
    unmanaged.write_text("unmanaged\n", encoding="utf-8")
    skill = sample_agent_skill(
        native_installations=[
            {"path": ".opencode/skills/review-helper", "manifest": ["SKILL.md"]},
            {"path": ".agents/skills/review-helper", "manifest": []},
        ]
    )
    agent_skill_repository.write(skill)

    use_case = CleanupSkillUseCase(project_root=tmp_path, repository=agent_skill_repository)
    preview = use_case.execute(CleanupSkillCommand("review-helper", origin="test"))
    applied = use_case.execute(
        CleanupSkillCommand("review-helper", origin="test", dry_run=False)
    )

    assert preview.plan.removable_paths == [".opencode/skills/review-helper"]
    assert preview.plan.blocked_paths == [".agents/skills/review-helper"]
    assert applied.removed_paths == [".opencode/skills/review-helper"]
    assert not managed.parent.exists()
    assert unmanaged.is_file()


def test_repair_dry_run_lists_orphan_native_targets(
    tmp_path: Path,
    agent_skill_repository: LocalAgentSkillRepository,
) -> None:
    orphan = tmp_path / ".opencode" / "skills" / "orphan-helper" / "SKILL.md"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("orphan\n", encoding="utf-8")

    result = RepairSkillsUseCase(project_root=tmp_path, repository=agent_skill_repository).execute(
        RepairSkillsCommand(origin="test", remove_orphan_targets=True)
    )

    assert result.plans[0].removable_paths == [".opencode/skills/orphan-helper"]
    assert orphan.is_file()
