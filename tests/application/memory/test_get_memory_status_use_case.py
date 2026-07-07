from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.application.memory import GetMemoryStatusCommand, GetMemoryStatusUseCase
from universal_memory.application.security import SafeWriteResult
from universal_memory.domain import ProjectLayoutPort, ProjectLayoutResult
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    AuditEvent,
    AuditEventScope,
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
from universal_memory.domain.ports import (
    AgentSkillRepository,
    AuditLogRepository,
    FactRepository,
    LatentSkillRepository,
    RuleRepository,
)
from universal_memory.domain.project_layout import (
    ProjectLayoutInspection,
    ProjectLayoutMode,
    ProjectLayoutPolicy,
    ProjectLayoutPrecedence,
    ResolvedProjectLayout,
)

EXPECTED_MIN_SIZE_BYTES = 3
MIN_SHARED_LAYOUT_PATHS = 2


class RecordingLayoutPort(ProjectLayoutPort):
    def __init__(self, *, initialized: bool, layout: str = "legacy") -> None:
        self.initialized = initialized
        self.layout = layout
        self.checked_roots: list[Path] = []
        self.ensure_calls = 0

    def ensure_project_layout(self, project_root: Path) -> ProjectLayoutResult:
        self.ensure_calls += 1
        return ProjectLayoutResult(created=False, created_paths=[], existing_paths=[])

    def is_project_initialized(self, project_root: Path) -> bool:
        self.checked_roots.append(project_root)
        return self.initialized

    def inspect_project_layout(self, project_root: Path) -> ProjectLayoutInspection:
        return ProjectLayoutInspection(
            operation="layout.status",
            layout=self.layout if self.initialized else "uninitialized",
            shared_root="umem",
            operational_root=".umem",
            precedence="shared_over_legacy",
            warnings=[],
            recommended_actions=[],
        )

    def resolve_project_layout(self, project_root: Path) -> ResolvedProjectLayout:
        shared_root = project_root / "umem"
        operational_root = project_root / ".umem"
        return ResolvedProjectLayout(
            project_root=project_root,
            policy=ProjectLayoutPolicy(
                schema_version="1",
                layout=ProjectLayoutMode(self.layout),
                shared_root="umem",
                operational_root=".umem",
                precedence=ProjectLayoutPrecedence.shared_over_legacy,
            ),
            shared_root_path=shared_root,
            operational_root_path=operational_root,
            shared_memory_root=shared_root / "memory",
            shared_skills_root=shared_root / "skills",
            operational_memory_root=operational_root / "memory",
            operational_skills_root=operational_root / "skills",
            operational_locks_root=operational_root / "locks",
        )

    def write_project_layout_metadata(
        self,
        project_root: Path,
        *,
        layout: str = "shared",
    ) -> ProjectLayoutPolicy:
        return ProjectLayoutPolicy(
            schema_version="1",
            layout=ProjectLayoutMode(layout),
            shared_root="umem",
            operational_root=".umem",
            precedence=ProjectLayoutPrecedence.shared_over_legacy,
        )


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

    def write(self, entity: LatentSkill, *, origin: str = "repository") -> None:
        self.skills.append(entity)

    def delete(self, id: str) -> None:
        raise KeyError(id)

    def migrate(self, target_version: int) -> None:
        return None


class RecordingAgentSkillRepository(AgentSkillRepository):
    def __init__(self, skills: list[AgentSkill]) -> None:
        self.skills = skills
        self.filters: list[tuple[LatentSkillScope | None, AgentSkillStatus | None]] = []

    def read(self, id: str) -> AgentSkill:
        raise KeyError(id)

    def list(
        self, scope: LatentSkillScope | None = None, status: AgentSkillStatus | None = None
    ) -> list[AgentSkill]:
        self.filters.append((scope, status))
        skills = self.skills
        if scope is not None:
            skills = [skill for skill in skills if skill.scope == scope]
        if status is not None:
            skills = [skill for skill in skills if skill.status == status]
        return skills

    def write(self, entity: AgentSkill, *, origin: str = "repository") -> SafeWriteResult | None:
        self.skills.append(entity)
        return None

    def delete(self, id: str) -> None:
        raise KeyError(id)

    def migrate(self, target_version: int) -> None:
        return None


