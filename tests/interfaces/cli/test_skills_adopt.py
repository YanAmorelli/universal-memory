from __future__ import annotations

from tests.application.skills.conftest import sample_agent_skill
from universal_memory.application.skills import AdoptSkillCommand, AdoptSkillResult
from universal_memory.interfaces.cli.init_command import main as cli_main


def test_skills_adopt_help_mentions_slug_sync_and_conflicts(capsys) -> None:
    exit_code = cli_main(["skills", "adopt", "--help"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "--slug" in output
    assert "--sync" in output
    assert "Existing skill directory" in output


def test_skills_adopt_passes_slug_sync_and_replace_native(capsys) -> None:
    seen: list[AdoptSkillCommand] = []

    def adopt(command: AdoptSkillCommand) -> AdoptSkillResult:
        seen.append(command)
        skill = sample_agent_skill(slug=command.slug or "review-helper")
        return AdoptSkillResult(
            agent_skill=skill,
            slug=skill.slug,
            skill_dir=f".umem/skills/{skill.slug}",
            skill_file=f".umem/skills/{skill.slug}/SKILL.md",
            adopted_source=".umem/skills/review-helper",
            affected_paths=[f".umem/skills/{skill.slug}/SKILL.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        )

    exit_code = cli_main(
        [
            "skills",
            "adopt",
            ".umem/skills/review-helper",
            "--slug",
            "review-helper",
            "--sync",
            "--replace-native",
            "--format",
            "json",
        ],
        adopt_skill_command=adopt,
    )

    assert exit_code == 0
    assert seen[0].slug == "review-helper"
    assert seen[0].sync_after_adopt is True
    assert seen[0].replace_native is True
