from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain.entities import Fact, FactScope, FactStatus
from universal_memory.domain.ports import FactRepository


@dataclass(frozen=True, slots=True)
class RememberFactCommand:
    content: str
    scope: FactScope
    source: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    origin: str = "application"


@dataclass(frozen=True, slots=True)
class RememberFactResult:
    fact: Fact
    audit_reference: str
    snapshot_reference: str


class RememberFactUseCase:
    def __init__(
        self,
        *,
        fact_repository: FactRepository,
        safe_write_use_case: SafeWriteUseCase | None = None,
    ) -> None:
        self.fact_repository = fact_repository
        self.safe_write_use_case = safe_write_use_case
        
        # Propagate safe_write_use_case to repository for legacy test structures
        if safe_write_use_case is not None and hasattr(fact_repository, "safe_write_use_case"):
            local_repository = cast(Any, fact_repository)
            if local_repository.safe_write_use_case is None:
                local_repository.safe_write_use_case = safe_write_use_case
                global_use_case = SafeWriteUseCase(
                    project_root=getattr(safe_write_use_case, "project_root", Path.home()),
                    secret_scanner=safe_write_use_case.secret_scanner,
                    snapshot_repository=safe_write_use_case.snapshot_repository,
                    audit_log_repository=safe_write_use_case.audit_log_repository,
                )
                local_repository.global_safe_write_use_case = global_use_case

    def execute(self, command: RememberFactCommand) -> RememberFactResult:
        timestamp = datetime.now(UTC)
        fact = Fact(
            id=str(uuid4()),
            created_at=timestamp,
            updated_at=timestamp,
            content=command.content,
            scope=command.scope,
            source=command.source,
            status=FactStatus.active,
            tags=command.tags,
            metadata=command.metadata,
        )

        # Delegate entirely to the locked Repository to prevent race conditions
        write_result = self.fact_repository.write(fact)

        # Retrieve audit and snapshot references from the repository safe write execution
        audit_ref = "UNAUDITED"
        snapshot_ref = ""
        
        # SafeWriteResult can be returned from LocalFactRepository.write in python
        if write_result is not None and hasattr(write_result, "audit_reference"):
            safe_result = cast(Any, write_result)
            audit_ref = getattr(safe_result, "audit_reference", "UNAUDITED")
            snapshot_ref = getattr(safe_result, "snapshot_reference", "")

        return RememberFactResult(
            fact=fact,
            audit_reference=audit_ref,
            snapshot_reference=snapshot_ref,
        )
