from __future__ import annotations

import re
import shlex
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Literal, Self

from universal_memory import __version__
from universal_memory.domain import ValidationFailedError

OFFICIAL_SKILL_NAME = "universal-memory"
OFFICIAL_SKILL_REPOSITORY = "https://github.com/YanAmorelli/universal-memory"
OFFICIAL_SKILLS_CLI_PACKAGE = "skills@1.5.20"
OFFICIAL_SKILL_RELATIVE_PATH = "skills/universal-memory"
OFFICIAL_AGENTS_BOOTSTRAP_RELATIVE_PATH = "skills/universal-memory/assets/agents-md-bootstrap.md"
OFFICIAL_SKILL_PACKAGE = "universal_memory"
OFFICIAL_SKILL_PACKAGE_RELATIVE_PATH = "resources/skills/universal-memory"
OFFICIAL_AGENTS_BOOTSTRAP_PACKAGE_RELATIVE_PATH = (
    "resources/skills/universal-memory/assets/agents-md-bootstrap.md"
)
DIRECTED_CLI_SUPPORT_TIER = "tier_2_directed_cli"
READINESS_CHECKS = (
    "instruction_presence",
    "umem_cli_available",
    "project_context_read",
)

_AGENT_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_SOURCE_REF_PATTERN = re.compile(r"(?:v[0-9][0-9A-Za-z.-]*|[0-9a-f]{40})")


class SkillInstallScope(StrEnum):
    project = "project"
    global_ = "global"


class SkillInstallMethod(StrEnum):
    symlink = "symlink"
    copy = "copy"


class ConnectionPlanAction(StrEnum):
    external_action = "external_action"
    managed_fallback = "managed_fallback"
    pending = "pending"


FallbackChannel = Literal["agents_md", "umem_native", "manual_copy"]


@dataclass(frozen=True, slots=True)
class OfficialSkillAgent:
    agent_id: str
    display_name: str


@dataclass(frozen=True, slots=True)
class OfficialSkillEnvironment:
    node_available: bool
    npx_available: bool
    network_available: bool
    agent_mapping_available: bool
    agents_md_available: bool
    umem_native_available: bool
    manual_copy_available: bool


@dataclass(frozen=True, slots=True)
class ManagedSkillFallback:
    channel: FallbackChannel
    source_package: str
    source_path: str
    guidance: str
    recommended: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "source_package": self.source_package,
            "source_path": self.source_path,
            "guidance": self.guidance,
            "recommended": self.recommended,
        }


@dataclass(frozen=True, slots=True)
class OfficialSkillConnectionPlan:
    action: ConnectionPlanAction
    channel: str | None
    agent: OfficialSkillAgent
    scope: SkillInstallScope
    install_method: SkillInstallMethod
    support_tier: str
    ready: bool
    requires_confirmation: bool
    primary_prompt: str
    argv: tuple[str, ...]
    environment: Mapping[str, str]
    display_command: str
    technical_details: Mapping[str, Any]
    readiness_checks: tuple[str, ...]
    fallbacks: tuple[ManagedSkillFallback, ...] = ()
    unavailable_reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "channel": self.channel,
            "agent": {
                "id": self.agent.agent_id,
                "display_name": self.agent.display_name,
            },
            "scope": self.scope.value,
            "install_method": self.install_method.value,
            "support_tier": self.support_tier,
            "ready": self.ready,
            "requires_confirmation": self.requires_confirmation,
            "primary_prompt": self.primary_prompt,
            "argv": list(self.argv),
            "environment": dict(self.environment),
            "display_command": self.display_command,
            "technical_details": dict(self.technical_details),
            "readiness_checks": list(self.readiness_checks),
            "fallbacks": [fallback.to_payload() for fallback in self.fallbacks],
            "unavailable_reason": self.unavailable_reason,
        }


