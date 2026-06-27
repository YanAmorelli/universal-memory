from __future__ import annotations

from tests.application.skills.conftest import sample_agent_skill
from tests.interfaces.conftest import summary_lines
from universal_memory.application.skills import (
    AdoptSkillCommand,
    AdoptSkillResult,
    CleanupPlan,
    CleanupSkillCommand,
    CleanupSkillResult,
    CreateSkillCommand,
    CreateSkillDraftCommand,
    CreateSkillResult,
    DraftSkillResult,
    SkillValidationReport,
    SyncSkillResult,
    SyncSkillsCommand,
    SyncSkillsResult,
    ValidateSkillCommand,
    ValidateSkillResult,
)
from universal_memory.interfaces.cli.init_command import main as cli_main


def test_skills_create_summary_outputs_concise_payload(capsys) -> None:
    def create(command: CreateSkillCommand) -> CreateSkillResult:
        skill = sample_agent_skill(name=command.name, slug=command.slug or "review-helper")
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

    exit_code = cli_main(
        [
            "skills",
            "create",
            "--name",
            "Review Helper",
            "--description",
            "Review implementation changes safely.",
            "--format",
            "summary",
        ],
        create_skill_command=create,
    )

    assert exit_code == 0
    lines = summary_lines(capsys.readouterr().out)
    assert "Operation: skills.create" in lines
    assert any(".umem/skills/review-helper/SKILL.md" in line for line in lines)
    assert "Native targets: not synced by this command" in lines
    assert any("umem skills sync review-helper" in line for line in lines)


def test_skills_draft_create_summary_outputs_draft_path(capsys) -> None:
    def draft(command: CreateSkillDraftCommand) -> DraftSkillResult:
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
            "summary",
        ],
        create_skill_draft_command=draft,
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Operation: skills.draft.create" in output
    assert ".umem/drafts/skills/review-helper/SKILL.md" in output
    assert "umem skills draft validate review-helper" in output


def test_skills_adopt_validate_sync_and_cleanup_summary(capsys) -> None:
    skill = sample_agent_skill()

    def adopt(command: AdoptSkillCommand) -> AdoptSkillResult:
        return AdoptSkillResult(
            agent_skill=skill,
            slug="review-helper",
            skill_dir=".umem/skills/review-helper",
            skill_file=".umem/skills/review-helper/SKILL.md",
            adopted_source=".umem/skills/review-helper",
            affected_paths=[".umem/skills/review-helper/SKILL.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        )

    def validate(command: ValidateSkillCommand) -> ValidateSkillResult:
        return ValidateSkillResult(
            SkillValidationReport(
                subject=command.skill_or_path,
                status="pass",
                checks=[],
                affected_paths=[".umem/skills/review-helper/SKILL.md"],
            )
        )

    def sync(command: SyncSkillsCommand) -> SyncSkillsResult:
        return SyncSkillsResult(
            skills=[
                SyncSkillResult(
                    skill_id=skill.id,
                    name=skill.name,
                    scope="project",
                    status="active",
                    canonical_path=skill.canonical_path,
                    affected_paths=[".opencode/skills/review-helper/SKILL.md"],
                )
            ],
            affected_paths=[".opencode/skills/review-helper/SKILL.md"],
            warnings=[
                "Warning: Native target is not ignored by git: .opencode/skills/review-helper"
            ],
        )

    def cleanup(command: CleanupSkillCommand) -> CleanupSkillResult:
        return CleanupSkillResult(
            plan=CleanupPlan(
                skill="review-helper",
                mode="targets",
                dry_run=True,
                removable_paths=[".opencode/skills/review-helper"],
            )
        )

    commands = [
        (
            ["skills", "adopt", ".umem/skills/review-helper", "--format", "summary"],
            "skills.adopt",
        ),
        (["skills", "validate", "review-helper", "--format", "summary"], "skills.validate"),
        (
            [
                "skills",
                "sync",
                "review-helper",
                "--check-gitignore",
                "--format",
                "summary",
            ],
            "skills.sync",
        ),
        (["skills", "cleanup", "review-helper", "--format", "summary"], "skills.cleanup"),
    ]

    for argv, operation in commands:
        exit_code = cli_main(
            argv,
            adopt_skill_command=adopt,
            validate_skill_command=validate,
            sync_skills_command=sync,
            cleanup_skill_command=cleanup,
        )
        assert exit_code == 0
        output = capsys.readouterr().out
        assert f"Operation: {operation}" in output
        assert "Next steps:" in output


def test_skills_cleanup_summary_explains_dry_run_apply_and_blocked_paths(capsys) -> None:
    def cleanup(command: CleanupSkillCommand) -> CleanupSkillResult:
        return CleanupSkillResult(
            plan=CleanupPlan(
                skill=command.skill_id_or_name,
                mode="targets",
                dry_run=command.dry_run,
                removable_paths=[".opencode/skills/review-helper"],
                blocked_paths=[".opencode/skills/manual-skill"],
            )
        )

    exit_code = cli_main(
        ["skills", "cleanup", "review-helper", "--format", "summary"],
        cleanup_skill_command=cleanup,
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Mode: dry-run preview" in output
    assert "Removable managed paths:" in output
    assert "Blocked paths:" in output
    assert "umem skills cleanup review-helper --targets --apply" in output


def test_skills_cleanup_apply_summary_shows_removed_without_removable_noise(capsys) -> None:
    def cleanup(command: CleanupSkillCommand) -> CleanupSkillResult:
        return CleanupSkillResult(
            plan=CleanupPlan(
                skill=command.skill_id_or_name,
                mode="targets",
                dry_run=command.dry_run,
                removable_paths=[".opencode/skills/review-helper"],
            ),
            removed_paths=[".opencode/skills/review-helper"],
        )

    exit_code = cli_main(
        ["skills", "cleanup", "review-helper", "--apply", "--format", "summary"],
        cleanup_skill_command=cleanup,
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Mode: apply" in output
    assert "Removed managed paths:" in output
    assert "Removable managed paths:" not in output


def test_skills_sync_summary_explains_gitignore_check_is_diagnostic(capsys) -> None:
    skill = sample_agent_skill()

    def sync(command: SyncSkillsCommand) -> SyncSkillsResult:
        return SyncSkillsResult(
            skills=[
                SyncSkillResult(
                    skill_id=skill.id,
                    name=skill.name,
                    scope="project",
                    status="active",
                    canonical_path=skill.canonical_path,
                    affected_paths=[".opencode/skills/review-helper/SKILL.md"],
                    targets=[
                        {
                            "runtime": "opencode",
                            "path": ".opencode/skills/review-helper",
                            "status": "synced",
                        }
                    ],
                )
            ],
            affected_paths=[".opencode/skills/review-helper/SKILL.md"],
            warnings=[
                "Warning: Native target is not ignored by git: .opencode/skills/review-helper"
            ],
        )

    exit_code = cli_main(
        [
            "skills",
            "sync",
            "review-helper",
            "--check-gitignore",
            "--format",
            "summary",
        ],
        sync_skills_command=sync,
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Gitignore check: ran after target planning/writes." in output
    assert "Gitignore check: diagnostic only; .gitignore was not edited." in output
    assert "Update .gitignore or untrack generated targets if that is policy." in output
