from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from universal_memory.application.skills import (
    CreateSkillCommand,
    CreateSkillResult,
)
from universal_memory.domain.entities import AgentSkill, AgentSkillStatus, LatentSkillScope
from universal_memory.interfaces.cli.init_command import main as cli_main


def make_result() -> CreateSkillResult:
    now = datetime.now(UTC)
    skill = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Launch Funnel Operator",
        slug="launch-funnel-operator",
        description="Operate launch funnel: CTAs and UTMs.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/launch-funnel-operator/SKILL.md",
        origin="cli",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"triggers": ["when creating launch schedules"], "creation_flow": "direct"},
    )
    return CreateSkillResult(
        agent_skill=skill,
        slug="launch-funnel-operator",
        skill_dir=".umem/skills/launch-funnel-operator",
        skill_file=".umem/skills/launch-funnel-operator/SKILL.md",
        created_paths=[".umem/skills/launch-funnel-operator/SKILL.md"],
        affected_paths=[".umem/skills/launch-funnel-operator/SKILL.md"],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def test_skills_create_json_uses_cli_origin_and_success_envelope(capsys) -> None:
    seen: list[CreateSkillCommand] = []

    def create(command: CreateSkillCommand) -> CreateSkillResult:
        seen.append(command)
        return make_result()

    exit_code = cli_main(
        [
            "skills",
            "create",
            "--name",
            "Launch Funnel Operator",
            "--description",
            "Operate launch funnel: CTAs and UTMs.",
            "--trigger",
            "when creating launch schedules",
            "--scope",
            "project",
            "--visibility",
            "shared",
            "--category",
            "user-facing",
            "--format",
            "json",
        ],
        create_skill_command=create,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == [
        CreateSkillCommand(
            name="Launch Funnel Operator",
            description="Operate launch funnel: CTAs and UTMs.",
            scope=LatentSkillScope.project,
            origin="cli",
            triggers=["when creating launch schedules"],
            visibility="shared",
            category="user-facing",
        )
    ]
    assert payload["operation"] == "skills.create"
    assert payload["scope"] == "project"
    assert payload["data"]["skill_file"] == ".umem/skills/launch-funnel-operator/SKILL.md"


def test_skills_create_human_output(capsys) -> None:
    exit_code = cli_main(
        [
            "skills",
            "create",
            "--name",
            "Launch Funnel Operator",
            "--description",
            "Operate launch funnel.",
            "--trigger",
            "when creating launch schedules",
        ],
        create_skill_command=lambda _command: make_result(),
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Operation: skills.create" in output
    assert ".umem/skills/launch-funnel-operator/SKILL.md" in output
