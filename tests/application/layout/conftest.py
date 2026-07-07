from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def shared_layout_root(tmp_path: Path) -> Path:
    (tmp_path / ".umem").mkdir()
    (tmp_path / "umem" / "memory").mkdir(parents=True)
    (tmp_path / "umem" / "skills").mkdir(parents=True)
    (tmp_path / "umem" / "project.toml").write_text(
        "\n".join(
            [
                'schema_version = "1"',
                'layout = "shared"',
                'shared_root = "umem"',
                'operational_root = ".umem"',
                'precedence = "shared_over_legacy"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return tmp_path
