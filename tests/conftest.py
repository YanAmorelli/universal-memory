"""Shared pytest configuration for universal-memory tests."""

import os
import tempfile
from pathlib import Path

import pytest

# Apply before collection and session/module fixtures, including hook children.
# Keep this object alive until interpreter teardown; all test user data is private.
_collection_user = tempfile.TemporaryDirectory(prefix="umem-collection-user-")
for _key in tuple(os.environ):
    if _key.startswith("GIT_") or _key == "UMEM_MEMORY_ROOT":
        os.environ.pop(_key)
for _name in ("HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
    _target = Path(_collection_user.name) / _name.lower()
    _target.mkdir()
    os.environ[_name] = str(_target)
os.environ.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)


@pytest.fixture(autouse=True)
def isolated_user_and_git_environment(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_root = tmp_path_factory.mktemp("user-environment")
    for name in ("HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        target = user_root / name.lower()
        target.mkdir(parents=True)
        monkeypatch.setenv(name, str(target))
    for key in tuple(os.environ):
        if key.startswith("GIT_") or key == "UMEM_MEMORY_ROOT":
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
