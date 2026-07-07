from pathlib import Path
from typing import Any

import tomli_w

from universal_memory.domain import StorageError
from universal_memory.domain.project_layout import (
    ProjectLayoutInspection,
    ProjectLayoutMode,
    ProjectLayoutPolicy,
    ProjectLayoutPrecedence,
    ProjectLayoutResult,
    ResolvedProjectLayout,
)

try:
    import tomllib
except ModuleNotFoundError as error:  # pragma: no cover
    raise RuntimeError("Python 3.11+ with tomllib is required") from error

PROJECT_LAYOUT_PATHS = [
    ".umem/config.toml",
    ".umem/memory",
    ".umem/audit/events.jsonl",
    ".umem/snapshots",
    ".umem/skills",
    ".umem/benchmarks",
    ".umem/benchmarks/retrieval-results.json",
]

DEFAULT_CONFIG_TOML = '[project]\nname = ""\ncreated_by = "universal-memory"\n'
DEFAULT_AUDIT_EVENTS_JSONL = ""
DEFAULT_RETRIEVAL_RESULTS_JSON = "{\n}\n"
DIRECTORY_LAYOUT_PATHS = {
    ".umem/memory",
    ".umem/snapshots",
    ".umem/skills",
    ".umem/benchmarks",
}
SHARED_LAYOUT_PATHS = [
    "umem/project.toml",
    "umem/memory",
    "umem/skills",
]


def inspect_project_layout(project_root: Path) -> ProjectLayoutInspection:
    normalized_root = project_root.resolve()
    policy_path = normalized_root / "umem" / "project.toml"
    shared_root = "umem"
    operational_root = ".umem"
    precedence = ProjectLayoutPrecedence.shared_over_legacy.value
    warnings: list[str] = []
    recommended_actions: list[str] = []

    if policy_path.exists():
        policy = _load_project_layout_policy(normalized_root)
        return ProjectLayoutInspection(
            operation="layout.status",
            layout=policy.layout.value,
            shared_root=policy.shared_root,
            operational_root=policy.operational_root,
            precedence=policy.precedence.value,
            warnings=[],
            recommended_actions=[],
        )

    if (normalized_root / "umem").exists():
        warnings.append("umem/project.toml is missing for the visible shared root.")
        recommended_actions.append("Run umem layout status after creating shared metadata.")
        layout = ProjectLayoutMode.partial.value
    elif (normalized_root / ".umem").exists():
        layout = ProjectLayoutMode.legacy.value
    else:
        layout = ProjectLayoutMode.uninitialized.value

    return ProjectLayoutInspection(
        operation="layout.status",
        layout=layout,
        shared_root=shared_root,
        operational_root=operational_root,
        precedence=precedence,
        warnings=warnings,
        recommended_actions=recommended_actions,
    )


def resolve_project_layout(project_root: Path) -> ResolvedProjectLayout:
    normalized_root = project_root.resolve()
    policy_path = normalized_root / "umem" / "project.toml"
    policy = (
        _load_project_layout_policy(normalized_root)
        if policy_path.exists()
        else ProjectLayoutPolicy(
            schema_version="1",
            layout=ProjectLayoutMode.legacy,
            shared_root="umem",
            operational_root=".umem",
            precedence=ProjectLayoutPrecedence.shared_over_legacy,
        )
    )
    shared_root_path = normalized_root / policy.shared_root
    operational_root_path = normalized_root / policy.operational_root
    return ResolvedProjectLayout(
        project_root=normalized_root,
        policy=policy,
        shared_root_path=shared_root_path,
        operational_root_path=operational_root_path,
        shared_memory_root=shared_root_path / "memory",
        shared_skills_root=shared_root_path / "skills",
        operational_memory_root=operational_root_path / "memory",
        operational_skills_root=operational_root_path / "skills",
        operational_locks_root=operational_root_path / "locks",
    )


def write_project_layout_metadata(
    project_root: Path,
    *,
    layout: str = "shared",
) -> ProjectLayoutPolicy:
    normalized_root = project_root.resolve()
    rendered = render_project_layout_metadata(layout=layout)
    policy_path = normalized_root / "umem" / "project.toml"
    try:
        (normalized_root / ".umem").mkdir(parents=True, exist_ok=True)
        (normalized_root / "umem" / "memory").mkdir(parents=True, exist_ok=True)
        (normalized_root / "umem" / "skills").mkdir(parents=True, exist_ok=True)
        policy_path.write_text(rendered, encoding="utf-8")
    except OSError as error:
        raise StorageError(f"Failed to write {policy_path.name}: {error}") from error
    return _load_project_layout_policy(normalized_root)


def render_project_layout_metadata(*, layout: str = "shared") -> str:
    document = {
        "schema_version": "1",
        "layout": layout,
        "shared_root": "umem",
        "operational_root": ".umem",
        "precedence": ProjectLayoutPrecedence.shared_over_legacy.value,
        "visibility_defaults": {
            "project_memories": "shared",
            "project_rules": "shared",
            "project_skills": "shared",
            "operational_skills": "private",
        },
        "shared_operational_skills": [],
    }
    return tomli_w.dumps(document)


