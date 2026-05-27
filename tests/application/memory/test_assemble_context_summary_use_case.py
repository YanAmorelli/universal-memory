from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from universal_memory.application.memory import (
    AssembleContextSummaryCommand,
    AssembleContextSummaryUseCase,
)
from universal_memory.domain import SecretDetectedError, StorageError
from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    ContextSummary,
    ContextSummaryScope,
    Fact,
    FactScope,
    FactStatus,
    Rule,
    RuleScope,
    RuleStatus,
)
from universal_memory.domain.ports import (
    AuditLogRepository,
    ContextSummaryRepository,
    FactRepository,
    RuleRepository,
    SecretScannerPort,
)

STRICT_SIZE_LIMIT = 170


def make_fact(  # noqa: PLR0913 - Test factory keeps individual scenarios readable.
    content: str,
    *,
    scope: FactScope = FactScope.project,
    status: FactStatus = FactStatus.active,
    created_at: datetime | None = None,
    recurrence_count: int = 0,
    tags: list[str] | None = None,
) -> Fact:
    timestamp = created_at or datetime.now(UTC)
    return Fact(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        content=content,
        scope=scope,
        source="test",
        status=status,
        recurrence_count=recurrence_count,
        tags=tags or [],
        metadata={},
    )


def make_rule(
    content: str,
    *,
    scope: RuleScope = RuleScope.project,
    status: RuleStatus = RuleStatus.active,
    created_at: datetime | None = None,
) -> Rule:
    timestamp = created_at or datetime.now(UTC)
    return Rule(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        name=content[:20],
        content=content,
        scope=scope,
        status=status,
        metadata={},
    )


class FakeFactRepository(FactRepository):
    def __init__(self, facts: list[Fact]) -> None:
        self.facts = facts

    def read(self, id: str) -> Fact:
        raise NotImplementedError

    def list(self, scope: FactScope | None = None, status: FactStatus | None = None) -> list[Fact]:
        facts = self.facts
        if scope is not None:
            facts = [fact for fact in facts if fact.scope == scope]
        if status is not None:
            facts = [fact for fact in facts if fact.status == status]
        return facts

    def search(self, query: str, include_inactive: bool = False) -> list[Fact]:
        return []

    def write(self, entity: Fact) -> object | None:
        return None

    def delete(self, id: str) -> None:
        raise NotImplementedError

    def purge(self, id: str) -> None:
        raise NotImplementedError

    def migrate(self, target_version: int) -> None:
        raise NotImplementedError


class FakeRuleRepository(RuleRepository):
    def __init__(self, rules: list[Rule]) -> None:
        self.rules = rules

    def read(self, id: str) -> Rule:
        raise NotImplementedError

    def list(self, scope: RuleScope | None = None, status: RuleStatus | None = None) -> list[Rule]:
        rules = self.rules
        if scope is not None:
            rules = [rule for rule in rules if rule.scope == scope]
        if status is not None:
            rules = [rule for rule in rules if rule.status == status]
        return rules

    def write(self, entity: Rule) -> None:
        raise NotImplementedError

    def delete(self, id: str) -> None:
        raise NotImplementedError

    def migrate(self, target_version: int) -> None:
        raise NotImplementedError


class FakeContextSummaryRepository(ContextSummaryRepository):
    def __init__(self, *, fail_write: bool = False) -> None:
        self.fail_write = fail_write
        self.written: list[ContextSummary] = []

    def read(self, id: str) -> ContextSummary:
        raise NotImplementedError

    def list(self, scope: ContextSummaryScope | None = None) -> list[ContextSummary]:
        return self.written

    def write(self, entity: ContextSummary) -> None:
        if self.fail_write:
            raise StorageError("corrupt context summary storage")
        self.written.append(entity)

    def migrate(self, target_version: int) -> None:
        raise NotImplementedError


class FakeAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def read(self, id: str) -> AuditEvent:
        raise NotImplementedError

    def list(self, scope: AuditEventScope | None = None) -> list[AuditEvent]:
        return self.events

    def write(self, entity: AuditEvent) -> None:
        self.events.append(entity)

    def migrate(self, target_version: int) -> None:
        raise NotImplementedError


