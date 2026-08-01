from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from universal_memory.domain.entities.instruction_target import (
    InstructionClassification,
    InstructionTarget,
    InstructionTargetOwnership,
    InstructionTargetType,
)


class RuntimeId(StrEnum):
    claude_code = "claude_code"
    opencode = "opencode"
    codex = "codex"
    cursor = "cursor"
    antigravity = "antigravity"


class RuntimeSupportTier(StrEnum):
    tier_1_native_managed = "tier_1_native_managed"
    tier_2_directed_cli = "tier_2_directed_cli"
    tier_3_unmanaged_mcp = "tier_3_unmanaged_mcp"


class RuntimeInstructionChannel(StrEnum):
    agents_md = "agents_md"
    native_file = "native_file"
    agent_skill = "agent_skill"


class RuntimeCliAccess(StrEnum):
    required = "required"
    optional = "optional"
    unavailable = "unavailable"


class RuntimeSkillSupport(StrEnum):
    native = "native"
    portable = "portable"
    equivalent_rules = "equivalent_rules"
    unsupported = "unsupported"


class RuntimeSkillInstaller(StrEnum):
    umem_native = "umem_native"
    npx_skills = "npx_skills"
    manual = "manual"
    unavailable = "unavailable"


class RuntimeMcpMode(StrEnum):
    managed = "managed"
    optional = "optional"
    unmanaged = "unmanaged"
    unavailable = "unavailable"


class RuntimeValidationLevel(StrEnum):
    native_context_read = "native_context_read"
    directed_cli_context_read = "directed_cli_context_read"
    mcp_availability = "mcp_availability"


class RuntimeSupportProfileId(StrEnum):
    directed_cli = "directed_cli"
    unmanaged_mcp = "unmanaged_mcp"


class RuntimeDetectionSignalKind(StrEnum):
    project_path = "project_path"
    global_path = "global_path"
    executable = "executable"


class RuntimeDetectionSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: RuntimeDetectionSignalKind
    value: str

    @model_validator(mode="after")
    def validate_signal_value(self) -> Self:
        if self.kind == RuntimeDetectionSignalKind.executable:
            if (
                self.value.strip() != self.value
                or self.value == ""
                or any(character.isspace() for character in self.value)
                or "/" in self.value
                or "\\" in self.value
            ):
                raise ValueError("executable detection signal must be a simple command name")
            return self
        if "\\" in self.value:
            raise ValueError("detection path must not contain backslashes")
        path = PurePosixPath(self.value)
        if (
            self.value == ""
            or not path.parts
            or path == PurePosixPath(".")
            or path.is_absolute()
            or ".." in path.parts
        ):
            raise ValueError("detection path must be a safe relative path")
        return self


class Tier1SelectionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluated_on: date
    market_relevance: str
    demand: str
    internal_use: str
    strategic_value: str
    validation_feasibility: str
    maintenance_capacity: str

    @field_validator(
        "market_relevance",
        "demand",
        "internal_use",
        "strategic_value",
        "validation_feasibility",
        "maintenance_capacity",
    )
    @classmethod
    def validate_non_blank_evidence(cls, value: str, info) -> str:
        stripped = value.strip()
        if stripped == "":
            raise ValueError(f"{info.field_name} must not be blank")
        return stripped


class RuntimeSupportCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    support_tier: RuntimeSupportTier
    managed_by_umem: bool
    instruction_channels: list[RuntimeInstructionChannel] = Field(default_factory=list)
    cli_access: RuntimeCliAccess
    skill_support: RuntimeSkillSupport
    skill_installer: RuntimeSkillInstaller
    mcp_mode: RuntimeMcpMode
    validation_level: RuntimeValidationLevel
    selection_evidence: Tier1SelectionEvidence | None = None
    known_limitations: list[str] = Field(default_factory=list)

    @field_validator("instruction_channels")
    @classmethod
    def validate_instruction_channels_unique(
        cls, value: list[RuntimeInstructionChannel]
    ) -> list[RuntimeInstructionChannel]:
        if len(value) != len(set(value)):
            raise ValueError("instruction_channels must not contain duplicates")
        return value

    @field_validator("known_limitations")
    @classmethod
    def validate_known_limitations(cls, value: list[str]) -> list[str]:
        normalized = [limitation.strip() for limitation in value]
        if any(limitation == "" for limitation in normalized):
            raise ValueError("known_limitations must not contain blank values")
        return normalized

    @model_validator(mode="after")
    def validate_tier_capability_contract(self) -> Self:
        self._validate_skill_contract()
        if self.support_tier == RuntimeSupportTier.tier_1_native_managed:
            self._validate_tier_1_contract()
        elif self.support_tier == RuntimeSupportTier.tier_2_directed_cli:
            self._validate_non_native_contract()
            self._validate_tier_2_contract()
        else:
            self._validate_non_native_contract()
            self._validate_tier_3_contract()
        return self

    def _validate_skill_contract(self) -> None:
        if self.skill_support == RuntimeSkillSupport.unsupported:
            if self.skill_installer != RuntimeSkillInstaller.unavailable:
                raise ValueError("unsupported skills require an unavailable installer")
            if RuntimeInstructionChannel.agent_skill in self.instruction_channels:
                raise ValueError("Agent Skill instructions require skill support")
        elif self.skill_installer == RuntimeSkillInstaller.unavailable:
            raise ValueError("supported skills require an available installer")

        has_agent_skill = RuntimeInstructionChannel.agent_skill in self.instruction_channels
        has_native_file = RuntimeInstructionChannel.native_file in self.instruction_channels
        if has_agent_skill and self.skill_support not in {
            RuntimeSkillSupport.native,
            RuntimeSkillSupport.portable,
        }:
            raise ValueError("Agent Skill instructions require native or portable skill support")
        if self.skill_support == RuntimeSkillSupport.portable and not has_agent_skill:
            raise ValueError("portable skills require the Agent Skill instruction channel")
        if self.skill_support == RuntimeSkillSupport.equivalent_rules:
            if not has_native_file or has_agent_skill:
                raise ValueError(
                    "equivalent-rule skills require native-file instructions "
                    "without an Agent Skill channel"
                )
            if self.skill_installer not in {
                RuntimeSkillInstaller.umem_native,
                RuntimeSkillInstaller.manual,
            }:
                raise ValueError(
                    "equivalent-rule skills require the UMEM native or manual installer"
                )
        if self.skill_installer == RuntimeSkillInstaller.npx_skills and (
            self.skill_support != RuntimeSkillSupport.portable or not has_agent_skill
        ):
            raise ValueError("npx skills requires portable Agent Skill support")

    def _validate_tier_1_contract(self) -> None:
        if not self.managed_by_umem:
            raise ValueError("Tier 1 must be managed by UMEM")
        if self.selection_evidence is None:
            raise ValueError("Tier 1 requires selection_evidence")
        if self.validation_level != RuntimeValidationLevel.native_context_read:
            raise ValueError("Tier 1 requires native context-read validation")
        if self.cli_access == RuntimeCliAccess.unavailable:
            raise ValueError("Tier 1 requires supported CLI access")

    def _validate_non_native_contract(self) -> None:
        if self.selection_evidence is not None:
            raise ValueError("selection_evidence is reserved for Tier 1")
        if self.managed_by_umem:
            raise ValueError("Only Tier 1 can be managed by UMEM")

    def _validate_tier_2_contract(self) -> None:
        if self.cli_access != RuntimeCliAccess.required:
            raise ValueError("Tier 2 requires CLI access")
        if self.validation_level != RuntimeValidationLevel.directed_cli_context_read:
            raise ValueError("Tier 2 requires directed CLI context-read validation")
        has_portable_channel = bool(
            {
                RuntimeInstructionChannel.agents_md,
                RuntimeInstructionChannel.agent_skill,
            }.intersection(self.instruction_channels)
        )
        has_equivalent_contract = (
            RuntimeInstructionChannel.native_file in self.instruction_channels
            and self.skill_support == RuntimeSkillSupport.equivalent_rules
            and self.skill_installer
            in {RuntimeSkillInstaller.umem_native, RuntimeSkillInstaller.manual}
        )
        if not has_portable_channel and not has_equivalent_contract:
            raise ValueError(
                "Tier 2 requires AGENTS.md, Agent Skill, or an explicit "
                "equivalent-rule instruction contract"
            )

    def _validate_tier_3_contract(self) -> None:
        if self.mcp_mode != RuntimeMcpMode.unmanaged:
            raise ValueError("Tier 3 requires unmanaged MCP mode")
        if self.validation_level != RuntimeValidationLevel.mcp_availability:
            raise ValueError("Tier 3 validation must stop at MCP availability")


class RuntimeTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    global_config_path: str
    project_config_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("global_config_path", "project_config_path")
    @classmethod
    def validate_safe_config_path(cls, value: str) -> str:
        if "\\" in value:
            raise ValueError("config paths must not contain backslashes")
        path = PurePosixPath(value)
        if value == "" or path.is_absolute() or ".." in path.parts:
            raise ValueError("config paths must be safe relative paths")
        return value


class NativeSkillTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    format: str
    install_strategy: str
    drift_strategy: str
    rollback_policy: str
    disable_policy: str = "remove"

    @field_validator("relative_path")
    @classmethod
    def validate_safe_relative_path(cls, value: str) -> str:
        if "\\" in value:
            raise ValueError("relative_path must not contain backslashes")
        path = PurePosixPath(value)
        if value == "" or path.is_absolute() or ".." in path.parts:
            raise ValueError("relative_path must be a safe relative path")
        return value

    @field_validator(
        "format", "install_strategy", "drift_strategy", "rollback_policy", "disable_policy"
    )
    @classmethod
    def validate_non_blank_contract_field(cls, value: str, info) -> str:
        stripped = value.strip()
        if stripped == "":
            raise ValueError(f"{info.field_name} must not be blank")
        return stripped


class RuntimeInstructionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: InstructionTargetType | str
    relative_path: str
    ownership: InstructionTargetOwnership
    supported_classifications: list[InstructionClassification] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("relative_path")
    @classmethod
    def validate_safe_relative_path(cls, value: str) -> str:
        if "\\" in value:
            raise ValueError("relative_path must not contain backslashes")
        path = PurePosixPath(value)
        if value == "" or path.is_absolute() or ".." in path.parts:
            raise ValueError("relative_path must be a safe relative path")
        return value


class RuntimeAdapter(RuntimeSupportCapabilities):
    model_config = ConfigDict(extra="forbid", revalidate_instances="never")

    runtime_id: RuntimeId
    display_name: str
    detection_signals: list[RuntimeDetectionSignal] = Field(min_length=1)
    runtime_target: RuntimeTarget
    instruction_targets: list[InstructionTarget | RuntimeInstructionTarget] = Field(min_length=1)
    native_skill_targets: list[NativeSkillTarget] = Field(default_factory=list)
    mcp_config_method: str
    read_validation_method: str
    write_validation_method: str
    rollback_behavior: str
    mutation_behavior: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "display_name",
        "mcp_config_method",
        "read_validation_method",
        "write_validation_method",
        "rollback_behavior",
        "mutation_behavior",
    )
    @classmethod
    def validate_non_blank_runtime_field(cls, value: str, info) -> str:
        stripped = value.strip()
        if stripped == "":
            raise ValueError(f"{info.field_name} must not be blank")
        return stripped

    @field_validator("instruction_targets")
    @classmethod
    def validate_instruction_targets_unique(
        cls, value: list[InstructionTarget | RuntimeInstructionTarget]
    ) -> list[InstructionTarget | RuntimeInstructionTarget]:
        names = [target.name for target in value]
        if len(names) != len(set(names)):
            raise ValueError("instruction_targets must not contain duplicate targets")
        return value

    @property
    def supports_native_skill_sync(self) -> bool:
        return (
            bool(self.native_skill_targets)
            and self.skill_support
            in {
                RuntimeSkillSupport.native,
                RuntimeSkillSupport.equivalent_rules,
            }
            and self.skill_installer == RuntimeSkillInstaller.umem_native
        )

    @model_validator(mode="after")
    def validate_native_skill_target_capability(self) -> Self:
        if self.native_skill_targets and not self.supports_native_skill_sync:
            raise ValueError(
                "native_skill_targets require native or equivalent-rules support "
                "with the UMEM native installer"
            )
        if (
            not self.native_skill_targets
            and self.skill_installer == RuntimeSkillInstaller.umem_native
        ):
            raise ValueError("UMEM native skill installer requires native_skill_targets")
        return self


