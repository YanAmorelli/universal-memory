from __future__ import annotations

from tests.application.skills.conftest import sample_agent_skill
from universal_memory.application.skills import (
    CleanupPlan,
    CleanupSkillCommand,
    CleanupSkillResult,
    CreateSkillCommand,
    CreateSkillResult,
    PublishSkillCommand,
    PublishSkillResult,
    RenameSkillCommand,
    RenameSkillResult,
    RepairSkillsCommand,
    RepairSkillsResult,
    SkillValidationReport,
    SyncSkillsCommand,
    SyncSkillsResult,
    UpdateCanonicalSkillCommand,
    UpdateCanonicalSkillResult,
)
from universal_memory.interfaces.cli.init_command import main as cli_main


def test_skills_authoring_commands_preserve_safe_defaults_and_flags(capsys) -> None:
    seen_create: list[CreateSkillCommand] = []
    seen_publish: list[PublishSkillCommand] = []
    seen_update: list[UpdateCanonicalSkillCommand] = []
    seen_sync: list[SyncSkillsCommand] = []

    def create(command: CreateSkillCommand) -> CreateSkillResult:
        seen_create.append(command)
        skill = sample_agent_skill(name=command.name, slug="review-helper")
        return CreateSkillResult(
            agent_skill=skill,
            slug=skill.slug,
            skill_dir=".umem/skills/review-helper",
            skill_file=".umem/skills/review-helper/SKILL.md",
            created_paths=[".umem/skills/review-helper/SKILL.md"],
            affected_paths=[".umem/skills/review-helper/SKILL.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        )

    def publish(command: PublishSkillCommand) -> PublishSkillResult:
        seen_publish.append(command)
        skill = sample_agent_skill(slug="review-helper")
        return PublishSkillResult(
            agent_skill=skill,
            slug=skill.slug,
            skill_dir=".umem/skills/review-helper",
            skill_file=".umem/skills/review-helper/SKILL.md",
            affected_paths=[".umem/skills/review-helper/SKILL.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
            validation=SkillValidationReport(
                subject="review-helper",
                status="pass",
                checks=[],
                affected_paths=[".umem/skills/review-helper/SKILL.md"],
            ),
        )

    def update(command: UpdateCanonicalSkillCommand) -> UpdateCanonicalSkillResult:
        seen_update.append(command)
        skill = sample_agent_skill(slug="review-helper")
        return UpdateCanonicalSkillResult(
            agent_skill=skill,
            skill_file=".umem/skills/review-helper/SKILL.md",
            validation=SkillValidationReport(
                subject="review-helper",
                status="pass",
                checks=[],
                affected_paths=[".umem/skills/review-helper/SKILL.md"],
            ),
            affected_paths=[".umem/skills/review-helper/SKILL.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        )

    def sync(command: SyncSkillsCommand) -> SyncSkillsResult:
        seen_sync.append(command)
        return SyncSkillsResult(skills=[])

    assert (
        cli_main(
            [
                "skills",
                "create",
                "--name",
                "Review Helper",
                "--description",
                "Review implementation changes safely.",
                "--format",
                "json",
            ],
            create_skill_command=create,
        )
        == 0
    )
    assert (
        cli_main(
            ["skills", "publish", "review-helper", "--format", "json"],
            publish_skill_command=publish,
        )
        == 0
    )
    assert (
        cli_main(
            [
                "skills",
                "canonical",
                "update",
                "review-helper",
                "--file",
                ".umem/skills/review-helper/SKILL.md",
                "--sync",
                "--format",
                "json",
            ],
            update_canonical_skill_command=update,
        )
        == 0
    )
    assert (
        cli_main(
            ["skills", "sync", "review-helper", "--check-gitignore", "--format", "json"],
            sync_skills_command=sync,
        )
        == 0
    )

    assert seen_create[0].sync is False
    assert seen_publish[0].sync is False
    assert seen_update[0].sync is True
    assert seen_sync[0].check_gitignore is True
    capsys.readouterr()


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
