from __future__ import annotations

from pathlib import Path

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    CreateSkillCommand,
    CreateSkillUseCase,
    UpdateCanonicalSkillCommand,
    UpdateCanonicalSkillUseCase,
)
from universal_memory.domain.entities import LatentSkillScope
from universal_memory.infrastructure.storage import LocalAgentSkillRepository


def test_canonical_update_validates_content_and_can_sync(
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
    markdown = (
        "---\n"
        'name: "Review Helper"\n'
        'description: "Updated review flow."\n'
        "triggers:\n"
        '  - "review changes"\n'
        "---\n\n"
        "# Review Helper\n\nUpdated body.\n"
    )

    result = UpdateCanonicalSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        UpdateCanonicalSkillCommand(
            skill_id_or_name=created.agent_skill.id,
            raw_markdown=markdown,
            origin="test",
            sync=True,
        )
    )

    assert result.validation.status == "pass"
    assert result.agent_skill.description == "Updated review flow."
    assert ".agents/skills/review-helper/SKILL.md" in result.affected_paths
    assert repository.read(created.agent_skill.id).native_installations


def test_canonical_update_file_validates_links_relative_to_source_directory(
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
            name="Reference Helper",
            description="Uses local references.",
            scope=LatentSkillScope.project,
            origin="test",
            targets=[],
        )
    )
    skill_dir = tmp_path / ".umem" / "skills" / "reference-helper"
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "checklist.md").write_text("Checklist.\n", encoding="utf-8")
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\n"
        'name: "Reference Helper"\n'
        'description: "Uses local references."\n'
        "triggers:\n"
        '  - "reference review"\n'
        "---\n\n"
        "Use [checklist](references/checklist.md).\n",
        encoding="utf-8",
    )

    result = UpdateCanonicalSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=skill_safe_write,
    ).execute(
        UpdateCanonicalSkillCommand(
            skill_id_or_name=created.agent_skill.id,
            file=".umem/skills/reference-helper/SKILL.md",
            origin="test",
        )
    )

    assert result.validation.status == "pass"
