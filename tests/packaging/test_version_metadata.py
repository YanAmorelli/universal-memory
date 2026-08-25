from __future__ import annotations

import re
import tomllib
from pathlib import Path

EXPECTED_VERSION = "0.6.1"


def test_package_version_metadata_is_consistent() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    package_init = Path("src/universal_memory/__init__.py").read_text(encoding="utf-8")
    homepage_override = Path("docs/overrides/main.html").read_text(encoding="utf-8")
    lockfile = Path("uv.lock").read_text(encoding="utf-8")

    assert project["project"]["version"] == EXPECTED_VERSION
    assert f'__version__ = "{EXPECTED_VERSION}"' in package_init
    assert f'"softwareVersion": "{EXPECTED_VERSION}"' in homepage_override
    assert re.search(
        rf'\[\[package\]\]\nname = "universal-memory"\nversion = "{EXPECTED_VERSION}"',
        lockfile,
    )
