from dataclasses import replace
from typing import cast

import pytest

from universal_memory.application.host import ConfigureHostCommand, ConfigureHostResult
from universal_memory.application.memory import (
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
)
from universal_memory.application.onboarding import (
    AgentConnectionPlan,
    ConnectionRecommendation,
    ExecuteAgentConnectionsUseCase,
    ExternalActionExecution,
    ExternalSkillAction,
)
from universal_memory.domain import ValidationFailedError


class McpAvailability:
    def __init__(self, available: bool) -> None:
        self.available = available

    def is_available(self, *, host_id: str) -> bool:
        assert host_id == "custom-host"
        return self.available


class RecordingExternalExecutor:
    def __init__(self) -> None:
        self.actions: list[ExternalSkillAction] = []

    def execute(self, action: ExternalSkillAction):
        self.actions.append(action)
        raise AssertionError("The default pending behavior should be used in this test")


class SuccessfulExternalExecutor:
    def __init__(self) -> None:
        self.actions: list[ExternalSkillAction] = []

    def execute(self, action: ExternalSkillAction):
        self.actions.append(action)
        return ExternalActionExecution(
            status="executed",
            instruction_present=True,
            mutation_boundary="external_unmanaged",
            exit_code=0,
        )


def _context(_command: AssembleContextSummaryCommand) -> AssembleContextSummaryResult:
    return cast(AssembleContextSummaryResult, object())


def _host_result(command: ConfigureHostCommand) -> ConfigureHostResult:
    return ConfigureHostResult(
        host_id=command.host_id,
        instruction_targets=["agents_md"],
        planned_changes=[],
        manual_steps=[],
        validation_status="success",
        audit_reference="audit-host",
        snapshot_reference="snapshot-host",
        timestamp="2026-07-31T12:00:00Z",
    )


@pytest.mark.parametrize(
    ("available", "expected"),
    [(False, "action_required"), (True, "connected_and_validated")],
)
def test_tier_3_connection_uses_injected_mcp_availability(
    available: bool,
    expected: str,
) -> None:
    recommendation = ConnectionRecommendation(
        agent_id="custom-host",
        display_name="Custom Host",
        support_tier="tier_3_unmanaged_mcp",
        connection_method="unmanaged_mcp",
        instruction_channels=("mcp_only",),
        manual_step="Configure MCP manually.",
    )
    plan = AgentConnectionPlan((), (), (recommendation,))
    executor = ExecuteAgentConnectionsUseCase(
        mcp_availability_port=McpAvailability(available),
    )

    result = executor.execute(plan, accepted=True, origin="test")

    assert result.connection_results[0]["status"] == expected
    assert result.validation_results[0]["mcp_available"] is available


def test_executor_rejects_unsafe_plan_before_any_mutation() -> None:
    host_calls: list[ConfigureHostCommand] = []
    recommendation = ConnectionRecommendation(
        agent_id="codex",
        display_name="Codex",
        support_tier="tier_1_native_managed",
        connection_method="native",
        instruction_channels=("agents_md",),
        scope="global",
    )
    executor = ExecuteAgentConnectionsUseCase(
        host_setup_command=lambda command: host_calls.append(command) or _host_result(command),
        host_check_command=_host_result,
        context_read_command=_context,
    )

    with pytest.raises(ValidationFailedError, match="safe and unambiguous"):
        executor.execute(
            AgentConnectionPlan((), (), (recommendation,)),
            accepted=True,
            origin="test",
        )

    assert host_calls == []


def test_external_npx_plan_stays_pending_until_an_executor_runs_it() -> None:
    host_calls: list[ConfigureHostCommand] = []
    action = ExternalSkillAction(
        agent_id="windsurf",
        available=True,
        action="external_action",
        channel="npx_skills",
        argv=("npx", "--yes", "skills@1.0.0", "add", "owner/repo"),
    )
    recommendation = ConnectionRecommendation(
        agent_id="windsurf",
        display_name="Windsurf",
        support_tier="tier_2_directed_cli",
        connection_method="directed_cli",
        instruction_channels=("agent_skill",),
        external_action=action,
    )
    executor = ExecuteAgentConnectionsUseCase(
        host_setup_command=lambda command: host_calls.append(command) or _host_result(command),
        host_check_command=_host_result,
        context_read_command=_context,
    )

    result = executor.execute(
        AgentConnectionPlan((), (), (recommendation,), (action,)),
        accepted=True,
        external_execution_authorized=True,
        origin="test",
    )

    assert host_calls == []
    assert result.connection_results[0]["status"] == "action_required"
    assert result.connection_results[0]["external_action_status"] == "pending"
    assert result.validation_results[0]["instruction_presence"] is False


def test_managed_fallback_is_executed_and_validated() -> None:
    host_calls: list[ConfigureHostCommand] = []
    action = ExternalSkillAction(
        agent_id="windsurf",
        available=True,
        network_required=False,
        mutation_owner="umem",
        action="managed_fallback",
        channel="agents_md",
    )
    recommendation = ConnectionRecommendation(
        agent_id="windsurf",
        display_name="Windsurf",
        support_tier="tier_2_directed_cli",
        connection_method="directed_cli",
        instruction_channels=("agents_md", "agent_skill"),
        external_action=action,
    )
    executor = ExecuteAgentConnectionsUseCase(
        host_setup_command=lambda command: host_calls.append(command) or _host_result(command),
        host_check_command=lambda command: host_calls.append(command) or _host_result(command),
        context_read_command=_context,
    )

    result = executor.execute(
        AgentConnectionPlan((), (), (recommendation,), (action,)),
        accepted=True,
        origin="test",
    )

    assert [command.apply for command in host_calls] == [True, False]
    assert result.connection_results[0]["status"] == "connected_and_validated"
    assert result.connection_results[0]["external_action_status"] == "managed_fallback"


