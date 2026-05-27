from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.application.memory import GetMemoryStatusCommand, GetMemoryStatusUseCase
from universal_memory.domain import ProjectLayoutPort, ProjectLayoutResult
from universal_memory.domain.entities import (
    Fact,
    FactScope,
    FactStatus,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    Rule,
    RuleScope,
    RuleStatus,
)
from universal_memory.domain.ports import FactRepository, LatentSkillRepository, RuleRepository

EXPECTED_MIN_SIZE_BYTES = 3


class RecordingLayoutPort(ProjectLayoutPort):
    def __init__(self, *, initialized: bool) -> None:
        self.initialized = initialized
        self.checked_roots: list[Path] = []
        self.ensure_calls = 0

    def ensure_project_layout(self, project_root: Path) -> ProjectLayoutResult:
        self.ensure_calls += 1
        return ProjectLayoutResult(created=False, created_paths=[], existing_paths=[])

    def is_project_initialized(self, project_root: Path) -> bool:
        self.checked_roots.append(project_root)
        return self.initialized


class RecordingFactRepository(FactRepository):
    def __init__(self, facts: list[Fact]) -> None:
        self.facts = facts

    def read(self, id: str) -> Fact:
        raise KeyError(id)

    def list(self, scope: FactScope | None = None, status: FactStatus | None = None) -> list[Fact]:
        facts = self.facts
        if scope is not None:
            facts = [fact for fact in facts if fact.scope == scope]
        if status is not None:
            facts = [fact for fact in facts if fact.status == status]
        return facts

    def search(self, query: str, include_inactive: bool = False) -> list[Fact]:
        return []

    def write(self, entity: Fact) -> None:
        self.facts.append(entity)

    def delete(self, id: str) -> None:
        raise KeyError(id)

    def purge(self, id: str) -> None:
        raise KeyError(id)

    def migrate(self, target_version: int) -> None:
        return None


class RecordingRuleRepository(RuleRepository):
    def __init__(self, rules: list[Rule]) -> None:
        self.rules = rules
        self.filters: list[tuple[RuleScope | None, RuleStatus | None]] = []

    def read(self, id: str) -> Rule:
        raise KeyError(id)

    def list(self, scope: RuleScope | None = None, status: RuleStatus | None = None) -> list[Rule]:
        self.filters.append((scope, status))
        rules = self.rules
        if scope is not None:
            rules = [rule for rule in rules if rule.scope == scope]
        if status is not None:
            rules = [rule for rule in rules if rule.status == status]
        return rules

    def write(self, entity: Rule) -> None:
        self.rules.append(entity)

    def delete(self, id: str) -> None:
        raise KeyError(id)

    def migrate(self, target_version: int) -> None:
        return None


class RecordingLatentSkillRepository(LatentSkillRepository):
    def __init__(self, skills: list[LatentSkill]) -> None:
        self.skills = skills
        self.filters: list[tuple[LatentSkillScope | None, LatentSkillStatus | None]] = []

    def read(self, id: str) -> LatentSkill:
        raise KeyError(id)

    def list(
        self, scope: LatentSkillScope | None = None, status: LatentSkillStatus | None = None
    ) -> list[LatentSkill]:
        self.filters.append((scope, status))
        skills = self.skills
        if scope is not None:
            skills = [skill for skill in skills if skill.scope == scope]
        if status is not None:
            skills = [skill for skill in skills if skill.status == status]
        return skills

    def write(self, entity: LatentSkill) -> None:
        self.skills.append(entity)

    def delete(self, id: str) -> None:
        raise KeyError(id)

    def migrate(self, target_version: int) -> None:
        return None


def make_fact(*, scope: FactScope, status: FactStatus) -> Fact:
    now = datetime(2026, 5, 27, tzinfo=UTC)
    return Fact(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        content="Preferir saida JSON pura",
        scope=scope,
        source="test",
        status=status,
    )


def make_rule(*, status: RuleStatus) -> Rule:
    now = datetime(2026, 5, 27, tzinfo=UTC)
    return Rule(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Regra",
        content="Use caminhos relativos",
        scope=RuleScope.project,
        status=status,
    )


def make_skill(*, status: LatentSkillStatus) -> LatentSkill:
    now = datetime(2026, 5, 27, tzinfo=UTC)
    return LatentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="status",
        description="Exibir status",
        scope=LatentSkillScope.project,
        status=status,
    )


def build_use_case(
    *,
    initialized: bool,
    project_root: Path,
    facts: list[Fact] | None = None,
    rules: list[Rule] | None = None,
    skills: list[LatentSkill] | None = None,
) -> tuple[
    GetMemoryStatusUseCase,
    RecordingLayoutPort,
    RecordingRuleRepository,
    RecordingLatentSkillRepository,
]:
    layout_port = RecordingLayoutPort(initialized=initialized)
    rule_repository = RecordingRuleRepository(rules or [])
    skill_repository = RecordingLatentSkillRepository(skills or [])
    return (
        GetMemoryStatusUseCase(
            fact_repository=RecordingFactRepository(facts or []),
            rule_repository=rule_repository,
            latent_skill_repository=skill_repository,
            layout_port=layout_port,
        ),
        layout_port,
        rule_repository,
        skill_repository,
    )


def test_status_returns_actionable_uninitialized_result_without_creating_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_case, layout_port, _rules, _skills = build_use_case(
        initialized=False,
        project_root=tmp_path,
    )

    result = use_case.execute(GetMemoryStatusCommand(project_root=tmp_path))

    assert result.initialized is False
    assert result.project_path == "."
    assert result.recommended_action == "Execute 'umem init' a partir do diretorio raiz do projeto."
    assert result.fact_counts == {}
    assert result.last_health_check is None
    assert layout_port.checked_roots == [tmp_path]
    assert layout_port.ensure_calls == 0
    assert not (tmp_path / ".umem").exists()


def test_status_counts_initialized_memory_and_detects_hosts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem" / "memory").mkdir(parents=True)
    (tmp_path / ".umem" / "memory" / "facts.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("agents", encoding="utf-8")
    facts = [
        make_fact(scope=FactScope.project, status=FactStatus.active),
        make_fact(scope=FactScope.project, status=FactStatus.stale),
        make_fact(scope=FactScope.global_, status=FactStatus.archived),
    ]
    use_case, _layout, rules, skills = build_use_case(
        initialized=True,
        project_root=tmp_path,
        facts=facts,
        rules=[make_rule(status=RuleStatus.active), make_rule(status=RuleStatus.inactive)],
        skills=[
            make_skill(status=LatentSkillStatus.active),
            make_skill(status=LatentSkillStatus.proposed),
        ],
    )

    result = use_case.execute(GetMemoryStatusCommand(project_root=tmp_path))

    assert result.initialized is True
    assert result.project_path == "."
    assert result.fact_counts == {
        "global": {"active": 0, "stale": 0, "archived": 1, "purged": 0},
        "project": {"active": 1, "stale": 1, "archived": 0, "purged": 0},
    }
    assert result.active_rules_count == 1
    assert result.registered_skills_count == 1
    assert result.approximate_size_bytes >= EXPECTED_MIN_SIZE_BYTES
    assert result.last_health_check is not None
    assert result.last_health_check.endswith("Z")
    assert result.host_validation == {"claude": "unconfigured", "gemini": "valid"}
    assert rules.filters == [(None, RuleStatus.active)]
    assert skills.filters == [(None, LatentSkillStatus.active)]