class FakeSecretScanner(SecretScannerPort):
    def __init__(self, blocked_fragments: list[str] | None = None) -> None:
        self.blocked_fragments = blocked_fragments or []

    def scan(self, content: str, *, origin: str | None = None) -> None:
        if any(fragment in content for fragment in self.blocked_fragments):
            raise SecretDetectedError("Secret detected", metadata={"type": "test"})


def build_use_case(
    *,
    facts: list[Fact],
    rules: list[Rule] | None = None,
    secret_scanner: FakeSecretScanner | None = None,
    context_repository: FakeContextSummaryRepository | None = None,
    audit_repository: FakeAuditLogRepository | None = None,
) -> tuple[AssembleContextSummaryUseCase, FakeContextSummaryRepository, FakeAuditLogRepository]:
    context_repository = context_repository or FakeContextSummaryRepository()
    audit_repository = audit_repository or FakeAuditLogRepository()
    use_case = AssembleContextSummaryUseCase(
        fact_repository=FakeFactRepository(facts),
        rule_repository=FakeRuleRepository(rules or []),
        secret_scanner=secret_scanner or FakeSecretScanner(),
        audit_log_repository=audit_repository,
        context_summary_repository=context_repository,
    )
    return use_case, context_repository, audit_repository


def test_assembles_sections_prioritizing_scope_recency_status_and_relevance() -> None:
    base = datetime(2026, 5, 27, tzinfo=UTC)
    project_recent = make_fact("Projeto recente", created_at=base + timedelta(minutes=2))
    project_preference = make_fact(
        "Preferencia de projeto",
        created_at=base,
        tags=["preferences"],
    )
    global_recent = make_fact(
        "Preferencia global",
        scope=FactScope.global_,
        created_at=base + timedelta(minutes=1),
    )
    stale = make_fact("Nao deve aparecer", status=FactStatus.stale)
    rule = make_rule("Regra ativa do projeto", created_at=base + timedelta(minutes=3))
    inactive_rule = make_rule("Regra inativa", status=RuleStatus.inactive)
    use_case, context_repository, audit_repository = build_use_case(
        facts=[stale, global_recent, project_recent, project_preference],
        rules=[inactive_rule, rule],
    )

    result = use_case.execute(
        AssembleContextSummaryCommand(
            scope=ContextSummaryScope.project,
            max_size_chars=2_000,
            agent_session_key="agent-1",
        )
    )

    assert result.context_markdown.startswith("# MEMORY CONTEXT SUMMARY")
    assert "## Project Summary" in result.context_markdown
    assert "## Universal Preferences" in result.context_markdown
    assert "## Active Rules" in result.context_markdown
    assert result.context_summary.project_summary.index("Preferencia de projeto") < (
        result.context_summary.project_summary.index("Projeto recente")
    )
    assert "Preferencia global" in result.context_summary.universal_preferences
    assert "Regra ativa do projeto" in result.context_summary.active_rules
    assert "Nao deve aparecer" not in result.context_markdown
    assert "Regra inativa" not in result.context_markdown
    assert context_repository.written == [result.context_summary]
    assert audit_repository.events[0].id == result.context_summary.audit_reference
    assert project_recent.id in result.included_fact_ids
    assert global_recent.id in result.included_fact_ids


def test_respects_max_size_by_pruning_lower_priority_facts() -> None:
    base = datetime(2026, 5, 27, tzinfo=UTC)
    important = make_fact(
        "Preferir respostas curtas",
        tags=["core-behavior"],
        created_at=base,
    )
    low_priority = make_fact(
        "Detalhe operacional muito longo que deve ser podado do resumo final",
        created_at=base + timedelta(minutes=1),
    )
    use_case, _, audit_repository = build_use_case(facts=[low_priority, important])

    result = use_case.execute(
        AssembleContextSummaryCommand(
            scope=ContextSummaryScope.project,
            max_size_chars=STRICT_SIZE_LIMIT,
        )
    )

    assert len(result.context_markdown) <= STRICT_SIZE_LIMIT
    assert "Preferir respostas curtas" in result.context_markdown
    assert "Detalhe operacional" not in result.context_markdown
    details = json.loads(audit_repository.events[0].details or "{}")
    assert details["included_fact_ids"] == [important.id]


