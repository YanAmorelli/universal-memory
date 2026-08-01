import json
import tomllib
from pathlib import Path
from typing import cast

import pytest

from universal_memory.application.host import (
    ConfigureHostCommand,
    ConfigureHostResult,
    ConfigureHostUseCase,
)
from universal_memory.application.memory import (
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
)
from universal_memory.application.onboarding import (
    AgentConnectionPlan,
    AgentConnectionPlanner,
    ConnectionRecommendation,
    DetectedAgent,
    ExecuteAgentConnectionsUseCase,
    ExternalActionExecution,
    ExternalSkillAction,
    RegistrySignalAgentDetector,
)
from universal_memory.application.onboarding.setup_project import setup_project
from universal_memory.bootstrap.cli import main as bootstrap_main
from universal_memory.domain.entities.runtime import default_runtime_registry
from universal_memory.infrastructure.config import (
    LocalConfigValidationPort,
    LocalProjectLayoutPort,
)
from universal_memory.interfaces.cli import main as cli_main

EXTERNAL_FAILURE_EXIT_CODE = 128


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


def _host_result(command: ConfigureHostCommand) -> ConfigureHostResult:
    return ConfigureHostResult(
        host_id=command.host_id,
        instruction_targets=["agents_md"],
        planned_changes=(
            [{"target": "agents_md", "action": "create", "path": "AGENTS.md"}]
            if command.apply
            else []
        ),
        manual_steps=[],
        validation_status="success",
        audit_reference="audit-ref" if command.apply else "audit-check-ref",
        snapshot_reference="snapshot-ref" if command.apply else "planned",
        timestamp="2026-07-31T12:00:00Z",
    )


def _project_only_plan(project_root: Path, **kwargs) -> AgentConnectionPlan:
    planner = AgentConnectionPlanner(
        registry=default_runtime_registry(),
        detector=RegistrySignalAgentDetector(which=lambda _name: None),
    )
    return planner.plan(project_root, **kwargs)


def _context_result(_command: AssembleContextSummaryCommand) -> AssembleContextSummaryResult:
    return cast(AssembleContextSummaryResult, object())


class RecordingExternalActionExecutor:
    def __init__(self) -> None:
        self.actions: list[ExternalSkillAction] = []

    def execute(self, action: ExternalSkillAction) -> ExternalActionExecution:
        self.actions.append(action)
        return ExternalActionExecution(
            status="executed",
            instruction_present=True,
            mutation_boundary="external_unmanaged",
            exit_code=0,
        )


class FailingExternalActionExecutor:
    def execute(self, action: ExternalSkillAction) -> ExternalActionExecution:
        del action
        return ExternalActionExecution(
            status="failed",
            instruction_present=False,
            detail="Could not find remote branch v0.5.0.",
            mutation_boundary="external_unmanaged",
            exit_code=EXTERNAL_FAILURE_EXIT_CODE,
        )


def _external_connection_plan(_project_root: Path, **_kwargs) -> AgentConnectionPlan:
    action = ExternalSkillAction(
        agent_id="windsurf",
        available=True,
        external_agent_id="windsurf",
        instruction_targets=(".windsurf/skills/universal-memory/SKILL.md",),
        action="external_action",
        channel="npx_skills",
        argv=("npx", "--yes", "skills@1.5.20", "add", "official"),
        environment=(("DISABLE_TELEMETRY", "1"),),
    )
    recommendation = ConnectionRecommendation(
        agent_id="windsurf",
        display_name="Windsurf",
        support_tier="tier_2_directed_cli",
        connection_method="directed_cli",
        instruction_channels=("agent_skill",),
        external_action=action,
    )
    detected = DetectedAgent(
        agent_id="windsurf",
        display_name="Windsurf",
        detected_by=("explicit_selection",),
    )
    return AgentConnectionPlan((detected,), (), (recommendation,), (action,))


