from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from universal_memory.application.skills import (
    ProposeSkillCommand,
    ProposeSkillDecision,
    ProposeSkillResult,
)
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.interfaces.cli.init_command import main as cli_main


def make_skill(*, status: LatentSkillStatus = LatentSkillStatus.proposed) -> LatentSkill:
    timestamp = datetime.now(UTC)
    return LatentSkill(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        name="TDD recorrente",
        description="Usuario pede sempre ciclo red green refactor",
        scope=LatentSkillScope.project,
        status=status,
        recurrence_count=3,
        metadata={
            "evidence": [
                {"origin": "cli", "summary": "Pedido em story anterior"},
                {"origin": "mcp", "summary": "Pedido em review"},
            ]
        },
    )


def make_result(
    *,
    decision: ProposeSkillDecision | None = None,
    requires_decision: bool = False,
    scope: LatentSkillScope = LatentSkillScope.project,
) -> ProposeSkillResult:
    skill = make_skill(
        status=LatentSkillStatus.proposed
        if requires_decision
        else (
            LatentSkillStatus.ignored
            if decision == ProposeSkillDecision.nao
            else LatentSkillStatus.active
        )
    )
    skill = skill.model_copy(update={"scope": scope})
    return ProposeSkillResult(
        latent_skill=skill,
        proposal={
            "suggested_name": skill.name,
            "purpose": skill.description,
            "scope": skill.scope.value,
            "evidence": ["Pedido em story anterior", "Pedido em review"],
        },
        requires_decision=requires_decision,
        accepted=decision in {ProposeSkillDecision.sim, ProposeSkillDecision.sempre},
        auto_approval_recorded=decision == ProposeSkillDecision.sempre,
        audit_reference="audit-1" if decision is not None else "",
        snapshot_reference="snapshot-1" if decision is not None else "",
    )


def test_skills_propose_global_output_uses_umem_config_path(capsys) -> None:
    def propose(command: ProposeSkillCommand) -> ProposeSkillResult:
        return make_result(decision=command.decision, scope=LatentSkillScope.global_)

    exit_code = cli_main(
        ["skills", "propose", "skill-1", "--decision", "sempre"],
        propose_skill_command=propose,
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "~/.config/umem/config.toml" in output
    assert "~/.config/universal-memory/config.toml" not in output


def test_skills_propose_human_output_shows_proposal_and_choices(capsys) -> None:
    seen: list[ProposeSkillCommand] = []

    def propose(command: ProposeSkillCommand) -> ProposeSkillResult:
        seen.append(command)
        return make_result(decision=command.decision)

    exit_code = cli_main(
        ["skills", "propose", "skill-1", "--decision", "sim"],
        propose_skill_command=propose,
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert seen[0].latent_skill_id == "skill-1"
    assert seen[0].decision == ProposeSkillDecision.sim
    assert "TDD recorrente" in output
    assert "Usuario pede sempre ciclo red green refactor" in output
    assert "project" in output
    assert "Pedido em story anterior" in output
    assert "Sim" in output
    assert "Sempre" in output
    assert "Não" in output


def test_skills_propose_accepts_interactive_sim(monkeypatch, capsys) -> None:
    seen: list[ProposeSkillCommand] = []

    def propose(command: ProposeSkillCommand) -> ProposeSkillResult:
        seen.append(command)
        if command.decision is None:
            return make_result(requires_decision=True)
        return make_result(decision=command.decision)

    monkeypatch.setattr("builtins.input", lambda _prompt: "s")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    exit_code = cli_main(["skills", "propose", "skill-1"], propose_skill_command=propose)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert [command.decision for command in seen] == [None, ProposeSkillDecision.sim]
    assert "audit-1" in output


def test_skills_propose_yes_accepts_without_prompt(capsys) -> None:
    seen: list[ProposeSkillCommand] = []

    def propose(command: ProposeSkillCommand) -> ProposeSkillResult:
        seen.append(command)
        return make_result(decision=command.decision)

    exit_code = cli_main(
        ["skills", "propose", "skill-1", "--yes"],
        propose_skill_command=propose,
    )

    assert exit_code == 0
    assert capsys.readouterr().out
    assert [command.decision for command in seen] == [ProposeSkillDecision.sim]


def test_skills_propose_json_is_pure_success_envelope(capsys) -> None:
    def propose(command: ProposeSkillCommand) -> ProposeSkillResult:
        return make_result(decision=command.decision)

    exit_code = cli_main(
        ["skills", "propose", "skill-1", "--yes", "--format", "json"],
        propose_skill_command=propose,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "ok": True,
        "operation": "skills.propose",
        "scope": "project",
        "data": {
            "skill_id": payload["data"]["skill_id"],
            "suggested_name": "TDD recorrente",
            "status": "active",
            "accepted": True,
            "auto_approval_recorded": False,
            "audit_reference": "audit-1",
            "snapshot_reference": "snapshot-1",
            "choices": ["Sim", "Sempre", "Não"],
            "requires_decision": False,
            "evidence": ["Pedido em story anterior", "Pedido em review"],
        },
        "warnings": [],
    }


def test_skills_propose_raises_key_error_when_skill_not_found(capsys) -> None:
    def propose(command: ProposeSkillCommand) -> ProposeSkillResult:
        raise KeyError("skill-1")

    exit_code = cli_main(
        ["skills", "propose", "skill-not-found", "--yes"],
        propose_skill_command=propose,
    )
    output = capsys.readouterr().err

    assert exit_code == 1
    assert "Latent skill 'skill-not-found' nao encontrada no repositorio." in output


def test_skills_propose_non_tty_requires_decision(capsys, monkeypatch) -> None:
    def propose(command: ProposeSkillCommand) -> ProposeSkillResult:
        return make_result(requires_decision=True)

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    exit_code = cli_main(
        ["skills", "propose", "skill-1"],
        propose_skill_command=propose,
    )
    output = capsys.readouterr().err

    assert exit_code == 1
    assert "Ambiente nao-TTY exige --decision ou --yes." in output
