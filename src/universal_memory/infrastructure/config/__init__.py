"""Project layout and configuration I/O helpers."""

from universal_memory.infrastructure.config.adapters import (
    LocalConfigValidationPort,
    LocalProjectLayoutPort,
)
from universal_memory.infrastructure.config.project_layout import (
    PROJECT_LAYOUT_PATHS,
    SHARED_LAYOUT_PATHS,
    ensure_shared_project_layout,
    ensure_project_layout,
    inspect_project_layout,
    is_project_initialized,
    render_project_layout_metadata,
    resolve_project_layout,
    write_project_layout_metadata,
)
from universal_memory.infrastructure.config.toml_loader import (
    LoadedConfig,
    dump_toml_document,
    load_config,
)

__all__ = [
    "PROJECT_LAYOUT_PATHS",
    "SHARED_LAYOUT_PATHS",
    "LoadedConfig",
    "LocalConfigValidationPort",
    "LocalProjectLayoutPort",
    "dump_toml_document",
    "ensure_shared_project_layout",
    "ensure_project_layout",
    "inspect_project_layout",
    "is_project_initialized",
    "load_config",
    "render_project_layout_metadata",
    "resolve_project_layout",
    "write_project_layout_metadata",
]
