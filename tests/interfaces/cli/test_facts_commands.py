from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.__main__ import main
from universal_memory.domain.entities import Fact, FactScope, FactStatus
from universal_memory.infrastructure.storage import LocalFactRepository
from universal_memory.interfaces.cli import main as cli_main

EXPECTED_PROJECT_PURGE_COUNT = 3


def make_fact(
    *,
    created_at: datetime,
    scope: FactScope = FactScope.project,
    status: FactStatus = FactStatus.active,
    content: str = "Fato persistido",
) -> Fact:
    return Fact(
        id=str(uuid4()),
        created_at=created_at,
        updated_at=created_at,
        content=content,
        scope=scope,
        source="test",
        status=status,
    )


def seed_facts(project_root: Path) -> list[Fact]:
    repository = LocalFactRepository(project_root=project_root, data_root=project_root / ".umem")
    base = datetime(2026, 5, 26, tzinfo=UTC)
    facts = [
        make_fact(created_at=base, content="Fato ativo do projeto"),
        make_fact(
            created_at=base + timedelta(minutes=1),
            status=FactStatus.archived,
            content="Fato arquivado do projeto",
        ),
        make_fact(
            created_at=base + timedelta(minutes=2),
            status=FactStatus.stale,
            content="Fato stale do projeto",
        ),
        make_fact(
            created_at=base + timedelta(minutes=3),
            scope=FactScope.global_,
            content="Fato global",
        ),
    ]
    for fact in facts:
        repository.write(fact)
    return facts


def test_facts_list_human_excludes_archived_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    seed_facts(tmp_path)

    exit_code = main(["facts", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert "Facts:" in captured.out
    assert "Fato ativo do projeto" in captured.out
    assert "Fato global" in captured.out
    assert "Fato arquivado do projeto" not in captured.out


def test_facts_list_json_supports_scope_and_archived_status_filters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    seed_facts(tmp_path)

    exit_code = main(
        ["facts", "list", "--scope", "project", "--status", "archived", "--format", "json"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert payload["operation"] == "facts.list"
    assert payload["scope"] == "project"
    assert payload["warnings"] == []
    assert [fact["content"] for fact in payload["data"]["facts"]] == ["Fato arquivado do projeto"]
    assert payload["data"]["facts"][0]["status"] == "archived"


def test_facts_purge_by_id_requires_confirmation_and_removes_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    facts = seed_facts(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")

    exit_code = main(["facts", "purge", "--id", facts[0].id])

    captured = capsys.readouterr()
    remaining = LocalFactRepository(project_root=tmp_path, data_root=tmp_path / ".umem").list()
    assert exit_code == 0
    assert captured.err == ""
    assert "Purge completed." in captured.out
    assert facts[0].id not in [fact.id for fact in remaining]


def test_facts_purge_json_requires_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    facts = seed_facts(tmp_path)

    exit_code = main(["facts", "purge", "--id", facts[0].id, "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_failed"
    assert "--yes" in payload["error"]["detail"]


def test_facts_purge_by_scope_uses_requested_scope_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    seed_facts(tmp_path)

    exit_code = main(["facts", "purge", "--scope", "project", "--yes", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    remaining = LocalFactRepository(project_root=tmp_path, data_root=tmp_path / ".umem").list()
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["operation"] == "facts.purge"
    assert payload["scope"] == "project"
    assert payload["data"]["purged_count"] == EXPECTED_PROJECT_PURGE_COUNT
    assert [fact.content for fact in remaining] == ["Fato global"]


def test_facts_hygiene_transitions_project_facts_and_outputs_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    seed_facts(tmp_path)

    exit_code = main(["facts", "hygiene", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    facts = LocalFactRepository(project_root=tmp_path, data_root=tmp_path / ".umem").list()
    project_statuses = sorted(
        fact.status.value for fact in facts if fact.scope == FactScope.project
    )
    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert payload["operation"] == "facts.hygiene"
    assert payload["scope"] == "project"
    assert payload["data"]["stale_count"] == 1
    assert payload["data"]["archived_count"] == 1
    assert project_statuses == ["archived", "archived", "stale"]


def test_cli_adapter_requires_composed_facts_dependencies() -> None:
    with pytest.raises(RuntimeError, match="facts_list_command"):
        cli_main(["facts", "list"])

    with pytest.raises(RuntimeError, match="facts_purge_command"):
        cli_main(["facts", "purge", "--scope", "project", "--yes"])

    with pytest.raises(RuntimeError, match="facts_hygiene_command"):
        cli_main(["facts", "hygiene"])