class RuntimeSupportProfile(RuntimeSupportCapabilities):
    model_config = ConfigDict(extra="forbid")

    profile_id: RuntimeSupportProfileId
    display_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        stripped = value.strip()
        if stripped == "":
            raise ValueError("display_name must not be blank")
        return stripped

    @model_validator(mode="after")
    def validate_profile_contract(self) -> Self:
        if self.profile_id == RuntimeSupportProfileId.directed_cli:
            portable_channels = {
                RuntimeInstructionChannel.agents_md,
                RuntimeInstructionChannel.agent_skill,
            }
            if self.support_tier != RuntimeSupportTier.tier_2_directed_cli:
                raise ValueError("Directed CLI profile requires the Tier 2 support tier")
            if not portable_channels.intersection(self.instruction_channels):
                raise ValueError("Tier 2 requires AGENTS.md or Agent Skill instructions")
            if self.skill_support == RuntimeSkillSupport.portable and self.skill_installer not in {
                RuntimeSkillInstaller.npx_skills,
                RuntimeSkillInstaller.manual,
            }:
                raise ValueError("portable skills require an external or manual installer")
        elif self.support_tier != RuntimeSupportTier.tier_3_unmanaged_mcp:
            raise ValueError("Unmanaged MCP profile requires the Tier 3 support tier")
        return self


class RuntimeRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtimes: list[RuntimeAdapter] = Field(min_length=1)
    support_profiles: list[RuntimeSupportProfile] = Field(default_factory=list)

    @property
    def runtime_ids(self) -> list[RuntimeId]:
        return [runtime.runtime_id for runtime in self.runtimes]

    def get(self, runtime_id: RuntimeId | str) -> RuntimeAdapter:
        resolved = RuntimeId(runtime_id)
        for runtime in self.runtimes:
            if runtime.runtime_id == resolved:
                return runtime
        raise KeyError(resolved.value)

    def get_profile(self, profile_id: RuntimeSupportProfileId | str) -> RuntimeSupportProfile:
        resolved = RuntimeSupportProfileId(profile_id)
        for profile in self.support_profiles:
            if profile.profile_id == resolved:
                return profile
        raise KeyError(resolved.value)

    def single_writer_runtime_ids(self, target_type: InstructionTargetType) -> list[RuntimeId]:
        return [
            runtime.runtime_id
            for runtime in self.runtimes
            for target in runtime.instruction_targets
            if target.name == target_type
            and target.ownership == InstructionTargetOwnership.single_writer
        ]

    @model_validator(mode="after")
    def validate_registry_contract(self) -> Self:
        if len(self.runtime_ids) != len(set(self.runtime_ids)):
            raise ValueError("runtime_ids must be unique")
        profile_ids = [profile.profile_id for profile in self.support_profiles]
        if len(profile_ids) != len(set(profile_ids)):
            raise ValueError("support profile IDs must be unique")
        agents_writers = self.single_writer_runtime_ids(InstructionTargetType.agents_md)
        if len(agents_writers) != 1:
            raise ValueError("agents_md must have exactly one writer")
        return self


