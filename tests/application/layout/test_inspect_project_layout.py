from __future__ import annotations

from pathlib import Path

from universal_memory.application.layout import InspectProjectLayoutUseCase
from universal_memory.infrastructure.config import LocalProjectLayoutPort


def inspect(project_root: Path) -> dict:
    return InspectProjectLayoutUseCase(
        project_root=project_root,
        layout_port=LocalProjectLayoutPort(),
    ).execute()


def test_inspect_project_layout_reports_uninitialized(tmp_path: Path) -> None:
    payload = inspect(tmp_path)

    assert payload["operation"] == "layout.status"
    assert payload["scope"] == "project"
    assert payload["data"]["layout"] == "uninitialized"


def test_inspect_project_layout_reports_legacy(tmp_path: Path) -> None:
    (tmp_path / ".umem").mkdir()

    payload = inspect(tmp_path)

    assert payload["data"]["layout"] == "legacy"
    assert payload["data"]["operational_root"] == ".umem"


def test_inspect_project_layout_reports_shared(tmp_path: Path) -> None:
    (tmp_path / "umem").mkdir()
    (tmp_path / "umem" / "project.toml").write_text(
        'schema_version = "1"\nlayout = "shared"\n',
        encoding="utf-8",
    )

    payload = inspect(tmp_path)

    assert payload["data"]["layout"] == "shared"
    assert payload["data"]["shared_root"] == "umem"
    assert payload["data"]["precedence"] == "shared_over_legacy"


def test_inspect_project_layout_reports_partial(tmp_path: Path) -> None:
    (tmp_path / "umem").mkdir()

    payload = inspect(tmp_path)

    assert payload["data"]["layout"] == "partial"
    assert payload["data"]["warnings"]
