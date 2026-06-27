from __future__ import annotations

from tests.application.skills.conftest import sample_agent_skill
from universal_memory.application.skills import (
    CleanupPlan,
    CleanupSkillCommand,
    CleanupSkillResult,
    RenameSkillCommand,
    RenameSkillResult,
    RepairSkillsCommand,
    RepairSkillsResult,
)
from universal_memory.interfaces.cli.init_command import main as cli_main


def test_skills_maintenance_help_mentions_supported_commands(capsys) -> None:
    for argv, expected in [
        (["skills", "canonical", "update", "--help"], "--sync"),
        (["skills", "create", "--help"], "not synced unless --sync"),
        (["skills", "draft", "create", "--help"], "without native side effects"),
        (["skills", "publish", "--help"], "Default is canonical-only"),
        (["skills", "adopt", "--help"], ".agents/skills"),
        (["skills", "rename", "--help"], "--slug"),
        (["skills", "validate", "--help"], "Skill id"),
        (["skills", "sync", "--help"], "does not edit .gitignore"),
        (["skills", "cleanup", "--help"], "dry-run"),
        (["skills", "repair", "--help"], "dry-run"),
    ]:
        assert cli_main(argv) == 0
        assert expected in capsys.readouterr().out


def test_skills_rename_and_cleanup_use_cli_origin(capsys) -> None:
    seen_rename: list[RenameSkillCommand] = []
    seen_cleanup: list[CleanupSkillCommand] = []

    def rename(command: RenameSkillCommand) -> RenameSkillResult:
        seen_rename.append(command)
        skill = sample_agent_skill(slug=command.slug)
        return RenameSkillResult(
            agent_skill=skill,
            old_path=".umem/skills/review-helper/SKILL.md",
            new_path=f".umem/skills/{command.slug}/SKILL.md",
            affected_paths=[".umem/skills/review-helper/SKILL.md"],
        )

    def cleanup(command: CleanupSkillCommand) -> CleanupSkillResult:
        seen_cleanup.append(command)
        return CleanupSkillResult(
            CleanupPlan(
                skill=command.skill_id_or_name,
                mode="targets",
                dry_run=command.dry_run,
                removable_paths=[".opencode/skills/review-helper"],
            )
        )

    assert (
        cli_main(
            ["skills", "rename", "review-helper", "--slug", "review-operator"],
            rename_skill_command=rename,
        )
        == 0
    )
    assert (
        cli_main(
            ["skills", "cleanup", "review-helper", "--apply"],
            cleanup_skill_command=cleanup,
        )
        == 0
    )
    assert seen_rename[0].origin == "cli"
    assert seen_cleanup[0].origin == "cli"
    assert seen_cleanup[0].dry_run is False


def test_skills_repair_summary_explains_noop_and_apply(capsys) -> None:
    seen: list[RepairSkillsCommand] = []

    def repair(command: RepairSkillsCommand) -> RepairSkillsResult:
        seen.append(command)
        return RepairSkillsResult(
            plans=[
                CleanupPlan(
                    skill="orphan-skill",
                    mode="orphan_targets",
                    dry_run=command.dry_run,
                    removable_paths=[".opencode/skills/orphan-skill"],
                )
            ],
        )

    exit_code = cli_main(
        [
            "skills",
            "repair",
            "--remove-orphan-targets",
            "--format",
            "summary",
        ],
        repair_skills_command=repair,
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert seen[0].dry_run is True
    assert "Mode: dry-run preview" in output
    assert "Removable orphan targets:" in output
    assert "umem skills repair --remove-orphan-targets --apply" in output
