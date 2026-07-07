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
    SkillListItem,
    SyncSkillResult,
    SyncSkillsCommand,
    SyncSkillsResult,
    UpdateSkillCommand,
    UpdateSkillResult,
)
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.interfaces.cli.init_command import main as cli_main

MIN_BENCHMARK_FACT_COUNT = 1000
MIN_BENCHMARK_QUERY_COUNT = 30
LEGACY_SKILLS_LIFECYCLE = """# Skills Lifecycle

Use this reference for UMEM skill discovery, latent skill tracking, approval, generation,
activation, deactivation, and updates.

## Canonical CLI

```bash
umem skills list --format json
umem skills generate <latent-skill-id> --yes --format json
umem skills update <latent-skill-id> --file <relative-markdown-path> --format json
```
"""


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
        sync_skills_command=lambda _command: SyncSkillsResult(skills=[]),
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


def test_update_skills_json_syncs_canonical_agent_skills_from_list_result(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    seen_sync: list[SyncSkillsCommand] = []
    seen_update: list[UpdateSkillCommand] = []
    monkeypatch.chdir(tmp_path)

    def list_skills(command: ListSkillsCommand) -> ListSkillsResult:
        assert command.status == LatentSkillStatus.active
        return ListSkillsResult(
            skills=[
                SkillListItem(
                    id="agent-skill-1",
                    name="Review Helper",
                    scope="project",
                    status="active",
                    relative_path=".umem/skills/review-helper/SKILL.md",
                    canonical_path=".umem/skills/review-helper/SKILL.md",
                    created_at="2026-06-01T00:00:00Z",
                    updated_at="2026-06-01T00:00:00Z",
                    origin="test",
                    audit_reference="audit-list",
                    targets=[],
                )
            ]
        )

    def sync_skills(command: SyncSkillsCommand) -> SyncSkillsResult:
        seen_sync.append(command)
        return SyncSkillsResult(
            skills=[
                SyncSkillResult(
                    skill_id="agent-skill-1",
                    name="Review Helper",
                    scope="project",
                    status="active",
                    canonical_path=".umem/skills/review-helper/SKILL.md",
                    affected_paths=[".agents/skills/review-helper/SKILL.md"],
                    targets=[{"runtime": "codex", "path": ".agents/skills/review-helper"}],
                )
            ],
            affected_paths=[".agents/skills/review-helper/SKILL.md"],
        )

    def update_skill(command: UpdateSkillCommand) -> UpdateSkillResult:
        seen_update.append(command)
        return _update_skill_result()

    exit_code = cli_main(
        ["update", "--skills", "--format", "json"],
        list_skills_command=list_skills,
        sync_skills_command=sync_skills,
        update_skill_command=update_skill,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["updated_count"] == 1
    assert payload["data"]["skills"][0]["managed"] is False
    assert payload["data"]["skills"][0]["canonical_path"] == (".umem/skills/review-helper/SKILL.md")
    assert seen_sync == [
        SyncSkillsCommand(
            skill_id_or_name="agent-skill-1",
            origin="cli_update_skills",
            drift_decision="keep",
        )
    ]
    assert seen_update == []


def test_update_skills_human_separates_removed_managed_paths(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)

    def list_skills(command: ListSkillsCommand) -> ListSkillsResult:
        assert command.status == LatentSkillStatus.active
        return ListSkillsResult(
            skills=[
                SkillListItem(
                    id="agent-skill-1",
                    name="Review Helper",
                    scope="project",
                    status="active",
                    relative_path=".umem/skills/review-helper/SKILL.md",
                    canonical_path=".umem/skills/review-helper/SKILL.md",
                    created_at="2026-06-01T00:00:00Z",
                    updated_at="2026-06-01T00:00:00Z",
                    origin="test",
                    audit_reference="audit-list",
                    targets=[],
                )
            ]
        )

    def sync_skills(_command: SyncSkillsCommand) -> SyncSkillsResult:
        return SyncSkillsResult(
            skills=[
                SyncSkillResult(
                    skill_id="agent-skill-1",
                    name="Review Helper",
                    scope="project",
                    status="active",
                    canonical_path=".umem/skills/review-helper/SKILL.md",
                    affected_paths=[
                        ".agents/skills/review-helper/SKILL.md",
                        ".agents/skills/review-helper/references/old.md",
                    ],
                    removed_paths=[".agents/skills/review-helper/references/old.md"],
                    targets=[{"runtime": "codex", "path": ".agents/skills/review-helper"}],
                )
            ],
            affected_paths=[
                ".agents/skills/review-helper/SKILL.md",
                ".agents/skills/review-helper/references/old.md",
            ],
            removed_paths=[".agents/skills/review-helper/references/old.md"],
        )

    exit_code = cli_main(
        ["update", "--skills"],
        list_skills_command=list_skills,
        sync_skills_command=sync_skills,
        update_skill_command=lambda _command: _update_skill_result(),
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Synced paths:" in output
    assert "Removed managed paths:" in output
    assert ".agents/skills/review-helper/references/old.md" in output
    assert output.count(".agents/skills/review-helper/references/old.md") == 1


def test_update_skills_json_updates_managed_default_umem_skill_and_reports_preserved_paths(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--yes", "--format", "json"]) == 0
    capsys.readouterr()
    lifecycle_path = (
        tmp_path
        / ".umem"
        / "skills"
        / "use-universal-memory"
        / "references"
        / "skills-lifecycle.md"
    )
    lifecycle_path.write_text(LEGACY_SKILLS_LIFECYCLE, encoding="utf-8")

    exit_code = main(["update", "--skills", "--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["operation"] == "update.skills"
    assert payload["data"]["updated_count"] == 1
    assert payload["data"]["preserved_count"] == 0
    skill = payload["data"]["skills"][0]
    assert skill["managed"] is True
    assert skill["name"] == "use-universal-memory"
    assert skill["status"] == "updated"
    assert skill["updated_paths"] == [
        ".umem/skills/use-universal-memory/references/skills-lifecycle.md"
    ]
    assert ".umem/skills/use-universal-memory/SKILL.md" in skill["preserved_paths"]
    assert skill["audit_reference"]
    assert skill["snapshot_reference"]
    assert (
        "umem skills import .agents/skills/<skill-name> --scope project --visibility shared --category user-facing --sync"
        in lifecycle_path.read_text(encoding="utf-8")
    )


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
