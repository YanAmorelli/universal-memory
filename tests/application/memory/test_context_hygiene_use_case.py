from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from universal_memory.application.memory import ContextHygieneCommand, ContextHygieneUseCase
from universal_memory.domain.entities import Fact, FactScope, FactStatus
from universal_memory.domain.ports import FactRepository


class RecordingFactRepository(FactRepository):
    def __init__(self, facts: list[Fact]) -> None:
        self.facts = facts
        self.list_filters: list[tuple[FactScope | None, FactStatus | None]] = []
        self.written: list[Fact] = []

    def read(self, id: str) -> Fact:
        raise KeyError(id)

    def list(self, scope: FactScope | None = None, status: FactStatus | None = None) -> list[Fact]:
        self.list_filters.append((scope, status))
        facts = self.facts
        if scope is not None:
            facts = [fact for fact in facts if fact.scope == scope]
        if status is not None:
            facts = [fact for fact in facts if fact.status == status]
        return facts

    def search(self, query: str, include_inactive: bool = False) -> list[Fact]:
        return []

    def write(self, entity: Fact) -> object | None:
        self.written.append(entity)
        self.facts = [fact for fact in self.facts if fact.id != entity.id]
        self.facts.append(entity)
        return None

    def delete(self, id: str) -> None:
        return None

    def purge(self, id: str) -> None:
        return None

    def migrate(self, target_version: int) -> None:
        return None


def make_fact(*, scope: FactScope = FactScope.project, status: FactStatus) -> Fact:
    timestamp = datetime.now(UTC)
    return Fact(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        content="Fato para higiene",
        scope=scope,
        source="test",
        status=status,
    )


def test_context_hygiene_transitions_project_active_and_stale_facts() -> None:
    active = make_fact(status=FactStatus.active)
    stale = make_fact(status=FactStatus.stale)
    archived = make_fact(status=FactStatus.archived)
    global_active = make_fact(scope=FactScope.global_, status=FactStatus.active)
    repository = RecordingFactRepository([active, stale, archived, global_active])
    use_case = ContextHygieneUseCase(fact_repository=repository)

    result = use_case.execute(ContextHygieneCommand(scope=FactScope.project))

    assert repository.list_filters == [(FactScope.project, None)]
    assert result.stale_count == 1
    assert result.archived_count == 1
    assert result.audit_reference == "repository-managed"
    assert [fact.id for fact in repository.written] == [active.id, stale.id]
    assert repository.written[0].status == FactStatus.stale
    assert repository.written[1].status == FactStatus.archived
    assert all(fact.id != archived.id for fact in repository.written)
    assert all(fact.id != global_active.id for fact in repository.written)


def test_context_hygiene_returns_zero_counts_when_no_transition_is_needed() -> None:
    archived = make_fact(status=FactStatus.archived)
    repository = RecordingFactRepository([archived])
    use_case = ContextHygieneUseCase(fact_repository=repository)

    result = use_case.execute(ContextHygieneCommand(scope=FactScope.project))

    assert result.stale_count == 0
    assert result.archived_count == 0
    assert repository.written == []
