import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.domain import FactNotFoundError, StorageError
from universal_memory.domain.entities import Fact, FactScope, FactStatus
from universal_memory.infrastructure.storage import LocalFactRepository


def make_fact(
    *,
    scope: FactScope = FactScope.project,
    status: FactStatus = FactStatus.active,
    content: str = "Preferir TDD para memoria local",
    created_at: datetime | None = None,
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
        tags=["memory"],
        metadata={"origin": "unit-test"},
    )


def test_initializes_with_explicit_storage_path(tmp_path: Path) -> None:
    facts_path = tmp_path / ".umem" / "memory" / "facts.jsonl"

    repository = LocalFactRepository(project_root=tmp_path, facts_path=facts_path)

    assert repository.project_root == tmp_path
    assert repository.facts_path == facts_path
    assert repository.list() == []


def test_list_filters_by_scope_and_status_ordered_by_creation(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)
    base = datetime(2026, 5, 26, tzinfo=UTC)
    project_active = make_fact(scope=FactScope.project, status=FactStatus.active, created_at=base)
    global_active = make_fact(
        scope=FactScope.global_, status=FactStatus.active, created_at=base + timedelta(minutes=1)
    )
    project_stale = make_fact(
        scope=FactScope.project, status=FactStatus.stale, created_at=base + timedelta(minutes=2)
    )

    repository.write(project_stale)
    repository.write(global_active)
    repository.write(project_active)

    assert repository.list(scope=FactScope.project) == [project_active, project_stale]
    assert repository.list(status=FactStatus.active) == [project_active, global_active]
    assert repository.list(scope=FactScope.global_, status=FactStatus.active) == [global_active]


def test_read_returns_fact_by_id_or_raises_typed_not_found(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)
    fact = make_fact()
    repository.write(fact)

    assert repository.read(fact.id) == fact

    with pytest.raises(FactNotFoundError, match="Fact not found"):
        repository.read(str(uuid4()))


def test_write_adds_and_updates_fact_directly(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)
    fact = make_fact(content="Versao inicial")
    updated = fact.model_copy(update={"content": "Versao atualizada"})

    repository.write(fact)
    repository.write(updated)

    assert repository.list() == [updated]
    lines = repository.facts_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["content"] == "Versao atualizada"


def test_delete_soft_deletes_fact_as_archived(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)
    fact = make_fact()
    repository.write(fact)

    repository.delete(fact.id)

    deleted = repository.read(fact.id)
    assert deleted.status == FactStatus.archived
    assert deleted.updated_at >= fact.updated_at


def test_purge_removes_fact_permanently(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)
    kept = make_fact(content="Manter")
    removed = make_fact(content="Remover")
    repository.write(kept)
    repository.write(removed)

    repository.purge(removed.id)

    assert repository.list() == [kept]
    with pytest.raises(FactNotFoundError):
        repository.read(removed.id)


def test_list_returns_empty_when_file_is_missing_or_empty(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)

    assert repository.list() == []

    repository.facts_path.parent.mkdir(parents=True, exist_ok=True)
    repository.facts_path.write_text("", encoding="utf-8")

    assert repository.list(scope=FactScope.project, status=FactStatus.active) == []


def test_corrupt_lines_are_skipped_individually(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)
    fact = make_fact()
    repository.facts_path.parent.mkdir(parents=True)
    repository.facts_path.write_text(
        "\n".join(["{not-json}", fact.model_dump_json(), '{"id":"invalid"}']),
        encoding="utf-8",
    )

    assert repository.list() == [fact]


def test_unreadable_storage_raises_typed_storage_error(tmp_path: Path) -> None:
    repository = LocalFactRepository(project_root=tmp_path)
    repository.facts_path.parent.mkdir(parents=True)
    repository.facts_path.mkdir()

    with pytest.raises(StorageError, match="Failed to read facts"):
        repository.list()
