import json
import socket
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import click
import pytest

from universal_memory.__main__ import main
from universal_memory.application.host import ConfigureHostCommand, ConfigureHostResult
from universal_memory.application.memory import PurgeFactResult
from universal_memory.application.onboarding.setup_project import setup_project
from universal_memory.application.skills import ProposeSkillDecision, ProposeSkillResult
from universal_memory.application.update import UpdateCheckResult
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.infrastructure.config import (
    LocalConfigValidationPort,
    LocalProjectLayoutPort,
)
from universal_memory.interfaces.cli import main as cli_main


def _setup_project_command(
    project_root: Path,
    enabled_runtime_ids: list[str] | None = None,
    *,
    layout: str = "legacy",
):
    return setup_project(
        project_root,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        enabled_runtime_ids=enabled_runtime_ids,
        layout=layout,
    )


def test_init_in_clean_directory_creates_layout_with_human_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["init"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert ".umem/" in captured.out
    assert "Local memory created" in captured.out
    assert "criada" not in captured.out
    assert ".umem/config.toml" in captured.out
    assert ".umem/memory" in captured.out
    assert ".umem/audit/events.jsonl" in captured.out
    assert ".umem/snapshots" in captured.out
    assert "umem status" in captured.out
    assert (tmp_path / ".umem" / "config.toml").is_file()
    assert (tmp_path / ".umem" / "memory").is_dir()
    config = tomllib.loads((tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8"))
    assert config["preferences"]["locale"] == "en"


def test_cli_help_uses_english_text_by_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_main(["--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Manage memory facts" in captured.out
    assert "Inspect audit events" in captured.out
    assert "Gerenciar" not in captured.out
    assert "auditoria" not in captured.out


def test_expected_human_errors_default_to_english(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_main(
        ["facts", "purge"],
        facts_purge_command=lambda _command: PurgeFactResult(
            purged_count=0,
            affected_ids=[],
            audit_reference="audit-ref",
        ),
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Provide exactly one option" in captured.err
    assert "Informe exatamente" not in captured.err


def test_update_conflicting_options_error_defaults_to_english(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_main(
        ["update", "--check", "--migrate"],
        update_check_command=lambda _command: UpdateCheckResult(
            installed_version="test",
            target_schema_version=1,
            project_config_schema_version=None,
            memory_schema_versions={},
            benchmarks_status="missing",
            updates_available=False,
            migration_required=False,
        ),
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Provide only one update option per execution" in captured.err
    assert "Informe apenas" not in captured.err


def test_skills_propose_accepts_english_decision_alias(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[ProposeSkillDecision] = []

    def propose(command):
        seen.append(command.decision)
        return ProposeSkillResult(
            latent_skill=LatentSkill(
                id="00000000-0000-4000-8000-000000000001",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                updated_at=datetime(2026, 1, 1, tzinfo=UTC),
                name="Skill",
                description="Description",
                scope=LatentSkillScope.project,
                status=LatentSkillStatus.ignored,
            ),
            proposal={
                "suggested_name": "Skill",
                "purpose": "Purpose",
                "evidence": [],
                "scope": "project",
            },
            accepted=True,
            audit_reference="audit-ref",
        )

    exit_code = cli_main(
        ["skills", "propose", "latent-1", "--decision", "yes"],
        propose_skill_command=propose,
    )

    capsys.readouterr()
    assert exit_code == 0
    assert seen == [ProposeSkillDecision.sim]


def test_init_json_outputs_pure_parseable_payload_with_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.startswith("{")
    assert payload["ok"] is True
    assert payload["operation"] == "init"
    assert payload["scope"] == "project"
    assert payload["warnings"] == []

    data = payload["data"]
    assert data["project_path"] == "."
    assert data["config_path"] == ".umem/config.toml"
    assert data["memory_path"] == ".umem/memory"
    assert data["audit_path"] == ".umem/audit/events.jsonl"
    assert data["snapshots_path"] == ".umem/snapshots"
    assert data["already_initialized"] is False
    assert payload["runtimes_selected"] == [
        "claude_code",
        "opencode",
        "codex",
        "cursor",
        "antigravity",
    ]
    assert payload["runtimes_skipped"] == []
    assert payload["target_paths"] == {
        "claude_code": ["CLAUDE.md"],
        "codex": ["AGENTS.md"],
    }
    assert payload["manual_steps_pending"] == []


def test_init_shared_layout_json_outputs_shared_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["init", "--layout", "shared", "--yes", "--format", "json"],
        setup_project_command=_setup_project_command,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert payload["data"]["layout"] == "shared"
    assert payload["data"]["shared_root"] == "umem"
    assert payload["data"]["operational_root"] == ".umem"
    assert payload["data"]["shared_paths"] == ["umem/project.toml", "umem/memory", "umem/skills"]
    assert payload["data"]["operational_paths"] == [
        ".umem/config.toml",
        ".umem/memory",
        ".umem/audit/events.jsonl",
        ".umem/snapshots",
        ".umem/skills",
        ".umem/benchmarks",
    ]
    assert (tmp_path / "umem" / "project.toml").is_file()
    assert (tmp_path / "umem" / "memory").is_dir()
    assert (tmp_path / "umem" / "skills").is_dir()
    assert (tmp_path / ".umem" / "skills" / "use-universal-memory" / "SKILL.md").is_file()
    assert not (tmp_path / "umem" / "skills" / "use-universal-memory").exists()


def test_init_json_runtime_option_persists_selection_and_runs_selected_runtime_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[ConfigureHostCommand] = []

    def host_setup(command: ConfigureHostCommand) -> ConfigureHostResult:
        seen.append(command)
        return ConfigureHostResult(
            host_id=command.host_id,
            instruction_targets=["agents_md"],
            planned_changes=[{"target": "agents_md", "action": "create", "path": "AGENTS.md"}],
            manual_steps=[],
            validation_status="success",
            audit_reference="audit-ref",
            snapshot_reference="snapshot-ref",
            timestamp="2026-05-29T12:00:00Z",
        )

    def host_check(command: ConfigureHostCommand) -> ConfigureHostResult:
        seen.append(command)
        return ConfigureHostResult(
            host_id=command.host_id,
            instruction_targets=["agents_md"],
            planned_changes=[],
            manual_steps=[],
            validation_status="success",
            audit_reference="audit-check-ref",
            snapshot_reference="planned",
            timestamp="2026-05-29T12:00:00Z",
        )

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["init", "--runtime", "codex", "--yes", "--format", "json"],
        setup_project_command=_setup_project_command,
        host_setup_command=host_setup,
        host_check_command=host_check,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["runtimes_selected"] == ["codex"]
    assert payload["runtimes_skipped"] == [
        "claude_code",
        "opencode",
        "cursor",
        "antigravity",
    ]
    config = tomllib.loads((tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8"))
    assert config["runtimes"]["enabled"] == ["codex"]
    assert config["preferences"]["locale"] == "en"
    assert seen == [
        ConfigureHostCommand(host_id="codex", apply=True, origin="cli_init"),
        ConfigureHostCommand(host_id="codex", apply=False, check=True, origin="cli_init"),
    ]


def test_init_json_accepts_repeated_runtime_flags_with_hyphen_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        [
            "init",
            "--runtime",
            "claude-code",
            "--runtime",
            "opencode",
            "--format",
            "json",
        ],
        setup_project_command=_setup_project_command,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["runtimes_selected"] == ["claude_code", "opencode"]
    assert '[runtimes]\nenabled = [\n    "claude_code",\n    "opencode",\n]\n' in (
        tmp_path / ".umem" / "config.toml"
    ).read_text(encoding="utf-8")


def test_init_human_interactive_prompts_for_runtime_indices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prompts: list[str] = []

    def prompt(prompt_text: str) -> str:
        prompts.append(prompt_text)
        return "1, 3"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("universal_memory.interfaces.cli.init_command._prompt", prompt)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    exit_code = cli_main(
        ["init", "--format", "human"], setup_project_command=_setup_project_command
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert prompts == ["Which runtime(s) would you like to install for? [1 2 3 4 5]: "]
    assert "Which runtime(s) would you like to install for?" in captured.out
    assert "1. Claude Code (tier_1)" in captured.out
    assert "2. OpenCode (tier_1)" in captured.out
    assert "3. Codex/OpenAI-class (tier_1)" in captured.out
    assert "4. Cursor (tier_2)" in captured.out
    assert "5. Antigravity (tier_2)" in captured.out
    assert '[runtimes]\nenabled = [\n    "claude_code",\n    "codex",\n]\n' in (
        tmp_path / ".umem" / "config.toml"
    ).read_text(encoding="utf-8")


def test_init_rejects_invalid_runtime_with_english_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["init", "--runtime", "desconhecido"],
        setup_project_command=_setup_project_command,
        locale_resolver=lambda: "pt-BR",
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Unsupported runtimes: desconhecido" in captured.err
    assert "nao suportado" not in captured.err.lower()


def test_init_human_uses_pt_br_overlay_when_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--format", "json"]) == 0
    capsys.readouterr()
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace('locale = "en"', 'locale = "pt-BR"'),
        encoding="utf-8",
    )

    exit_code = main(["init"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Memoria local ja inicializada." in captured.out
    assert "Local memory already initialized." not in captured.out


def test_init_human_interactive_renders_terminal_splash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr(
        "universal_memory.interfaces.cli.init_command._confirm", lambda *_args: True
    )

    exit_code = cli_main(
        ["init", "--runtime", "codex"], setup_project_command=_setup_project_command
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "umem" in captured.out
    assert "_    _ __  __" in captured.out
    assert "persistent context for AI agents" in captured.out
    assert "USB" not in captured.out
    assert captured.out.index("_    _ __  __") < captured.out.index(".umem/")
    assert "\x1b[" not in captured.out


def test_init_json_never_renders_terminal_splash_or_ansi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    exit_code = cli_main(["init", "--format", "json"], setup_project_command=_setup_project_command)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("{")
    assert json.loads(captured.out)["ok"] is True
    assert "_    _ __  __" not in captured.out
    assert "USB" not in captured.out
    assert "\x1b[" not in captured.out


@pytest.mark.parametrize(
    ("stdin_tty", "stdout_tty"),
    [(False, True), (True, False)],
)
def test_init_non_interactive_does_not_render_terminal_splash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdin_tty: bool,
    stdout_tty: bool,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: stdin_tty)
    monkeypatch.setattr("sys.stdout.isatty", lambda: stdout_tty)
    monkeypatch.setattr(
        "universal_memory.interfaces.cli.init_command._confirm", lambda *_args: True
    )

    exit_code = cli_main(
        ["init", "--runtime", "codex"], setup_project_command=_setup_project_command
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "_    _ __  __" not in captured.out
    assert "USB" not in captured.out
    assert "\x1b[" not in captured.out


def test_init_ci_environment_does_not_render_terminal_splash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr(
        "universal_memory.interfaces.cli.init_command._confirm", lambda *_args: True
    )

    exit_code = cli_main(
        ["init", "--runtime", "codex"], setup_project_command=_setup_project_command
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "_    _ __  __" not in captured.out
    assert "USB" not in captured.out
    assert "\x1b[" not in captured.out


@pytest.mark.parametrize("ci_value", ["false", "0", "no", "off"])
def test_init_ci_falsy_values_do_not_suppress_terminal_splash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    ci_value: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CI", ci_value)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    exit_code = cli_main(
        ["init", "--runtime", "codex"], setup_project_command=_setup_project_command
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "_    _ __  __" in captured.out
    assert "USB" not in captured.out


def test_init_no_color_renders_plain_ascii_splash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("NO_COLOR", "")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr(
        "universal_memory.interfaces.cli.init_command._confirm", lambda *_args: True
    )

    exit_code = cli_main(
        ["init", "--runtime", "codex"], setup_project_command=_setup_project_command
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "umem" in captured.out
    assert "_    _ __  __" in captured.out
    assert "persistent context for AI agents" in captured.out
    assert "USB" not in captured.out
    assert "\x1b[" not in captured.out


def test_init_missing_term_renders_plain_ascii_splash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr(
        "universal_memory.interfaces.cli.init_command._confirm", lambda *_args: True
    )

    exit_code = cli_main(
        ["init", "--runtime", "codex"], setup_project_command=_setup_project_command
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "_    _ __  __" in captured.out
    assert "USB" not in captured.out
    assert "\x1b[" not in captured.out


def test_init_module_execution_exits_with_process_status_and_json(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "universal_memory", "init", "--format", "json"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert payload["ok"] is True
    assert payload["operation"] == "init"
    assert payload["data"]["project_path"] == "."


def test_installed_cli_entry_points_use_bootstrap_composition_root() -> None:
    scripts = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'umem = "universal_memory.bootstrap.cli:main"' in scripts
    assert 'universal-memory = "universal_memory.bootstrap.cli:main"' in scripts


def test_cli_adapter_maps_unexpected_os_errors_to_json_error_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_with_os_error(_project_root: Path):
        raise OSError("filesystem unavailable")

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["init", "--format", "json"],
        setup_project_command=fail_with_os_error,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code != 0
    assert captured.err == ""
    assert payload == {
        "ok": False,
        "error": {
            "code": "storage_error",
            "message": "Storage error.",
            "detail": "filesystem unavailable",
            "recovery_hint": "Check the local layout and run umem init at the project root.",
            "audit_reference": None,
        },
    }


def test_cli_adapter_requires_composed_dependencies() -> None:
    with pytest.raises(RuntimeError, match="setup_project_command"):
        cli_main(["init"])


def test_init_json_data_contains_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert set(payload["data"]) == {
        "project_path",
        "config_path",
        "memory_path",
        "audit_path",
        "snapshots_path",
        "created",
        "already_initialized",
        "audit_reference",
        "layout",
        "shared_root",
        "operational_root",
        "shared_paths",
        "operational_paths",
    }


def test_init_is_idempotent_and_does_not_corrupt_existing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--format", "json"]) == 0
    capsys.readouterr()
    config_path = tmp_path / ".umem" / "config.toml"
    original_config = config_path.read_text()

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["data"]["already_initialized"] is True
    assert payload["data"]["created"] == []
    assert payload["data"]["project_path"] == "."
    assert payload["data"]["config_path"] == ".umem/config.toml"
    assert payload["data"]["memory_path"] == ".umem/memory"
    assert payload["data"]["audit_path"] == ".umem/audit/events.jsonl"
    assert payload["data"]["snapshots_path"] == ".umem/snapshots"
    assert config_path.read_text() == original_config


def test_init_does_not_attempt_network_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_network_access(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is not allowed during init")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket, "create_connection", fail_network_access)
    monkeypatch.setattr(socket, "socket", fail_network_access)

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["data"]["project_path"] == "."


def test_init_repairs_partial_layout_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".umem").mkdir()
    (tmp_path / ".umem" / "memory").mkdir()

    exit_code = main(["init", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert ".umem/config.toml" in payload["data"]["created"]
    assert (tmp_path / ".umem" / "config.toml").is_file()
    assert (tmp_path / ".umem" / "audit" / "events.jsonl").is_file()
    assert (tmp_path / ".umem" / "snapshots").is_dir()
    assert (tmp_path / ".umem" / "skills").is_dir()


CLICK_USAGE_ERROR_EXIT_CODE = 2


def test_click_exception_json_format_uses_error_envelope(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_main(["--format", "json", "--bad-option"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == CLICK_USAGE_ERROR_EXIT_CODE
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_failed"


def test_click_abort_json_format_uses_aborted_envelope(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def raise_abort(*args, **kwargs):
        raise click.exceptions.Abort()

    exit_code = cli_main(
        ["init", "--format", "json"],
        setup_project_command=raise_abort,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "aborted"
    assert "aborted" in payload["error"]["detail"]


def test_click_abort_human_format_prints_aborted_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def raise_abort(*args, **kwargs):
        raise click.exceptions.Abort()

    exit_code = cli_main(
        ["init", "--format", "human"],
        setup_project_command=raise_abort,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Aborted.\n"
