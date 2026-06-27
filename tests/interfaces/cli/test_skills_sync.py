from __future__ import annotations

import json
import sys

import pytest

from universal_memory.application.skills import SyncSkillResult, SyncSkillsCommand, SyncSkillsResult
from universal_memory.interfaces.cli.init_command import main as cli_main


def test_skills_sync_json_uses_cli_origin_targets_and_success_envelope(capsys) -> None:
    seen: list[SyncSkillsCommand] = []

    def sync(command: SyncSkillsCommand) -> SyncSkillsResult:
        seen.append(command)
        return SyncSkillsResult(
            skills=[
                SyncSkillResult(
                    skill_id="skill-1",
                    name="Repair Skill",
                    scope="project",
                    status="active",
                    canonical_path=".umem/skills/repair-skill/SKILL.md",
                    affected_paths=[
                        ".opencode/skills/repair-skill/SKILL.md",
                        ".opencode/skills/repair-skill/references/old.md",
                    ],
                    removed_paths=[".opencode/skills/repair-skill/references/old.md"],
                    targets=[
                        {
                            "runtime": "opencode",
                            "path": ".opencode/skills/repair-skill",
                            "status": "synced",
                            "drift_detected": False,
                            "canonical_hash": "canonical",
                            "target_hash": "target",
                            "hash_algorithm": "manifest_tree_sha256",
                            "audit_reference": "audit-1",
                            "snapshot_reference": "snapshot-1",
                            "affected_paths": ["SKILL.md"],
                            "removed_paths": ["references/old.md"],
                        }
                    ],
                    audit_reference="audit-1",
                    snapshot_reference="snapshot-1",
                )
            ],
            affected_paths=[
                ".opencode/skills/repair-skill/SKILL.md",
                ".opencode/skills/repair-skill/references/old.md",
            ],
            removed_paths=[".opencode/skills/repair-skill/references/old.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        )

    exit_code = cli_main(
        [
            "skills",
            "sync",
            "Repair Skill",
            "--target",
            "opencode",
            "--format",
            "json",
            "--check-gitignore",
        ],
        sync_skills_command=sync,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == [
        SyncSkillsCommand(
            skill_id_or_name="Repair Skill",
            targets=["opencode"],
            drift_decision="keep",
            origin="cli",
            check_gitignore=True,
        )
    ]
    assert payload["operation"] == "skills.sync"
    assert payload["data"]["removed_paths"] == [".opencode/skills/repair-skill/references/old.md"]
    assert payload["data"]["skills"][0]["removed_paths"] == [
        ".opencode/skills/repair-skill/references/old.md"
    ]
    assert payload["data"]["skills"][0]["targets"][0]["removed_paths"] == ["references/old.md"]
    assert payload["data"]["skills"][0]["targets"][0]["hash_algorithm"] == "manifest_tree_sha256"
    assert payload["data"]["skills"][0]["targets"][0]["status"] == "synced"


def test_skills_sync_human_outputs_native_targets_and_worktree_note(capsys) -> None:
    def sync(command: SyncSkillsCommand) -> SyncSkillsResult:
        return SyncSkillsResult(
            skills=[
                SyncSkillResult(
                    skill_id="skill-1",
                    name="Repair Skill",
                    scope="project",
                    status="active",
                    canonical_path=".umem/skills/repair-skill/SKILL.md",
                    affected_paths=[
                        ".opencode/skills/repair-skill/SKILL.md",
                        ".opencode/skills/repair-skill/references/old.md",
                    ],
                    removed_paths=[".opencode/skills/repair-skill/references/old.md"],
                    targets=[
                        {
                            "runtime": "opencode",
                            "path": ".opencode/skills/repair-skill",
                            "status": "synced",
                        }
                    ],
                )
            ],
            affected_paths=[
                ".opencode/skills/repair-skill/SKILL.md",
                ".opencode/skills/repair-skill/references/old.md",
            ],
            removed_paths=[".opencode/skills/repair-skill/references/old.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        )

    exit_code = cli_main(["skills", "sync", "Repair Skill"], sync_skills_command=sync)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Native runtime targets:" in output
    assert ".opencode/skills/repair-skill (synced)" in output
    assert "Removed managed paths:" in output
    assert ".opencode/skills/repair-skill/references/old.md" in output
    assert output.count(".opencode/skills/repair-skill/references/old.md") == 1
    assert "Review git status and ignore rules intentionally" in output


def test_skills_sync_human_prompts_overwrite_only_after_managed_drift(
    capsys,
    monkeypatch,
) -> None:
    seen: list[SyncSkillsCommand] = []

    def result_for(status: str) -> SyncSkillsResult:
        return SyncSkillsResult(
            skills=[
                SyncSkillResult(
                    skill_id="skill-1",
                    name="Repair Skill",
                    scope="project",
                    status="active",
                    canonical_path=".umem/skills/repair-skill/SKILL.md",
                    targets=[
                        {
                            "runtime": "opencode",
                            "path": ".opencode/skills/repair-skill",
                            "status": status,
                            "drift_detected": status == "drift_kept",
                        }
                    ],
                )
            ],
        )

    def sync(command: SyncSkillsCommand) -> SyncSkillsResult:
        seen.append(command)
        if command.drift_decision == "overwrite":
            return result_for("overwritten")
        return result_for("drift_kept")

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")

    exit_code = cli_main(
        ["skills", "sync", "Repair Skill"],
        sync_skills_command=sync,
    )

    assert exit_code == 0
    assert [command.drift_decision for command in seen] == ["keep", "overwrite"]
    assert "Operation: skills.sync" in capsys.readouterr().out


def test_skills_sync_human_does_not_prompt_for_unmanaged_native(capsys, monkeypatch) -> None:
    seen: list[SyncSkillsCommand] = []

    def sync(command: SyncSkillsCommand) -> SyncSkillsResult:
        seen.append(command)
        return SyncSkillsResult(
            skills=[
                SyncSkillResult(
                    skill_id="skill-1",
                    name="Repair Skill",
                    scope="project",
                    status="active",
                    canonical_path=".umem/skills/repair-skill/SKILL.md",
                    targets=[
                        {
                            "runtime": "opencode",
                            "path": ".opencode/skills/repair-skill",
                            "status": "unmanaged_native",
                            "drift_detected": True,
                        }
                    ],
                )
            ],
        )

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("unexpected prompt"))

    exit_code = cli_main(
        ["skills", "sync", "Repair Skill"],
        sync_skills_command=sync,
    )

    assert exit_code == 0
    assert [command.drift_decision for command in seen] == ["keep"]
    assert "Operation: skills.sync" in capsys.readouterr().out
