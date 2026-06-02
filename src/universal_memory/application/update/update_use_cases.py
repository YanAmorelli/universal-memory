from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, cast

import tomli_w
from pydantic import BaseModel, ValidationError

from universal_memory import __version__
from universal_memory.application.security import (
    PreparedSafeWrite,
    SafeWriteCommand,
    SafeWriteResult,
)
from universal_memory.domain import InvalidConfigError, StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEventScope,
    ContextSummary,
    Fact,
    LatentSkill,
    Rule,
)

try:
    import tomllib
except ModuleNotFoundError as error:  # pragma: no cover
    raise RuntimeError("Python 3.11+ with tomllib is required") from error

TARGET_SCHEMA_VERSION = 1
MEMORY_FILES = (
    "facts.jsonl",
    "rules.jsonl",
    "latent_skills.jsonl",
    "context_summaries.jsonl",
)
LEGACY_MEMORY_FILES = tuple(filename.removesuffix("l") for filename in MEMORY_FILES)
ALL_MEMORY_FILES = (*MEMORY_FILES, *LEGACY_MEMORY_FILES)
MEMORY_ALLOWED_FIELDS: dict[str, set[str]] = {
    "facts.jsonl": {
        "schema_version",
        "id",
        "created_at",
        "updated_at",
        "content",
        "scope",
        "source",
        "status",
        "recurrence_count",
        "tags",
        "metadata",
    },
    "rules.jsonl": {
        "schema_version",
        "id",
        "created_at",
        "updated_at",
        "name",
        "content",
        "scope",
        "status",
        "metadata",
    },
    "latent_skills.jsonl": {
        "schema_version",
        "id",
        "created_at",
        "updated_at",
        "name",
        "description",
        "scope",
        "status",
        "recurrence_count",
        "metadata",
    },
    "context_summaries.jsonl": {
        "schema_version",
        "id",
        "created_at",
        "updated_at",
        "project_summary",
        "universal_preferences",
        "active_rules",
        "audit_reference",
        "status",
        "scope",
        "metadata",
    },
}
MEMORY_MODELS: dict[str, type[BaseModel]] = {
    "facts": Fact,
    "rules": Rule,
    "latent_skills": LatentSkill,
    "context_summaries": ContextSummary,
}


class SafeWritePort(Protocol):
    def execute(self, command: SafeWriteCommand) -> SafeWriteResult: ...

    def prepare(self, command: SafeWriteCommand) -> PreparedSafeWrite: ...

    def commit_prepared(self, prepared: PreparedSafeWrite) -> SafeWriteResult: ...

    def rollback_prepared(self, prepared: PreparedSafeWrite) -> None: ...


BenchmarkRunner = Callable[[Path], dict[str, object]]


@dataclass(frozen=True, slots=True)
class UpdateCheckCommand:
    project_root: Path


@dataclass(frozen=True, slots=True)
class UpdateCheckResult:
    installed_version: str
    target_schema_version: int
    project_config_schema_version: int | None
    memory_schema_versions: dict[str, list[int]]
    benchmarks_status: str
    updates_available: bool | str
    migration_required: bool
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "installed_version": self.installed_version,
            "target_schema_version": self.target_schema_version,
            "project_config_schema_version": self.project_config_schema_version,
            "memory_schema_versions": self.memory_schema_versions,
            "benchmarks_status": self.benchmarks_status,
            "updates_available": self.updates_available,
            "migration_required": self.migration_required,
            "warnings": self.warnings,
        }


@dataclass(frozen=True, slots=True)
class UpdateMigrateCommand:
    project_root: Path
    origin: str = "cli"


@dataclass(frozen=True, slots=True)
class UpdateMigrateResult:
    target_schema_version: int
    migrated_files: list[str]
    audit_reference: str
    snapshot_references: list[str]
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "target_schema_version": self.target_schema_version,
            "migrated_files": self.migrated_files,
            "audit_reference": self.audit_reference,
            "snapshot_references": self.snapshot_references,
            "warnings": self.warnings,
        }


