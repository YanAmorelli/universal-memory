import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.domain import StorageError
from universal_memory.domain.entities import ContextSummary, ContextSummaryScope
from universal_memory.infrastructure.storage import LocalContextSummaryRepository


def make_context_summary(
    *,
    scope: ContextSummaryScope = ContextSummaryScope.project,
    status: str = "completed",
    created_at: datetime | None = None,
) -> ContextSummary:
    timestamp = created_at or datetime.now(UTC)
    return ContextSummary(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        project_summary="- Projeto prefere TDD",
        universal_preferences="- Responder em portugues",
        active_rules="- Nunca expor segredos",
        audit_reference=str(uuid4()),
        status=status,
        scope=scope,
    )


def test_initializes_with_explicit_storage_path(tmp_path: Path) -> None:
    summaries_path = tmp_path / ".umem" / "memory" / "context_summaries.jsonl"

    repository = LocalContextSummaryRepository(
        project_root=tmp_path,
        summaries_path=summaries_path,
    )

    assert repository.project_root == tmp_path
    assert repository.summaries_path == summaries_path
    assert repository.list() == []


def test_write_adds_and_updates_context_summary(tmp_path: Path) -> None:
    repository = LocalContextSummaryRepository(project_root=tmp_path)
    summary = make_context_summary(status="generated")
    updated = summary.model_copy(update={"status": "injected"})

    repository.write(summary)
    repository.write(updated)

    assert repository.list() == [updated]
    lines = repository.summaries_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["status"] == "injected"


def test_read_returns_context_summary_by_id_or_raises_typed_error(tmp_path: Path) -> None:
    repository = LocalContextSummaryRepository(project_root=tmp_path)
    summary = make_context_summary()
    repository.write(summary)

    assert repository.read(summary.id) == summary

    with pytest.raises(StorageError, match="Context summary not found"):
        repository.read(str(uuid4()))


def test_list_filters_by_scope_and_orders_by_creation(tmp_path: Path) -> None:
    repository = LocalContextSummaryRepository(project_root=tmp_path)
    base = datetime(2026, 5, 27, tzinfo=UTC)
    older_project = make_context_summary(
        scope=ContextSummaryScope.project,
        created_at=base,
    )
    newer_global = make_context_summary(
        scope=ContextSummaryScope.global_,
        created_at=base + timedelta(minutes=1),
    )

    repository.write(newer_global)
    repository.write(older_project)

    assert repository.list() == [older_project, newer_global]
    assert repository.list(scope=ContextSummaryScope.project) == [older_project]
    assert repository.list(scope=ContextSummaryScope.global_) == [newer_global]


def test_list_returns_empty_when_storage_file_is_missing_or_empty(tmp_path: Path) -> None:
    repository = LocalContextSummaryRepository(project_root=tmp_path)

    assert repository.list() == []

    repository.summaries_path.parent.mkdir(parents=True, exist_ok=True)
    repository.summaries_path.write_text("", encoding="utf-8")

    assert repository.list(scope=ContextSummaryScope.project) == []


def test_corrupt_lines_are_skipped_during_reads(tmp_path: Path) -> None:
    repository = LocalContextSummaryRepository(project_root=tmp_path)
    summary = make_context_summary()
    repository.summaries_path.parent.mkdir(parents=True)
    repository.summaries_path.write_text(
        "\n".join(["{not-json}", summary.model_dump_json(), '{"id":"invalid"}']),
        encoding="utf-8",
    )

    assert repository.list() == [summary]


def test_corrupt_storage_blocks_writes_without_overwriting_file(tmp_path: Path) -> None:
    repository = LocalContextSummaryRepository(project_root=tmp_path)
    repository.summaries_path.parent.mkdir(parents=True)
    repository.summaries_path.write_text("{not-json}", encoding="utf-8")

    with pytest.raises(StorageError, match="Corrupt context summary line"):
        repository.write(make_context_summary())

    assert repository.summaries_path.read_text(encoding="utf-8") == "{not-json}"


def test_unreadable_storage_raises_typed_storage_error(tmp_path: Path) -> None:
    repository = LocalContextSummaryRepository(project_root=tmp_path)
    repository.summaries_path.parent.mkdir(parents=True)
    repository.summaries_path.mkdir()

    with pytest.raises(StorageError, match="Failed to read context summaries"):
        repository.list()


def test_migrate_accepts_only_current_schema_version(tmp_path: Path) -> None:
    repository = LocalContextSummaryRepository(project_root=tmp_path)

    repository.migrate(1)

    with pytest.raises(StorageError, match="Unsupported context summary repository schema version"):
        repository.migrate(2)
