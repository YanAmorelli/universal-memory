from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from universal_memory.application.skills import (
    ActivateSkillCommand,
    ActivateSkillResult,
    DeactivateSkillCommand,
    DeactivateSkillResult,
    UpdateSkillCommand,
    UpdateSkillResult,
)
from universal_memory.domain import SecretDetectedError, StorageError, ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.interfaces.cli.init_command import main as cli_main

SKILL_ID = "11111111-1111-4111-8111-111111111111"


def make_skill(*, status: LatentSkillStatus = LatentSkillStatus.active) -> LatentSkill:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    return LatentSkill(
        id=SKILL_ID,
        created_at=now,
        updated_at=now,
        name="TDD Recorrente",
        description="Executa red green refactor",
        scope=LatentSkillScope.project,
        status=status,
        recurrence_count=4,
        metadata={"triggers": ["red green refactor"]},
    )


def activate_result() -> ActivateSkillResult:
    return ActivateSkillResult(
        latent_skill=make_skill(status=LatentSkillStatus.active),
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def deactivate_result() -> DeactivateSkillResult:
    return DeactivateSkillResult(
        latent_skill=make_skill(status=LatentSkillStatus.ignored),
        audit_reference="audit-2",
        snapshot_reference="snapshot-2",
    )


def update_result() -> UpdateSkillResult:
    return UpdateSkillResult(
        latent_skill=make_skill(status=LatentSkillStatus.active),
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        audit_reference="audit-3",
        snapshot_reference="snapshot-3",
        rollback_hint="Use rollback por escopo para restaurar o snapshot anterior.",
    )


def global_deactivate_result() -> DeactivateSkillResult:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    return DeactivateSkillResult(
        latent_skill=LatentSkill(
            id=SKILL_ID,
            created_at=now,
            updated_at=now,
            name="Padrao Global",
            description="Aplica instrucoes compartilhadas.",
            scope=LatentSkillScope.global_,
            status=LatentSkillStatus.ignored,
            recurrence_count=2,
            metadata={"triggers": ["global"]},
        ),
        audit_reference="audit-global",
        snapshot_reference="snapshot-global",
    )


def test_skills_activate_json_uses_cli_origin_and_success_envelope(capsys) -> None:
    seen: list[ActivateSkillCommand] = []

    def activate(command: ActivateSkillCommand) -> ActivateSkillResult:
        seen.append(command)
        return activate_result()

    exit_code = cli_main(
        ["skills", "activate", SKILL_ID, "--format", "json"],
        activate_skill_command=activate,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == [ActivateSkillCommand(latent_skill_id=SKILL_ID, origin="cli")]
    assert payload == {
        "ok": True,
        "operation": "skills.activate",
        "scope": "project",
        "data": {
            "latent_skill": {
                "id": SKILL_ID,
                "name": "TDD Recorrente",
                "description": "Executa red green refactor",
                "status": "active",
                "scope": "project",
                "triggers": ["red green refactor"],
            },
            "skill_file": ".umem/skills/tdd-recorrente/SKILL.md",
            "audit_reference": "audit-1",
            "snapshot_reference": "snapshot-1",
        },
        "warnings": [],
    }


def test_skills_deactivate_human_output_shows_audit_and_snapshot(capsys) -> None:
    def deactivate(command: DeactivateSkillCommand) -> DeactivateSkillResult:
        assert command == DeactivateSkillCommand(latent_skill_id=SKILL_ID, origin="cli")
        return deactivate_result()

    exit_code = cli_main(
        ["skills", "deactivate", SKILL_ID],
        deactivate_skill_command=deactivate,
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Operation: skills.deactivate" in output
    assert "Scope: project" in output
    assert ".umem/memory/latent_skills.jsonl" in output
    assert "Audit: audit-2" in output
    assert "Snapshot: snapshot-2" in output


def test_skills_update_accepts_metadata_options_and_file(
    tmp_path: Path,
    capsys,
) -> None:
    markdown_file = tmp_path / "SKILL.md"
    markdown_file.write_text(
        "---\n"
        "name: Skill Atualizada\n"
        "description: Conteudo novo\n"
        "triggers:\n"
        "  - trigger arquivo\n"
        "---\n",
        encoding="utf-8",
    )
    seen: list[UpdateSkillCommand] = []

    def update(command: UpdateSkillCommand) -> UpdateSkillResult:
        seen.append(command)
        return update_result()

    exit_code = cli_main(
        [
            "skills",
            "update",
            SKILL_ID,
            "--name",
            "Nome Novo",
            "--description",
            "Descricao Nova",
            "--trigger",
            "trigger A",
            "--trigger",
            "trigger B",
            "--file",
            str(markdown_file),
            "--format",
            "json",
        ],
        update_skill_command=update,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == [
        UpdateSkillCommand(
            latent_skill_id=SKILL_ID,
            origin="cli",
            name="Nome Novo",
            description="Descricao Nova",
            triggers=["trigger A", "trigger B"],
            raw_markdown=markdown_file.read_text(encoding="utf-8"),
        )
    ]
    assert payload["operation"] == "skills.update"
    assert payload["data"]["skill_file"] == ".umem/skills/tdd-recorrente/SKILL.md"
    assert payload["data"]["audit_reference"] == "audit-3"


def test_skills_update_missing_file_returns_validation_error(capsys) -> None:
    exit_code = cli_main(
        ["skills", "update", SKILL_ID, "--file", "missing.md"],
        update_skill_command=lambda _command: update_result(),
    )
    output = capsys.readouterr().err

    assert exit_code == 1
    assert "Markdown file not found: missing.md" in output


def test_skills_mutation_errors_are_mapped_to_safe_json(capsys) -> None:
    def activate(_command: ActivateSkillCommand) -> ActivateSkillResult:
        raise SecretDetectedError("blocked sk-test-secret-value")

    exit_code = cli_main(
        ["skills", "activate", SKILL_ID, "--format", "json"],
        activate_skill_command=activate,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "secret_detected"
    assert "sk-test-secret-value" not in payload["error"]["detail"]


def test_skills_mutation_maps_validation_and_storage_errors(capsys) -> None:
    def update(_command: UpdateSkillCommand) -> UpdateSkillResult:
        raise StorageError("disk unavailable")

    exit_code = cli_main(
        ["skills", "update", SKILL_ID, "--description", "x", "--format", "json"],
        update_skill_command=update,
    )
    storage_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert storage_payload["error"]["code"] == "storage_error"

    def deactivate(_command: DeactivateSkillCommand) -> DeactivateSkillResult:
        raise ValidationFailedError("invalid status")

    exit_code = cli_main(
        ["skills", "deactivate", SKILL_ID, "--format", "json"],
        deactivate_skill_command=deactivate,
    )
    validation_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert validation_payload["error"]["code"] == "validation_failed"


def test_skills_missing_id_maps_not_found_storage_error_to_validation_failed(capsys) -> None:
    def activate(_command: ActivateSkillCommand) -> ActivateSkillResult:
        raise StorageError(f"Latent skill not found: {SKILL_ID}")

    exit_code = cli_main(
        ["skills", "activate", SKILL_ID, "--format", "json"],
        activate_skill_command=activate,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["error"]["code"] == "validation_failed"


def test_skills_global_mutation_human_output_uses_global_store_path(capsys) -> None:
    exit_code = cli_main(
        ["skills", "deactivate", SKILL_ID],
        deactivate_skill_command=lambda _command: global_deactivate_result(),
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "memory/latent_skills.jsonl" in output
    assert ".umem/memory/latent_skills.jsonl" not in output
