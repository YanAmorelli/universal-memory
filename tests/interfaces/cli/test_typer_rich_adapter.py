from pathlib import Path

import typer

from universal_memory.interfaces.cli.init_command import create_typer_app


def test_cli_adapter_is_declared_as_typer_app() -> None:
    app = create_typer_app()

    assert isinstance(app, typer.Typer)


def test_runtime_dependencies_include_typer_and_rich() -> None:
    # Resolve pyproject.toml relative to the project root directory
    root = Path(__file__).resolve().parents[3]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")

    assert "typer" in pyproject
    assert "rich" in pyproject
