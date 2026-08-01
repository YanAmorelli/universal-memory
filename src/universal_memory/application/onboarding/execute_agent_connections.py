from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from universal_memory.application.host import ConfigureHostCommand, ConfigureHostResult
from universal_memory.application.memory import (
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
)
from universal_memory.application.onboarding.agent_connections import (
    AgentConnectionPlan,
    ConnectionRecommendation,
    ExternalSkillAction,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import ContextSummaryScope

HostConnectionCommand = Callable[[ConfigureHostCommand], ConfigureHostResult]
ContextReadCommand = Callable[[AssembleContextSummaryCommand], AssembleContextSummaryResult]


@dataclass(frozen=True, slots=True)
class PersistedConnections:
    agent_ids: tuple[str, ...]
    audit_reference: str | None = None


class ConnectionStatePort(Protocol):
    def persist(self, agent_ids: list[str], *, origin: str) -> PersistedConnections: ...


class McpAvailabilityPort(Protocol):
    def is_available(self, *, host_id: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class ExternalActionExecution:
    status: str
    instruction_present: bool = False
    audit_reference: str | None = None
    detail: str | None = None
    mutation_boundary: str | None = None
    exit_code: int | None = None
    relative_target: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "mutation_boundary": self.mutation_boundary,
            "exit_code": self.exit_code,
            "detail": self.detail,
            "relative_target": self.relative_target,
        }


class ExternalActionExecutorPort(Protocol):
    def execute(self, action: ExternalSkillAction) -> ExternalActionExecution: ...


class UnavailableMcpAvailability:
    def is_available(self, *, host_id: str) -> bool:
        del host_id
        return False


class PendingExternalActionExecutor:
    def execute(self, action: ExternalSkillAction) -> ExternalActionExecution:
        del action
        return ExternalActionExecution(
            status="pending",
            detail="External installer execution is not configured.",
        )


@dataclass(frozen=True, slots=True)
class AgentConnectionExecution:
    validation_results: list[dict[str, Any]]
    connection_results: list[dict[str, Any]]
    audit_references: list[str]
    host_results: list[ConfigureHostResult]
    persisted_connections: tuple[str, ...] = ()


class ExecuteAgentConnectionsUseCase:
    def __init__(  # noqa: PLR0913
        self,
        *,
        host_setup_command: HostConnectionCommand | None = None,
        host_check_command: HostConnectionCommand | None = None,
        context_read_command: ContextReadCommand | None = None,
        connection_state_port: ConnectionStatePort | None = None,
        mcp_availability_port: McpAvailabilityPort | None = None,
        external_action_executor: ExternalActionExecutorPort | None = None,
        configurable_runtime_ids: frozenset[str] = frozenset({"claude_code", "codex"}),
        known_runtime_ids: frozenset[str] = frozenset(),
        context_max_size_chars: int = 4000,
    ) -> None:
        self._host_setup_command = host_setup_command
        self._host_check_command = host_check_command
        self._context_read_command = context_read_command
        self._connection_state_port = connection_state_port
        self._mcp_availability_port = mcp_availability_port or UnavailableMcpAvailability()
        self._external_action_executor = external_action_executor or PendingExternalActionExecutor()
        self._configurable_runtime_ids = configurable_runtime_ids
        self._known_runtime_ids = known_runtime_ids
        self._context_max_size_chars = context_max_size_chars

    def execute(
        self,
        plan: AgentConnectionPlan,
        *,
        accepted: bool,
        origin: str,
        persist_connections: bool = False,
        external_execution_authorized: bool = False,
    ) -> AgentConnectionExecution:
        if not plan.is_safe_and_unambiguous:
            raise ValidationFailedError(
                "The connection plan is not safe and unambiguous for automatic execution."
            )

        recommendations = (*plan.existing_connections, *plan.recommended_connections)
        validations: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        host_results: list[ConfigureHostResult] = []
        audit_references: list[str] = []
        connected_ids: list[str] = []
        external_executions: dict[str, ExternalActionExecution] = {}
        conflicting_external_agents = _conflicting_external_agents(plan.external_actions)

        for recommendation in recommendations:
            is_recommended = recommendation in plan.recommended_connections
            if is_recommended and not accepted:
                results.append(_connection_result(recommendation, status="skipped"))
                continue

            external_execution = self._execute_external_action(
                recommendation,
                authorized=external_execution_authorized,
                executions=external_executions,
                conflicting_agents=conflicting_external_agents,
            )
            if external_execution.audit_reference:
                _append_audit_reference(
                    audit_references,
                    external_execution.audit_reference,
                )
            host_validation = self._execute_managed_channel(
                recommendation,
                is_recommended=is_recommended,
                origin=origin,
                external_execution=external_execution,
                host_results=host_results,
                audit_references=audit_references,
            )
            instruction_presence = _connection_instruction_present(
                recommendation,
                host_validation=host_validation,
                external_execution=external_execution,
            )
            context_read = self._validate_project_context_read()
            mcp_available = (
                self._mcp_availability_port.is_available(host_id=recommendation.agent_id)
                if recommendation.connection_method == "unmanaged_mcp"
                else False
            )
            if recommendation.connection_method == "unmanaged_mcp":
                ready = mcp_available
                validation_status = "success" if ready else "manual_pending"
            else:
                ready = instruction_presence and context_read
                validation_status = "success" if ready else "action_required"

            validations.append(
                {
                    "agent_id": recommendation.agent_id,
                    "validation_level": (
                        "mcp_availability"
                        if recommendation.connection_method == "unmanaged_mcp"
                        else "context_read"
                    ),
                    "instruction_presence": instruction_presence,
                    "cli_available": self._context_read_command is not None,
                    "context_read": context_read,
                    "mcp_available": mcp_available,
                    "status": validation_status,
                }
            )
            status = "connected_and_validated" if ready else "action_required"
            results.append(
                _connection_result(
                    recommendation,
                    status=status,
                    audit_reference=(
                        host_validation.audit_reference
                        if host_validation is not None
                        else external_execution.audit_reference
                    ),
                    external_action_status=external_execution.status,
                    external_execution=external_execution,
                )
            )
            if ready:
                connected_ids.append(recommendation.agent_id)

        persisted: tuple[str, ...] = ()
        if persist_connections and connected_ids and self._connection_state_port is not None:
            known_connected = [
                agent_id for agent_id in connected_ids if agent_id in self._known_runtime_ids
            ]
            if known_connected:
                state = self._connection_state_port.persist(known_connected, origin=origin)
                persisted = state.agent_ids
                if state.audit_reference:
                    audit_references.append(state.audit_reference)

        return AgentConnectionExecution(
            validation_results=validations,
            connection_results=results,
            audit_references=list(dict.fromkeys(audit_references)),
            host_results=host_results,
            persisted_connections=persisted,
        )

    def _validate_project_context_read(self) -> bool:
        if self._context_read_command is None:
            return False
        try:
            self._context_read_command(
                AssembleContextSummaryCommand(
                    scope=ContextSummaryScope.project,
                    max_size_chars=self._context_max_size_chars,
                )
            )
        except Exception:
            return False
        return True

    def _execute_external_action(  # noqa: PLR0911
        self,
        recommendation: ConnectionRecommendation,
        *,
        authorized: bool,
        executions: dict[str, ExternalActionExecution],
        conflicting_agents: frozenset[str],
    ) -> ExternalActionExecution:
        if recommendation.already_connected:
            return ExternalActionExecution(status="not_required")
        action = recommendation.external_action
        if action is None:
            return ExternalActionExecution(status="not_required")
        if action.action == "managed_fallback":
            return ExternalActionExecution(status="managed_fallback")
        if action.action == "external_action":
            if action.agent_id in conflicting_agents:
                return ExternalActionExecution(
                    status="conflict",
                    detail="Conflicting external actions were proposed for the same agent.",
                    mutation_boundary="external_unmanaged",
                )
            if not authorized:
                return ExternalActionExecution(
                    status="planning_only",
                    detail="External execution requires explicit authority.",
                    mutation_boundary="external_unmanaged",
                )
            identity = json.dumps(action.to_payload(), sort_keys=True, separators=(",", ":"))
            if identity not in executions:
                executions[identity] = self._external_action_executor.execute(action)
            return executions[identity]
        return ExternalActionExecution(status="pending", detail=action.detail)

    def _execute_managed_channel(  # noqa: PLR0913
        self,
        recommendation: ConnectionRecommendation,
        *,
        is_recommended: bool,
        origin: str,
        external_execution: ExternalActionExecution,
        host_results: list[ConfigureHostResult],
        audit_references: list[str],
    ) -> ConfigureHostResult | None:
        if external_execution.status == "pending":
            return None
        managed_host_id = self._managed_host_id(recommendation, external_execution)
        if managed_host_id is None or self._host_check_command is None:
            return None
        if (
            is_recommended
            and not recommendation.already_connected
            and self._host_setup_command is not None
        ):
            try:
                setup_result = self._host_setup_command(
                    ConfigureHostCommand(host_id=managed_host_id, apply=True, origin=origin)
                )
            except Exception:
                return None
            host_results.append(setup_result)
            _append_audit_reference(audit_references, setup_result.audit_reference)
        try:
            validation = self._host_check_command(
                ConfigureHostCommand(
                    host_id=managed_host_id,
                    apply=False,
                    check=True,
                    origin=origin,
                )
            )
        except Exception:
            return None
        host_results.append(validation)
        _append_audit_reference(audit_references, validation.audit_reference)
        return validation

    def _managed_host_id(
        self,
        recommendation: ConnectionRecommendation,
        external_execution: ExternalActionExecution,
    ) -> str | None:
        managed_host_id: str | None = None
        if recommendation.connection_method == "native":
            if recommendation.agent_id in self._configurable_runtime_ids:
                managed_host_id = recommendation.agent_id
            elif "agents_md" in recommendation.instruction_channels:
                managed_host_id = "codex"
        elif recommendation.connection_method == "directed_cli":
            action = recommendation.external_action
            if action is not None and action.action == "external_action":
                managed_host_id = None
            elif external_execution.status == "managed_fallback" and action is not None:
                managed_host_id = "codex" if action.channel == "agents_md" else None
            elif action is None and "agents_md" in recommendation.instruction_channels:
                managed_host_id = "codex"
        return managed_host_id


def _connection_instruction_present(
    recommendation: ConnectionRecommendation,
    *,
    host_validation: ConfigureHostResult | None,
    external_execution: ExternalActionExecution,
) -> bool:
    if host_validation is not None:
        return host_validation.validation_status == "success"
    if external_execution.instruction_present:
        return True
    return recommendation.already_connected


def _connection_result(
    recommendation: ConnectionRecommendation,
    *,
    status: str,
    audit_reference: str | None = None,
    external_action_status: str = "not_required",
    external_execution: ExternalActionExecution | None = None,
) -> dict[str, Any]:
    return {
        "agent_id": recommendation.agent_id,
        "display_name": recommendation.display_name,
        "status": status,
        "connection_method": recommendation.connection_method,
        "external_action_status": external_action_status,
        "external_execution": (
            external_execution.to_payload()
            if external_execution is not None
            else ExternalActionExecution(status=external_action_status).to_payload()
        ),
        "audit_reference": audit_reference,
        "next_action": "Run umem doctor." if status == "action_required" else None,
    }


def _append_audit_reference(references: list[str], value: str) -> None:
    if value not in {"", "not-recorded"}:
        references.append(value)


def _conflicting_external_agents(
    actions: tuple[ExternalSkillAction, ...],
) -> frozenset[str]:
    identities: dict[str, set[str]] = {}
    for action in actions:
        identity = json.dumps(action.to_payload(), sort_keys=True, separators=(",", ":"))
        identities.setdefault(action.agent_id, set()).add(identity)
    return frozenset(agent_id for agent_id, values in identities.items() if len(values) > 1)
