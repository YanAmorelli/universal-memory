from dataclasses import dataclass

from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import FactScope
from universal_memory.domain.ports import FactRepository


@dataclass(frozen=True, slots=True)
class PurgeFactCommand:
    id: str | None
    scope: FactScope | None
    origin: str = "cli"


@dataclass(frozen=True, slots=True)
class PurgeFactResult:
    purged_count: int
    affected_ids: list[str]
    audit_reference: str


class PurgeFactUseCase:
    def __init__(self, *, fact_repository: FactRepository) -> None:
        self.fact_repository = fact_repository

    def execute(self, command: PurgeFactCommand) -> PurgeFactResult:
        if command.id is None and command.scope is None:
            raise ValidationFailedError("Provide either a fact ID or a scope to purge.")

        if command.id is not None and command.scope is not None:
            raise ValidationFailedError("Provide either a fact ID or a scope to purge, not both.")

        if command.id is not None:
            fact = self.fact_repository.read(command.id)
            self.fact_repository.purge(fact.id)
            affected_ids = [fact.id]
        else:
            facts = self.fact_repository.list(scope=command.scope)
            affected_ids = [fact.id for fact in facts]
            if affected_ids:
                self.fact_repository.purge_batch(affected_ids)

        return PurgeFactResult(
            purged_count=len(affected_ids),
            affected_ids=affected_ids,
            audit_reference="repository-managed",
        )