@dataclass(frozen=True, slots=True)
class UpdateBenchmarksCommand:
    project_root: Path
    origin: str = "cli"


@dataclass(frozen=True, slots=True)
class UpdateBenchmarksResult:
    benchmarks_updated: bool
    retrieval_results_path: str
    query_count: int
    fact_count: int
    selected_default_strategy: str
    p95_latency_ms: float
    audit_reference: str
    snapshot_reference: str
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "benchmarks_updated": self.benchmarks_updated,
            "retrieval_results_path": self.retrieval_results_path,
            "query_count": self.query_count,
            "fact_count": self.fact_count,
            "selected_default_strategy": self.selected_default_strategy,
            "p95_latency_ms": self.p95_latency_ms,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "warnings": self.warnings,
        }


class UpdateCheckUseCase:
    def __init__(self, *, installed_version: str = __version__) -> None:
        self.installed_version = installed_version

    def execute(self, command: UpdateCheckCommand) -> UpdateCheckResult:
        root = command.project_root
        data_root = root / ".umem"
        warnings: list[str] = []

        if not data_root.exists():
            warnings.append(".umem directory is missing; run `umem init` first.")
        config_version = self._read_config_version(data_root / "config.toml", warnings)
        memory_versions = self._read_memory_versions(data_root / "memory", warnings)
        benchmarks_path = data_root / "benchmarks" / "retrieval-results.json"
        benchmarks_status = "present" if benchmarks_path.is_file() else "missing"
        if benchmarks_status == "missing":
            warnings.append(
                "Benchmark results are missing at .umem/benchmarks/retrieval-results.json."
            )

        migration_required = (
            config_version != TARGET_SCHEMA_VERSION
            or self._config_requires_runtime_migration(data_root / "config.toml", warnings)
            or any(
                any(version != TARGET_SCHEMA_VERSION for version in versions)
                for versions in memory_versions.values()
            )
        )
        return UpdateCheckResult(
            installed_version=self.installed_version,
            target_schema_version=TARGET_SCHEMA_VERSION,
            project_config_schema_version=config_version,
            memory_schema_versions=memory_versions,
            benchmarks_status=benchmarks_status,
            updates_available=False,
            migration_required=migration_required,
            warnings=warnings,
        )

    def _read_config_version(self, path: Path, warnings: list[str]) -> int | None:
        if not path.exists():
            warnings.append("Project config is missing at .umem/config.toml.")
            return None
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as error:
            warnings.append(f"Invalid TOML in .umem/config.toml: {error}")
            return None
        except OSError as error:
            warnings.append(f"Could not read .umem/config.toml: {error}")
            return None
        raw = data.get("schema_version")
        if raw is None:
            return None
        if type(raw) is int:
            if raw > TARGET_SCHEMA_VERSION:
                warnings.append("Project config schema_version is newer than supported.")
            return raw
        warnings.append("Project config schema_version is not an integer.")
        return None

    def _read_memory_versions(  # noqa: PLR0912
        self, memory_root: Path, warnings: list[str]
    ) -> dict[str, list[int]]:
        versions_by_file: dict[str, list[int]] = {}
        if not memory_root.exists():
            warnings.append("Memory directory is missing at .umem/memory/.")
            return versions_by_file
        for filename in ALL_MEMORY_FILES:
            path = memory_root / filename
            if not path.exists():
                continue
            found: set[int] = set()
            records: list[tuple[int, Any]] = []
            if filename.endswith(".jsonl"):
                try:
                    lines = path.read_text(encoding="utf-8").splitlines()
                except OSError as error:
                    warnings.append(f"Could not read .umem/memory/{filename}: {error}")
                    continue
                for line_number, line in enumerate(lines, start=1):
                    if not line.strip():
                        continue
                    try:
                        records.append((line_number, json.loads(line)))
                    except json.JSONDecodeError:
                        warnings.append(
                            f"corrupt JSONL line in .umem/memory/{filename}:{line_number}."
                        )
            else:
                try:
                    records = _read_memory_records(path, filename)
                except OSError as error:
                    warnings.append(f"Could not read .umem/memory/{filename}: {error}")
                    continue
                except json.JSONDecodeError as error:
                    warnings.append(f"corrupt JSON in .umem/memory/{filename}: {error}.")
                    versions_by_file[filename] = sorted(found)
                    continue
                except TypeError as error:
                    warnings.append(f"Invalid memory file .umem/memory/{filename}: {error}.")
                    versions_by_file[filename] = sorted(found)
                    continue
            for line_number, payload in records:
                if not isinstance(payload, dict):
                    warnings.append(
                        f"Invalid memory record in .umem/memory/{filename}:{line_number}."
                    )
                    continue
                raw_version = payload.get("schema_version")
                version = raw_version if type(raw_version) is int else 0
                if raw_version is not None and type(raw_version) is not int:
                    warnings.append(
                        f".umem/memory/{filename}:{line_number} schema_version is not an integer."
                    )
                if version > TARGET_SCHEMA_VERSION:
                    warnings.append(f".umem/memory/{filename} has schema newer than supported.")
                found.add(version)
            versions_by_file[filename] = sorted(found)
        return versions_by_file

    def _config_requires_runtime_migration(self, path: Path, warnings: list[str]) -> bool:
        if not path.exists():
            return False
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (tomllib.TOMLDecodeError, OSError):
            return False
        needs_migration = "runtimes" not in data and isinstance(data.get("hosts"), dict)
        if needs_migration:
            warnings.append("Legacy [hosts] config will be migrated to [runtimes].")
        return needs_migration


