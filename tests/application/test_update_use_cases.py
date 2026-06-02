from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.application.update import (
    TARGET_SCHEMA_VERSION,
    UpdateBenchmarksCommand,
    UpdateBenchmarksUseCase,
    UpdateCheckCommand,
    UpdateCheckUseCase,
    UpdateMigrateCommand,
    UpdateMigrateUseCase,
)
from universal_memory.domain import SnapshotFailedError, StorageError
from universal_memory.infrastructure.security import (
    EntropySecretScanner,
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)

MIN_BENCHMARK_FACT_COUNT = 1000
MIN_BENCHMARK_QUERY_COUNT = 30


def _safe_write(project_root: Path) -> SafeWriteUseCase:
    return SafeWriteUseCase(
        project_root=project_root,
        secret_scanner=EntropySecretScanner(),
        snapshot_repository=LocalSnapshotRepository(
            project_root=project_root,
            data_root=project_root / ".umem",
        ),
        audit_log_repository=LocalAuditLogRepository(
            project_root=project_root,
            data_root=project_root / ".umem",
        ),
    )


def _init_project(project_root: Path) -> None:
    (project_root / ".umem" / "memory").mkdir(parents=True)
    (project_root / ".umem" / "benchmarks").mkdir(parents=True)
    (project_root / ".umem" / "config.toml").write_text(
        (
            '[hosts]\nenabled = ["codex"]\n\n'
            '[preferences]\nlocale = "pt_BR"\n\n'
            "[custom]\nflag = true\n"
        ),
        encoding="utf-8",
    )


def test_update_check_is_read_only_and_reports_required_fields(tmp_path: Path) -> None:
    _init_project(tmp_path)
    facts = tmp_path / ".umem" / "memory" / "facts.jsonl"
    facts.write_text('{"schema_version":1,"id":"x"}\nnot-json\n', encoding="utf-8")
    result_file = tmp_path / ".umem" / "benchmarks" / "retrieval-results.json"
    result_file.write_text('{"custom": true}\n', encoding="utf-8")
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in [tmp_path / ".umem" / "config.toml", facts, result_file]
    }

    result = UpdateCheckUseCase(installed_version="test-version").execute(
        UpdateCheckCommand(project_root=tmp_path)
    )

    assert result.installed_version == "test-version"
    assert result.target_schema_version == TARGET_SCHEMA_VERSION
    assert result.project_config_schema_version is None
    assert result.memory_schema_versions["facts.jsonl"] == [1]
    assert result.benchmarks_status == "present"
    assert result.updates_available is False
    assert result.migration_required is True
    assert any("corrupt" in warning for warning in result.warnings)
    assert {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in [tmp_path / ".umem" / "config.toml", facts, result_file]
    } == before


def test_update_migrate_preserves_config_and_memory_custom_fields(tmp_path: Path) -> None:
    _init_project(tmp_path)
    fact_id = "00000000-0000-4000-8000-000000000001"
    rule_id = "00000000-0000-4000-8000-000000000002"
    (tmp_path / ".umem" / "memory" / "facts.jsonl").write_text(
        json.dumps(
            {
                "id": fact_id,
                "created_at": "2026-05-01T00:00:00Z",
                "updated_at": "2026-05-01T00:00:00Z",
                "content": "Preserve me",
                "scope": "project",
                "source": "test",
                "status": "active",
                "tags": ["legacy"],
                "metadata": {"kept": True},
                "custom_field": "safe-extra",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / ".umem" / "memory" / "rules.jsonl").write_text(
        json.dumps(
            {
                "id": rule_id,
                "created_at": "2026-05-01T00:00:00Z",
                "updated_at": "2026-05-01T00:00:00Z",
                "name": "Rule",
                "content": "Keep rule",
                "scope": "project",
                "status": "active",
                "extra": "value",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = UpdateMigrateUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
        UpdateMigrateCommand(project_root=tmp_path)
    )

    config_text = (tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8")
    assert "schema_version = 1" in config_text
    config_data = tomllib.loads(config_text)
    assert config_data["hosts"]["enabled"] == ["codex"]
    assert config_data["preferences"]["locale"] == "pt_BR"
    assert config_data["custom"]["flag"] is True
    migrated_fact = json.loads((tmp_path / ".umem" / "memory" / "facts.jsonl").read_text().strip())
    migrated_rule = json.loads((tmp_path / ".umem" / "memory" / "rules.jsonl").read_text().strip())
    assert migrated_fact["id"] == fact_id
    assert migrated_fact["schema_version"] == 1
    assert migrated_fact["metadata"]["kept"] is True
    assert migrated_fact["metadata"]["custom_field"] == "safe-extra"
    assert migrated_rule["metadata"]["extra"] == "value"
    assert result.migrated_files == [
        ".umem/config.toml",
        ".umem/memory/facts.jsonl",
        ".umem/memory/rules.jsonl",
    ]
    assert result.audit_reference
    assert result.snapshot_references


def test_update_migrate_invalid_jsonl_aborts_without_rewrite(tmp_path: Path) -> None:
    _init_project(tmp_path)
    facts = tmp_path / ".umem" / "memory" / "facts.jsonl"
    original = '{"id":"ok"}\n{broken\n'
    facts.write_text(original, encoding="utf-8")

    with pytest.raises(StorageError):
        UpdateMigrateUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
            UpdateMigrateCommand(project_root=tmp_path)
        )

    assert facts.read_text(encoding="utf-8") == original


def test_update_migrate_snapshot_failure_preserves_original(tmp_path: Path) -> None:
    _init_project(tmp_path)
    original = (tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8")

    class FailingSafeWrite:
        def execute(self, command: SafeWriteCommand):
            if command.relative_path == ".umem/config.toml":
                raise SnapshotFailedError("snapshot failed")
            raise AssertionError("unexpected write")

    with pytest.raises(SnapshotFailedError):
        UpdateMigrateUseCase(safe_write_use_case=FailingSafeWrite()).execute(  # type: ignore[arg-type]
            UpdateMigrateCommand(project_root=tmp_path)
        )

    assert (tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8") == original


def test_update_benchmarks_runs_offline_and_uses_safe_write(tmp_path: Path) -> None:
    _init_project(tmp_path)
    existing = tmp_path / ".umem" / "benchmarks" / "retrieval-results.json"
    existing.write_text('{"custom": true}\n', encoding="utf-8")

    result = UpdateBenchmarksUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
        UpdateBenchmarksCommand(project_root=tmp_path)
    )

    assert result.benchmarks_updated is True
    assert result.retrieval_results_path == ".umem/benchmarks/retrieval-results.json"
    assert result.fact_count >= MIN_BENCHMARK_FACT_COUNT
    assert result.query_count >= MIN_BENCHMARK_QUERY_COUNT
    assert result.selected_default_strategy == "local_text"
    assert result.p95_latency_ms >= 0
    assert result.audit_reference
    assert (
        json.loads(existing.read_text(encoding="utf-8"))["fact_count"]
        >= MIN_BENCHMARK_FACT_COUNT
    )
