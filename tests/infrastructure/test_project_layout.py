from pathlib import Path

import pytest

from universal_memory.domain import StorageError
from universal_memory.infrastructure.config.project_layout import (
    PROJECT_LAYOUT_PATHS,
    ensure_project_layout,
    inspect_project_layout,
    is_project_initialized,
    render_project_layout_metadata,
    resolve_project_layout,
    write_project_layout_metadata,
)


def test_ensure_project_layout_creates_canonical_tree_with_human_readable_files(
    tmp_path: Path,
) -> None:
    result = ensure_project_layout(tmp_path)
    umem_root = tmp_path / ".umem"

    assert result.created is True
    assert result.created_paths == PROJECT_LAYOUT_PATHS
    assert umem_root.is_dir()
    assert (umem_root / "memory").is_dir()
    assert (umem_root / "audit").is_dir()
    assert (umem_root / "snapshots").is_dir()
    assert (umem_root / "skills").is_dir()
    assert (umem_root / "benchmarks").is_dir()
    assert (umem_root / "config.toml").read_text() == (
        '[project]\nname = ""\ncreated_by = "universal-memory"\n'
    )
    assert (umem_root / "audit" / "events.jsonl").read_text() == ""
    assert (umem_root / "benchmarks" / "retrieval-results.json").read_text() == "{\n}\n"
    assert is_project_initialized(tmp_path) is True


def test_ensure_project_layout_is_idempotent_and_reports_existing_paths(tmp_path: Path) -> None:
    ensure_project_layout(tmp_path)

    result = ensure_project_layout(tmp_path)

    assert result.created is False
    assert result.created_paths == []
    assert result.existing_paths == PROJECT_LAYOUT_PATHS
    assert is_project_initialized(tmp_path) is True


def test_ensure_project_layout_repairs_partial_existing_tree(tmp_path: Path) -> None:
    umem_root = tmp_path / ".umem"
    umem_root.mkdir()
    (umem_root / "memory").mkdir()

    result = ensure_project_layout(tmp_path)

    assert result.created is True
    assert result.existing_paths == [".umem/memory"]
    assert result.created_paths == [
        ".umem/config.toml",
        ".umem/audit/events.jsonl",
        ".umem/snapshots",
        ".umem/skills",
        ".umem/benchmarks",
        ".umem/benchmarks/retrieval-results.json",
    ]
    assert is_project_initialized(tmp_path) is True


def test_ensure_project_layout_rejects_file_directory_collisions(tmp_path: Path) -> None:
    umem_root = tmp_path / ".umem"
    umem_root.mkdir()
    (umem_root / "config.toml").mkdir()

    with pytest.raises(StorageError, match="must be a file"):
        ensure_project_layout(tmp_path)

    assert is_project_initialized(tmp_path) is False


def test_shared_layout_metadata_loads_with_relative_paths(tmp_path: Path) -> None:
    write_project_layout_metadata(tmp_path, layout="shared")

    report = inspect_project_layout(tmp_path)
    resolved = resolve_project_layout(tmp_path)

    assert report.layout == "shared"
    assert report.shared_root == "umem"
    assert report.operational_root == ".umem"
    assert report.precedence == "shared_over_legacy"
    assert resolved.shared_memory_root == tmp_path / "umem" / "memory"
    assert resolved.operational_locks_root == tmp_path / ".umem" / "locks"


def test_shared_layout_metadata_rejects_absolute_or_traversal_roots(tmp_path: Path) -> None:
    policy_path = tmp_path / "umem" / "project.toml"
    policy_path.parent.mkdir()
    policy_path.write_text(
        'schema_version = "1"\nlayout = "shared"\nshared_root = "../outside"\n',
        encoding="utf-8",
    )

    with pytest.raises(StorageError, match="project-relative"):
        resolve_project_layout(tmp_path)


def test_partial_layout_report_when_visible_root_exists_without_metadata(tmp_path: Path) -> None:
    (tmp_path / "umem").mkdir()

    report = inspect_project_layout(tmp_path)

    assert report.layout == "partial"
    assert "umem/project.toml" in report.warnings[0]


def test_project_layout_metadata_rendering_uses_stable_defaults() -> None:
    rendered = render_project_layout_metadata(layout="shared")

    assert 'layout = "shared"' in rendered
    assert 'shared_root = "umem"' in rendered
    assert 'operational_root = ".umem"' in rendered
    assert 'precedence = "shared_over_legacy"' in rendered
