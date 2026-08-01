from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from universal_memory.application.skills.official_skill_distribution import (
    ConnectionPlanAction,
    OfficialSkillAgent,
    OfficialSkillDistributionPlanner,
    OfficialSkillEnvironment,
    SkillInstallMethod,
    SkillInstallScope,
)
from universal_memory.domain.entities.runtime import (
    RuntimeAdapter,
    RuntimeRegistry,
    RuntimeSupportProfile,
    RuntimeSupportProfileId,
)


@dataclass(frozen=True, slots=True)
class DetectedAgent:
    agent_id: str
    display_name: str
    detected_by: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "detected_by": list(self.detected_by),
        }


@dataclass(frozen=True, slots=True)
class ExternalSkillAction:
    agent_id: str
    available: bool
    external_agent_id: str | None = None
    instruction_targets: tuple[str, ...] = ()
    already_installed: bool = False
    scope: str = "project"
    installer: str = "external_skill_installer"
    network_required: bool = True
    telemetry_disabled: bool = True
    mutation_owner: str = "external"
    detail: str | None = None
    action: str = "pending"
    channel: str | None = None
    argv: tuple[str, ...] = ()
    environment: tuple[tuple[str, str], ...] = ()
    technical_details: dict[str, object] = field(default_factory=dict)
    readiness_checks: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "external_agent_id": self.external_agent_id,
            "instruction_targets": list(self.instruction_targets),
            "already_installed": self.already_installed,
            "available": self.available,
            "scope": self.scope,
            "installer": self.installer,
            "network_required": self.network_required,
            "telemetry_disabled": self.telemetry_disabled,
            "mutation_owner": self.mutation_owner,
            "detail": self.detail,
            "action": self.action,
            "channel": self.channel,
            "argv": list(self.argv),
            "environment": dict(self.environment),
            "technical_details": self.technical_details,
            "readiness_checks": list(self.readiness_checks),
        }


class AgentDetectorPort(Protocol):
    def detect(
        self,
        project_root: Path,
        runtimes: tuple[RuntimeAdapter, ...],
    ) -> list[DetectedAgent]: ...


class ExternalSkillInstallerPort(Protocol):
    def plan(self, *, agent_id: str) -> ExternalSkillAction: ...


class OfficialSkillEnvironmentPort(Protocol):
    def resolve(self, *, agent_id: str) -> OfficialSkillEnvironment: ...


@dataclass(frozen=True, slots=True)
class OfficialSkillAgentMapping:
    external_agent_id: str
    instruction_targets: tuple[str, ...]
    installed: bool = False


class OfficialSkillAgentMappingPort(Protocol):
    def resolve(self, *, agent_id: str) -> OfficialSkillAgentMapping | None: ...


class UnavailableExternalSkillInstaller:
    """Use the managed bootstrap until an external installer adapter is configured."""

    def plan(self, *, agent_id: str) -> ExternalSkillAction:
        return ExternalSkillAction(
            agent_id=agent_id,
            available=True,
            network_required=False,
            mutation_owner="umem",
            detail="Using the managed AGENTS.md fallback.",
            action="managed_fallback",
            channel="agents_md",
            readiness_checks=(
                "instruction_presence",
                "umem_cli_available",
                "project_context_read",
            ),
        )