def test_external_action_requires_separate_execution_authority() -> None:
    action = ExternalSkillAction(
        agent_id="windsurf",
        available=True,
        action="external_action",
        channel="npx_skills",
        argv=("npx", "--yes", "skills@1.5.20", "add", "official-source"),
    )
    recommendation = ConnectionRecommendation(
        agent_id="windsurf",
        display_name="Windsurf",
        support_tier="tier_2_directed_cli",
        connection_method="directed_cli",
        instruction_channels=("agent_skill",),
        external_action=action,
    )
    runner = SuccessfulExternalExecutor()
    executor = ExecuteAgentConnectionsUseCase(
        context_read_command=_context,
        external_action_executor=runner,
    )

    result = executor.execute(
        AgentConnectionPlan((), (), (recommendation,), (action,)),
        accepted=True,
        external_execution_authorized=False,
        origin="test",
    )

    assert runner.actions == []
    assert result.connection_results[0]["status"] == "action_required"
    assert result.connection_results[0]["external_action_status"] == "planning_only"
    assert result.connection_results[0]["external_execution"] == {
        "status": "planning_only",
        "mutation_boundary": "external_unmanaged",
        "exit_code": None,
        "detail": "External execution requires explicit authority.",
        "relative_target": None,
    }


def test_context_read_happens_after_external_execution_and_actions_are_deduplicated() -> None:
    events: list[str] = []

    class OrderedExecutor(SuccessfulExternalExecutor):
        def execute(self, action: ExternalSkillAction):
            events.append("external")
            return super().execute(action)

    def context_after_execution(
        _command: AssembleContextSummaryCommand,
    ) -> AssembleContextSummaryResult:
        events.append("context")
        assert "external" in events
        return cast(AssembleContextSummaryResult, object())

    action = ExternalSkillAction(
        agent_id="windsurf",
        available=True,
        action="external_action",
        channel="npx_skills",
        argv=("npx", "--yes", "skills@1.5.20", "add", "official-source"),
    )
    recommendation = ConnectionRecommendation(
        agent_id="windsurf",
        display_name="Windsurf",
        support_tier="tier_2_directed_cli",
        connection_method="directed_cli",
        instruction_channels=("agent_skill",),
        external_action=action,
    )
    runner = OrderedExecutor()
    executor = ExecuteAgentConnectionsUseCase(
        context_read_command=context_after_execution,
        external_action_executor=runner,
    )

    result = executor.execute(
        AgentConnectionPlan((), (), (recommendation, recommendation), (action, action)),
        accepted=True,
        external_execution_authorized=True,
        origin="test",
    )

    assert len(runner.actions) == 1
    assert events == ["external", "context", "context"]
    assert all(item["status"] == "connected_and_validated" for item in result.connection_results)


def test_conflicting_external_actions_for_one_agent_are_not_deduplicated_or_executed() -> None:
    action = ExternalSkillAction(
        agent_id="windsurf",
        available=True,
        action="external_action",
        channel="npx_skills",
        argv=("npx", "--yes", "skills@1.5.20", "add", "official-source"),
    )
    conflicting = replace(action, environment=(("DISABLE_TELEMETRY", "0"),))
    recommendation = ConnectionRecommendation(
        agent_id="windsurf",
        display_name="Windsurf",
        support_tier="tier_2_directed_cli",
        connection_method="directed_cli",
        instruction_channels=("agent_skill",),
        external_action=action,
    )
    runner = SuccessfulExternalExecutor()

    result = ExecuteAgentConnectionsUseCase(
        context_read_command=_context,
        external_action_executor=runner,
    ).execute(
        AgentConnectionPlan((), (), (recommendation,), (action, conflicting)),
        accepted=True,
        external_execution_authorized=True,
        origin="test",
    )

    assert runner.actions == []
    assert result.connection_results[0]["external_action_status"] == "conflict"


def test_external_audit_reference_is_exposed_in_execution_summary() -> None:
    action = ExternalSkillAction(
        agent_id="windsurf",
        available=True,
        action="external_action",
        channel="npx_skills",
        argv=("npx", "--yes", "skills@1.5.20", "add", "official-source"),
    )
    recommendation = ConnectionRecommendation(
        agent_id="windsurf",
        display_name="Windsurf",
        support_tier="tier_2_directed_cli",
        connection_method="directed_cli",
        instruction_channels=("agent_skill",),
        external_action=action,
    )

    class AuditedExecutor(SuccessfulExternalExecutor):
        def execute(self, action: ExternalSkillAction):
            result = super().execute(action)
            return replace(result, audit_reference="audit-external")

    result = ExecuteAgentConnectionsUseCase(
        context_read_command=_context,
        external_action_executor=AuditedExecutor(),
    ).execute(
        AgentConnectionPlan((), (), (recommendation,), (action,)),
        accepted=True,
        external_execution_authorized=True,
        origin="test",
    )

    assert result.audit_references == ["audit-external"]
    assert result.connection_results[0]["audit_reference"] == "audit-external"
