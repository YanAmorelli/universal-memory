from dataclasses import dataclass
from pathlib import Path

from universal_memory.domain import ConfigValidationPort, ProjectLayoutPort
from universal_memory.infrastructure.config.toml_loader import update_project_config

DEFAULT_ENABLED_HOST_IDS = ["codex", "claude_code"]


@dataclass(frozen=True, slots=True)
class SetupProjectResult:
    project_path: Path
    config_path: Path
    memory_path: Path
    audit_path: Path
    snapshots_path: Path
    skills_path: Path
    benchmarks_path: Path
    created: bool
    already_initialized: bool
    created_paths: list[str]
    existing_paths: list[str]


def setup_project(
    project_root: Path,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
    global_config_path: Path | None = None,
    enabled_host_ids: list[str] | None = None,
) -> SetupProjectResult:
    normalized_project_root = project_root.resolve()
    layout_result = layout_port.ensure_project_layout(normalized_project_root)
    if enabled_host_ids is not None:
        unsupported = [h for h in enabled_host_ids if h not in DEFAULT_ENABLED_HOST_IDS]
        if unsupported:
            from universal_memory.domain import InvalidConfigError
            raise InvalidConfigError(f"Hosts nao suportados: {', '.join(unsupported)}")

    update_project_config(
        normalized_project_root,
        {"hosts": {"enabled": enabled_host_ids if enabled_host_ids is not None else DEFAULT_ENABLED_HOST_IDS}},
        global_config_path=global_config_path,
    )

    # Validate config after materializing defaults so downstream adapters can rely on valid TOML.
    config_validation_port.validate_project_config(
        project_root=normalized_project_root,
        global_config_path=global_config_path,
    )

    umem_root = Path(".umem")
    return SetupProjectResult(
        project_path=Path("."),
        config_path=umem_root / "config.toml",
        memory_path=umem_root / "memory",
        audit_path=umem_root / "audit" / "events.jsonl",
        snapshots_path=umem_root / "snapshots",
        skills_path=umem_root / "skills",
        benchmarks_path=umem_root / "benchmarks",
        created=layout_result.created,
        already_initialized=not layout_result.created,
        created_paths=layout_result.created_paths,
        existing_paths=layout_result.existing_paths,
    )
