from dataclasses import dataclass
from datetime import UTC, datetime

from universal_memory.domain.entities import FactScope, FactStatus
from universal_memory.domain.ports import FactRepository


@dataclass(frozen=True, slots=True)
class ContextHygieneCommand:
    scope: FactScope


@dataclass(frozen=True, slots=True)
class ContextHygieneResult:
    stale_count: int
    archived_count: int
    audit_reference: str


class ContextHygieneUseCase:
    def __init__(self, *, fact_repository: FactRepository) -> None:
        self.fact_repository = fact_repository

    def execute(self, command: ContextHygieneCommand) -> ContextHygieneResult:
        stale_count = 0
        archived_count = 0
        to_write = []

        for fact in self.fact_repository.list(scope=command.scope):
            next_status: FactStatus | None = None
            if fact.status == FactStatus.active:
                next_status = FactStatus.stale
                stale_count += 1
            elif fact.status == FactStatus.stale:
                next_status = FactStatus.archived
                archived_count += 1

            if next_status is not None:
                to_write.append(
                    fact.model_copy(update={"status": next_status, "updated_at": datetime.now(UTC)})
                )

        if to_write:
            self.fact_repository.write_batch(to_write)

        return ContextHygieneResult(
            stale_count=stale_count,
            archived_count=archived_count,
            audit_reference="repository-managed",
        )