class OfficialSkillInstallerPlannerAdapter:
    """Adapts Story 6.13 planning without executing its external argv."""

    def __init__(
        self,
        *,
        environment_port: OfficialSkillEnvironmentPort,
        agent_mapping_port: OfficialSkillAgentMappingPort | None = None,
        planner: OfficialSkillDistributionPlanner | None = None,
    ) -> None:
        self._environment_port = environment_port
        self._agent_mapping_port = agent_mapping_port
        self._planner = planner or OfficialSkillDistributionPlanner()

    def plan(self, *, agent_id: str) -> ExternalSkillAction:
        mapping = (
            self._agent_mapping_port.resolve(agent_id=agent_id)
            if self._agent_mapping_port is not None
            else None
        )
        external_agent_id = mapping.external_agent_id if mapping is not None else agent_id
        connection = self._planner.plan(
            OfficialSkillAgent(
                agent_id=external_agent_id,
                display_name=_display_name(agent_id),
            ),
            self._environment_port.resolve(agent_id=agent_id),
            scope=SkillInstallScope.project,
            install_method=SkillInstallMethod.copy,
        )
        return ExternalSkillAction(
            agent_id=agent_id,
            external_agent_id=(mapping.external_agent_id if mapping is not None else None),
            instruction_targets=(mapping.instruction_targets if mapping is not None else ()),
            already_installed=(mapping.installed if mapping is not None else False),
            available=connection.action != ConnectionPlanAction.pending,
            scope=connection.scope.value,
            installer=connection.channel or "official_skill_fallback",
            network_required=bool(connection.argv),
            telemetry_disabled=connection.environment.get("DISABLE_TELEMETRY") == "1",
            mutation_owner=("external" if connection.argv else "umem_or_user"),
            detail=connection.unavailable_reason,
            action=connection.action.value,
            channel=connection.channel,
            argv=connection.argv,
            environment=tuple(connection.environment.items()),
            technical_details=dict(connection.technical_details),
            readiness_checks=connection.readiness_checks,
        )


@dataclass(frozen=True, slots=True)
class ConnectionRecommendation:
    agent_id: str
    display_name: str
    support_tier: str
    connection_method: str
    instruction_channels: tuple[str, ...]
    scope: str = "project"
    already_connected: bool = False
    manual_step: str | None = None
    external_action: ExternalSkillAction | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "support_tier": self.support_tier,
            "connection_method": self.connection_method,
            "instruction_channels": list(self.instruction_channels),
            "scope": self.scope,
            "already_connected": self.already_connected,
            "manual_step": self.manual_step,
        }


@dataclass(frozen=True, slots=True)
class AgentConnectionPlan:
    detected_agents: tuple[DetectedAgent, ...]
    existing_connections: tuple[ConnectionRecommendation, ...]
    recommended_connections: tuple[ConnectionRecommendation, ...]
    external_actions: tuple[ExternalSkillAction, ...] = field(default_factory=tuple)
    manual_steps_pending: tuple[dict[str, str], ...] = field(default_factory=tuple)

    @property
    def requires_confirmation(self) -> bool:
        return bool(self.recommended_connections)

    @property
    def is_safe_and_unambiguous(self) -> bool:
        return all(item.scope == "project" for item in self.recommended_connections) and all(
            item.scope == "project" for item in self.external_actions
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "detected_agents": [item.to_payload() for item in self.detected_agents],
            "existing_connections": [item.to_payload() for item in self.existing_connections],
            "recommended_connections": [item.to_payload() for item in self.recommended_connections],
            "support_tiers": {
                item.agent_id: item.support_tier
                for item in (*self.existing_connections, *self.recommended_connections)
            },
            "instruction_channels": {
                item.agent_id: list(item.instruction_channels)
                for item in (*self.existing_connections, *self.recommended_connections)
            },
            "directed_cli_agents": [
                item.agent_id
                for item in (*self.existing_connections, *self.recommended_connections)
                if item.connection_method == "directed_cli"
            ],
            "unmanaged_mcp_hosts": [
                item.agent_id
                for item in (*self.existing_connections, *self.recommended_connections)
                if item.connection_method == "unmanaged_mcp"
            ],
            "external_actions": [item.to_payload() for item in self.external_actions],
            "manual_steps_pending": list(self.manual_steps_pending),
        }


class RegistrySignalAgentDetector:
    """Detect project agents only from registry-owned typed detection signals."""

    def __init__(self, *, which=shutil.which, home: Path | None = None) -> None:
        self._which = which
        self._home = home or Path.home()

    def detect(
        self,
        project_root: Path,
        runtimes: tuple[RuntimeAdapter, ...],
    ) -> list[DetectedAgent]:
        detected: list[DetectedAgent] = []
        for runtime in runtimes:
            matches = self._matches(project_root, runtime)
            if matches:
                detected.append(
                    DetectedAgent(
                        agent_id=_runtime_id(runtime),
                        display_name=runtime.display_name,
                        detected_by=tuple(matches),
                    )
                )
        return detected

    def _matches(self, project_root: Path, runtime: RuntimeAdapter) -> list[str]:
        matches: list[str] = []
        for signal in getattr(runtime, "detection_signals", ()):
            kind = _enum_value(getattr(signal, "kind", ""))
            value = str(getattr(signal, "value", ""))
            if kind == "project_path" and (project_root / value).exists():
                matches.append(value)
            elif kind == "global_path" and (self._home / value).exists():
                matches.append(f"global:{value}")
            elif kind == "executable" and self._which(value) is not None:
                matches.append(f"executable:{value}")
        return matches


