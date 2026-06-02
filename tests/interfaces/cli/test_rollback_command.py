from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.__main__ import main
from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
from universal_memory.infrastructure.security import LocalSnapshotRepository


def seed_snapshot(
    project_root: Path,
    *,
    content: bytes = b"previous state\n",
    scope: SnapshotScope = SnapshotScope.project,
    relative_path: str = ".umem/memory/facts.jsonl",
    action: str = "safe_write",
) -> Snapshot:
    target = project_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    timestamp = datetime(2026, 5, 26, tzinfo=UTC)
    snapshot = Snapshot(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        timestamp=timestamp,
        scope=scope,
        origin="cli",
        action=action,
        relative_path=relative_path,
        hash=sha256(content).hexdigest(),
        status=SnapshotStatus.created,
    )
    LocalSnapshotRepository(
        project_root=project_root,
        data_root=project_root / ".umem",
    ).write(snapshot)
    target.write_bytes(b"current state\n")
    return snapshot


def test_rollback_yes_restores_snapshot_and_prints_human_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    snapshot = seed_snapshot(tmp_path)

    exit_code = main(["rollback", "--scope", "project", "--yes"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert (tmp_path / ".umem" / "memory" / "facts.jsonl").read_bytes() == b"previous state\n"
    assert "Rollback completed" in captured.out
    assert "Scope: project" in captured.out
    assert f"Snapshot: {snapshot.id}" in captured.out
    assert "Original action: safe_write" in captured.out
    assert "File: .umem/memory/facts.jsonl" in captured.out


def test_rollback_json_success_outputs_strict_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    snapshot = seed_snapshot(tmp_path)

    exit_code = main(["rollback", "--scope", "project", "--format", "json", "--yes"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert payload["operation"] == "rollback"
    assert payload["scope"] == "project"
    assert payload["warnings"] == []
    assert payload["data"]["scope"] == "project"
    assert payload["data"]["snapshot_reference"] == snapshot.id
    assert payload["data"]["restored_paths"] == [".umem/memory/facts.jsonl"]
    assert isinstance(payload["data"]["audit_reference"], str)


def test_rollback_json_removes_file_created_by_first_remember(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--yes", "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        main(
            [
                "remember",
                "Fato antes do rollback.",
                "--scope",
                "project",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    exit_code = main(["rollback", "--scope", "project", "--format", "json", "--yes"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert not (tmp_path / ".umem" / "memory" / "facts.jsonl").exists()


def test_rollback_interactive_confirmation_accepts_yes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    seed_snapshot(tmp_path)
    prompts: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "y")

    exit_code = main(["rollback", "--scope", "project"])

    assert exit_code == 0
    assert prompts == ["Proceed with rollback? [y/N]: "]
    assert (tmp_path / ".umem" / "memory" / "facts.jsonl").read_bytes() == b"previous state\n"
    assert "Rollback completed" in capsys.readouterr().out


def test_rollback_interactive_confirmation_declines_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    seed_snapshot(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    exit_code = main(["rollback", "--scope", "project"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert (tmp_path / ".umem" / "memory" / "facts.jsonl").read_bytes() == b"current state\n"
    assert "Rollback cancelled" in captured.out


def test_rollback_json_failure_uses_standard_error_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["rollback", "--scope", "project", "--format", "json", "--yes"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "snapshot_failed"
    assert "No snapshot" in payload["error"]["detail"]
