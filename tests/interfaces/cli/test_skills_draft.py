from __future__ import annotations

from tests.application.skills.conftest import sample_agent_skill
from universal_memory.application.skills import CreateSkillDraftCommand, DraftSkillResult
from universal_memory.interfaces.cli.init_command import main as cli_main


def test_skills_draft_create_accepts_required_authoring_options(capsys) -> None:
    seen: list[CreateSkillDraftCommand] = []

    def draft(command: CreateSkillDraftCommand) -> DraftSkillResult:
        seen.append(command)
        skill = sample_agent_skill(name=command.name, slug=command.slug or "review-helper")
        return DraftSkillResult(
            agent_skill=skill,
            slug=skill.slug,
            draft_path=f".umem/drafts/skills/{skill.slug}/SKILL.md",
            affected_paths=[f".umem/drafts/skills/{skill.slug}/SKILL.md"],
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
            "--slug",
            "review-helper",
            "--trigger",
            "when reviewing code",
            "--format",
            "json",
        ],
        create_skill_draft_command=draft,
    )

    assert exit_code == 0
    assert seen[0].name == "Review Helper"
    assert seen[0].description == "Review implementation changes safely."
    assert seen[0].slug == "review-helper"
    assert seen[0].triggers == ["when reviewing code"]
    capsys.readouterr()


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
