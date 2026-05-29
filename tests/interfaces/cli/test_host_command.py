import json
from pathlib import Path

import pytest

from universal_memory.application.host import ConfigureHostCommand, ConfigureHostResult
from universal_memory.interfaces.cli import main as cli_main


def test_host_setup_json_outputs_exact_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def host_setup(command: ConfigureHostCommand) -> ConfigureHostResult:
        assert command.host_id == "codex"
        assert command.apply is True
        return ConfigureHostResult(
            host_id="codex",
            instruction_targets=["agents_md"],
            planned_changes=[{"target": "agents_md", "action": "create", "path": "AGENTS.md"}],
            manual_steps=[],
            validation_status="success",
            audit_reference="uuid-v4-reference",
            snapshot_reference="snapshot-reference",
            timestamp="2026-05-28T20:00:00Z",
        )

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["host", "setup", "codex", "--yes", "--format", "json"],
        setup_project_command=lambda _project_root: None,  # type: ignore[arg-type,return-value]
        host_setup_command=host_setup,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "ok": True,
        "operation": "host_setup",
        "scope": "project",
        "data": {
            "host_id": "codex",
            "instruction_targets": ["agents_md"],
            "planned_changes": [{"target": "agents_md", "action": "create", "path": "AGENTS.md"}],
            "manual_steps": [],
            "validation_status": "success",
            "audit_reference": "uuid-v4-reference",
            "snapshot_reference": "snapshot-reference",
            "timestamp": "2026-05-28T20:00:00Z",
        },
        "warnings": [],
    }


def test_host_setup_json_requires_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_if_called(_command: ConfigureHostCommand) -> ConfigureHostResult:
        raise AssertionError("host setup should require --yes before executing")

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["host", "setup", "codex", "--format", "json"],
        setup_project_command=lambda _project_root: None,  # type: ignore[arg-type,return-value]
        host_setup_command=fail_if_called,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_failed"
    assert "--yes" in payload["error"]["detail"]


def test_host_check_json_uses_same_use_case_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def host_check(command: ConfigureHostCommand) -> ConfigureHostResult:
        assert command.host_id == "codex"
        assert command.check is True
        return ConfigureHostResult(
            host_id="codex",
            instruction_targets=["agents_md"],
            planned_changes=[],
            manual_steps=[],
            validation_status="success",
            audit_reference="not-applied",
            snapshot_reference="planned",
            timestamp="2026-05-28T20:00:00Z",
        )

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["host", "check", "codex", "--format", "json"],
        setup_project_command=lambda _project_root: None,  # type: ignore[arg-type,return-value]
        host_check_command=host_check,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["operation"] == "host_check"
    assert payload["data"]["validation_status"] == "success"


def test_claude_code_host_setup_json_outputs_devex_contract_with_warnings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def host_setup(command: ConfigureHostCommand) -> ConfigureHostResult:
        assert command.host_id == "claude_code"
        assert command.apply is True
        return ConfigureHostResult(
            host_id="claude_code",
            instruction_targets=["claude_md"],
            planned_changes=[{"target": "claude_md", "action": "create", "path": "CLAUDE.md"}],
            manual_steps=[],
            validation_status="success",
            audit_reference="uuid-v4-reference",
            snapshot_reference="uuid-v4-snapshot",
            timestamp="2026-05-29T00:00:00Z",
            warnings=["Instrucao duplicada em AGENTS.md e CLAUDE.md: Use relative paths."],
        )

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["host", "setup", "claude_code", "--yes", "--format", "json"],
        setup_project_command=lambda _project_root: None,  # type: ignore[arg-type,return-value]
        host_setup_command=host_setup,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {
        "ok": True,
        "operation": "host_setup",
        "scope": "project",
        "data": {
            "host_id": "claude_code",
            "instruction_targets": ["claude_md"],
            "planned_changes": [
                {"target": "claude_md", "action": "create", "path": "CLAUDE.md"}
            ],
            "manual_steps": [],
            "validation_status": "success",
            "audit_reference": "uuid-v4-reference",
            "snapshot_reference": "uuid-v4-snapshot",
            "timestamp": "2026-05-29T00:00:00Z",
        },
        "warnings": ["Instrucao duplicada em AGENTS.md e CLAUDE.md: Use relative paths."],
    }


def test_claude_code_host_check_json_outputs_devex_contract_with_warnings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def host_check(command: ConfigureHostCommand) -> ConfigureHostResult:
        assert command.host_id == "claude_code"
        assert command.check is True
        return ConfigureHostResult(
            host_id="claude_code",
            instruction_targets=["claude_md"],
            planned_changes=[],
            manual_steps=["Remova a duplicacao manualmente antes de aplicar setup."],
            validation_status="warning",
            audit_reference="not-applied",
            snapshot_reference="planned",
            timestamp="2026-05-29T00:00:00Z",
            warnings=["Instrucao duplicada em AGENTS.md e CLAUDE.md: Use relative paths."],
        )

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["host", "check", "claude_code", "--format", "json"],
        setup_project_command=lambda _project_root: None,  # type: ignore[arg-type,return-value]
        host_check_command=host_check,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["operation"] == "host_check"
    assert payload["data"]["host_id"] == "claude_code"
    assert payload["data"]["instruction_targets"] == ["claude_md"]
    assert payload["data"]["manual_steps"] == [
        "Remova a duplicacao manualmente antes de aplicar setup."
    ]
    assert payload["data"]["snapshot_reference"] == "planned"
    assert payload["warnings"] == [
        "Instrucao duplicada em AGENTS.md e CLAUDE.md: Use relative paths."
    ]
