from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from universal_memory.application.skills import (
    GenerateSkillCommand,
    GenerateSkillResult,
)
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.interfaces.cli.init_command import main as cli_main


def make_result(
    *, collision_detected: bool = False, suggested_slug: str | None = None
) -> GenerateSkillResult:
    now = datetime.now(UTC)
    skill = LatentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="TDD Recorrente",
        description="Executa red green refactor",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.active,
        recurrence_count=4,
        metadata={},
    )
    return GenerateSkillResult(
        latent_skill=skill,
        slug="tdd-recorrente",
        skill_dir=".umem/skills/tdd-recorrente",
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        created_paths=[
            ".umem/skills/tdd-recorrente/SKILL.md",
            ".umem/skills/tdd-recorrente/scripts/.gitkeep",
        ],
        affected_paths=[
            ".umem/skills/tdd-recorrente/SKILL.md",
            ".umem/skills/tdd-recorrente/scripts/.gitkeep",
        ],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
        collision_detected=collision_detected,
        suggested_slug=suggested_slug,
    )


def test_skills_generate_human_output_shows_plan_and_prompts(monkeypatch, capsys) -> None:
    seen: list[GenerateSkillCommand] = []

    def generate(command: GenerateSkillCommand) -> GenerateSkillResult:
        seen.append(command)
        return make_result()

    monkeypatch.setattr("builtins.input", lambda _prompt: "s")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    exit_code = cli_main(
        ["skills", "generate", "skill-1"],
        generate_skill_command=generate,
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert seen == [
        GenerateSkillCommand(latent_skill_id="skill-1", origin="cli", dry_run=True),
        GenerateSkillCommand(latent_skill_id="skill-1", origin="cli", dry_run=False),
    ]
    assert "Operacao: skills.generate" in output
    assert ".umem/skills/tdd-recorrente/SKILL.md" in output
    assert "Snapshot: snapshot-" in output
    assert "Auditoria: audit-" in output


def test_skills_generate_yes_runs_without_prompt(capsys, monkeypatch) -> None:
    seen: list[GenerateSkillCommand] = []

    def generate(command: GenerateSkillCommand) -> GenerateSkillResult:
        seen.append(command)
        return make_result()

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    exit_code = cli_main(
        ["skills", "generate", "skill-1", "--yes"],
        generate_skill_command=generate,
    )

    assert exit_code == 0
    assert capsys.readouterr().out
    assert seen == [
        GenerateSkillCommand(latent_skill_id="skill-1", origin="cli", dry_run=True),
        GenerateSkillCommand(latent_skill_id="skill-1", origin="cli", dry_run=False),
    ]


def test_skills_generate_json_is_pure_success_envelope(capsys, monkeypatch) -> None:
    seen: list[GenerateSkillCommand] = []

    def generate(command: GenerateSkillCommand) -> GenerateSkillResult:
        seen.append(command)
        return make_result()

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    exit_code = cli_main(
        ["skills", "generate", "skill-1", "--yes", "--format", "json"],
        generate_skill_command=generate,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == [
        GenerateSkillCommand(latent_skill_id="skill-1", origin="cli", dry_run=False),
    ]
    assert payload == {
        "ok": True,
        "operation": "skills.generate",
        "scope": "project",
        "data": {
            "skill_id": payload["data"]["skill_id"],
            "name": "TDD Recorrente",
            "slug": "tdd-recorrente",
            "skill_dir": ".umem/skills/tdd-recorrente",
            "skill_file": ".umem/skills/tdd-recorrente/SKILL.md",
            "created_paths": [
                ".umem/skills/tdd-recorrente/SKILL.md",
                ".umem/skills/tdd-recorrente/scripts/.gitkeep",
            ],
            "affected_paths": [
                ".umem/skills/tdd-recorrente/SKILL.md",
                ".umem/skills/tdd-recorrente/scripts/.gitkeep",
            ],
            "audit_reference": "audit-1",
            "snapshot_reference": "snapshot-1",
            "collision_detected": False,
            "suggested_slug": None,
        },
        "warnings": [],
    }


def test_skills_generate_non_tty_requires_yes(capsys, monkeypatch) -> None:
    def generate(command: GenerateSkillCommand) -> GenerateSkillResult:
        return make_result()

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    exit_code = cli_main(
        ["skills", "generate", "skill-1"],
        generate_skill_command=generate,
    )
    output = capsys.readouterr().err

    assert exit_code == 1
    assert "Ambiente nao-TTY exige --yes para gerar skill." in output


def test_skills_generate_user_cancels(monkeypatch, capsys) -> None:
    seen: list[GenerateSkillCommand] = []

    def generate(command: GenerateSkillCommand) -> GenerateSkillResult:
        seen.append(command)
        return make_result()

    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    exit_code = cli_main(
        ["skills", "generate", "skill-1"],
        generate_skill_command=generate,
    )
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Geracao de skill cancelada." in output
    assert seen == [
        GenerateSkillCommand(latent_skill_id="skill-1", origin="cli", dry_run=True),
    ]


def test_skills_generate_collision_interactive_update(monkeypatch, capsys) -> None:
    seen: list[GenerateSkillCommand] = []

    def generate(command: GenerateSkillCommand) -> GenerateSkillResult:
        seen.append(command)
        if command.dry_run:
            return make_result(collision_detected=True, suggested_slug="tdd-recorrente-2")
        return make_result()

    inputs = ["u"]  # User chooses "u" (update)
    monkeypatch.setattr("builtins.input", lambda _prompt: inputs.pop(0))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    exit_code = cli_main(
        ["skills", "generate", "skill-1"],
        generate_skill_command=generate,
    )

    assert exit_code == 0
    assert seen == [
        GenerateSkillCommand(
            latent_skill_id="skill-1", origin="cli", dry_run=True, update_existing=False
        ),
        GenerateSkillCommand(
            latent_skill_id="skill-1", origin="cli", dry_run=False, update_existing=True
        ),
    ]


def test_skills_generate_collision_interactive_alternative(monkeypatch, capsys) -> None:
    seen: list[GenerateSkillCommand] = []

    def generate(command: GenerateSkillCommand) -> GenerateSkillResult:
        seen.append(command)
        if command.dry_run:
            return make_result(collision_detected=True, suggested_slug="tdd-recorrente-2")
        return make_result()

    inputs = ["a"]  # User chooses "a" (alternative)
    monkeypatch.setattr("builtins.input", lambda _prompt: inputs.pop(0))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    exit_code = cli_main(
        ["skills", "generate", "skill-1"],
        generate_skill_command=generate,
    )

    assert exit_code == 0
    assert seen == [
        GenerateSkillCommand(
            latent_skill_id="skill-1", origin="cli", dry_run=True, update_existing=False
        ),
        GenerateSkillCommand(
            latent_skill_id="skill-1", origin="cli", dry_run=False, update_existing=False
        ),
    ]