def default_runtime_registry() -> RuntimeRegistry:
    return RuntimeRegistry(
        runtimes=[
            _runtime(
                RuntimeId.claude_code,
                "Claude Code",
                RuntimeSupportTier.tier_1_native_managed,
                managed_by_umem=True,
                instruction_channels=[
                    RuntimeInstructionChannel.native_file,
                    RuntimeInstructionChannel.agent_skill,
                ],
                cli_access=RuntimeCliAccess.required,
                skill_support=RuntimeSkillSupport.native,
                skill_installer=RuntimeSkillInstaller.umem_native,
                mcp_mode=RuntimeMcpMode.managed,
                validation_level=RuntimeValidationLevel.native_context_read,
                selection_evidence=_tier_1_evidence(
                    market_relevance=(
                        "Established coding-agent ecosystem with stable project surfaces."
                    ),
                    demand="Included in the maintained MVP support set based on user demand.",
                    internal_use="Used in UMEM development and integration verification.",
                    strategic_value="Provides a first-class native-instruction integration path.",
                ),
                detection_signals=_detection_signals(".claude", "claude"),
                global_config_path=".claude/settings.json",
                project_config_path=".claude/settings.json",
                instruction_targets=[_claude_md_target()],
                native_skill_targets=[
                    _native_skill_target(
                        ".claude/skills",
                        "markdown-directory",
                        "sync_directory",
                    )
                ],
                mcp_config_method="claude_code_mcp_config",
                read_validation_method="claude_md_delta_validator",
                write_validation_method="safe_write_use_case_delta_only",
                known_limitations=["AGENTS.md is consumed as a shared manifest."],
            ),
            _runtime(
                RuntimeId.opencode,
                "OpenCode",
                RuntimeSupportTier.tier_1_native_managed,
                managed_by_umem=True,
                instruction_channels=[
                    RuntimeInstructionChannel.agents_md,
                    RuntimeInstructionChannel.agent_skill,
                ],
                cli_access=RuntimeCliAccess.required,
                skill_support=RuntimeSkillSupport.native,
                skill_installer=RuntimeSkillInstaller.umem_native,
                mcp_mode=RuntimeMcpMode.managed,
                validation_level=RuntimeValidationLevel.native_context_read,
                selection_evidence=_tier_1_evidence(
                    market_relevance=(
                        "Relevant open coding-agent runtime with stable project configuration."
                    ),
                    demand="Included in the maintained MVP support set based on ecosystem demand.",
                    internal_use="Covered by UMEM integration and regression workflows.",
                    strategic_value="Extends native support to an open agent runtime.",
                ),
                detection_signals=_detection_signals(".opencode", "opencode"),
                global_config_path=".config/opencode/opencode.jsonc",
                project_config_path=".opencode/opencode.jsonc",
                instruction_targets=[_agents_md_reader_target()],
                native_skill_targets=[
                    _native_skill_target(
                        ".opencode/skills",
                        "markdown-directory",
                        "sync_directory",
                    )
                ],
                mcp_config_method="opencode_jsonc_mcp_config",
                read_validation_method="agents_md_reference_validator",
                write_validation_method="reference_only_no_agents_md_write",
                known_limitations=["Does not own writes to AGENTS.md."],
            ),
            _runtime(
                RuntimeId.codex,
                "Codex/OpenAI-class",
                RuntimeSupportTier.tier_1_native_managed,
                managed_by_umem=True,
                instruction_channels=[
                    RuntimeInstructionChannel.agents_md,
                    RuntimeInstructionChannel.agent_skill,
                ],
                cli_access=RuntimeCliAccess.required,
                skill_support=RuntimeSkillSupport.native,
                skill_installer=RuntimeSkillInstaller.umem_native,
                mcp_mode=RuntimeMcpMode.managed,
                validation_level=RuntimeValidationLevel.native_context_read,
                selection_evidence=_tier_1_evidence(
                    market_relevance=(
                        "Core OpenAI coding-agent runtime with stable project instructions."
                    ),
                    demand="Included in the maintained MVP support set based on user demand.",
                    internal_use="Used as a primary runtime by UMEM maintainers.",
                    strategic_value="Owns the canonical shared AGENTS.md integration path.",
                ),
                detection_signals=_detection_signals(".codex", "codex"),
                global_config_path=".codex/config.toml",
                project_config_path=".codex/config.toml",
                instruction_targets=[_agents_md_target()],
                native_skill_targets=[
                    _native_skill_target(
                        ".agents/skills",
                        "markdown-directory",
                        "sync_directory",
                    )
                ],
                mcp_config_method="codex_toml_mcp_config",
                read_validation_method="agents_md_compact_validator",
                write_validation_method="safe_write_use_case",
                known_limitations=["Sole runtime owner of the shared AGENTS.md manifest."],
            ),
            _runtime(
                RuntimeId.cursor,
                "Cursor",
                RuntimeSupportTier.tier_2_directed_cli,
                managed_by_umem=False,
                instruction_channels=[
                    RuntimeInstructionChannel.native_file,
                ],
                cli_access=RuntimeCliAccess.required,
                skill_support=RuntimeSkillSupport.equivalent_rules,
                skill_installer=RuntimeSkillInstaller.umem_native,
                mcp_mode=RuntimeMcpMode.optional,
                validation_level=RuntimeValidationLevel.directed_cli_context_read,
                selection_evidence=None,
                detection_signals=_detection_signals(".cursor", "cursor"),
                global_config_path=".cursor/mcp.json",
                project_config_path=".cursor/mcp.json",
                instruction_targets=[_cursor_rules_target()],
                native_skill_targets=[
                    _native_skill_target(".cursor/rules", "mdc-directory", "sync_directory")
                ],
                mcp_config_method="cursor_mcp_json_config",
                read_validation_method="cursor_rules_validator",
                write_validation_method="safe_write_use_case_rules_only",
                known_limitations=[
                    "Portable contract does not guarantee every host-specific surface."
                ],
            ),
            _runtime(
                RuntimeId.antigravity,
                "Antigravity",
                RuntimeSupportTier.tier_2_directed_cli,
                managed_by_umem=False,
                instruction_channels=[
                    RuntimeInstructionChannel.native_file,
                ],
                cli_access=RuntimeCliAccess.required,
                skill_support=RuntimeSkillSupport.equivalent_rules,
                skill_installer=RuntimeSkillInstaller.umem_native,
                mcp_mode=RuntimeMcpMode.optional,
                validation_level=RuntimeValidationLevel.directed_cli_context_read,
                selection_evidence=None,
                detection_signals=_detection_signals(".antigravity", "antigravity"),
                global_config_path=".antigravity/config.json",
                project_config_path=".antigravity/config.json",
                instruction_targets=[_antigravity_rules_target()],
                native_skill_targets=[
                    _native_skill_target(
                        ".antigravity/rules",
                        "markdown-directory",
                        "sync_directory",
                    )
                ],
                mcp_config_method="antigravity_json_mcp_config",
                read_validation_method="antigravity_rules_validator",
                write_validation_method="safe_write_use_case_rules_only",
                known_limitations=[
                    "Portable contract is subject to changes in the external runtime."
                ],
            ),
        ],
        support_profiles=[
            RuntimeSupportProfile(
                profile_id=RuntimeSupportProfileId.directed_cli,
                display_name="Directed CLI",
                support_tier=RuntimeSupportTier.tier_2_directed_cli,
                managed_by_umem=False,
                instruction_channels=[
                    RuntimeInstructionChannel.agents_md,
                    RuntimeInstructionChannel.agent_skill,
                ],
                cli_access=RuntimeCliAccess.required,
                skill_support=RuntimeSkillSupport.portable,
                skill_installer=RuntimeSkillInstaller.npx_skills,
                mcp_mode=RuntimeMcpMode.optional,
                validation_level=RuntimeValidationLevel.directed_cli_context_read,
                known_limitations=[
                    "Host-specific behavior is outside the portable support contract."
                ],
            ),
            RuntimeSupportProfile(
                profile_id=RuntimeSupportProfileId.unmanaged_mcp,
                display_name="Unmanaged MCP",
                support_tier=RuntimeSupportTier.tier_3_unmanaged_mcp,
                managed_by_umem=False,
                instruction_channels=[],
                cli_access=RuntimeCliAccess.optional,
                skill_support=RuntimeSkillSupport.unsupported,
                skill_installer=RuntimeSkillInstaller.unavailable,
                mcp_mode=RuntimeMcpMode.unmanaged,
                validation_level=RuntimeValidationLevel.mcp_availability,
                known_limitations=[
                    "Only MCP availability is validated; agent behavior is unmanaged."
                ],
            ),
        ],
    )