class AgentConnectionPlanner:
    def __init__(
        self,
        *,
        registry: RuntimeRegistry,
        detector: AgentDetectorPort,
        external_skill_installer: ExternalSkillInstallerPort | None = None,
    ) -> None:
        self._registry = registry
        self._detector = detector
        self._external_skill_installer = (
            external_skill_installer or UnavailableExternalSkillInstaller()
        )

    def plan(
        self,
        project_root: Path,
        *,
        selected_agent_ids: list[str] | None = None,
        unmanaged_mcp_host_ids: list[str] | None = None,
        include_existing: bool = False,
    ) -> AgentConnectionPlan:
        runtimes = tuple(self._registry.runtimes)
        if selected_agent_ids is None:
            detected = self._detector.detect(project_root, runtimes)
        else:
            selected = set(selected_agent_ids)
            detected = [
                DetectedAgent(
                    agent_id=_runtime_id(runtime),
                    display_name=runtime.display_name,
                    detected_by=("explicit_selection",),
                )
                for runtime in runtimes
                if _runtime_id(runtime) in selected
            ]
            known_ids = {_runtime_id(runtime) for runtime in runtimes}
            detected.extend(
                DetectedAgent(
                    agent_id=agent_id,
                    display_name=_display_name(agent_id),
                    detected_by=("explicit_selection",),
                )
                for agent_id in selected_agent_ids
                if agent_id not in known_ids
            )

        by_id = {_runtime_id(runtime): runtime for runtime in runtimes}
        existing: list[ConnectionRecommendation] = []
        recommended: list[ConnectionRecommendation] = []
        external_actions: list[ExternalSkillAction] = []
        manual_steps: list[dict[str, str]] = []

        for agent in detected:
            runtime = by_id.get(agent.agent_id)
            recommendation = (
                self._recommend(runtime, project_root)
                if runtime is not None
                else self._recommend_profile(agent, project_root)
            )
            if recommendation.already_connected:
                existing.append(recommendation)
                if include_existing:
                    recommended.append(recommendation)
                continue
            recommended.append(recommendation)
            if recommendation.external_action is not None:
                external_actions.append(recommendation.external_action)
            if recommendation.manual_step is not None:
                manual_steps.append(
                    {"agent_id": agent.agent_id, "step": recommendation.manual_step}
                )

        if unmanaged_mcp_host_ids:
            profile = self._registry.get_profile(RuntimeSupportProfileId.unmanaged_mcp)
            for host_id in dict.fromkeys(unmanaged_mcp_host_ids):
                detected_agent = DetectedAgent(
                    agent_id=host_id,
                    display_name=host_id,
                    detected_by=("explicit_unmanaged_mcp",),
                )
                detected.append(detected_agent)
                step = (
                    "Configure the UMEM MCP server manually, then run umem doctor; "
                    "agent behavior remains unmanaged."
                )
                recommendation = ConnectionRecommendation(
                    agent_id=host_id,
                    display_name=host_id,
                    support_tier=profile.support_tier.value,
                    connection_method="unmanaged_mcp",
                    instruction_channels=tuple(
                        channel.value for channel in profile.instruction_channels
                    ),
                    manual_step=step,
                )
                recommended.append(recommendation)
                manual_steps.append({"agent_id": host_id, "step": step})

        return AgentConnectionPlan(
            detected_agents=tuple(detected),
            existing_connections=tuple(existing),
            recommended_connections=tuple(recommended),
            external_actions=tuple(external_actions),
            manual_steps_pending=tuple(manual_steps),
        )

    def _recommend(self, runtime: RuntimeAdapter, project_root: Path) -> ConnectionRecommendation:
        tier = _enum_value(runtime.support_tier)
        managed = bool(
            getattr(
                runtime,
                "managed_by_umem",
                tier in {"tier_1", "tier_1_native_managed"},
            )
        )
        channels = _instruction_channels(runtime)
        method = _connection_method(tier=tier, managed=managed)
        already_connected = _has_existing_connection(
            project_root,
            runtime,
            method=method,
            channels=channels,
        )
        external_action: ExternalSkillAction | None = None
        manual_step: str | None = None

        if method == "directed_cli" and not already_connected:
            if "agent_skill" in channels:
                external_action = self._external_skill_installer.plan(agent_id=_runtime_id(runtime))
                already_connected = external_action.already_installed
            if "agents_md" not in channels and (
                external_action is None or not external_action.available
            ):
                manual_step = "Connect portable instructions later, then run umem doctor."
        elif method == "unmanaged_mcp" and not already_connected:
            manual_step = (
                "Configure the UMEM MCP server manually, then run umem doctor; "
                "agent behavior remains unmanaged."
            )

        return ConnectionRecommendation(
            agent_id=_runtime_id(runtime),
            display_name=runtime.display_name,
            support_tier=tier,
            connection_method=method,
            instruction_channels=channels,
            already_connected=already_connected,
            manual_step=manual_step,
            external_action=external_action,
        )

    def _recommend_profile(
        self,
        agent: DetectedAgent,
        project_root: Path,
    ) -> ConnectionRecommendation:
        profile = self._registry.get_profile(RuntimeSupportProfileId.directed_cli)
        channels = _profile_instruction_channels(profile)
        external_action = self._external_skill_installer.plan(agent_id=agent.agent_id)
        return ConnectionRecommendation(
            agent_id=agent.agent_id,
            display_name=agent.display_name,
            support_tier=profile.support_tier.value,
            connection_method="directed_cli",
            instruction_channels=channels,
            already_connected=(
                external_action.already_installed
                or (
                    "agents_md" in channels
                    and _valid_umem_instruction_file(project_root / "AGENTS.md")
                )
            ),
            external_action=external_action,
        )


