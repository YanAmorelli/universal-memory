from __future__ import annotations

import tomllib
from pathlib import Path


def test_runtime_dependency_bounds_match_architecture() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = {}
    for dependency in project["project"]["dependencies"]:
        package_name = dependency.split(";", 1)[0]
        package_name = package_name.split("[", 1)[0]
        package_name = package_name.split(">", 1)[0]
        package_name = package_name.split("<", 1)[0]
        package_name = package_name.split("=", 1)[0]
        dependencies[package_name] = dependency

    assert dependencies["fastmcp"] == "fastmcp>=3.3.1,<4"
    assert dependencies["pydantic"] == "pydantic>=2.13.4,<3"
    assert dependencies["typer"] == "typer>=0.25.1"
    assert dependencies["tomli-w"] == "tomli-w>=1.2.0"
