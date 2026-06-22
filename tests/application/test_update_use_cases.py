from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import cast

import pytest

from universal_memory.application.onboarding.setup_project import (
    DEFAULT_UMEM_SKILL_REFERENCES,
    setup_project,
)
from universal_memory.application.security import (
    PreparedSafeWrite,
    SafeWriteCommand,
    SafeWriteUseCase,
)
from universal_memory.application.update import (
    TARGET_SCHEMA_VERSION,
    UpdateBenchmarksCommand,
    UpdateBenchmarksUseCase,
    UpdateCheckCommand,
    UpdateCheckUseCase,
    UpdateManagedSkillsCommand,
    UpdateManagedSkillsUseCase,
    UpdateMigrateCommand,
    UpdateMigrateUseCase,
)
from universal_memory.domain import (
    InvalidConfigError,
    SnapshotFailedError,
    StorageError,
    ValidationFailedError,
)
from universal_memory.domain.entities import Snapshot
from universal_memory.infrastructure.config import LocalConfigValidationPort, LocalProjectLayoutPort
from universal_memory.infrastructure.security import (
    EntropySecretScanner,
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)

MIN_BENCHMARK_FACT_COUNT = 1000
MIN_BENCHMARK_QUERY_COUNT = 30
VALID_CREATED_AT = "2026-05-01T00:00:00Z"
LEGACY_SKILLS_LIFECYCLE = """# Skills Lifecycle

Use this reference for UMEM skill discovery, latent skill tracking, approval, generation,
activation, deactivation, and updates.

## Canonical CLI

```bash
umem skills list --format json
umem skills generate <latent-skill-id> --yes --format json
umem skills update <latent-skill-id> --file <relative-markdown-path> --format json
```
"""


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


def _setup_full_project(project_root: Path) -> None:
    setup_project(
        project_root,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )


def _legacy_fact_payload(
    fact_id: str = "00000000-0000-4000-8000-000000000001",
) -> dict[str, object]:
    return {
        "id": fact_id,
        "created_at": VALID_CREATED_AT,
        "updated_at": VALID_CREATED_AT,
        "content": "Preserve me",
        "scope": "project",
        "source": "test",
        "status": "active",
    }


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


def test_update_managed_skills_updates_legacy_default_umem_lifecycle(
    tmp_path: Path,
) -> None:
    _setup_full_project(tmp_path)
    lifecycle_path = (
        tmp_path
        / ".umem"
        / "skills"
        / "use-universal-memory"
        / "references"
        / "skills-lifecycle.md"
    )
    lifecycle_path.write_text(LEGACY_SKILLS_LIFECYCLE, encoding="utf-8")

    result = UpdateManagedSkillsUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
        UpdateManagedSkillsCommand(project_root=tmp_path)
    )

    assert len(result) == 1
    assert result[0].status == "updated"
    assert result[0].updated_paths == [
        ".umem/skills/use-universal-memory/references/skills-lifecycle.md"
    ]
    assert result[0].audit_reference
    assert result[0].snapshot_reference
    assert (
        lifecycle_path.read_text(encoding="utf-8")
        == DEFAULT_UMEM_SKILL_REFERENCES[
            ".umem/skills/use-universal-memory/references/skills-lifecycle.md"
        ]
    )


def test_update_managed_skills_detects_default_umem_skill_without_latent_record(
    tmp_path: Path,
) -> None:
    _setup_full_project(tmp_path)
    (tmp_path / ".umem" / "memory" / "latent_skills.jsonl").unlink()
    lifecycle_path = (
        tmp_path
        / ".umem"
        / "skills"
        / "use-universal-memory"
        / "references"
        / "skills-lifecycle.md"
    )
    lifecycle_path.write_text(LEGACY_SKILLS_LIFECYCLE, encoding="utf-8")

    result = UpdateManagedSkillsUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
        UpdateManagedSkillsCommand(project_root=tmp_path)
    )

    assert len(result) == 1
    assert result[0].status == "updated"
    assert result[0].updated_paths == [
        ".umem/skills/use-universal-memory/references/skills-lifecycle.md"
    ]


def test_update_managed_skills_preserves_custom_default_umem_skill_with_warning(
    tmp_path: Path,
) -> None:
    _setup_full_project(tmp_path)
    lifecycle_path = (
        tmp_path
        / ".umem"
        / "skills"
        / "use-universal-memory"
        / "references"
        / "skills-lifecycle.md"
    )
    custom_content = "# Skills Lifecycle\n\nCustom team instructions.\n"
    lifecycle_path.write_text(custom_content, encoding="utf-8")

    result = UpdateManagedSkillsUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
        UpdateManagedSkillsCommand(project_root=tmp_path)
    )

    assert result[0].status == "preserved"
    assert result[0].updated_paths == []
    assert (
        ".umem/skills/use-universal-memory/references/skills-lifecycle.md"
        in result[0].preserved_paths
    )
    assert any("Preserved customized UMEM skill file" in warning for warning in result[0].warnings)
    assert lifecycle_path.read_text(encoding="utf-8") == custom_content


