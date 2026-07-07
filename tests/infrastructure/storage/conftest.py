from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def legacy_project_root(tmp_path: Path) -> Path:
    (tmp_path / ".umem" / "memory").mkdir(parents=True)
    (tmp_path / ".umem" / "skills").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def shared_project_root(tmp_path: Path) -> Path:
    (tmp_path / ".umem" / "memory").mkdir(parents=True)
    (tmp_path / ".umem" / "skills").mkdir(parents=True)
    (tmp_path / "umem" / "memory").mkdir(parents=True)
    (tmp_path / "umem" / "skills").mkdir(parents=True)
    (tmp_path / "umem" / "project.toml").write_text(
        'schema_version = "1"\n'
        'layout = "shared"\n'
        'shared_root = "umem"\n'
        'operational_root = ".umem"\n'
        'precedence = "shared_over_legacy"\n',
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def private_project_root(shared_project_root: Path) -> Path:
    (shared_project_root / ".umem" / "memory" / "private").mkdir(parents=True)
    return shared_project_root
