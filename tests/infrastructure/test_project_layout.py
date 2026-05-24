from pathlib import Path

import pytest

from universal_memory.domain import StorageError
from universal_memory.infrastructure.config.project_layout import (
    PROJECT_LAYOUT_PATHS,
    ensure_project_layout,
    is_project_initialized,
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


def test_ensure_project_layout_rejects_partial_existing_tree(tmp_path: Path) -> None:
    umem_root = tmp_path / ".umem"
    umem_root.mkdir()
    (umem_root / "memory").mkdir()

    with pytest.raises(StorageError, match="partial or corrupted"):
        ensure_project_layout(tmp_path)

    assert is_project_initialized(tmp_path) is False


def test_ensure_project_layout_rejects_file_directory_collisions(tmp_path: Path) -> None:
    umem_root = tmp_path / ".umem"
    umem_root.mkdir()
    (umem_root / "config.toml").mkdir()

    with pytest.raises(StorageError, match="must be a file"):
        ensure_project_layout(tmp_path)

    assert is_project_initialized(tmp_path) is False
