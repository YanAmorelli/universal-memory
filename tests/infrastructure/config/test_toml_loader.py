from pathlib import Path

import pytest

from universal_memory.domain import InvalidConfigError, StorageError
from universal_memory.infrastructure.config.toml_loader import (
    dump_toml_document,
    load_config,
    update_project_config,
)


def test_load_config_merges_global_and_project_config(tmp_path: Path) -> None:
    global_config = tmp_path / "global.toml"
    project_root = tmp_path / "workspace"
    project_config = project_root / ".umem" / "config.toml"

    global_config.write_text(
        """
[paths]
storage_root = "/global/storage"

[defaults]
scope = "project"
""".lstrip()
    )
    project_config.parent.mkdir(parents=True)
    project_config.write_text(
        """
[paths]
storage_root = ".umem/memory"

[defaults]
scope = "session"
""".lstrip()
    )

    config = load_config(project_root=project_root, global_config_path=global_config)

    assert config.global_config_path == global_config
    assert config.project_config_path == project_config
    assert config.merged["paths"]["storage_root"] == ".umem/memory"
    assert config.merged["defaults"]["scope"] == "session"
    assert config.resolved_paths["paths"]["storage_root"] == project_root / ".umem" / "memory"
    assert config.global_data == {
        "paths": {"storage_root": "/global/storage"},
        "defaults": {"scope": "project"},
    }
    assert config.project_data == {
        "paths": {"storage_root": ".umem/memory"},
        "defaults": {"scope": "session"},
    }


def test_load_config_uses_default_global_path_when_not_overridden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    project_root = tmp_path / "workspace"
    project_config = project_root / ".umem" / "config.toml"

    project_config.parent.mkdir(parents=True)
    project_config.write_text('[project]\nname = "demo"\n')

    config = load_config(project_root=project_root)

    assert config.global_config_path == tmp_path / ".config" / "umem" / "config.toml"
    assert config.project_config_path == project_config
    assert config.merged["project"]["name"] == "demo"


def test_load_config_raises_invalid_config_error_for_invalid_toml(tmp_path: Path) -> None:
    broken_config = tmp_path / "broken.toml"
    broken_config.write_text('[project\nname = "demo"\n')

    with pytest.raises(InvalidConfigError, match=r"broken\.toml"):
        load_config(project_root=tmp_path, global_config_path=broken_config)


def test_load_config_raises_invalid_config_error_for_directory_path(tmp_path: Path) -> None:
    broken_config = tmp_path / "broken.toml"
    broken_config.mkdir()

    with pytest.raises(InvalidConfigError, match="expected a file"):
        load_config(project_root=tmp_path, global_config_path=broken_config)


def test_load_config_raises_storage_error_for_os_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken_config = tmp_path / "broken.toml"
    broken_config.write_text('[project]\nname = "demo"\n')

    def raise_os_error(*args: object, **kwargs: object) -> object:
        raise OSError("boom")

    monkeypatch.setattr(Path, "open", raise_os_error)

    with pytest.raises(StorageError, match=r"Failed to read config broken\.toml"):
        load_config(project_root=tmp_path, global_config_path=broken_config)


def test_load_config_returns_independent_merged_data(tmp_path: Path) -> None:
    global_config = tmp_path / "global.toml"
    project_root = tmp_path / "workspace"
    project_config = project_root / ".umem" / "config.toml"

    global_config.write_text('[paths]\nstorage_root = "/global/storage"\n')
    project_config.parent.mkdir(parents=True)
    project_config.write_text('[paths]\nstorage_root = ".umem/memory"\n')

    config = load_config(project_root=project_root, global_config_path=global_config)
    config.merged["paths"]["storage_root"] = "changed"

    assert config.global_data["paths"]["storage_root"] == "/global/storage"
    assert config.project_data["paths"]["storage_root"] == ".umem/memory"


def test_dump_toml_document_serializes_with_tomli_w_style() -> None:
    document = {"project": {"name": "demo"}, "paths": {"storage_root": ".umem/memory"}}

    rendered = dump_toml_document(document)

    assert rendered == ('[project]\nname = "demo"\n\n[paths]\nstorage_root = ".umem/memory"\n')


def test_update_project_config_persists_hosts_with_tomli_w_style(tmp_path: Path) -> None:
    project_root = tmp_path / "workspace"
    config_path = project_root / ".umem" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('[project]\nname = "demo"\n', encoding="utf-8")

    updated = update_project_config(
        project_root,
        {"hosts": {"enabled": ["codex", "claude_code"]}},
    )

    assert updated.project_data["hosts"]["enabled"] == ["codex", "claude_code"]
    assert config_path.read_text(encoding="utf-8") == (
        '[project]\nname = "demo"\n\n[hosts]\nenabled = [\n    "codex",\n    "claude_code",\n]\n'
    )
