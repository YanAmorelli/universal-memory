from __future__ import annotations

import json

from universal_memory.application.layout import MigrateProjectLayoutCommand
from universal_memory.interfaces.cli import main as cli_main


def test_layout_migrate_dry_run_json_payload(capsys) -> None:
    seen: list[MigrateProjectLayoutCommand] = []

    def migrate(command: MigrateProjectLayoutCommand) -> dict:
        seen.append(command)
        return _migration_payload(dry_run=command.dry_run)

    exit_code = cli_main(
        ["layout", "migrate", "--to", "shared", "--dry-run", "--format", "json"],
        layout_migrate_command=migrate,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert seen[0].dry_run is True
    assert payload["operation"] == "layout.migrate"
    assert payload["scope"] == "project"
    assert payload["data"]["dry_run"] is True
    assert {"copied", "already_shared", "skipped", "conflicts"} <= set(payload["data"])


def test_layout_migrate_apply_json_payload(capsys) -> None:
    seen: list[MigrateProjectLayoutCommand] = []

    def migrate(command: MigrateProjectLayoutCommand) -> dict:
        seen.append(command)
        return _migration_payload(dry_run=command.dry_run)

    exit_code = cli_main(
        ["layout", "migrate", "--to", "shared", "--apply", "--format", "json"],
        layout_migrate_command=migrate,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert seen[0].dry_run is False
    assert payload["data"]["dry_run"] is False


def _migration_payload(*, dry_run: bool) -> dict:
    data = {
        "operation": "layout.migrate",
        "source_layout": "legacy",
        "target_layout": "shared",
        "dry_run": dry_run,
        "copied": [
            {
                "kind": "fact",
                "id": "fact-1",
                "reason": "copied",
                "path": "umem/memory/facts.jsonl",
            }
        ],
        "already_shared": [],
        "skipped": [],
        "conflicts": [],
        "remaining_local": [],
        "affected_paths": ["umem/project.toml", "umem/memory/facts.jsonl"],
        "next_steps": [],
        "warnings": [],
    }
    return {"operation": "layout.migrate", "scope": "project", "data": data, "warnings": []}
