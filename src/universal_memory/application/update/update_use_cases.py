from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, cast

import tomli_w

from universal_memory import __version__
from universal_memory.application.security import SafeWriteCommand, SafeWriteResult
from universal_memory.domain import InvalidConfigError, StorageError, ValidationFailedError
from universal_memory.domain.entities import AuditEventScope

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


class SafeWritePort(Protocol):
    def execute(self, command: SafeWriteCommand) -> SafeWriteResult: ...


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

        migration_required = config_version != TARGET_SCHEMA_VERSION or any(
            any(version != TARGET_SCHEMA_VERSION for version in versions)
            for versions in memory_versions.values()
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
        if isinstance(raw, int):
            if raw > TARGET_SCHEMA_VERSION:
                warnings.append("Project config schema_version is newer than supported.")
            return raw
        warnings.append("Project config schema_version is not an integer.")
        return None

    def _read_memory_versions(self, memory_root: Path, warnings: list[str]) -> dict[str, list[int]]:
        versions_by_file: dict[str, list[int]] = {}
        if not memory_root.exists():
            warnings.append("Memory directory is missing at .umem/memory/.")
            return versions_by_file
        for filename in MEMORY_FILES:
            path = memory_root / filename
            if not path.exists():
                continue
            found: set[int] = set()
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError as error:
                warnings.append(f"Could not read .umem/memory/{filename}: {error}")
                continue
            for line_number, line in enumerate(lines, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    warnings.append(f"corrupt JSONL line in .umem/memory/{filename}:{line_number}.")
                    continue
                raw_version = payload.get("schema_version") if isinstance(payload, dict) else None
                version = raw_version if isinstance(raw_version, int) else 0
                if version > TARGET_SCHEMA_VERSION:
                    warnings.append(f".umem/memory/{filename} has schema newer than supported.")
                found.add(version)
            versions_by_file[filename] = sorted(found)
        return versions_by_file


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

        migrated_files: list[str] = []
        audit_refs: list[str] = []
        snapshot_refs: list[str] = []

        if planned_config is not None:
            result = self._safe_write(
                relative_path=".umem/config.toml",
                content=planned_config,
                origin=command.origin,
                action="update_migrate_config",
            )
            migrated_files.append(".umem/config.toml")
            audit_refs.append(result.audit_reference)
            snapshot_refs.append(result.snapshot_reference)

        for relative_path, content in planned_memory:
            result = self._safe_write(
                relative_path=relative_path,
                content=content,
                origin=command.origin,
                action="update_migrate_memory",
            )
            migrated_files.append(relative_path)
            audit_refs.append(result.audit_reference)
            snapshot_refs.append(result.snapshot_reference)

        return UpdateMigrateResult(
            target_schema_version=TARGET_SCHEMA_VERSION,
            migrated_files=migrated_files,
            audit_reference=audit_refs[-1] if audit_refs else "",
            snapshot_references=snapshot_refs,
            warnings=warnings,
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
        if raw_version == TARGET_SCHEMA_VERSION:
            return None
        if isinstance(raw_version, int) and raw_version > TARGET_SCHEMA_VERSION:
            raise InvalidConfigError("Cannot downgrade config schema_version.")
        migrated = {"schema_version": TARGET_SCHEMA_VERSION, **data}
        rendered = tomli_w.dumps(migrated)
        try:
            tomllib.loads(rendered)
        except tomllib.TOMLDecodeError as error:
            raise InvalidConfigError(f"Rendered config is invalid: {error}") from error
        return rendered

    def _plan_memory_migrations(self, memory_root: Path) -> list[tuple[str, str]]:
        planned: list[tuple[str, str]] = []
        for filename in MEMORY_FILES:
            path = memory_root / filename
            if not path.exists():
                continue
            migrated_lines: list[str] = []
            changed = False
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError as error:
                raise StorageError(f"Failed to read .umem/memory/{filename}: {error}") from error
            for line_number, line in enumerate(lines, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as error:
                    raise StorageError(
                        f"Corrupt JSONL line in .umem/memory/{filename}:{line_number}: {error}"
                    ) from error
                if not isinstance(payload, dict):
                    raise ValidationFailedError(
                        f"Invalid memory record in .umem/memory/{filename}:{line_number}."
                    )
                migrated = self._migrate_memory_payload(filename, payload)
                changed = changed or migrated != payload
                migrated_lines.append(json.dumps(migrated, sort_keys=True, separators=(",", ":")))
            if changed:
                planned.append((f".umem/memory/{filename}", f"{'\n'.join(migrated_lines)}\n"))
        return planned

    def _migrate_memory_payload(self, filename: str, payload: dict[str, Any]) -> dict[str, Any]:
        raw_version = payload.get("schema_version", 0)
        if isinstance(raw_version, int) and raw_version > TARGET_SCHEMA_VERSION:
            raise ValidationFailedError(f"Cannot downgrade .umem/memory/{filename}.")
        if raw_version == TARGET_SCHEMA_VERSION:
            return payload
        allowed = MEMORY_ALLOWED_FIELDS[filename]
        migrated = {key: value for key, value in payload.items() if key in allowed}
        raw_metadata = migrated.get("metadata")
        metadata = cast(dict[str, Any], raw_metadata) if isinstance(raw_metadata, dict) else {}
        extras = {key: value for key, value in payload.items() if key not in allowed}
        if extras:
            metadata = {**metadata, **extras}
            migrated["metadata"] = metadata
        migrated["schema_version"] = TARGET_SCHEMA_VERSION
        return migrated

    def _safe_write(
        self,
        *,
        relative_path: str,
        content: str,
        origin: str,
        action: str,
    ) -> SafeWriteResult:
        return self.safe_write_use_case.execute(
            SafeWriteCommand(
                relative_path=relative_path,
                content=content,
                scope=AuditEventScope.project,
                origin=origin,
                action=action,
            )
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