def _runtime(  # noqa: PLR0913
    runtime_id: RuntimeId,
    display_name: str,
    support_tier: RuntimeSupportTier,
    *,
    managed_by_umem: bool,
    instruction_channels: list[RuntimeInstructionChannel],
    cli_access: RuntimeCliAccess,
    skill_support: RuntimeSkillSupport,
    skill_installer: RuntimeSkillInstaller,
    mcp_mode: RuntimeMcpMode,
    validation_level: RuntimeValidationLevel,
    selection_evidence: Tier1SelectionEvidence | None,
    detection_signals: list[RuntimeDetectionSignal],
    global_config_path: str,
    project_config_path: str,
    instruction_targets: list[InstructionTarget | RuntimeInstructionTarget],
    native_skill_targets: list[NativeSkillTarget],
    mcp_config_method: str,
    read_validation_method: str,
    write_validation_method: str,
    known_limitations: list[str],
) -> RuntimeAdapter:
    return RuntimeAdapter(
        runtime_id=runtime_id,
        display_name=display_name,
        support_tier=support_tier,
        managed_by_umem=managed_by_umem,
        instruction_channels=instruction_channels,
        cli_access=cli_access,
        skill_support=skill_support,
        skill_installer=skill_installer,
        mcp_mode=mcp_mode,
        validation_level=validation_level,
        selection_evidence=selection_evidence,
        detection_signals=detection_signals,
        runtime_target=RuntimeTarget(
            global_config_path=global_config_path,
            project_config_path=project_config_path,
        ),
        instruction_targets=instruction_targets,
        native_skill_targets=native_skill_targets,
        mcp_config_method=mcp_config_method,
        read_validation_method=read_validation_method,
        write_validation_method=write_validation_method,
        rollback_behavior="snapshot_rollback",
        mutation_behavior="safe_write_with_audit_and_snapshot",
        known_limitations=known_limitations,
    )


