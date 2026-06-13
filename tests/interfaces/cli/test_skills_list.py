from __future__ import annotations

import json

from universal_memory.application.skills import (
    GetSkillDetailCommand,
    GetSkillDetailResult,
    ListSkillsCommand,
    ListSkillsResult,
    SkillListItem,
)
from universal_memory.interfaces.cli.init_command import main as cli_main


def skill_item(
    *,
    name: str = "TDD Recorrente",
    status: str = "active",
    relative_path: str | None = ".umem/skills/tdd-recorrente/SKILL.md",
) -> SkillListItem:
    return SkillListItem(
        name=name,
        scope="project",
        status=status,
        relative_path=relative_path,
        created_at="2026-05-29T12:00:00Z",
        updated_at="2026-05-29T12:05:00Z",
        origin="cli",
        audit_reference="audit-1",
    )


def test_skills_list_human_output_shows_table_content(capsys) -> None:
    seen: list[ListSkillsCommand] = []

    def list_skills(command: ListSkillsCommand) -> ListSkillsResult:
        seen.append(command)
        return ListSkillsResult(
            skills=[
                skill_item(),
                skill_item(
                    name="Brainstorm Guiado",
                    status="candidate",
                    relative_path=None,
                ),
                skill_item(name="Formato Antigo", status="disabled"),
            ]
        )

    exit_code = cli_main(["skills", "list"], list_skills_command=list_skills)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert seen == [ListSkillsCommand()]
    assert "TDD Recorrente" in output
    assert "active" in output
    assert "candidate" in output
    assert "disabled" in output
    assert ".umem/skills/tdd-recorrente/SKILL.md" in output
    assert "cli" in output
    assert "2026-05-29T12:00:00Z" in output


def test_skills_list_empty_human_output_suggests_actionable_next_step(capsys) -> None:
    def list_skills(command: ListSkillsCommand) -> ListSkillsResult:
        return ListSkillsResult(
            skills=[],
            recommended_action=(
                "Latent skills aparecem quando o universal-memory registra evidencias recorrentes. "
                "Use `umem skills track --name ... --description ... --evidence-summary ...` "
                "para capturar evidencia explicita; depois rode `umem skills recommend`."
            ),
        )

    exit_code = cli_main(["skills", "list"], list_skills_command=list_skills)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "No skills registered" in output
    assert "umem skills track" in output
    assert "umem skills recommend" in output
    assert "umem remember" not in output
    assert "umem skills propose" not in output


def test_skills_list_json_is_pure_success_envelope(capsys) -> None:
    def list_skills(command: ListSkillsCommand) -> ListSkillsResult:
        return ListSkillsResult(skills=[skill_item()])

    exit_code = cli_main(
        ["skills", "list", "--format", "json"],
        list_skills_command=list_skills,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "ok": True,
        "operation": "skills.list",
        "scope": "all",
        "data": {
            "skills": [
                {
                    "name": "TDD Recorrente",
                    "scope": "project",
                    "status": "active",
                    "relative_path": ".umem/skills/tdd-recorrente/SKILL.md",
                    "created_at": "2026-05-29T12:00:00Z",
                    "updated_at": "2026-05-29T12:05:00Z",
                    "origin": "cli",
                    "audit_reference": "audit-1",
                }
            ]
        },
        "warnings": [],
    }


def test_skills_detail_json_uses_standard_envelope(capsys) -> None:
    seen: list[GetSkillDetailCommand] = []

    def get_detail(command: GetSkillDetailCommand) -> GetSkillDetailResult:
        seen.append(command)
        return GetSkillDetailResult(
            name="TDD Recorrente",
            scope="project",
            status="active",
            relative_path=".umem/skills/tdd-recorrente/SKILL.md",
            triggers=["red green refactor", "implementar story"],
            audit_reference="audit-1",
            references_loaded=False,
        )

    exit_code = cli_main(
        ["skills", "detail", "TDD Recorrente", "--format", "json"],
        get_skill_detail_command=get_detail,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == [GetSkillDetailCommand(name_or_id="TDD Recorrente")]
    assert payload == {
        "ok": True,
        "operation": "skills.detail",
        "scope": "project",
        "data": {
            "name": "TDD Recorrente",
            "scope": "project",
            "status": "active",
            "relative_path": ".umem/skills/tdd-recorrente/SKILL.md",
            "triggers": ["red green refactor", "implementar story"],
            "audit_reference": "audit-1",
            "references_loaded": False,
        },
        "warnings": [],
    }
