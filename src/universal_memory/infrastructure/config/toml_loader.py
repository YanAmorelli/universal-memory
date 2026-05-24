from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli_w

from universal_memory.domain import InvalidConfigError, StorageError

try:
    import tomllib
except ModuleNotFoundError as error:  # pragma: no cover
    raise RuntimeError("Python 3.11+ with tomllib is required") from error


TomlData = dict[str, Any]


@dataclass(frozen=True, slots=True)
class LoadedConfig:
    global_config_path: Path
    project_config_path: Path
    global_data: TomlData
    project_data: TomlData
    merged: TomlData
    resolved_paths: TomlData


def load_config(project_root: Path, global_config_path: Path | None = None) -> LoadedConfig:
    normalized_project_root = project_root.resolve()
    resolved_global_config_path = (
        global_config_path.resolve()
        if global_config_path is not None
        else Path.home() / ".config" / "universal-memory" / "config.toml"
    )
    project_config_path = normalized_project_root / ".umem" / "config.toml"

    global_data = _read_toml_document(resolved_global_config_path)
    project_data = _read_toml_document(project_config_path)
    merged = _deep_merge(global_data, project_data)
    resolved_paths = _deep_merge(
        _resolve_config_paths(global_data, resolved_global_config_path.parent),
        _resolve_config_paths(project_data, normalized_project_root),
    )

    return LoadedConfig(
        global_config_path=resolved_global_config_path,
        project_config_path=project_config_path,
        global_data=global_data,
        project_data=project_data,
        merged=merged,
        resolved_paths=resolved_paths,
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
