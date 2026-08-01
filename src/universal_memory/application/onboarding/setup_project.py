# ruff: noqa: E501

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from universal_memory.application.skills.official_skill_assets import official_skill_assets
from universal_memory.domain import ConfigValidationPort, InvalidConfigError, ProjectLayoutPort
from universal_memory.domain.entities.runtime import RuntimeId, default_runtime_registry
from universal_memory.infrastructure.config.toml_loader import load_config, update_project_config

DEFAULT_ENABLED_RUNTIME_IDS = [
    runtime_id.value for runtime_id in default_runtime_registry().runtime_ids
]
DEFAULT_ENABLED_HOST_IDS = DEFAULT_ENABLED_RUNTIME_IDS
DEFAULT_UMEM_SKILL_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_UMEM_SKILL_NAME = "universal-memory"
LEGACY_DEFAULT_UMEM_SKILL_NAME = "use-universal-memory"
DEFAULT_UMEM_SKILL_ROOT = ".umem/skills/universal-memory"
LEGACY_DEFAULT_UMEM_SKILL_ROOT = ".umem/skills/use-universal-memory"
DEFAULT_UMEM_SKILL_RELATIVE_PATH = f"{DEFAULT_UMEM_SKILL_ROOT}/SKILL.md"
LEGACY_DEFAULT_UMEM_SKILL_RELATIVE_PATH = f"{LEGACY_DEFAULT_UMEM_SKILL_ROOT}/SKILL.md"
DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH = ".umem/memory/latent_skills.jsonl"
_DEFAULT_UMEM_SKILL_ASSETS = official_skill_assets()
DEFAULT_UMEM_SKILL_MARKDOWN = _DEFAULT_UMEM_SKILL_ASSETS["SKILL.md"]
DEFAULT_UMEM_SKILL_REFERENCES = {
    f"{DEFAULT_UMEM_SKILL_ROOT}/{relative_path}": asset
    for relative_path, asset in _DEFAULT_UMEM_SKILL_ASSETS.items()
    if relative_path != "SKILL.md"
}


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
    layout: str = "legacy"
    shared_root: Path | None = None
    operational_root: Path = Path(".umem")
    shared_paths: list[str] | None = None
    operational_paths: list[str] | None = None


def setup_project(  # noqa: PLR0913
    project_root: Path,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
    global_config_path: Path | None = None,
    enabled_runtime_ids: list[str] | None = None,
    enabled_host_ids: list[str] | None = None,
    layout: str = "legacy",
) -> SetupProjectResult:
    normalized_project_root = project_root.resolve()
    layout_result = layout_port.ensure_project_layout(normalized_project_root)
    shared_created_paths: list[str] = []
    shared_existing_paths: list[str] = []
    shared_paths: list[str] = []
    if layout == "shared":
        shared_paths = ["umem/project.toml", "umem/memory", "umem/skills"]
        existing_shared_paths = {
            shared_path
            for shared_path in shared_paths
            if (normalized_project_root / shared_path).exists()
        }
        layout_port.write_project_layout_metadata(normalized_project_root, layout="shared")
        for shared_path in shared_paths:
            if shared_path in existing_shared_paths:
                shared_existing_paths.append(shared_path)
            else:
                shared_created_paths.append(shared_path)
    seeded_skill_paths = _ensure_default_umem_skill(normalized_project_root)
    loaded_config = load_config(normalized_project_root, global_config_path=global_config_path)
    requested_runtime_ids = (
        enabled_runtime_ids if enabled_runtime_ids is not None else enabled_host_ids
    )
    if requested_runtime_ids is None:
        configured_runtime_ids = _configured_runtime_ids(loaded_config.merged)
        normalized_runtime_ids = (
            configured_runtime_ids
            if configured_runtime_ids is not None
            else list(DEFAULT_ENABLED_RUNTIME_IDS)
        )
    else:
        normalized_runtime_ids = _normalize_runtime_ids(requested_runtime_ids)
    unsupported = [
        runtime_id
        for runtime_id in normalized_runtime_ids
        if runtime_id not in DEFAULT_ENABLED_RUNTIME_IDS
    ]
    if unsupported:
        raise InvalidConfigError(f"Unsupported runtimes: {', '.join(unsupported)}")

    preferences = loaded_config.project_data.get("preferences")
    updates: dict[str, Any] = {"runtimes": {"enabled": normalized_runtime_ids}}
    if not isinstance(preferences, dict) or "locale" not in preferences:
        updates["preferences"] = {"locale": "en"}

    update_project_config(
        normalized_project_root,
        updates,
        global_config_path=global_config_path,
    )

    # Validate config after materializing defaults so downstream adapters can rely on valid TOML.
    config_validation_port.validate_project_config(
        project_root=normalized_project_root,
        global_config_path=global_config_path,
    )

    umem_root = Path(".umem")
    operational_paths = [
        ".umem/config.toml",
        ".umem/memory",
        ".umem/audit/events.jsonl",
        ".umem/snapshots",
        ".umem/skills",
        ".umem/benchmarks",
    ]
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
        created_paths=[
            *layout_result.created_paths,
            *[
                shared_path
                for shared_path in shared_created_paths
                if shared_path not in layout_result.created_paths
            ],
            *seeded_skill_paths["created"],
        ],
        existing_paths=[
            *layout_result.existing_paths,
            *[
                shared_path
                for shared_path in shared_existing_paths
                if shared_path not in layout_result.existing_paths
            ],
            *seeded_skill_paths["existing"],
        ],
        layout=layout,
        shared_root=Path("umem") if layout == "shared" else None,
        operational_root=Path(".umem"),
        shared_paths=shared_paths if layout == "shared" else [],
        operational_paths=operational_paths,
    )


