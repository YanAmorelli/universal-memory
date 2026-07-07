from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli_w

from universal_memory.application.security import (
    SafeWriteCommand,
    SafeWriteResult,
    SafeWriteUseCase,
)
from universal_memory.domain import InvalidConfigError, StorageError
from universal_memory.domain.entities import AuditEventScope

try:
    import tomllib
except ModuleNotFoundError as error:  # pragma: no cover
    raise RuntimeError("Python 3.11+ with tomllib is required") from error


TomlData = dict[str, Any]


@dataclass(frozen=True, slots=True)
class LoadedConfig:
    global_config_path: Path
    project_config_path: Path
    shared_project_config_path: Path
    global_data: TomlData
    project_data: TomlData
    shared_project_data: TomlData
    merged: TomlData
    resolved_paths: TomlData
    write_result: SafeWriteResult | None = None


@dataclass(frozen=True, slots=True)
class ConfigWriteOptions:
    safe_write_use_case: SafeWriteUseCase
    origin: str = "config"
    action: str = "update_project_config"
    scope: str = "project"


def load_config(project_root: Path, global_config_path: Path | None = None) -> LoadedConfig:
    normalized_project_root = project_root.resolve()
    resolved_global_config_path = (
        global_config_path.resolve()
        if global_config_path is not None
        else Path.home() / ".config" / "umem" / "config.toml"
    )
    project_config_path = normalized_project_root / ".umem" / "config.toml"
    shared_project_config_path = normalized_project_root / "umem" / "project.toml"

    global_data = _read_toml_document(resolved_global_config_path)
    project_data = _read_toml_document(project_config_path)
    raw_shared_project_data = _read_toml_document(shared_project_config_path)
    shared_project_data = (
        {"project_layout": raw_shared_project_data} if raw_shared_project_data else {}
    )
    merged = _with_legacy_hosts_migration(
        _deep_merge(_deep_merge(global_data, project_data), shared_project_data)
    )
    resolved_paths = _deep_merge(
        _resolve_config_paths(global_data, resolved_global_config_path.parent),
        _deep_merge(
            _resolve_config_paths(project_data, normalized_project_root),
            _resolve_config_paths(shared_project_data, normalized_project_root),
        ),
    )

    return LoadedConfig(
        global_config_path=resolved_global_config_path,
        project_config_path=project_config_path,
        shared_project_config_path=shared_project_config_path,
        global_data=global_data,
        project_data=project_data,
        shared_project_data=shared_project_data,
        merged=merged,
        resolved_paths=resolved_paths,
    )


def update_project_config(
    project_root: Path,
    updates: TomlData,
    global_config_path: Path | None = None,
    write_options: ConfigWriteOptions | None = None,
) -> LoadedConfig:
    loaded = load_config(project_root=project_root, global_config_path=global_config_path)
    is_global = write_options is not None and write_options.scope == "global"
    config_path = loaded.global_config_path if is_global else loaded.project_config_path

    if is_global:
        global_data = _deep_merge(loaded.global_data, updates)
        rendered = dump_toml_document(global_data)
        project_data = loaded.project_data
    else:
        project_data = _deep_merge(loaded.project_data, updates)
        rendered = dump_toml_document(project_data)
        global_data = loaded.global_data

    write_result = None
    if write_options is None:
        temp_path = config_path.with_suffix(".tmp")
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_text(rendered, encoding="utf-8")
            temp_path.replace(config_path)
        except OSError as error:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass
            raise StorageError(f"Failed to write config {config_path.name}: {error}") from error
    elif is_global:
        global_config_dir = config_path.parent
        global_config_dir.mkdir(parents=True, exist_ok=True)
        use_case = SafeWriteUseCase(
            project_root=global_config_dir,
            secret_scanner=write_options.safe_write_use_case.secret_scanner,
            snapshot_repository=write_options.safe_write_use_case.snapshot_repository,
            audit_log_repository=write_options.safe_write_use_case.audit_log_repository,
        )
        write_result = use_case.execute(
            SafeWriteCommand(
                relative_path=config_path.name,
                content=rendered,
                scope=AuditEventScope.global_,
                origin=write_options.origin,
                action=write_options.action,
            )
        )
    else:
        try:
            relative_path = str(config_path.relative_to(project_root.resolve()))
        except ValueError:
            relative_path = ".umem/config.toml"
        write_result = write_options.safe_write_use_case.execute(
            SafeWriteCommand(
                relative_path=relative_path,
                content=rendered,
                scope=AuditEventScope.project,
                origin=write_options.origin,
                action=write_options.action,
            )
        )

    merged = _with_legacy_hosts_migration(
        _deep_merge(_deep_merge(global_data, project_data), loaded.shared_project_data)
    )
    resolved_paths = _deep_merge(
        _resolve_config_paths(global_data, loaded.global_config_path.parent),
        _deep_merge(
            _resolve_config_paths(project_data, project_root.resolve()),
            _resolve_config_paths(loaded.shared_project_data, project_root.resolve()),
        ),
    )
    return LoadedConfig(
        global_config_path=loaded.global_config_path,
        project_config_path=loaded.project_config_path,
        shared_project_config_path=loaded.shared_project_config_path,
        global_data=global_data,
        project_data=project_data,
        shared_project_data=loaded.shared_project_data,
        merged=merged,
        resolved_paths=resolved_paths,
        write_result=write_result,
    )


def dump_toml_document(document: TomlData) -> str:
    return tomli_w.dumps(document)


def _read_toml_document(path: Path) -> TomlData:
    if not path.exists():
        return {}
    if not path.is_file():
        raise InvalidConfigError(f"Invalid config path {path.name}: expected a file")

    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as error:
        raise InvalidConfigError(f"Invalid TOML in {path.name}: {error}") from error
    except OSError as error:
        raise StorageError(f"Failed to read config {path.name}: {error}") from error

    if not isinstance(data, dict):
        raise InvalidConfigError(f"Invalid TOML in {path.name}: root must be a table")
    return data


def _deep_merge(base: TomlData, override: TomlData) -> TomlData:
    merged: TomlData = deepcopy(base)

    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
            continue
        merged[key] = deepcopy(value)

    return merged


def _with_legacy_hosts_migration(document: TomlData) -> TomlData:
    migrated = deepcopy(document)
    if "runtimes" not in migrated and isinstance(migrated.get("hosts"), dict):
        hosts_enabled = migrated["hosts"].get("enabled")
        if hosts_enabled is not None:
            migrated["runtimes"] = {"enabled": deepcopy(hosts_enabled)}
    return migrated


def _resolve_config_paths(document: TomlData, base_dir: Path) -> TomlData:
    resolved: TomlData = {}

    for key, value in document.items():
        if isinstance(value, dict):
            nested = _resolve_config_paths(value, base_dir)
            if nested:
                resolved[key] = nested
            continue
        if isinstance(value, str) and _looks_like_path_key(key):
            resolved[key] = _resolve_path(base_dir, value)

    return resolved


def _looks_like_path_key(key: str) -> bool:
    return key.endswith(("_path", "_paths", "_dir", "_root"))


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()