def test_update_check_treats_boolean_config_schema_as_invalid(tmp_path: Path) -> None:
    _init_project(tmp_path)
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.write_text("schema_version = true\n", encoding="utf-8")

    result = UpdateCheckUseCase(installed_version="test-version").execute(
        UpdateCheckCommand(project_root=tmp_path)
    )

    assert result.project_config_schema_version is None
    assert result.migration_required is True
    assert any("schema_version is not an integer" in warning for warning in result.warnings)


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
    assert config_data["runtimes"]["enabled"] == ["codex"]
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


def test_update_migrate_migrates_legacy_json_with_snapshot_and_audit(tmp_path: Path) -> None:
    _init_project(tmp_path)
    legacy_json = tmp_path / ".umem" / "memory" / "facts.json"
    payload = _legacy_fact_payload()
    payload["custom_field"] = "safe-extra"
    legacy_json.write_text(json.dumps([payload], sort_keys=True), encoding="utf-8")

    check = UpdateCheckUseCase(installed_version="test-version").execute(
        UpdateCheckCommand(project_root=tmp_path)
    )
    result = UpdateMigrateUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
        UpdateMigrateCommand(project_root=tmp_path)
    )

    migrated = json.loads(legacy_json.read_text(encoding="utf-8"))
    assert check.memory_schema_versions["facts.json"] == [0]
    assert migrated[0]["schema_version"] == 1
    assert migrated[0]["metadata"]["custom_field"] == "safe-extra"
    assert ".umem/memory/facts.json" in result.migrated_files
    assert result.audit_reference
    assert result.snapshot_references


def test_update_migrate_updates_explicit_legacy_config_schema(tmp_path: Path) -> None:
    _init_project(tmp_path)
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.write_text(
        'schema_version = 0\n\n[hosts]\nenabled = ["codex"]\n',
        encoding="utf-8",
    )

    UpdateMigrateUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
        UpdateMigrateCommand(project_root=tmp_path)
    )

    config_data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert config_data["schema_version"] == 1
    assert config_data["runtimes"]["enabled"] == ["codex"]


def test_update_migrate_prepares_all_snapshots_before_any_rewrite(tmp_path: Path) -> None:
    _init_project(tmp_path)
    facts = tmp_path / ".umem" / "memory" / "facts.jsonl"
    facts.write_text(json.dumps(_legacy_fact_payload()) + "\n", encoding="utf-8")
    calls: list[str] = []

    class RecordingSafeWrite:
        def prepare(self, command: SafeWriteCommand) -> PreparedSafeWrite:
            calls.append(f"prepare:{command.relative_path}")
            return PreparedSafeWrite(
                command=command,
                relative_path=command.relative_path,
                target_path=tmp_path / command.relative_path,
                snapshot=cast(Snapshot, object()),
                previous_bytes=(tmp_path / command.relative_path).read_bytes()
                if (tmp_path / command.relative_path).exists()
                else b"",
                previous_file_existed=(tmp_path / command.relative_path).exists(),
            )

        def commit_prepared(self, prepared: PreparedSafeWrite):
            calls.append(f"commit:{prepared.relative_path}")
            return type(
                "Result",
                (),
                {
                    "relative_path": prepared.relative_path,
                    "audit_reference": f"audit:{prepared.relative_path}",
                    "snapshot_reference": f"snapshot:{prepared.relative_path}",
                },
            )()

        def execute(self, command: SafeWriteCommand):
            raise AssertionError("migrations should use prepare/commit_prepared")

        def rollback_prepared(self, prepared: PreparedSafeWrite) -> None:
            raise AssertionError("unexpected rollback")

    UpdateMigrateUseCase(safe_write_use_case=RecordingSafeWrite()).execute(  # type: ignore[arg-type]
        UpdateMigrateCommand(project_root=tmp_path)
    )

    first_commit = next(index for index, call in enumerate(calls) if call.startswith("commit:"))
    assert all(call.startswith("prepare:") for call in calls[:first_commit])
    assert calls[:first_commit] == [
        "prepare:.umem/config.toml",
        "prepare:.umem/memory/facts.jsonl",
    ]