def default_agent_connection_planner(
    registry: RuntimeRegistry,
    *,
    detector: AgentDetectorPort | None = None,
    external_skill_installer: ExternalSkillInstallerPort | None = None,
) -> AgentConnectionPlanner:
    return AgentConnectionPlanner(
        registry=registry,
        detector=detector or RegistrySignalAgentDetector(),
        external_skill_installer=external_skill_installer,
    )


def _runtime_id(runtime: RuntimeAdapter) -> str:
    return _enum_value(runtime.runtime_id)


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _instruction_channels(runtime: RuntimeAdapter) -> tuple[str, ...]:
    declared = getattr(runtime, "instruction_channels", None)
    if declared:
        return tuple(_enum_value(channel) for channel in declared)
    return tuple(
        _enum_value(getattr(target, "name", "unknown")) for target in runtime.instruction_targets
    )


def _profile_instruction_channels(
    profile: RuntimeSupportProfile,
) -> tuple[str, ...]:
    return tuple(channel.value for channel in profile.instruction_channels)


def _display_name(agent_id: str) -> str:
    return " ".join(part.capitalize() for part in agent_id.replace("_", "-").split("-"))


def _connection_method(*, tier: str, managed: bool) -> str:
    if managed:
        return "native"
    if tier in {"tier_3", "tier_3_unmanaged_mcp"}:
        return "unmanaged_mcp"
    return "directed_cli"


def _has_existing_connection(
    project_root: Path,
    runtime: RuntimeAdapter,
    *,
    method: str,
    channels: tuple[str, ...],
) -> bool:
    if method == "unmanaged_mcp":
        return False
    if "agents_md" in channels and _valid_umem_instruction_file(project_root / "AGENTS.md"):
        return True
    for target in runtime.instruction_targets:
        relative_path = getattr(target, "relative_path", None)
        if isinstance(relative_path, str) and _valid_umem_instruction_file(
            project_root / relative_path
        ):
            return True
    return False


def _valid_umem_instruction_file(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    start_marker = "<!-- UMEM: START -->"
    end_marker = "<!-- UMEM: END -->"
    start = content.find(start_marker)
    end = content.find(end_marker)
    if start < 0 or end <= start:
        return False
    managed = content[start + len(start_marker) : end].strip().lower()
    return bool(managed) and any(
        reference in managed for reference in ("universal-memory", "umem context", "umem status")
    )
