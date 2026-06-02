import json
from pathlib import Path

import pytest

from universal_memory.application.host import SyncInstructionsCommand, SyncInstructionsResult
from universal_memory.interfaces.cli import main as cli_main


def test_host_sync_json_outputs_preview_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def host_sync(command: SyncInstructionsCommand) -> SyncInstructionsResult:
        assert command.apply is False
        assert command.host_ids == ["codex", "claude_code"]
        return SyncInstructionsResult(
            host_ids=["codex", "claude_code"],
            instruction_targets=["AGENTS.md", "CLAUDE.md"],
            planned_changes=[
                {"target": "agents_md", "action": "create", "path": "AGENTS.md"},
                {"target": "claude_md", "action": "create", "path": "CLAUDE.md"},
            ],
            manual_steps=["Revise os caminhos afetados antes de aplicar."],
            validation_status="planned",
            audit_reference="not-applied",
            snapshot_reference="planned",
            timestamp="2026-05-29T12:00:00Z",
        )

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["host", "sync", "--format", "json"],
        setup_project_command=lambda _project_root: None,  # type: ignore[arg-type,return-value]
        host_sync_command=host_sync,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "ok": True,
        "operation": "host_sync",
        "scope": "project",
        "data": {
            "host_ids": ["codex", "claude_code"],
            "instruction_targets": ["AGENTS.md", "CLAUDE.md"],
            "planned_changes": [
                {"target": "agents_md", "action": "create", "path": "AGENTS.md"},
                {"target": "claude_md", "action": "create", "path": "CLAUDE.md"},
            ],
            "manual_steps": ["Revise os caminhos afetados antes de aplicar."],
            "validation_status": "planned",
            "audit_reference": "not-applied",
            "snapshot_reference": "planned",
            "timestamp": "2026-05-29T12:00:00Z",
        },
        "warnings": [],
    }


def test_host_sync_json_apply_requires_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_if_called(_command: SyncInstructionsCommand) -> SyncInstructionsResult:
        raise AssertionError("host sync should require --yes before JSON apply")

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["host", "sync", "--apply", "--format", "json"],
        setup_project_command=lambda _project_root: None,  # type: ignore[arg-type,return-value]
        host_sync_command=fail_if_called,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_failed"
    assert "--yes" in payload["error"]["detail"]


def test_host_sync_human_dry_run_displays_plan_and_dry_run_concluido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def host_sync(command: SyncInstructionsCommand) -> SyncInstructionsResult:
        assert command.apply is False
        return SyncInstructionsResult(
            host_ids=["codex", "claude_code"],
            instruction_targets=["AGENTS.md", "CLAUDE.md"],
            planned_changes=[
                {"target": "agents_md", "action": "create", "path": "AGENTS.md"},
                {"target": "claude_md", "action": "create", "path": "CLAUDE.md"},
            ],
            manual_steps=["Revise os caminhos afetados antes de aplicar."],
            validation_status="planned",
            audit_reference="not-applied",
            snapshot_reference="planned",
            timestamp="2026-05-29T12:00:00Z",
        )

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["host", "sync", "--format", "human"],
        setup_project_command=lambda _project_root: None,  # type: ignore[arg-type,return-value]
        host_sync_command=host_sync,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Instruction synchronization plan" in captured.out
    assert "Scope" in captured.out
    assert "project" in captured.out
    assert (
        "Dry-run completed. No changes were applied to the filesystem." in captured.out
    )


def test_host_sync_human_apply_interactive_confirmation_no(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = []

    def host_sync(command: SyncInstructionsCommand) -> SyncInstructionsResult:
        calls.append(command)
        return SyncInstructionsResult(
            host_ids=["codex", "claude_code"],
            instruction_targets=["AGENTS.md", "CLAUDE.md"],
            planned_changes=[
                {"target": "agents_md", "action": "create", "path": "AGENTS.md"},
                {"target": "claude_md", "action": "create", "path": "CLAUDE.md"},
            ],
            manual_steps=["Revise os caminhos afetados antes de aplicar."],
            validation_status="planned",
            audit_reference="not-applied",
            snapshot_reference="planned",
            timestamp="2026-05-29T12:00:00Z",
        )

    # Mock interactive prompt to return False (No)
    monkeypatch.setattr(
        "universal_memory.interfaces.cli.init_command._confirm",
        lambda _prompt, **kwargs: False,
    )
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["host", "sync", "--apply", "--format", "human"],
        setup_project_command=lambda _project_root: None,  # type: ignore[arg-type,return-value]
        host_sync_command=host_sync,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Instruction synchronization cancelled." in captured.out
    assert len(calls) == 1
    assert calls[0].apply is False
