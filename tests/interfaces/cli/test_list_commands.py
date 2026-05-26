from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.__main__ import main
from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.infrastructure.security import (
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)
from universal_memory.interfaces.cli import main as cli_main


def make_event(
    *,
    created_at: datetime,
    action: str,
    scope: AuditEventScope = AuditEventScope.project,
    origin: str = "cli",
) -> AuditEvent:
    audit_reference = str(uuid4())
    return AuditEvent(
        id=audit_reference,
        created_at=created_at,
        updated_at=created_at,
        timestamp=created_at,
        action=action,
        scope=scope,
        origin=origin,
        result="success",
        snapshot_reference=str(uuid4()),
        audit_reference=audit_reference,
        status="logged",
    )


def make_snapshot(  # noqa: PLR0913
    *,
    project_root: Path,
    created_at: datetime,
    action: str,
    scope: SnapshotScope = SnapshotScope.project,
    origin: str = "cli",
    relative_path: str = ".umem/memory/facts.jsonl",
    content: bytes = b"previous",
) -> Snapshot:
    source = project_root / relative_path
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(content)
    return Snapshot(
        id=str(uuid4()),
        created_at=created_at,
        updated_at=created_at,
        timestamp=created_at,
        scope=scope,
        origin=origin,
        action=action,
        relative_path=relative_path,
        hash=sha256(content).hexdigest(),
        status=SnapshotStatus.created,
    )


def seed_audit_events(project_root: Path) -> list[AuditEvent]:
    repository = LocalAuditLogRepository(
        project_root=project_root,
        data_root=project_root / ".umem",
    )
    base = datetime(2026, 5, 26, tzinfo=UTC)
    newer = make_event(created_at=base + timedelta(minutes=2), action="second")
    older = make_event(created_at=base, action="first")
    repository.write(newer)
    repository.write(older)
    return [older, newer]


def seed_snapshots(project_root: Path) -> list[Snapshot]:
    repository = LocalSnapshotRepository(
        project_root=project_root,
        data_root=project_root / ".umem",
    )
    base = datetime(2026, 5, 26, tzinfo=UTC)
    newer = make_snapshot(
        project_root=project_root,
        created_at=base + timedelta(minutes=2),
        action="second",
    )
    older = make_snapshot(project_root=project_root, created_at=base, action="first")
    repository.write(newer)
    repository.write(older)
    return [older, newer]


def test_audit_list_human_output_is_concise_and_ordered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    seed_audit_events(tmp_path)

    exit_code = main(["audit", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert "Eventos de auditoria" in captured.out
    assert captured.out.index("first") < captured.out.index("second")
    assert "project" in captured.out
    assert "success" in captured.out


def test_audit_list_json_outputs_success_envelope_and_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    expected_events = seed_audit_events(tmp_path)

    exit_code = main(["audit", "list", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert payload["operation"] == "audit"
    assert payload["scope"] == "project"
    assert payload["warnings"] == []
    assert [event["action"] for event in payload["data"]["events"]] == ["first", "second"]
    assert set(payload["data"]["events"][0]) == {
        "timestamp",
        "action",
        "scope",
        "origin",
        "result",
        "snapshot_reference",
        "audit_reference",
    }
    assert payload["data"]["events"][0]["audit_reference"] == expected_events[0].audit_reference


def test_snapshots_list_human_output_is_concise_and_ordered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    seed_snapshots(tmp_path)

    exit_code = main(["snapshots", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert "Snapshots" in captured.out
    assert captured.out.index("first") < captured.out.index("second")
    assert ".umem/memory/facts.jsonl" in captured.out


def test_snapshots_list_json_outputs_success_envelope_and_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    expected_snapshots = seed_snapshots(tmp_path)

    exit_code = main(["snapshots", "list", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert payload["operation"] == "snapshots"
    assert payload["scope"] == "project"
    assert payload["warnings"] == []
    assert [snapshot["action"] for snapshot in payload["data"]["snapshots"]] == ["first", "second"]
    assert set(payload["data"]["snapshots"][0]) == {
        "timestamp",
        "scope",
        "origin",
        "action",
        "relative_path",
        "hash",
        "manifest_path",
    }
    assert payload["data"]["snapshots"][0]["hash"] == expected_snapshots[0].hash


def test_list_commands_return_explicit_empty_state_without_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["audit", "list", "--format", "json"]) == 0
    audit_payload = json.loads(capsys.readouterr().out)
    assert audit_payload["data"]["events"] == []

    assert main(["snapshots", "list", "--format", "json"]) == 0
    snapshots_payload = json.loads(capsys.readouterr().out)
    assert snapshots_payload["data"]["snapshots"] == []

    assert main(["audit", "list"]) == 0
    assert "Nenhum evento de auditoria encontrado." in capsys.readouterr().out

    assert main(["snapshots", "list"]) == 0
    assert "Nenhum snapshot encontrado." in capsys.readouterr().out


def test_cli_adapter_requires_composed_list_dependencies() -> None:
    with pytest.raises(RuntimeError, match="audit_list_command"):
        cli_main(["audit", "list"])

    with pytest.raises(RuntimeError, match="snapshots_list_command"):
        cli_main(["snapshots", "list"])
