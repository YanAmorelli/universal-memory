from __future__ import annotations

import subprocess
from pathlib import Path

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    CreateSkillCommand,
    CreateSkillUseCase,
    SyncSkillsCommand,
    SyncSkillsUseCase,
)
from universal_memory.domain.entities import LatentSkillScope
from universal_memory.infrastructure.storage import LocalAgentSkillRepository


def test_sync_check_gitignore_warns_for_unignored_native_target(
    tmp_path: Path,
    skill_safe_write: SafeWriteUseCase,
) -> None:
    _git_init(tmp_path)
    repository = LocalAgentSkillRepository(
        project_root=tmp_path,
        safe_write_use_case=skill_safe_write,
    )
    CreateSkillUseCase(
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

    result = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        SyncSkillsCommand(origin="test", targets=["opencode"], check_gitignore=True)
    )

    assert any(
        "not ignored by git: .opencode/skills/review-helper" in item
        for item in result.warnings
    )
    assert result.skills[0].warnings == result.warnings


def test_sync_check_gitignore_warns_for_tracked_native_target(
    tmp_path: Path,
    skill_safe_write: SafeWriteUseCase,
) -> None:
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text(".opencode/skills/\n", encoding="utf-8")
    repository = LocalAgentSkillRepository(
        project_root=tmp_path,
        safe_write_use_case=skill_safe_write,
    )
    CreateSkillUseCase(
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
    native_file = tmp_path / ".opencode" / "skills" / "review-helper" / "SKILL.md"
    native_file.parent.mkdir(parents=True)
    native_file.write_text("tracked native skill\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-f", ".opencode/skills/review-helper/SKILL.md"],  # noqa: S607
        cwd=tmp_path,
        check=True,
    )

    result = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        SyncSkillsCommand(origin="test", targets=["opencode"], check_gitignore=True)
    )

    assert any(
        "tracked by git: .opencode/skills/review-helper" in item for item in result.warnings
    )


def _git_init(path: Path) -> None:
    subprocess.run(
        ["git", "init"],  # noqa: S607
        cwd=path,
        check=True,
        stdout=subprocess.DEVNULL,
    )