def test_init_golden_path_detects_confirms_once_and_reports_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / ".codex").mkdir()
    confirmations: list[str] = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)

    def confirm(prompt: str, default: bool = False) -> bool:
        confirmations.append(prompt)
        assert default is True
        return True

    monkeypatch.setattr("universal_memory.interfaces.cli.init_command._confirm", confirm)

    exit_code = cli_main(
        ["init"],
        setup_project_command=_setup_project_command,
        host_setup_command=_host_result,
        host_check_command=_host_result,
        context_command=_context_result,
        agent_connection_plan_command=_project_only_plan,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert len(confirmations) == 1
    assert "Codex/OpenAI-class" in captured.out
    assert "connected and context access verified" in captured.out
    assert "You're ready. Work with your agents normally." in captured.out
    assert "tier_1" not in captured.out
    assert "npx" not in captured.out
    assert ".codex/config.toml" not in captured.out


def test_connect_json_persists_runtime_without_reinitializing_memory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    config_path = tmp_path / ".umem" / "config.toml"
    memory_path = tmp_path / ".umem" / "memory"
    original_memory_paths = sorted(path.relative_to(tmp_path) for path in memory_path.rglob("*"))
    (tmp_path / ".codex").mkdir()

    exit_code = bootstrap_main(["connect", "--agent", "codex", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["operation"] == "connect"
    assert payload["data"]["detected_agents"][0]["agent_id"] == "codex"
    assert payload["data"]["connection_results"][0]["status"] == ("connected_and_validated")
    assert payload["data"]["validation_results"][0]["context_read"] is True
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert config["runtimes"]["enabled"] == ["codex"]
    assert payload["data"]["persisted_connections"] == ["codex"]
    current_memory_paths = {path.relative_to(tmp_path) for path in memory_path.rglob("*")}
    assert set(original_memory_paths) <= current_memory_paths


def test_connect_json_external_action_is_planning_only_without_yes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    external = RecordingExternalActionExecutor()
    executor = ExecuteAgentConnectionsUseCase(
        context_read_command=_context_result,
        external_action_executor=external,
    )

    exit_code = cli_main(
        ["connect", "--agent", "windsurf", "--format", "json"],
        agent_connection_plan_command=_external_connection_plan,
        agent_connection_executor=executor,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert external.actions == []
    result = payload["data"]["connection_results"][0]
    assert result["status"] == "action_required"
    assert result["external_action_status"] == "planning_only"
    assert result["external_execution"]["mutation_boundary"] == "external_unmanaged"


def test_connect_json_yes_is_explicit_external_execution_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    external = RecordingExternalActionExecutor()
    executor = ExecuteAgentConnectionsUseCase(
        context_read_command=_context_result,
        external_action_executor=external,
    )

    exit_code = cli_main(
        ["connect", "--agent", "windsurf", "--yes", "--format", "json"],
        agent_connection_plan_command=_external_connection_plan,
        agent_connection_executor=executor,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert len(external.actions) == 1
    result = payload["data"]["connection_results"][0]
    assert result["status"] == "connected_and_validated"
    assert result["external_action_status"] == "executed"


def test_connect_json_returns_failure_when_authorized_external_execution_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    executor = ExecuteAgentConnectionsUseCase(
        context_read_command=_context_result,
        external_action_executor=FailingExternalActionExecutor(),
    )

    exit_code = cli_main(
        ["connect", "--agent", "windsurf", "--yes", "--format", "json"],
        agent_connection_plan_command=_external_connection_plan,
        agent_connection_executor=executor,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "external_action_failed"
    result = payload["data"]["connection_results"][0]
    assert result["status"] == "action_required"
    assert result["external_action_status"] == "failed"
    assert result["external_execution"]["exit_code"] == EXTERNAL_FAILURE_EXIT_CODE


def test_init_json_returns_failure_when_authorized_external_execution_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    executor = ExecuteAgentConnectionsUseCase(
        context_read_command=_context_result,
        external_action_executor=FailingExternalActionExecutor(),
    )

    exit_code = cli_main(
        ["init", "--runtime", "cursor", "--yes", "--format", "json"],
        setup_project_command=_setup_project_command,
        agent_connection_plan_command=_external_connection_plan,
        agent_connection_executor=executor,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "external_action_failed"
    assert payload["data"]["connection_results"][0]["external_action_status"] == "failed"
    assert (tmp_path / ".umem" / "config.toml").is_file()


def test_connect_interactive_confirmation_authorizes_external_execution_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    confirmations: list[str] = []
    monkeypatch.setattr(
        "universal_memory.interfaces.cli.init_command._confirm",
        lambda prompt, default=False: confirmations.append(prompt) or True,
    )
    external = RecordingExternalActionExecutor()
    executor = ExecuteAgentConnectionsUseCase(
        context_read_command=_context_result,
        external_action_executor=external,
    )

    exit_code = cli_main(
        ["connect", "--agent", "windsurf"],
        agent_connection_plan_command=_external_connection_plan,
        agent_connection_executor=executor,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert len(confirmations) == 1
    assert len(external.actions) == 1
    assert "network access and a deterministic project-scoped copy" in captured.out
    assert "Anonymous installer telemetry is disabled" in captured.out
    assert "outside UMEM snapshot" in captured.out
    assert "rollback coverage" in captured.out
    assert "connected and context access verified" in captured.out
    assert "npx" not in captured.out


def test_connect_noninteractive_does_not_authorize_external_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    external = RecordingExternalActionExecutor()
    executor = ExecuteAgentConnectionsUseCase(
        context_read_command=_context_result,
        external_action_executor=external,
    )

    exit_code = cli_main(
        ["connect", "--agent", "windsurf"],
        agent_connection_plan_command=_external_connection_plan,
        agent_connection_executor=executor,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert external.actions == []
    assert "needs attention" in captured.out
    assert "npx" not in captured.out


def test_init_explicit_selection_without_yes_does_not_authorize_external_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    external = RecordingExternalActionExecutor()
    executor = ExecuteAgentConnectionsUseCase(
        context_read_command=_context_result,
        external_action_executor=external,
    )

    exit_code = cli_main(
        ["init", "--runtime", "cursor"],
        setup_project_command=_setup_project_command,
        agent_connection_plan_command=_external_connection_plan,
        agent_connection_executor=executor,
    )

    capsys.readouterr()
    assert exit_code == 0
    assert external.actions == []


def test_connect_generic_agent_uses_managed_agents_md_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    commands: list[ConfigureHostCommand] = []

    def host_command(command: ConfigureHostCommand) -> ConfigureHostResult:
        commands.append(command)
        return _host_result(command)

    exit_code = cli_main(
        ["connect", "--agent", "windsurf", "--format", "json"],
        host_setup_command=host_command,
        host_check_command=host_command,
        context_command=_context_result,
        agent_connection_plan_command=_project_only_plan,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert [command.host_id for command in commands] == ["codex", "codex"]
    recommendation = payload["data"]["recommended_connections"][0]
    assert recommendation["agent_id"] == "windsurf"
    assert recommendation["connection_method"] == "directed_cli"
    assert payload["data"]["connection_results"][0]["status"] == ("connected_and_validated")


def test_connect_no_new_agent_is_no_change_and_preserves_umem(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    context_calls: list[object] = []

    def empty_plan(_project_root: Path, **_kwargs) -> AgentConnectionPlan:
        return AgentConnectionPlan((), (), ())

    def unexpected_context(
        command: AssembleContextSummaryCommand,
    ) -> AssembleContextSummaryResult:
        context_calls.append(command)
        return cast(AssembleContextSummaryResult, object())

    exit_code = cli_main(
        ["connect"],
        agent_connection_plan_command=empty_plan,
        context_command=unexpected_context,
    )

    captured = capsys.readouterr()
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert exit_code == 0
    assert "No agent was detected" in captured.out
    assert before == after
    assert context_calls == []


def test_connect_reuses_existing_connection_without_setup_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    (tmp_path / ".codex").mkdir()
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text(
        "<!-- UMEM: START -->\nRun `umem context --scope project`.\n<!-- UMEM: END -->\n"
    )
    original_content = agents_path.read_text(encoding="utf-8")
    host_calls: list[ConfigureHostCommand] = []
    original_execute = ConfigureHostUseCase.execute

    def recording_execute(
        use_case: ConfigureHostUseCase,
        command: ConfigureHostCommand,
    ) -> ConfigureHostResult:
        host_calls.append(command)
        return original_execute(use_case, command)

    monkeypatch.setattr(ConfigureHostUseCase, "execute", recording_execute)

    exit_code = bootstrap_main(
        ["connect", "--agent", "codex", "--format", "json"],
    )

    payload = json.loads(capsys.readouterr().out)
    config = tomllib.loads((tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert not any(command.apply for command in host_calls)
    assert any(command.check for command in host_calls)
    assert agents_path.read_text(encoding="utf-8") == original_content
    assert config["runtimes"]["enabled"] == ["codex"]
    assert payload["data"]["persisted_connections"] == ["codex"]
    assert payload["data"]["recommended_connections"] == []
    assert payload["data"]["existing_connections"][0]["agent_id"] == "codex"
    assert payload["data"]["connection_results"][0]["status"] == ("connected_and_validated")


def test_init_declined_connection_still_initializes_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.setattr(
        "universal_memory.interfaces.cli.init_command._confirm",
        lambda _prompt, default=False: False,
    )
    (tmp_path / ".codex").mkdir()

    exit_code = cli_main(
        ["init"],
        setup_project_command=_setup_project_command,
        agent_connection_plan_command=_project_only_plan,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert (tmp_path / ".umem" / "config.toml").is_file()
    assert "Codex/OpenAI-class skipped" in captured.out


def test_init_legacy_hosts_flag_remains_automation_compatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["init", "--hosts", "codex", "--format", "json"],
        setup_project_command=_setup_project_command,
        agent_connection_plan_command=_project_only_plan,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["runtimes_selected"] == ["codex"]
    assert payload["data"]["detected_agents"][0]["detected_by"] == ["explicit_selection"]


def test_connect_unmanaged_mcp_reports_capability_only_and_pending_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])

    exit_code = cli_main(
        ["connect", "--unmanaged-mcp", "custom-host", "--format", "json"],
        agent_connection_plan_command=_project_only_plan,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["unmanaged_mcp_hosts"] == ["custom-host"]
    validation = next(
        item for item in payload["data"]["validation_results"] if item["agent_id"] == "custom-host"
    )
    assert validation["validation_level"] == "mcp_availability"
    assert validation["mcp_available"] is False
    assert validation["status"] == "manual_pending"
    connection = next(
        item for item in payload["data"]["connection_results"] if item["agent_id"] == "custom-host"
    )
    assert connection["status"] == "action_required"


def test_connect_requires_initialized_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(["connect", "--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert "Run umem init first" in payload["error"]["detail"]
    assert not (tmp_path / ".umem").exists()


def test_connect_rejects_unsafe_plan_even_in_json_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_project_command(tmp_path, [])
    host_calls: list[ConfigureHostCommand] = []

    def unsafe_plan(_project_root: Path, **_kwargs) -> AgentConnectionPlan:
        recommendation = ConnectionRecommendation(
            agent_id="codex",
            display_name="Codex",
            support_tier="tier_1_native_managed",
            connection_method="native",
            instruction_channels=("agents_md",),
            scope="global",
        )
        return AgentConnectionPlan((), (), (recommendation,))

    def host_setup(command: ConfigureHostCommand) -> ConfigureHostResult:
        host_calls.append(command)
        return _host_result(command)

    exit_code = cli_main(
        ["connect", "--yes", "--format", "json"],
        host_setup_command=host_setup,
        agent_connection_plan_command=unsafe_plan,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert "safe and unambiguous" in payload["error"]["detail"]
    assert host_calls == []
