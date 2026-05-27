from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.application.memory import (
    ListFactsCommand,
    ListFactsUseCase,
    RememberFactCommand,
    RememberFactUseCase,
    SearchFactsCommand,
    SearchFactsUseCase,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain import FactNotFoundError, SecretDetectedError
from universal_memory.domain.entities import AuditEvent, Fact, FactScope, FactStatus, Snapshot
from universal_memory.domain.ports import (
    AuditLogRepository,
    FactRepository,
    SecretScannerPort,
    SnapshotRepository,
)
from universal_memory.infrastructure.storage import LocalFactRepository

MIN_REGEX_QUERY_LENGTH = 2
EXPECTED_SEARCH_RESULT_COUNT = 2


class RecordingScanner(SecretScannerPort):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.scanned: list[str] = []

    def scan(self, content: str, *, origin: str | None = None) -> None:
        self.scanned.append(f"{origin}:{content}")
        if self.error is not None:
            raise self.error


class RecordingSnapshotRepository(SnapshotRepository):
    def __init__(self) -> None:
        self.written: list[Snapshot] = []

    def read(self, id: str) -> Snapshot:
        raise KeyError(id)

    def get_content(self, id: str) -> bytes:
        raise KeyError(id)

    def list(self, scope=None, status=None) -> list[Snapshot]:
        return self.written

    def write(self, entity: Snapshot) -> None:
        self.written.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


class RecordingAuditRepository(AuditLogRepository):
    def __init__(self) -> None:
        self.written: list[AuditEvent] = []

    def read(self, id: str) -> AuditEvent:
        raise KeyError(id)

    def list(self, scope=None) -> list[AuditEvent]:
        return self.written

    def write(self, entity: AuditEvent) -> None:
        self.written.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


class RecordingFactRepository(FactRepository):
    def __init__(self, facts: list[Fact] | None = None) -> None:
        self.facts = facts or []
        self.filters: list[tuple[FactScope | None, FactStatus | None]] = []
        self.searches: list[tuple[str, bool]] = []

    def read(self, id: str) -> Fact:
        for fact in self.facts:
            if fact.id == id:
                return fact
        raise FactNotFoundError(f"Fact not found: {id}")

    def list(self, scope: FactScope | None = None, status: FactStatus | None = None) -> list[Fact]:
        self.filters.append((scope, status))
        facts = self.facts
        if scope is not None:
            facts = [fact for fact in facts if fact.scope == scope]
        if status is not None:
            facts = [fact for fact in facts if fact.status == status]
        return sorted(facts, key=lambda fact: fact.created_at)

    def search(self, query: str, include_inactive: bool = False) -> list[Fact]:
        self.searches.append((query, include_inactive))
        if not query.strip():
            return []

        is_regex = (
            query.startswith("/") and query.endswith("/") and len(query) > MIN_REGEX_QUERY_LENGTH
        )
        clean_query = query[1:-1] if is_regex else query

        def normalize(value: str) -> str:
            decomposed = unicodedata.normalize("NFKD", value)
            without_accents = "".join(
                char for char in decomposed if not unicodedata.combining(char)
            )
            return without_accents.casefold()

        normalized_query = normalize(clean_query)
        facts = self.facts
        if not include_inactive:
            facts = [fact for fact in facts if fact.status == FactStatus.active]

        matches = []
        for fact in facts:
            if fact.content is None:
                continue
            normalized_content = normalize(fact.content)
            if is_regex:
                try:
                    if re.search(normalized_query, normalized_content) is not None:
                        matches.append(fact)
                except re.error:
                    pass
            elif normalized_query in normalized_content:
                matches.append(fact)

        return sorted(matches, key=lambda fact: fact.created_at, reverse=True)

    def write(self, entity: Fact) -> None:
        self.facts = [fact for fact in self.facts if fact.id != entity.id]
        self.facts.append(entity)

    def delete(self, id: str) -> None:
        raise NotImplementedError

    def purge(self, id: str) -> None:
        raise NotImplementedError

    def migrate(self, target_version: int) -> None:
        return None


def make_fact(
    *,
    scope: FactScope = FactScope.project,
    status: FactStatus = FactStatus.active,
    created_at: datetime | None = None,
    content: str = "Fato persistido",
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
    )


def build_safe_write(
    tmp_path: Path,
    *,
    scanner: RecordingScanner | None = None,
) -> tuple[
    SafeWriteUseCase,
    RecordingScanner,
    RecordingSnapshotRepository,
    RecordingAuditRepository,
]:
    resolved_scanner = scanner or RecordingScanner()
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    return (
        SafeWriteUseCase(
            project_root=tmp_path,
            secret_scanner=resolved_scanner,
            snapshot_repository=snapshots,
            audit_log_repository=audit,
        ),
        resolved_scanner,
        snapshots,
        audit,
    )


def test_remember_fact_persists_full_fact_through_safe_write_pipeline(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)
    safe_write, scanner, snapshots, audit = build_safe_write(tmp_path)
    use_case = RememberFactUseCase(fact_repository=repository, safe_write_use_case=safe_write)

    result = use_case.execute(
        RememberFactCommand(
            content="Preferir testes RED antes da implementacao",
            scope=FactScope.project,
            source="user_explicit",
            tags=["tdd", "memory"],
            metadata={"confidence": "high"},
            origin="cli",
        )
    )

    stored = repository.read(result.fact.id)
    assert stored.schema_version == 1
    assert stored.id == result.fact.id
    assert stored.created_at.tzinfo == UTC
    assert stored.updated_at.tzinfo == UTC
    assert stored.scope == FactScope.project
    assert stored.status == FactStatus.active
    assert stored.source == "user_explicit"
    assert stored.tags == ["tdd", "memory"]
    assert stored.metadata == {"confidence": "high"}
    assert scanner.scanned
    assert snapshots.written
    assert audit.written[0].result == "success"
    assert result.audit_reference == audit.written[0].audit_reference


def test_remember_fact_blocks_secret_and_records_safe_block_audit(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)
    safe_write, _scanner, snapshots, audit = build_safe_write(
        tmp_path,
        scanner=RecordingScanner(
            SecretDetectedError("blocked", metadata={"kind": "github_pat", "span": (0, 12)})
        ),
    )
    use_case = RememberFactUseCase(fact_repository=repository, safe_write_use_case=safe_write)

    with pytest.raises(SecretDetectedError):
        use_case.execute(
            RememberFactCommand(
                content="github_pat_1234567890",
                scope=FactScope.project,
                source="user_explicit",
                origin="cli",
            )
        )

    assert repository.list() == []
    assert snapshots.written == []
    assert len(audit.written) == 1
    assert audit.written[0].result == "blocked"
    assert audit.written[0].status == "blocked"


def test_list_facts_delegates_filters_to_repository() -> None:
    base = datetime(2026, 5, 26, tzinfo=UTC)
    project_active = make_fact(
        scope=FactScope.project, status=FactStatus.active, created_at=base
    )
    global_active = make_fact(
        scope=FactScope.global_, status=FactStatus.active, created_at=base + timedelta(minutes=1)
    )
    project_archived = make_fact(
        scope=FactScope.project, status=FactStatus.archived, created_at=base + timedelta(minutes=2)
    )
    repository = RecordingFactRepository([project_archived, global_active, project_active])
    use_case = ListFactsUseCase(fact_repository=repository)

    result = use_case.execute(ListFactsCommand(scope=FactScope.project, status=FactStatus.active))

    assert repository.filters == [(FactScope.project, FactStatus.active)]
    assert result.facts == [project_active]


def test_list_facts_returns_explicit_empty_list() -> None:
    use_case = ListFactsUseCase(fact_repository=RecordingFactRepository())

    result = use_case.execute(ListFactsCommand(scope=FactScope.global_, status=FactStatus.stale))

    assert result.facts == []


def test_search_facts_delegates_query_and_inactive_filter_to_repository() -> None:
    base = datetime(2026, 5, 26, tzinfo=UTC)
    archived = make_fact(
        status=FactStatus.archived,
        content="Fato arquivado de teste",
        created_at=base,
    )
    active = make_fact(
        status=FactStatus.active,
        content="Fato ativo de teste",
        created_at=base + timedelta(minutes=1),
    )
    repository = RecordingFactRepository([active, archived])
    use_case = SearchFactsUseCase(fact_repository=repository)

    result = use_case.execute(SearchFactsCommand(query="fato", include_inactive=True))

    assert repository.searches == [("fato", True)]
    assert len(result.items) == EXPECTED_SEARCH_RESULT_COUNT
    assert result.items[0].fact == active
    assert result.items[0].match_snippet == "Fato ativo de teste"
    assert result.items[0].match_reason == "Correspondência exata por substring"
    assert result.items[1].fact == archived
    assert result.items[1].match_snippet == "Fato arquivado de teste"
    assert result.items[1].match_reason == "Correspondência exata por substring"


def test_search_facts_returns_empty_result_for_blank_query_without_repository_call() -> None:
    repository = RecordingFactRepository([make_fact()])
    use_case = SearchFactsUseCase(fact_repository=repository)

    result = use_case.execute(SearchFactsCommand(query="   "))

    assert repository.searches == []
    assert result.items == []