def test_update_migrate_rolls_back_committed_files_when_later_commit_fails(
    tmp_path: Path,
) -> None:
    _init_project(tmp_path)
    config_path = tmp_path / ".umem" / "config.toml"
    facts_path = tmp_path / ".umem" / "memory" / "facts.jsonl"
    facts_path.write_text(json.dumps(_legacy_fact_payload()) + "\n", encoding="utf-8")
    original_config = config_path.read_bytes()

    class FailingCommitSafeWrite:
        def prepare(self, command: SafeWriteCommand) -> PreparedSafeWrite:
            target_path = tmp_path / command.relative_path
            return PreparedSafeWrite(
                command=command,
                relative_path=command.relative_path,
                target_path=target_path,
                snapshot=cast(Snapshot, object()),
                previous_bytes=target_path.read_bytes() if target_path.exists() else b"",
                previous_file_existed=target_path.exists(),
            )

        def commit_prepared(self, prepared: PreparedSafeWrite):
            if prepared.relative_path == ".umem/memory/facts.jsonl":
                raise StorageError("write failed")
            prepared.target_path.write_text(prepared.command.content, encoding="utf-8")
            return type(
                "Result",
                (),
                {
                    "relative_path": prepared.relative_path,
                    "audit_reference": f"audit:{prepared.relative_path}",
                    "snapshot_reference": f"snapshot:{prepared.relative_path}",
                },
            )()

        def rollback_prepared(self, prepared: PreparedSafeWrite) -> None:
            if prepared.previous_file_existed:
                prepared.target_path.write_bytes(prepared.previous_bytes)
            else:
                prepared.target_path.unlink(missing_ok=True)

        def execute(self, command: SafeWriteCommand):
            raise AssertionError("unexpected execute")

    with pytest.raises(StorageError):
        UpdateMigrateUseCase(safe_write_use_case=FailingCommitSafeWrite()).execute(  # type: ignore[arg-type]
            UpdateMigrateCommand(project_root=tmp_path)
        )

    assert config_path.read_bytes() == original_config


def test_update_migrate_rejects_invalid_config_schema_type(tmp_path: Path) -> None:
    _init_project(tmp_path)
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.write_text('schema_version = "0"\n', encoding="utf-8")

    with pytest.raises(InvalidConfigError):
        UpdateMigrateUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
            UpdateMigrateCommand(project_root=tmp_path)
        )


def test_update_migrate_rejects_boolean_config_schema_version(tmp_path: Path) -> None:
    _init_project(tmp_path)
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.write_text("schema_version = true\n", encoding="utf-8")

    with pytest.raises(InvalidConfigError):
        UpdateMigrateUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
            UpdateMigrateCommand(project_root=tmp_path)
        )


def test_update_migrate_rejects_boolean_memory_schema_version(tmp_path: Path) -> None:
    _init_project(tmp_path)
    facts_path = tmp_path / ".umem" / "memory" / "facts.jsonl"
    facts_path.write_text('{"id":"fact","schema_version":true}\n', encoding="utf-8")

    with pytest.raises(ValidationFailedError):
        UpdateMigrateUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
            UpdateMigrateCommand(project_root=tmp_path)
        )


def test_update_migrate_rejects_incomplete_jsonl_after_model_validation(tmp_path: Path) -> None:
    _init_project(tmp_path)
    facts_path = tmp_path / ".umem" / "memory" / "facts.jsonl"
    facts_path.write_text('{"id":"00000000-0000-4000-8000-000000000001"}\n', encoding="utf-8")

    with pytest.raises(ValidationFailedError):
        UpdateMigrateUseCase(safe_write_use_case=_safe_write(tmp_path)).execute(
            UpdateMigrateCommand(project_root=tmp_path)
        )


def test_update_migrate_invalid_jsonl_aborts_without_rewrite(tmp_path: Path) -> None:
    _init_project(tmp_path)
    facts = tmp_path / ".umem" / "memory" / "facts.jsonl"
    original = json.dumps(_legacy_fact_payload()) + "\n{broken\n"
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
        def prepare(self, command: SafeWriteCommand):
            if command.relative_path == ".umem/config.toml":
                raise SnapshotFailedError("snapshot failed")
            raise AssertionError("unexpected write")

        def commit_prepared(self, prepared: PreparedSafeWrite):
            raise AssertionError("unexpected commit")

        def rollback_prepared(self, prepared: PreparedSafeWrite) -> None:
            raise AssertionError("unexpected rollback")

        def execute(self, command: SafeWriteCommand):
            raise AssertionError("unexpected execute")

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
        json.loads(existing.read_text(encoding="utf-8"))["fact_count"] >= MIN_BENCHMARK_FACT_COUNT
    )
