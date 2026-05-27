from dataclasses import dataclass

from universal_memory.domain.entities import Fact, FactScope, FactStatus
from universal_memory.domain.ports import FactRepository


@dataclass(frozen=True, slots=True)
class ListFactsCommand:
    scope: FactScope | None = None
    status: FactStatus | None = None


@dataclass(frozen=True, slots=True)
class ListFactsResult:
    facts: list[Fact]


class ListFactsUseCase:
    def __init__(self, *, fact_repository: FactRepository) -> None:
        self.fact_repository = fact_repository

    def execute(self, command: ListFactsCommand) -> ListFactsResult:
        facts = self.fact_repository.list(scope=command.scope, status=command.status)
        return ListFactsResult(facts=facts)
