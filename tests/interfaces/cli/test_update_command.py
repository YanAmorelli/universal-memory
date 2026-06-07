from __future__ import annotations

import json
import socket
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from universal_memory.__main__ import main
from universal_memory.application.skills import (
    ListSkillsCommand,
    ListSkillsResult,
    UpdateSkillCommand,
    UpdateSkillResult,
)
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.interfaces.cli.init_command import main as cli_main

MIN_BENCHMARK_FACT_COUNT = 1000
MIN_BENCHMARK_QUERY_COUNT = 30


@pytest.fixture(autouse=True)
def fail_on_network(monkeypatch) -> None:
    def blocked(*args, **kwargs):
        raise AssertionError("update CLI tests must not use network sockets")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def test_update_check_json_is_pure_envelope(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--yes", "--format", "json"]) == 0
    capsys.readouterr()

    exit_code = main(["update", "--check", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert payload["operation"] == "update.check"
    assert payload["scope"] == "project"
    assert {
        "installed_version",
        "target_schema_version",
        "project_config_schema_version",
        "memory_schema_versions",
        "benchmarks_status",
        "updates_available",
        "migration_required",
        "warnings",
    } <= set(payload["data"])


def test_update_migrate_cli_adds_schema_and_reports_audit(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem" / "memory").mkdir(parents=True)
    (tmp_path / ".umem" / "config.toml").write_text(
        '[hosts]\nenabled = ["codex"]\n\n[preferences]\nlocale = "en"\n',
        encoding="utf-8",
    )

    exit_code = main(["update", "--migrate", "--format", "json", "--yes"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["operation"] == "update.migrate"
    assert payload["data"]["target_schema_version"] == 1
    assert ".umem/config.toml" in payload["data"]["migrated_files"]
    assert payload["data"]["audit_reference"]
    config = (tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8")
    assert "schema_version = 1" in config
    config_data = tomllib.loads(config)
    assert config_data["runtimes"]["enabled"] == ["codex"]
    assert config_data["hosts"]["enabled"] == ["codex"]
    assert config_data["preferences"]["locale"] == "en"


def test_update_benchmarks_cli_json_has_required_metrics(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem" / "benchmarks").mkdir(parents=True)

    exit_code = main(["update", "--benchmarks", "--format", "json", "--yes"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["operation"] == "update.benchmarks"
    assert payload["data"]["benchmarks_updated"] is True
    assert payload["data"]["retrieval_results_path"] == ".umem/benchmarks/retrieval-results.json"
    assert payload["data"]["fact_count"] >= MIN_BENCHMARK_FACT_COUNT
    assert payload["data"]["query_count"] >= MIN_BENCHMARK_QUERY_COUNT
    assert payload["data"]["selected_default_strategy"] == "local_text"
    assert payload["data"]["audit_reference"]


def test_update_default_applies_required_migration(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem" / "memory").mkdir(parents=True)
    (tmp_path / ".umem" / "config.toml").write_text(
        '[hosts]\nenabled = ["codex"]\n',
        encoding="utf-8",
    )

    exit_code = main(["update", "--format", "json", "--yes"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["operation"] == "update"
    assert payload["data"]["migration_applied"] is True
    assert ".umem/config.toml" in payload["data"]["migrated_files"]
    config = (tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8")
    assert "schema_version = 1" in config


def test_update_default_reports_no_action_when_current(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--yes", "--format", "json"]) == 0
    capsys.readouterr()
    assert main(["update", "--format", "json", "--yes"]) == 0
    capsys.readouterr()

    exit_code = main(["update", "--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["operation"] == "update"
    assert payload["data"]["migration_applied"] is False
    assert payload["data"]["migrated_files"] == []


def test_update_human_output_distinguishes_local_maintenance_from_package_upgrade(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--yes", "--format", "json"]) == 0
    capsys.readouterr()

    exit_code = main(["update", "--yes"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Local maintenance completed." in captured.out
    assert "Running package version:" in captured.out
    assert "Package upgrade check: not performed (offline command)" in captured.out
    assert "Updates available:" not in captured.out


def _active_skill() -> LatentSkill:
    now = datetime(2026, 6, 1, tzinfo=UTC)
    return LatentSkill(
        id="11111111-1111-4111-8111-111111111111",
        created_at=now,
        updated_at=now,
        name="TDD recorrente",
        description="Executa red green refactor",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.active,
        metadata={},
    )


def _update_skill_result(*, warnings: list[str] | None = None) -> UpdateSkillResult:
    return UpdateSkillResult(
        latent_skill=_active_skill(),
        skill_file=".umem/skills/tdd-recorrente/SKILL.md",
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
        warnings=warnings or [],
    )


def test_update_skills_json_syncs_active_project_skills_with_keep_and_preserves_warnings(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    seen: list[UpdateSkillCommand] = []
    store = tmp_path / ".umem" / "memory" / "latent_skills.jsonl"
    store.parent.mkdir(parents=True)
    store.write_text(
        json.dumps(
            {
                "id": "11111111-1111-4111-8111-111111111111",
                "created_at": "2026-06-01T00:00:00Z",
                "updated_at": "2026-06-01T00:00:00Z",
                "name": "TDD recorrente",
                "description": "Executa red green refactor",
                "scope": "project",
                "status": "active",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    def list_skills(command: ListSkillsCommand) -> ListSkillsResult:
        assert command.status == LatentSkillStatus.active
        return ListSkillsResult(skills=[])

    def update_skill(command: UpdateSkillCommand) -> UpdateSkillResult:
        seen.append(command)
        return _update_skill_result(warnings=["Warning: Native target has manual changes."])

    exit_code = cli_main(
        ["update", "--skills", "--format", "json"],
        list_skills_command=list_skills,
        update_skill_command=update_skill,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["operation"] == "update.skills"
    assert payload["data"]["updated_count"] == 1
    assert payload["warnings"] == ["Warning: Native target has manual changes."]
    assert seen == [
        UpdateSkillCommand(
            latent_skill_id="11111111-1111-4111-8111-111111111111",
            origin="cli_update_skills",
            native_drift_decision="keep",
        )
    ]


def test_skills_update_json_preserves_warnings_and_defaults_native_drift_to_keep(capsys) -> None:
    seen: list[UpdateSkillCommand] = []

    def update_skill(command: UpdateSkillCommand) -> UpdateSkillResult:
        seen.append(command)
        return _update_skill_result(warnings=["Warning: Native target has manual changes."])

    exit_code = cli_main(
        ["skills", "update", "11111111-1111-4111-8111-111111111111", "--format", "json"],
        update_skill_command=update_skill,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["operation"] == "skills.update"
    assert payload["warnings"] == ["Warning: Native target has manual changes."]
    assert seen[0].native_drift_decision == "keep"
