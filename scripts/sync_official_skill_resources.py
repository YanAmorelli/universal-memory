#!/usr/bin/env python3
"""Synchronize the canonical public skill into Python package resources."""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

SOURCE = Path("skills/universal-memory")
TARGET = Path("src/universal_memory/resources/skills/universal-memory")


def sync(*, check: bool) -> int:
    if not SOURCE.is_dir():
        raise SystemExit(f"Canonical skill is missing: {SOURCE}")
    if check:
        matches = TARGET.is_dir() and not _differences(SOURCE, TARGET)
        if not matches:
            raise SystemExit(
                "Packaged skill resources are stale; run "
                "`python scripts/sync_official_skill_resources.py`."
            )
        return 0

    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(SOURCE, TARGET)
    return 0


def _differences(left: Path, right: Path) -> list[str]:
    comparison = filecmp.dircmp(left, right)
    differences = [*comparison.left_only, *comparison.right_only, *comparison.diff_files]
    for name in comparison.common_dirs:
        differences.extend(f"{name}/{value}" for value in _differences(left / name, right / name))
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return sync(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