def ensure_project_layout(project_root: Path) -> ProjectLayoutResult:
    umem_root = project_root / ".umem"
    if umem_root.exists():
        created_paths, existing_paths = _ensure_existing_layout(umem_root)
        return ProjectLayoutResult(
            created=bool(created_paths),
            created_paths=created_paths,
            existing_paths=existing_paths,
        )

    umem_root.mkdir(parents=True, exist_ok=False)
    created_paths: list[str] = []
    tracked_paths = _tracked_paths(umem_root)
    default_files = _default_files()

    for relative_path in PROJECT_LAYOUT_PATHS:
        target = tracked_paths[relative_path]
        if relative_path in DIRECTORY_LAYOUT_PATHS:
            target.mkdir(parents=True, exist_ok=False)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(default_files[relative_path], encoding="utf-8")
        created_paths.append(relative_path)

    return ProjectLayoutResult(
        created=bool(created_paths),
        created_paths=created_paths,
        existing_paths=[],
    )


def ensure_shared_project_layout(project_root: Path) -> ProjectLayoutResult:
    ensure_project_layout(project_root)
    policy = write_project_layout_metadata(project_root, layout="shared")
    created_paths: list[str] = []
    existing_paths: list[str] = []
    for relative_path in SHARED_LAYOUT_PATHS:
        target = project_root / relative_path
        if target.exists():
            existing_paths.append(relative_path)
        else:
            created_paths.append(relative_path)
    return ProjectLayoutResult(
        created=policy.layout == ProjectLayoutMode.shared,
        created_paths=created_paths,
        existing_paths=existing_paths,
    )


def is_project_initialized(project_root: Path) -> bool:
    umem_root = project_root / ".umem"
    if not umem_root.is_dir():
        return False

    for relative_path, target in _tracked_paths(umem_root).items():
        if not _matches_expected_kind(relative_path, target):
            return False

    return True


def _tracked_paths(umem_root: Path) -> dict[str, Path]:
    return {
        ".umem/config.toml": umem_root / "config.toml",
        ".umem/memory": umem_root / "memory",
        ".umem/audit/events.jsonl": umem_root / "audit" / "events.jsonl",
        ".umem/snapshots": umem_root / "snapshots",
        ".umem/skills": umem_root / "skills",
        ".umem/benchmarks": umem_root / "benchmarks",
        ".umem/benchmarks/retrieval-results.json": umem_root
        / "benchmarks"
        / "retrieval-results.json",
    }


def _default_files() -> dict[str, str]:
    return {
        ".umem/config.toml": DEFAULT_CONFIG_TOML,
        ".umem/audit/events.jsonl": DEFAULT_AUDIT_EVENTS_JSONL,
        ".umem/benchmarks/retrieval-results.json": DEFAULT_RETRIEVAL_RESULTS_JSON,
    }


def _ensure_existing_layout(umem_root: Path) -> tuple[list[str], list[str]]:
    if not umem_root.is_dir():
        raise StorageError("Project layout root '.umem' exists but is not a directory")

    created_paths: list[str] = []
    existing_paths: list[str] = []
    tracked_paths = _tracked_paths(umem_root)
    default_files = _default_files()

    for relative_path in PROJECT_LAYOUT_PATHS:
        target = tracked_paths[relative_path]
        if not target.exists():
            if relative_path in DIRECTORY_LAYOUT_PATHS:
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(default_files[relative_path], encoding="utf-8")
            created_paths.append(relative_path)
            continue
        if not _matches_expected_kind(relative_path, target):
            expected_kind = "directory" if relative_path in DIRECTORY_LAYOUT_PATHS else "file"
            raise StorageError(f"Project layout path '{relative_path}' must be a {expected_kind}")
        existing_paths.append(relative_path)

    return created_paths, existing_paths


def _matches_expected_kind(relative_path: str, target: Path) -> bool:
    if relative_path in DIRECTORY_LAYOUT_PATHS:
        return target.is_dir()
    return target.is_file()


def _load_project_layout_policy(project_root: Path) -> ProjectLayoutPolicy:
    policy_path = project_root / "umem" / "project.toml"
    if not policy_path.is_file():
        raise StorageError("Shared layout metadata umem/project.toml is missing")
    try:
        with policy_path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as error:
        raise StorageError(f"Invalid TOML in umem/project.toml: {error}") from error
    except OSError as error:
        raise StorageError(f"Failed to read umem/project.toml: {error}") from error
    return _policy_from_data(data)


def _policy_from_data(data: dict[str, Any]) -> ProjectLayoutPolicy:
    layout = ProjectLayoutMode(str(data.get("layout", "shared")))
    shared_root = _validate_project_relative_root(
        str(data.get("shared_root", "umem")),
        field_name="shared_root",
    )
    operational_root = _validate_project_relative_root(
        str(data.get("operational_root", ".umem")),
        field_name="operational_root",
    )
    if shared_root == operational_root:
        raise StorageError("shared_root and operational_root must be different")
    precedence = ProjectLayoutPrecedence(str(data.get("precedence", "shared_over_legacy")))
    shared_operational_skills = data.get("shared_operational_skills", [])
    if not isinstance(shared_operational_skills, list) or not all(
        isinstance(value, str) for value in shared_operational_skills
    ):
        raise StorageError("shared_operational_skills must be a list of skill slugs")
    return ProjectLayoutPolicy(
        schema_version=str(data.get("schema_version", "1")),
        layout=layout,
        shared_root=shared_root,
        operational_root=operational_root,
        precedence=precedence,
        shared_operational_skills=tuple(shared_operational_skills),
    )


def _validate_project_relative_root(value: str, *, field_name: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise StorageError(f"{field_name} must be project-relative and contain no traversal")
    return value.replace("\\", "/").rstrip("/")