class RecordingAuditLogRepository(AuditLogRepository):
    def __init__(self, events: list[AuditEvent] | None = None, *, fail_list: bool = False) -> None:
        self.events = events or []
        self.fail_list = fail_list

    def read(self, id: str) -> AuditEvent:
        raise KeyError(id)

    def list(self, scope: AuditEventScope | None = None) -> list[AuditEvent]:
        if self.fail_list:
            raise OSError("audit unavailable")
        if scope is None:
            return self.events
        return [event for event in self.events if event.scope == scope]

    def write(self, entity: AuditEvent) -> None:
        self.events.append(entity)

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


def make_agent_skill(*, status: AgentSkillStatus) -> AgentSkill:
    now = datetime(2026, 5, 27, tzinfo=UTC)
    return AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="canonical status",
        slug="canonical-status",
        description="Canonical status skill",
        scope=LatentSkillScope.project,
        status=status,
        canonical_path=".umem/skills/canonical-status/SKILL.md",
        origin="test",
        audit_reference="audit-canonical",
        content_hash="hash-canonical",
    )


def make_host_validation_event(
    *,
    host_id: str,
    result: str,
    method: str,
    timestamp: datetime,
) -> AuditEvent:
    audit_reference = str(uuid4())
    return AuditEvent(
        id=audit_reference,
        created_at=timestamp,
        updated_at=timestamp,
        timestamp=timestamp,
        action=f"host_validation.{host_id}",
        scope=AuditEventScope.project,
        origin="cli",
        result=result,
        snapshot_reference=str(uuid4()),
        audit_reference=audit_reference,
        status="logged",
        details=f'{{"method":"{method}"}}',
    )


