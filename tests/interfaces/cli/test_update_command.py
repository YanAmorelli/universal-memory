from __future__ import annotations

import json
import tomllib
from pathlib import Path

from universal_memory.__main__ import main

MIN_BENCHMARK_FACT_COUNT = 1000
MIN_BENCHMARK_QUERY_COUNT = 30


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


def test_update_defaults_to_check(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem").mkdir()

    exit_code = main(["update", "--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["operation"] == "update.check"