def _normalize_runtime_ids(runtime_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    for runtime_id in runtime_ids:
        cleaned = runtime_id.strip().lower().replace("-", "_")
        try:
            resolved = RuntimeId(cleaned).value
        except ValueError:
            resolved = cleaned
        if resolved not in normalized:
            normalized.append(resolved)
    return normalized


def _configured_runtime_ids(config_data: dict[str, Any]) -> list[str] | None:
    raw_runtimes = config_data.get("runtimes")
    if not isinstance(raw_runtimes, dict):
        return None
    raw_enabled = raw_runtimes.get("enabled")
    if not isinstance(raw_enabled, list):
        return None
    return _normalize_runtime_ids([str(runtime_id) for runtime_id in raw_enabled])


def _ensure_default_umem_skill(project_root: Path) -> dict[str, list[str]]:
    created: list[str] = []
    existing: list[str] = []

    legacy_root = project_root / LEGACY_DEFAULT_UMEM_SKILL_ROOT
    canonical_root = project_root / DEFAULT_UMEM_SKILL_ROOT
    if legacy_root.exists() and canonical_root.exists():
        raise InvalidConfigError(
            "Both legacy and canonical Universal Memory skill roots exist. Preserve both "
            "trees and choose an explicit migration before running initialization again."
        )
    if (
        legacy_root.exists()
        and not (project_root / LEGACY_DEFAULT_UMEM_SKILL_RELATIVE_PATH).is_file()
    ):
        raise InvalidConfigError(
            "The legacy Universal Memory skill root is incomplete. Preserve it and review "
            "an explicit migration before running initialization again."
        )
    if legacy_root.is_dir() and not canonical_root.exists():
        existing.extend(
            path.relative_to(project_root).as_posix()
            for path in sorted(legacy_root.rglob("*"))
            if path.is_file()
        )
        latent_skills_path = project_root / DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH
        if _default_umem_skill_is_registered(latent_skills_path):
            existing.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)
        else:
            latent_skills_path.parent.mkdir(parents=True, exist_ok=True)
            with latent_skills_path.open("a", encoding="utf-8") as file:
                file.write(_default_umem_skill_jsonl_line(name=LEGACY_DEFAULT_UMEM_SKILL_NAME))
            created.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)
        return {"created": created, "existing": existing}

    skill_path = project_root / DEFAULT_UMEM_SKILL_RELATIVE_PATH
    if skill_path.exists():
        existing.append(DEFAULT_UMEM_SKILL_RELATIVE_PATH)
    else:
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(DEFAULT_UMEM_SKILL_MARKDOWN, encoding="utf-8")
        created.append(DEFAULT_UMEM_SKILL_RELATIVE_PATH)

    for relative_path, content in DEFAULT_UMEM_SKILL_REFERENCES.items():
        reference_path = project_root / relative_path
        if reference_path.exists():
            existing.append(relative_path)
        else:
            reference_path.parent.mkdir(parents=True, exist_ok=True)
            reference_path.write_text(content, encoding="utf-8")
            created.append(relative_path)

    latent_skills_path = project_root / DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH
    if _default_umem_skill_is_registered(latent_skills_path):
        existing.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)
    else:
        latent_skills_path.parent.mkdir(parents=True, exist_ok=True)
        with latent_skills_path.open("a", encoding="utf-8") as file:
            file.write(_default_umem_skill_jsonl_line())
        created.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)

    return {"created": created, "existing": existing}


def _default_umem_skill_is_registered(latent_skills_path: Path) -> bool:
    if not latent_skills_path.exists():
        return False
    try:
        content = latent_skills_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        DEFAULT_UMEM_SKILL_ID in content
        or DEFAULT_UMEM_SKILL_NAME in content
        or LEGACY_DEFAULT_UMEM_SKILL_NAME in content
    )


def _default_umem_skill_jsonl_line(*, name: str = DEFAULT_UMEM_SKILL_NAME) -> str:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = {
        "schema_version": 1,
        "id": DEFAULT_UMEM_SKILL_ID,
        "created_at": timestamp,
        "updated_at": timestamp,
        "name": name,
        "description": (
            "Operational hub for using Universal Memory context, facts, host sync, "
            "and skills lifecycle."
        ),
        "scope": "project",
        "status": "active",
        "recurrence_count": 1,
        "metadata": {
            "origin": "umem-init",
            "audit_reference": "seeded-by-init",
            "triggers": [
                "at the start of a work session or conversation",
                "before implementing, investigating, reviewing, or planning in a repository with .umem",
                "when the user mentions memory, facts, context, skills, AGENTS.md, CLAUDE.md, host sync, or learned preferences",
                "before recording durable project or global knowledge",
                "before creating, updating, activating, or deactivating a UMEM skill",
            ],
            "evidence": [
                {
                    "origin": "umem-init",
                    "summary": "Default operational skill installed during project initialization.",
                }
            ],
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
