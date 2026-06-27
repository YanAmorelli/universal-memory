from __future__ import annotations

from tests.application.skills.conftest import sample_agent_skill
from universal_memory.application.skills import CreateSkillDraftCommand, DraftSkillResult
from universal_memory.interfaces.cli.init_command import main as cli_main


def test_skills_draft_create_help_mentions_name_and_validate(capsys) -> None:
    exit_code = cli_main(["skills", "draft", "create", "--help"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "--name" in output
    assert "--description" in output


def test_skills_draft_create_uses_cli_origin(capsys) -> None:
    seen: list[CreateSkillDraftCommand] = []

    def draft(command: CreateSkillDraftCommand) -> DraftSkillResult:
        seen.append(command)
        skill = sample_agent_skill(name=command.name, slug="review-helper")
        return DraftSkillResult(
            agent_skill=skill,
            slug="review-helper",
            draft_path=".umem/drafts/skills/review-helper/SKILL.md",
            affected_paths=[".umem/drafts/skills/review-helper/SKILL.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        )

    exit_code = cli_main(
        [
            "skills",
            "draft",
            "create",
            "--name",
            "Review Helper",
            "--description",
            "Review implementation changes safely.",
            "--format",
            "json",
        ],
        create_skill_draft_command=draft,
    )

    assert exit_code == 0
    assert seen[0].origin == "cli"
    assert seen[0].name == "Review Helper"