class OfficialSkillDistributionPlanner:
    """Build an installation plan without probing or mutating the environment."""

    def __init__(self, *, source_ref: str | None = None) -> None:
        self.source_ref = _validate_source_ref(source_ref or f"v{__version__}")
        self.skill_source = (
            f"{OFFICIAL_SKILL_REPOSITORY}/tree/{self.source_ref}/skills/universal-memory"
        )

    @classmethod
    def for_published_distribution(cls) -> Self:
        """Use only in artifacts that passed the release provenance gate."""
        return cls(source_ref=f"v{__version__}")

    def plan(
        self,
        agent: OfficialSkillAgent,
        environment: OfficialSkillEnvironment,
        *,
        scope: SkillInstallScope = SkillInstallScope.project,
        install_method: SkillInstallMethod = SkillInstallMethod.copy,
    ) -> OfficialSkillConnectionPlan:
        validated_agent = _validate_agent(agent)
        validated_environment = _validate_environment(environment)
        validated_scope = _validate_scope(scope)
        validated_method = _validate_method(install_method)
        unavailable_reason = _external_unavailability_reason(validated_environment)
        if unavailable_reason is None:
            return self._external_plan(
                validated_agent,
                validated_scope,
                validated_method,
            )
        return self._fallback_plan(
            validated_agent,
            validated_environment,
            validated_scope,
            validated_method,
            unavailable_reason,
        )

    def _external_plan(
        self,
        agent: OfficialSkillAgent,
        scope: SkillInstallScope,
        install_method: SkillInstallMethod,
    ) -> OfficialSkillConnectionPlan:
        argv = [
            "npx",
            "--yes",
            OFFICIAL_SKILLS_CLI_PACKAGE,
            "add",
            self.skill_source,
            "--skill",
            OFFICIAL_SKILL_NAME,
            "--agent",
            agent.agent_id,
        ]
        if scope == SkillInstallScope.global_:
            argv.append("--global")
        if install_method == SkillInstallMethod.copy:
            argv.append("--copy")
        argv.append("-y")
        immutable_argv = tuple(argv)
        environment = MappingProxyType({"DISABLE_TELEMETRY": "1"})
        display_command = f"DISABLE_TELEMETRY=1 {shlex.join(immutable_argv)}"
        details = MappingProxyType(
            {
                "installer": "npx skills",
                "installer_package": OFFICIAL_SKILLS_CLI_PACKAGE,
                "agent": agent.agent_id,
                "skill_source": self.skill_source,
                "skill_source_ref": self.source_ref,
                "scope": scope.value,
                "install_method": install_method.value,
                "network_required": True,
                "anonymous_telemetry": "disabled",
                "mutation_boundary": "external_unmanaged",
                "mutation_disclosure": (
                    "The external installer writes agent files outside UMEM snapshot, audit, "
                    "and rollback coverage."
                ),
                "exact_command": display_command,
            }
        )
        return OfficialSkillConnectionPlan(
            action=ConnectionPlanAction.external_action,
            channel="npx_skills",
            agent=agent,
            scope=scope,
            install_method=install_method,
            support_tier=DIRECTED_CLI_SUPPORT_TIER,
            ready=False,
            requires_confirmation=True,
            primary_prompt=f"Connect Universal Memory to {agent.display_name}?",
            argv=immutable_argv,
            environment=environment,
            display_command=display_command,
            technical_details=details,
            readiness_checks=READINESS_CHECKS,
        )

    def _fallback_plan(
        self,
        agent: OfficialSkillAgent,
        environment: OfficialSkillEnvironment,
        scope: SkillInstallScope,
        install_method: SkillInstallMethod,
        unavailable_reason: str,
    ) -> OfficialSkillConnectionPlan:
        fallbacks = _available_fallbacks(environment)
        action = (
            ConnectionPlanAction.managed_fallback if fallbacks else ConnectionPlanAction.pending
        )
        channel = fallbacks[0].channel if fallbacks else None
        details = MappingProxyType(
            {
                "agent": agent.agent_id,
                "scope": scope.value,
                "external_installer": "unavailable",
                "unavailable_reason": unavailable_reason,
                "fallback_channel": channel,
                "readiness_required": True,
            }
        )
        return OfficialSkillConnectionPlan(
            action=action,
            channel=channel,
            agent=agent,
            scope=scope,
            install_method=install_method,
            support_tier=DIRECTED_CLI_SUPPORT_TIER,
            ready=False,
            requires_confirmation=bool(fallbacks),
            primary_prompt=f"Connect Universal Memory to {agent.display_name}?",
            argv=(),
            environment=MappingProxyType({}),
            display_command="",
            technical_details=details,
            readiness_checks=READINESS_CHECKS,
            fallbacks=fallbacks,
            unavailable_reason=unavailable_reason,
        )


