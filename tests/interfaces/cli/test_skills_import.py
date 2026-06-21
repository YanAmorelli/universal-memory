from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from universal_memory.application.skills import ImportSkillCommand, ImportSkillResult
from universal_memory.domain.entities import AgentSkill, AgentSkillStatus, LatentSkillScope
from universal_memory.interfaces.cli.init_command import main as cli_main


def make_result() -> ImportSkillResult:
    now = datetime.now(UTC)
    skill = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Review Helper",
        slug="review-helper",
        description="Review code with focused checks.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/review-helper/SKILL.md",
        origin="cli",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"triggers": ["when reviewing code"], "creation_flow": "import"},
    )
    return ImportSkillResult(
        agent_skill=skill,
        slug="review-helper",
        skill_dir=".umem/skills/review-helper",
        skill_file=".umem/skills/review-helper/SKILL.md",
        created_paths=[".umem/skills/review-helper/SKILL.md"],
        affected_paths=[".umem/skills/review-helper/SKILL.md"],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def test_skills_import_json_uses_cli_origin_and_replace_native(capsys) -> None:
    seen: list[ImportSkillCommand] = []

    def import_skill(command: ImportSkillCommand) -> ImportSkillResult:
        seen.append(command)
        return make_result()

    exit_code = cli_main(
        [
            "skills",
            "import",
            "native/review-helper/SKILL.md",
            "--scope",
            "project",
            "--replace-native",
            "--format",
            "json",
        ],
        import_skill_command=import_skill,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == [
        ImportSkillCommand(
            path=Path("native/review-helper/SKILL.md"),
            scope=LatentSkillScope.project,
            origin="cli",
            replace_native=True,
            sync_after_import=False,
        )
    ]
    assert payload["operation"] == "skills.import"
    assert payload["scope"] == "project"
    assert payload["data"]["skill_file"] == ".umem/skills/review-helper/SKILL.md"
    assert payload["data"]["native_installations"] == []
    assert "canonical .umem/skills registry" in payload["data"]["native_installations_note"]
    assert (
        "Supported compatible native targets can be adopted during import"
        in payload["data"]["native_installations_note"]
    )
    assert "complete synchronized copies" in payload["data"]["native_installations_note"]


def test_skills_import_human_output(capsys) -> None:
    exit_code = cli_main(
        ["skills", "import", "native/review-helper"],
        import_skill_command=lambda _command: make_result(),
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Operation: skills.import" in output
    assert ".umem/skills/review-helper/SKILL.md" in output
    assert "Canonical path: .umem/skills/review-helper/SKILL.md" in output
    assert "Import note:" in output
    assert "Native target note:" in output
    assert "native runtime copies" in output
    assert "--replace-native" in output
    assert "re-run import with `--sync`" in output


def test_skills_import_sync_flag_uses_cli_origin_and_sync_after_import(capsys) -> None:
    seen: list[ImportSkillCommand] = []

    def import_skill(command: ImportSkillCommand) -> ImportSkillResult:
        seen.append(command)
        return make_result()

    exit_code = cli_main(
        [
            "skills",
            "import",
            "native/review-helper",
            "--scope",
            "project",
            "--sync",
            "--format",
            "json",
        ],
        import_skill_command=import_skill,
    )

    assert exit_code == 0
    assert seen == [
        ImportSkillCommand(
            path=Path("native/review-helper"),
            scope=LatentSkillScope.project,
            origin="cli",
            replace_native=False,
            sync_after_import=True,
        )
    ]