def test_secret_scanner_blocks_sensitive_facts_from_summary_and_audit_details() -> None:
    secret_fact = make_fact("API_KEY=sk-test-secret")
    safe_fact = make_fact("Usar markdown limpo")
    use_case, _, audit_repository = build_use_case(
        facts=[secret_fact, safe_fact],
        secret_scanner=FakeSecretScanner(["sk-test-secret"]),
    )

    result = use_case.execute(
        AssembleContextSummaryCommand(
            scope=ContextSummaryScope.project,
            max_size_chars=2_000,
        )
    )

    assert "sk-test-secret" not in result.context_markdown
    assert secret_fact.id not in result.included_fact_ids
    assert safe_fact.id in result.included_fact_ids
    assert "sk-test-secret" not in (audit_repository.events[0].details or "")


def test_audit_event_records_context_read_evidence_and_summary_origin() -> None:
    fact = make_fact("Preferencia global", scope=FactScope.global_)
    use_case, _, audit_repository = build_use_case(facts=[fact])

    result = use_case.execute(
        AssembleContextSummaryCommand(
            scope=ContextSummaryScope.global_,
            max_size_chars=2_000,
            agent_session_key="session-123",
        )
    )

    event = audit_repository.events[0]
    details = json.loads(event.details or "{}")
    assert event.action == "assemble_context_summary"
    assert event.scope == AuditEventScope.global_
    assert event.result == "success"
    assert details["included_fact_ids"] == [fact.id]
    assert details["summary_origin"] == "global"
    assert details["agent_session_key"] == "session-123"
    assert result.context_summary.audit_reference == event.id


def test_persistence_failure_is_audited_without_returning_partial_summary() -> None:
    fact = make_fact("Contexto valido")
    audit_repository = FakeAuditLogRepository()
    failing_context_repository = FakeContextSummaryRepository(fail_write=True)
    use_case, _, _ = build_use_case(
        facts=[fact],
        context_repository=failing_context_repository,
        audit_repository=audit_repository,
    )

    with pytest.raises(StorageError, match="corrupt context summary storage"):
        use_case.execute(
            AssembleContextSummaryCommand(
                scope=ContextSummaryScope.project,
                max_size_chars=2_000,
            )
        )

    assert [event.result for event in audit_repository.events] == ["failure"]
    details = json.loads(audit_repository.events[0].details or "{}")
    assert details["error_type"] == "StorageError"
    assert "corrupt context summary storage" in details["error"]


def test_respects_max_size_by_prioritizing_rules_over_lower_priority_facts() -> None:
    base = datetime(2026, 5, 27, tzinfo=UTC)
    high_priority_rule = make_rule(
        "Regra super importante do projeto",
        scope=RuleScope.project,
        created_at=base,
    )
    low_priority_fact = make_fact(
        "Fato global irrelevante muito longo que devera ser podado sob limites restritos",
        scope=FactScope.global_,
        created_at=base,
    )

    use_case, _, _ = build_use_case(
        facts=[low_priority_fact],
        rules=[high_priority_rule],
    )

    result = use_case.execute(
        AssembleContextSummaryCommand(
            scope=ContextSummaryScope.project,
            max_size_chars=170,  # Strict limit
        )
    )

    assert "Regra super importante" in result.context_markdown
    assert "Fato global irrelevante" not in result.context_markdown


def test_validation_of_minimum_template_size() -> None:
    use_case, _, _ = build_use_case(facts=[])

    with pytest.raises(ValueError, match="must be at least 110"):
        use_case.execute(
            AssembleContextSummaryCommand(
                scope=ContextSummaryScope.project,
                max_size_chars=100,  # Invalid limit
            )
        )


def test_audit_event_logs_blocked_rule_ids_with_secrets() -> None:
    safe_rule = make_rule("Regra segura")
    secret_rule = make_rule("API_KEY=sk-test-secret-rule")
    use_case, _, audit_repository = build_use_case(
        facts=[],
        rules=[safe_rule, secret_rule],
        secret_scanner=FakeSecretScanner(["sk-test-secret-rule"]),
    )

    result = use_case.execute(
        AssembleContextSummaryCommand(
            scope=ContextSummaryScope.project,
            max_size_chars=2_000,
        )
    )

    assert "Regra segura" in result.context_markdown
    assert "sk-test-secret-rule" not in result.context_markdown
    details = json.loads(audit_repository.events[0].details or "{}")
    assert secret_rule.id in details["blocked_rule_ids"]