def _validate_agent(agent: OfficialSkillAgent) -> OfficialSkillAgent:
    if not isinstance(agent.agent_id, str) or not isinstance(agent.display_name, str):
        raise ValidationFailedError("Agent ID and display name must be strings.")
    agent_id = agent.agent_id.strip()
    display_name = agent.display_name.strip()
    if not _AGENT_ID_PATTERN.fullmatch(agent_id):
        raise ValidationFailedError(
            "External agent ID must use lowercase letters, numbers, and single hyphens."
        )
    if not display_name or any(
        unicodedata.category(character).startswith("C") for character in display_name
    ):
        raise ValidationFailedError("Agent display name must be a single non-empty line.")
    return OfficialSkillAgent(agent_id=agent_id, display_name=display_name)


def _validate_environment(environment: OfficialSkillEnvironment) -> OfficialSkillEnvironment:
    for field_name in OfficialSkillEnvironment.__dataclass_fields__:
        if type(getattr(environment, field_name)) is not bool:
            raise ValidationFailedError(
                f"Official skill environment capability {field_name} must be boolean."
            )
    return environment


def _validate_source_ref(source_ref: str) -> str:
    normalized = source_ref.strip() if isinstance(source_ref, str) else ""
    if not _SOURCE_REF_PATTERN.fullmatch(normalized):
        raise ValidationFailedError(
            "Official skill source ref must be a release tag or full immutable commit SHA."
        )
    return normalized


def _validate_scope(scope: SkillInstallScope) -> SkillInstallScope:
    try:
        return SkillInstallScope(scope)
    except ValueError as exc:
        raise ValidationFailedError(f"Unsupported skill installation scope: {scope}") from exc


def _validate_method(method: SkillInstallMethod) -> SkillInstallMethod:
    try:
        resolved = SkillInstallMethod(method)
    except ValueError as exc:
        raise ValidationFailedError(f"Unsupported skill installation method: {method}") from exc
    if resolved == SkillInstallMethod.symlink:
        raise ValidationFailedError(
            "The pinned external installer has no deterministic symlink mode; use copy."
        )
    return resolved


def _external_unavailability_reason(environment: OfficialSkillEnvironment) -> str | None:
    if not environment.node_available:
        return "node_unavailable"
    if not environment.npx_available:
        return "npx_unavailable"
    if not environment.network_available:
        return "network_unavailable"
    if not environment.agent_mapping_available:
        return "agent_mapping_unavailable"
    return None


def _available_fallbacks(
    environment: OfficialSkillEnvironment,
) -> tuple[ManagedSkillFallback, ...]:
    available: list[tuple[FallbackChannel, str, str]] = []
    if environment.agents_md_available:
        available.append(
            (
                "agents_md",
                OFFICIAL_AGENTS_BOOTSTRAP_PACKAGE_RELATIVE_PATH,
                "Install the compact project bootstrap through the managed instruction path.",
            )
        )
    if environment.umem_native_available:
        available.append(
            (
                "umem_native",
                OFFICIAL_SKILL_PACKAGE_RELATIVE_PATH,
                "Install the official skill through an available UMEM-managed target.",
            )
        )
    if environment.manual_copy_available:
        available.append(
            (
                "manual_copy",
                OFFICIAL_SKILL_PACKAGE_RELATIVE_PATH,
                "Copy the official skill to the target's project skill directory.",
            )
        )
    return tuple(
        ManagedSkillFallback(
            channel=channel,
            source_package=OFFICIAL_SKILL_PACKAGE,
            source_path=source_path,
            guidance=guidance,
            recommended=index == 0,
        )
        for index, (channel, source_path, guidance) in enumerate(available)
    )