def _detection_signals(project_path: str, executable: str) -> list[RuntimeDetectionSignal]:
    return [
        RuntimeDetectionSignal(
            kind=RuntimeDetectionSignalKind.project_path,
            value=project_path,
        ),
        RuntimeDetectionSignal(
            kind=RuntimeDetectionSignalKind.executable,
            value=executable,
        ),
    ]


def _tier_1_evidence(
    *,
    market_relevance: str,
    demand: str,
    internal_use: str,
    strategic_value: str,
) -> Tier1SelectionEvidence:
    return Tier1SelectionEvidence(
        evaluated_on=date(2026, 7, 31),
        market_relevance=market_relevance,
        demand=demand,
        internal_use=internal_use,
        strategic_value=strategic_value,
        validation_feasibility=(
            "Native setup, sync, and context-read checks are repeatable in the test suite."
        ),
        maintenance_capacity="Owned by UMEM maintainers for the current release.",
    )


def _agents_md_target() -> InstructionTarget:
    return InstructionTarget(
        id=str(uuid4()),
        created_at=_now(),
        updated_at=_now(),
        name=InstructionTargetType.agents_md,
        relative_path="AGENTS.md",
        ownership=InstructionTargetOwnership.single_writer,
        supported_classifications=[
            InstructionClassification.shared_policy,
            InstructionClassification.provider_delta,
            InstructionClassification.scoped_rule,
            InstructionClassification.canonical_doc,
        ],
    )


def _agents_md_reader_target() -> RuntimeInstructionTarget:
    return RuntimeInstructionTarget(
        name=InstructionTargetType.agents_md,
        relative_path="AGENTS.md",
        ownership=InstructionTargetOwnership.delta_consumer,
        supported_classifications=[InstructionClassification.shared_policy],
        metadata={"access": "read_reference_only"},
    )


def _claude_md_target() -> InstructionTarget:
    return InstructionTarget(
        id=str(uuid4()),
        created_at=_now(),
        updated_at=_now(),
        name=InstructionTargetType.claude_md,
        relative_path="CLAUDE.md",
        ownership=InstructionTargetOwnership.delta_consumer,
        supported_classifications=[
            InstructionClassification.provider_delta,
            InstructionClassification.scoped_rule,
        ],
    )


def _cursor_rules_target() -> RuntimeInstructionTarget:
    return _runtime_instruction_target("cursor_rules", ".cursor/rules/universal-memory.mdc")


def _antigravity_rules_target() -> RuntimeInstructionTarget:
    return _runtime_instruction_target(
        "antigravity_rules", ".antigravity/rules/universal-memory.md"
    )


def _runtime_instruction_target(name: str, relative_path: str) -> RuntimeInstructionTarget:
    return RuntimeInstructionTarget(
        name=name,
        relative_path=relative_path,
        ownership=InstructionTargetOwnership.delta_consumer,
        supported_classifications=[
            InstructionClassification.provider_delta,
            InstructionClassification.scoped_rule,
        ],
        metadata={},
    )


def _native_skill_target(
    relative_path: str,
    format: str,
    install_strategy: str,
) -> NativeSkillTarget:
    return NativeSkillTarget(
        relative_path=relative_path,
        format=format,
        install_strategy=install_strategy,
        drift_strategy="compare_manifest_hash",
        rollback_policy="snapshot_restore",
    )


def _now() -> datetime:
    return datetime.now(UTC)
