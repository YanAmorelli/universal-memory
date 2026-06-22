from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from universal_memory.application.memory import PurgeFactCommand, PurgeFactUseCase
from universal_memory.domain import FactNotFoundError, ValidationFailedError
from universal_memory.domain.entities import Fact, FactScope, FactStatus
from universal_memory.domain.ports import FactRepository


class RecordingFactRepository(FactRepository):
    def __init__(self, facts: list[Fact] | None = None) -> None:
        self.facts = facts or []
        self.read_ids: list[str] = []
        self.list_filters: list[tuple[FactScope | None, FactStatus | None]] = []
        self.purged_ids: list[str] = []

    def read(self, id: str) -> Fact:
        self.read_ids.append(id)
        for fact in self.facts:
            if fact.id == id:
                return fact
        raise FactNotFoundError(f"Fact not found: {id}")

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
        self.facts = [fact for fact in self.facts if fact.id != entity.id]
        self.facts.append(entity)
        return None

    def delete(self, id: str) -> None:
        return None

    def purge(self, id: str) -> None:
        self.purged_ids.append(id)
        self.facts = [fact for fact in self.facts if fact.id != id]

    def migrate(self, target_version: int) -> None:
        return None


def make_fact(*, scope: FactScope = FactScope.project) -> Fact:
    timestamp = datetime.now(UTC)
    return Fact(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        content="Fato para purga",
        scope=scope,
        source="test",
        status=FactStatus.active,
    )


def test_purge_fact_by_id_reads_then_purges_single_fact() -> None:
    fact = make_fact()
    repository = RecordingFactRepository([fact])
    use_case = PurgeFactUseCase(fact_repository=repository)

    result = use_case.execute(PurgeFactCommand(id=fact.id, scope=None, origin="cli"))

    assert repository.read_ids == [fact.id]
    assert repository.purged_ids == [fact.id]
    assert result.purged_count == 1
    assert result.affected_ids == [fact.id]
    assert result.audit_reference == "repository-managed"


def test_purge_fact_by_id_raises_when_fact_does_not_exist() -> None:
    repository = RecordingFactRepository()
    use_case = PurgeFactUseCase(fact_repository=repository)

    with pytest.raises(FactNotFoundError):
        use_case.execute(PurgeFactCommand(id=str(uuid4()), scope=None))

    assert repository.purged_ids == []


def test_purge_fact_by_scope_only_removes_matching_scope() -> None:
    project_fact = make_fact(scope=FactScope.project)
    global_fact = make_fact(scope=FactScope.global_)
    repository = RecordingFactRepository([project_fact, global_fact])
    use_case = PurgeFactUseCase(fact_repository=repository)

    result = use_case.execute(PurgeFactCommand(id=None, scope=FactScope.project))

    assert repository.list_filters == [(FactScope.project, None)]
    assert repository.purged_ids == [project_fact.id]
    assert result.purged_count == 1
    assert result.affected_ids == [project_fact.id]


def test_purge_fact_requires_id_or_scope() -> None:
    use_case = PurgeFactUseCase(fact_repository=RecordingFactRepository())

    with pytest.raises(ValidationFailedError, match="fact ID or a scope"):
        use_case.execute(PurgeFactCommand(id=None, scope=None))


def test_purge_fact_raises_when_both_id_and_scope_provided() -> None:
    use_case = PurgeFactUseCase(fact_repository=RecordingFactRepository())

    with pytest.raises(ValidationFailedError, match="not both"):
        use_case.execute(PurgeFactCommand(id="fact-id", scope=FactScope.project))