def _read_memory_records(path: Path, filename: str) -> list[tuple[int, Any]]:
    if filename.endswith(".jsonl"):
        records: list[tuple[int, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            records.append((line_number, json.loads(line)))
        return records
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return list(enumerate(raw, start=1))
    if isinstance(raw, dict):
        return [(1, raw)]
    raise TypeError("expected a JSON object or array")


def _memory_model_for(filename: str) -> type[BaseModel]:
    stem = Path(filename).stem
    model = MEMORY_MODELS.get(stem)
    if model is None:  # pragma: no cover - guarded by ALL_MEMORY_FILES
        raise ValidationFailedError(f"Unsupported memory file .umem/memory/{filename}.")
    return model


def _validate_memory_payload(filename: str, payload: dict[str, Any], line_number: int) -> None:
    try:
        _memory_model_for(filename).model_validate(payload)
    except ValidationError as error:
        raise ValidationFailedError(
            f"Invalid migrated memory record in .umem/memory/{filename}:{line_number}: {error}"
        ) from error


class UpdateMigrateUseCase:
    def __init__(self, *, safe_write_use_case: SafeWritePort) -> None:
        self.safe_write_use_case = safe_write_use_case

    def execute(self, command: UpdateMigrateCommand) -> UpdateMigrateResult:
        root = command.project_root
        config_path = root / ".umem" / "config.toml"
        warnings = [
            "TOML comments and formatting may be normalized; snapshot was created before write."
        ]
        planned_memory = self._plan_memory_migrations(root / ".umem" / "memory")
        planned_config = self._plan_config_migration(config_path)

        planned_writes: list[SafeWriteCommand] = []
        if planned_config is not None:
            planned_writes.append(
                self._safe_write_command(
                    relative_path=".umem/config.toml",
                    content=planned_config,
                    origin=command.origin,
                    action="update_migrate_config",
                )
            )

        for relative_path, content in planned_memory:
            planned_writes.append(
                self._safe_write_command(
                    relative_path=relative_path,
                    content=content,
                    origin=command.origin,
                    action="update_migrate_memory",
                )
            )

        prepared_writes = [self.safe_write_use_case.prepare(write) for write in planned_writes]
        migrated_files: list[str] = []
        audit_refs: list[str] = []
        snapshot_refs: list[str] = []
        committed_writes: list[PreparedSafeWrite] = []
        for prepared in prepared_writes:
            try:
                result = self.safe_write_use_case.commit_prepared(prepared)
            except Exception as error:
                self._rollback_committed_writes(committed_writes, error)
                raise
            committed_writes.append(prepared)
            migrated_files.append(result.relative_path)
            audit_refs.append(result.audit_reference)
            snapshot_refs.append(result.snapshot_reference)

        return UpdateMigrateResult(
            target_schema_version=TARGET_SCHEMA_VERSION,
            migrated_files=migrated_files,
            audit_reference=audit_refs[-1] if audit_refs else "",
            snapshot_references=snapshot_refs,
            warnings=warnings,
        )

    def _rollback_committed_writes(
        self,
        committed_writes: list[PreparedSafeWrite],
        original_error: Exception,
    ) -> None:
        for prepared in reversed(committed_writes):
            try:
                self.safe_write_use_case.rollback_prepared(prepared)
            except Exception as rollback_error:
                original_error.add_note(
                    f"Rollback failed for {prepared.relative_path}: {rollback_error}"
                )

    def _plan_config_migration(self, path: Path) -> str | None:
        data: dict[str, Any]
        if path.exists():
            try:
                with path.open("rb") as handle:
                    data = tomllib.load(handle)
            except tomllib.TOMLDecodeError as error:
                raise InvalidConfigError(f"Invalid TOML in .umem/config.toml: {error}") from error
            except OSError as error:
                raise StorageError(f"Failed to read .umem/config.toml: {error}") from error
        else:
            data = {}
        raw_version = data.get("schema_version")
        if raw_version is not None and type(raw_version) is not int:
            raise InvalidConfigError("config schema_version must be an integer.")
        needs_runtime_migration = "runtimes" not in data and isinstance(data.get("hosts"), dict)
        if raw_version == TARGET_SCHEMA_VERSION and not needs_runtime_migration:
            return None
        if raw_version is not None and raw_version > TARGET_SCHEMA_VERSION:
            raise InvalidConfigError("Cannot downgrade config schema_version.")
        migrated = {**data, "schema_version": TARGET_SCHEMA_VERSION}
        if needs_runtime_migration:
            hosts = migrated["hosts"]
            enabled = hosts.get("enabled")
            if enabled is not None:
                migrated["runtimes"] = {"enabled": enabled}
        rendered = tomli_w.dumps(migrated)
        try:
            tomllib.loads(rendered)
        except tomllib.TOMLDecodeError as error:
            raise InvalidConfigError(f"Rendered config is invalid: {error}") from error
        return rendered

    def _plan_memory_migrations(self, memory_root: Path) -> list[tuple[str, str]]:
        planned: list[tuple[str, str]] = []
        for filename in ALL_MEMORY_FILES:
            path = memory_root / filename
            if not path.exists():
                continue
            changed = False
            try:
                records = _read_memory_records(path, filename)
            except OSError as error:
                raise StorageError(f"Failed to read .umem/memory/{filename}: {error}") from error
            except json.JSONDecodeError as error:
                raise StorageError(f"Corrupt JSON in .umem/memory/{filename}: {error}") from error
            except TypeError as error:
                raise ValidationFailedError(
                    f"Invalid memory file .umem/memory/{filename}: {error}."
                ) from error
            migrated_records: list[dict[str, Any]] = []
            for line_number, payload in records:
                if not isinstance(payload, dict):
                    raise ValidationFailedError(
                        f"Invalid memory record in .umem/memory/{filename}:{line_number}."
                    )
                migrated = self._migrate_memory_payload(filename, payload, line_number)
                changed = changed or migrated != payload
                migrated_records.append(migrated)
            if changed:
                force_list = filename.endswith(".json") and self._json_memory_file_is_list(path)
                planned.append((
                    f".umem/memory/{filename}",
                    self._render_memory_records(filename, migrated_records, force_list=force_list),
                ))
        return planned

    def _json_memory_file_is_list(self, path: Path) -> bool:
        try:
            return isinstance(json.loads(path.read_text(encoding="utf-8")), list)
        except json.JSONDecodeError as error:
            raise StorageError(f"Corrupt JSON in {path}: {error}") from error

    def _render_memory_records(
        self, filename: str, records: list[dict[str, Any]], *, force_list: bool = False
    ) -> str:
        if filename.endswith(".jsonl"):
            lines = [
                json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records
            ]
            return f"{'\n'.join(lines)}\n"
        content: Any = records if force_list or len(records) != 1 else records[0]
        return f"{json.dumps(content, indent=2, sort_keys=True)}\n"

    def _migrate_memory_payload(
        self, filename: str, payload: dict[str, Any], line_number: int
    ) -> dict[str, Any]:
        raw_version = payload.get("schema_version", 0)
        if type(raw_version) is not int:
            raise ValidationFailedError(
                f".umem/memory/{filename}:{line_number} schema_version must be an integer."
            )
        if raw_version > TARGET_SCHEMA_VERSION:
            raise ValidationFailedError(f"Cannot downgrade .umem/memory/{filename}.")
        if raw_version == TARGET_SCHEMA_VERSION:
            _validate_memory_payload(filename, payload, line_number)
            return payload
        allowed = MEMORY_ALLOWED_FIELDS[f"{Path(filename).stem}.jsonl"]
        migrated = {key: value for key, value in payload.items() if key in allowed}
        raw_metadata = migrated.get("metadata")
        metadata = cast(dict[str, Any], raw_metadata) if isinstance(raw_metadata, dict) else {}
        extras = {key: value for key, value in payload.items() if key not in allowed}
        if extras:
            metadata = {**metadata, **extras}
            migrated["metadata"] = metadata
        migrated["schema_version"] = TARGET_SCHEMA_VERSION
        _validate_memory_payload(filename, migrated, line_number)
        return migrated

    def _safe_write_command(
        self,
        *,
        relative_path: str,
        content: str,
        origin: str,
        action: str,
    ) -> SafeWriteCommand:
        return SafeWriteCommand(
            relative_path=relative_path,
            content=content,
            scope=AuditEventScope.project,
            origin=origin,
            action=action,
        )


class UpdateBenchmarksUseCase:
    def __init__(
        self,
        *,
        safe_write_use_case: SafeWritePort,
        benchmark_runner: BenchmarkRunner | None = None,
    ) -> None:
        self.safe_write_use_case = safe_write_use_case
        self.benchmark_runner = benchmark_runner or self._default_runner

    def execute(self, command: UpdateBenchmarksCommand) -> UpdateBenchmarksResult:
        relative_path = ".umem/benchmarks/retrieval-results.json"
        with tempfile.TemporaryDirectory(prefix="umem-benchmarks-") as temp_dir:
            payload = self.benchmark_runner(Path(temp_dir))
        selected = str(payload.get("selected_default_strategy", ""))
        strategies = payload.get("strategies")
        selected_metrics = strategies.get(selected, {}) if isinstance(strategies, dict) else {}
        p95 = (
            selected_metrics.get("p95_latency_ms", 0.0)
            if isinstance(selected_metrics, dict)
            else 0.0
        )
        query_count = payload.get("query_count", 0)
        fact_count = payload.get("fact_count", 0)
        rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        result = self.safe_write_use_case.execute(
            SafeWriteCommand(
                relative_path=relative_path,
                content=rendered,
                scope=AuditEventScope.project,
                origin=command.origin,
                action="update_benchmarks",
            )
        )
        return UpdateBenchmarksResult(
            benchmarks_updated=True,
            retrieval_results_path=relative_path,
            query_count=int(query_count) if isinstance(query_count, int | float | str) else 0,
            fact_count=int(fact_count) if isinstance(fact_count, int | float | str) else 0,
            selected_default_strategy=selected,
            p95_latency_ms=float(p95),
            audit_reference=result.audit_reference,
            snapshot_reference=result.snapshot_reference,
            warnings=[],
        )

    @staticmethod
    def _default_runner(project_root: Path) -> dict[str, object]:
        from benchmarks.retrieval import run_benchmark  # noqa: PLC0415

        return run_benchmark(project_root=project_root)
