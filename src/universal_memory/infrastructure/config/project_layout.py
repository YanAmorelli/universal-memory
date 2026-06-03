from pathlib import Path

from universal_memory.domain import StorageError
from universal_memory.domain.project_layout import ProjectLayoutResult

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
