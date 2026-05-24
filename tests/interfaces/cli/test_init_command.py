import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from universal_memory.__main__ import main
from universal_memory.interfaces.cli import main as cli_main


def test_init_in_clean_directory_creates_layout_with_human_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["init"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert ".umem/" in captured.out
    assert "criada" in captured.out
    assert ".umem/config.toml" in captured.out
    assert ".umem/memory" in captured.out
    assert ".umem/audit/events.jsonl" in captured.out
    assert ".umem/snapshots" in captured.out
    assert "umem status" in captured.out
    assert (tmp_path / ".umem" / "config.toml").is_file()
    assert (tmp_path / ".umem" / "memory").is_dir()


def test_init_json_outputs_pure_parseable_payload_with_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload == {
        "ok": True,
        "operation": "init",
        "scope": "project",
        "warnings": [],
        "data": {
            "project_path": ".",
            "config_path": ".umem/config.toml",
            "memory_path": ".umem/memory",
            "audit_path": ".umem/audit/events.jsonl",
            "snapshots_path": ".umem/snapshots",
            "created": [
                ".umem/config.toml",
                ".umem/memory",
                ".umem/audit/events.jsonl",
                ".umem/snapshots",
                ".umem/skills",
                ".umem/benchmarks",
                ".umem/benchmarks/retrieval-results.json",
            ],
            "already_initialized": False,
            "audit_reference": "not-implemented-yet",
        },
    }


def test_init_module_execution_exits_with_process_status_and_json(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "universal_memory", "init", "--format", "json"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert payload["ok"] is True
    assert payload["operation"] == "init"
    assert payload["data"]["project_path"] == "."


def test_installed_cli_entry_points_use_bootstrap_composition_root() -> None:
    scripts = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'umem = "universal_memory.bootstrap.cli:main"' in scripts
    assert 'universal-memory = "universal_memory.bootstrap.cli:main"' in scripts


def test_cli_adapter_maps_unexpected_os_errors_to_json_error_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_with_os_error(_project_root: Path):
        raise OSError("filesystem unavailable")

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["init", "--format", "json"],
        setup_project_command=fail_with_os_error,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code != 0
    assert captured.err == ""
    assert payload == {
        "ok": False,
        "error": {
            "code": "storage_error",
            "message": "Falha de armazenamento.",
            "detail": "filesystem unavailable",
            "recovery_hint": "Verifique o layout local e execute umem init na raiz do projeto.",
            "audit_reference": None,
        },
    }


def test_cli_adapter_requires_composed_dependencies() -> None:
    with pytest.raises(RuntimeError, match="setup_project_command"):
        cli_main(["init"])


def test_init_json_data_contains_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert set(payload["data"]) == {
        "project_path",
        "config_path",
        "memory_path",
        "audit_path",
        "snapshots_path",
        "created",
        "already_initialized",
        "audit_reference",
    }


def test_init_is_idempotent_and_does_not_corrupt_existing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--format", "json"]) == 0
    capsys.readouterr()
    config_path = tmp_path / ".umem" / "config.toml"
    original_config = config_path.read_text()

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["data"]["already_initialized"] is True
    assert payload["data"]["created"] == []
    assert payload["data"]["project_path"] == "."
    assert payload["data"]["config_path"] == ".umem/config.toml"
    assert payload["data"]["memory_path"] == ".umem/memory"
    assert payload["data"]["audit_path"] == ".umem/audit/events.jsonl"
    assert payload["data"]["snapshots_path"] == ".umem/snapshots"
    assert config_path.read_text() == original_config


def test_init_does_not_attempt_network_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_network_access(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is not allowed during init")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket, "create_connection", fail_network_access)
    monkeypatch.setattr(socket, "socket", fail_network_access)

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["data"]["project_path"] == "."


def test_init_expected_errors_use_cli_error_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem").mkdir()
    (tmp_path / ".umem" / "memory").mkdir()

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code != 0
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "storage_error"
    assert "partial or corrupted" in payload["error"]["detail"]
    assert payload["error"]["audit_reference"] is None