def build_use_case(  # noqa: PLR0913
    *,
    initialized: bool,
    project_root: Path,
    facts: list[Fact] | None = None,
    rules: list[Rule] | None = None,
    skills: list[LatentSkill] | None = None,
    agent_skills: list[AgentSkill] | None = None,
    audit_log_repository: AuditLogRepository | None = None,
    layout: str = "legacy",
) -> tuple[
    GetMemoryStatusUseCase,
    RecordingLayoutPort,
    RecordingRuleRepository,
    RecordingLatentSkillRepository,
]:
    layout_port = RecordingLayoutPort(initialized=initialized, layout=layout)
    rule_repository = RecordingRuleRepository(rules or [])
    skill_repository = RecordingLatentSkillRepository(skills or [])
    agent_skill_repository = (
        RecordingAgentSkillRepository(agent_skills) if agent_skills is not None else None
    )
    return (
        GetMemoryStatusUseCase(
            fact_repository=RecordingFactRepository(facts or []),
            rule_repository=rule_repository,
            latent_skill_repository=skill_repository,
            agent_skill_repository=agent_skill_repository,
            layout_port=layout_port,
            audit_log_repository=audit_log_repository,
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
    assert result.recommended_action == "Run 'umem init' from the project root directory."
    assert result.fact_counts == {}
    assert result.last_health_check is None
    assert result.layout == "uninitialized"
    assert result.shared_root == "umem"
    assert result.operational_root == ".umem"
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
    assert result.layout == "legacy"
    assert result.shared_root == "umem"
    assert result.operational_root == ".umem"
    assert result.path_counts is not None
    assert result.path_counts["operational_paths"] >= 1
    assert result.approximate_size_bytes >= EXPECTED_MIN_SIZE_BYTES
    assert result.last_health_check is not None
    assert result.last_health_check.endswith("Z")
    assert result.host_validation == {
        "claude_code": {
            "status": "unconfigured",
            "timestamp": None,
            "method": None,
            "audit_reference": None,
        },
        "codex": {
            "status": "unconfigured",
            "timestamp": None,
            "method": None,
            "audit_reference": None,
        },
    }
    assert rules.filters == [(None, RuleStatus.active)]
    assert skills.filters == [(None, LatentSkillStatus.active)]


def test_status_counts_registered_canonical_skills_when_repository_is_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem" / "memory").mkdir(parents=True)
    use_case, _layout, _rules, latent_skills = build_use_case(
        initialized=True,
        project_root=tmp_path,
        skills=[make_skill(status=LatentSkillStatus.active)],
        agent_skills=[
            make_agent_skill(status=AgentSkillStatus.active),
            make_agent_skill(status=AgentSkillStatus.disabled),
        ],
    )

    result = use_case.execute(GetMemoryStatusCommand(project_root=tmp_path))

    assert result.registered_skills_count == 1
    assert latent_skills.filters == []


def test_status_reports_shared_layout_roots_and_path_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem" / "memory").mkdir(parents=True)
    (tmp_path / "umem" / "memory").mkdir(parents=True)
    (tmp_path / "umem" / "project.toml").write_text('layout = "shared"\n', encoding="utf-8")
    use_case, _layout, _rules, _skills = build_use_case(
        initialized=True,
        project_root=tmp_path,
        layout="shared",
    )

    result = use_case.execute(GetMemoryStatusCommand(project_root=tmp_path))

    assert result.layout == "shared"
    assert result.shared_root == "umem"
    assert result.operational_root == ".umem"
    assert result.path_counts is not None
    assert result.path_counts["shared_paths"] >= MIN_SHARED_LAYOUT_PATHS
    assert result.path_counts["operational_paths"] >= 1


def test_status_loads_latest_host_validation_from_audit_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem").mkdir()
    older = datetime(2026, 5, 28, 10, tzinfo=UTC)
    newer = datetime(2026, 5, 29, 10, tzinfo=UTC)
    codex_event = make_host_validation_event(
        host_id="codex",
        result="failure",
        method="agents_md_compact_validator",
        timestamp=older,
    )
    latest_codex_event = make_host_validation_event(
        host_id="codex",
        result="success",
        method="agents_md_compact_validator",
        timestamp=newer,
    )
    claude_event = make_host_validation_event(
        host_id="claude_code",
        result="manual_pending",
        method="claude_md_delta_validator",
        timestamp=older,
    )
    use_case, _layout, _rules, _skills = build_use_case(
        initialized=True,
        project_root=tmp_path,
        audit_log_repository=RecordingAuditLogRepository(
            [codex_event, latest_codex_event, claude_event]
        ),
    )

    result = use_case.execute(GetMemoryStatusCommand(project_root=tmp_path))

    assert result.host_validation == {
        "claude_code": {
            "status": "manual_pending",
            "timestamp": "2026-05-28T10:00:00Z",
            "method": "claude_md_delta_validator",
            "audit_reference": claude_event.audit_reference,
        },
        "codex": {
            "status": "success",
            "timestamp": "2026-05-29T10:00:00Z",
            "method": "agents_md_compact_validator",
            "audit_reference": latest_codex_event.audit_reference,
        },
    }


def test_status_tolerates_audit_log_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem").mkdir()
    use_case, _layout, _rules, _skills = build_use_case(
        initialized=True,
        project_root=tmp_path,
        audit_log_repository=RecordingAuditLogRepository(fail_list=True),
    )

    result = use_case.execute(GetMemoryStatusCommand(project_root=tmp_path))

    assert result.host_validation == {
        "claude_code": {
            "status": "unconfigured",
            "timestamp": None,
            "method": None,
            "audit_reference": None,
        },
        "codex": {
            "status": "unconfigured",
            "timestamp": None,
            "method": None,
            "audit_reference": None,
        },
    }
