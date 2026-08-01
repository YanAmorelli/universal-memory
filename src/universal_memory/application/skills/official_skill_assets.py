from __future__ import annotations

from importlib import resources
from pathlib import PurePosixPath
from types import MappingProxyType

from universal_memory.application.skills.official_skill_distribution import (
    OFFICIAL_SKILL_PACKAGE,
    OFFICIAL_SKILL_PACKAGE_RELATIVE_PATH,
)


def official_skill_assets() -> MappingProxyType[str, str]:
    """Return the packaged canonical skill tree as relative UTF-8 assets."""
    root = resources.files(OFFICIAL_SKILL_PACKAGE).joinpath(
        *PurePosixPath(OFFICIAL_SKILL_PACKAGE_RELATIVE_PATH).parts
    )
    assets: dict[str, str] = {}
    _collect_assets(root, prefix="", assets=assets)
    if "SKILL.md" not in assets:
        raise RuntimeError("Packaged Universal Memory skill is incomplete.")
    return MappingProxyType(dict(sorted(assets.items())))


def managed_skill_templates(*, skill_root: str) -> MappingProxyType[str, str]:
    return MappingProxyType(
        {
            f"{skill_root}/{relative_path}": content
            for relative_path, content in official_skill_assets().items()
        }
    )


def _collect_assets(root, *, prefix: str, assets: dict[str, str]) -> None:
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        relative_path = f"{prefix}/{child.name}" if prefix else child.name
        if child.is_dir():
            _collect_assets(child, prefix=relative_path, assets=assets)
        elif child.is_file():
            assets[relative_path] = child.read_text(encoding="utf-8")
