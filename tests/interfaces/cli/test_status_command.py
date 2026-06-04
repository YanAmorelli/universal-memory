from __future__ import annotations

import json
import socket
from dataclasses import replace
from pathlib import Path

import pytest

from universal_memory import __version__
from universal_memory.__main__ import main
from universal_memory.application.memory import GetMemoryStatusCommand, GetMemoryStatusResult
from universal_memory.interfaces.cli import main as cli_main


def initialized_result(project_root: Path) -> GetMemoryStatusResult:
    return GetMemoryStatusResult(
        initialized=True,
        project_path=".",
        fact_counts={
            "global": {"active": 0, "stale": 0, "archived": 0, "purged": 0},
            "project": {"active": 1, "stale": 0, "archived": 0, "purged": 0},
        },
        active_rules_count=2,
        registered_skills_count=3,
        approximate_size_bytes=42,
        last_health_check="2026-05-27T20:00:00Z",
        host_validation={
            "claude_code": {
                "status": "unconfigured",
                "timestamp": None,
                "method": None,
                "audit_reference": None,
            },
            "codex": {
                "status": "success",
                "timestamp": "2026-05-27T20:00:00Z",
                "method": "agents_md_compact_validator",
                "audit_reference": "audit-codex",
            },
        },
        recommended_action=None,
    )


def test_status_json_outputs_pure_success_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    received: list[GetMemoryStatusCommand] = []

    def command(cmd: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        received.append(cmd)
        return initialized_result(tmp_path)

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(["status", "--format", "json"], status_command=command)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert received == [GetMemoryStatusCommand(project_root=tmp_path)]
    assert payload == {
        "ok": True,
        "operation": "status",
        "scope": "project",
        "warnings": [],
        "data": {
            "initialized": True,
            "project_path": ".",
            "installed_version": __version__,
            "fact_counts": {
                "global": {"active": 0, "stale": 0, "archived": 0, "purged": 0},
                "project": {"active": 1, "stale": 0, "archived": 0, "purged": 0},
            },
            "active_rules_count": 2,
            "registered_skills_count": 3,
            "approximate_size_bytes": 42,
            "last_health_check": "2026-05-27T20:00:00Z",
            "host_validation": {
                "claude_code": {
                    "status": "unconfigured",
                    "timestamp": None,
                    "method": None,
                    "audit_reference": None,
                },
                "codex": {
                    "status": "success",
                    "timestamp": "2026-05-27T20:00:00Z",
                    "method": "agents_md_compact_validator",
                    "audit_reference": "audit-codex",
                },
            },
        },
    }


def test_status_uninitialized_json_includes_recommended_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def command(_cmd: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        return replace(
            initialized_result(tmp_path),
            initialized=False,
            fact_counts={},
            active_rules_count=0,
            registered_skills_count=0,
            approximate_size_bytes=0,
            last_health_check=None,
            host_validation={},
            recommended_action="Run umem init from the project root.",
        )

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(["status", "--format", "json"], status_command=command)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"] == {
        "initialized": False,
        "project_path": ".",
        "installed_version": __version__,
        "recommended_action": "Run umem init from the project root.",
    }


def test_status_human_output_summarizes_health(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(["status"], status_command=lambda _cmd: initialized_result(tmp_path))

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Local memory initialized." in captured.out
    assert f"Installed version: {__version__}" in captured.out
    assert "Facts by scope/status" in captured.out
    assert "project active: 1" in captured.out
    assert "Active rules: 2" in captured.out
    assert "Registered skills: 3" in captured.out
    assert "Approximate size: 42 bytes" in captured.out
    assert "codex: success" in captured.out
    assert "method=agents_md_compact_validator" in captured.out


def test_status_bootstrap_uses_local_data_and_no_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_network_access(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is not allowed during status")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket, "create_connection", fail_network_access)
    monkeypatch.setattr(socket, "socket", fail_network_access)
    assert main(["init", "--format", "json"]) == 0
    capsys.readouterr()

    exit_code = main(["status", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["data"]["initialized"] is True
    assert payload["data"]["active_rules_count"] == 0
    assert payload["data"]["registered_skills_count"] == 1


def test_cli_adapter_requires_composed_status_dependency() -> None:
    with pytest.raises(RuntimeError, match="status_command"):
        cli_main(["status"])


def test_root_version_option_outputs_installed_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_main(["--version"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == f"umem {__version__}\n"
    assert captured.err == ""
