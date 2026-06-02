from datetime import UTC, datetime
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
    tier_1 = "tier_1"
    tier_2 = "tier_2"


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


class RuntimeAdapter(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="never")

    runtime_id: RuntimeId
    display_name: str
    support_tier: RuntimeSupportTier
    runtime_target: RuntimeTarget
    instruction_targets: list[InstructionTarget | RuntimeInstructionTarget] = Field(min_length=1)
    native_skill_targets: list[NativeSkillTarget] = Field(default_factory=list)
    mcp_config_method: str
    read_validation_method: str
    write_validation_method: str
    rollback_behavior: str
    mutation_behavior: str
    known_limitations: list[str] = Field(default_factory=list)
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


class RuntimeRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtimes: list[RuntimeAdapter] = Field(min_length=1)

    @property
    def runtime_ids(self) -> list[RuntimeId]:
        return [runtime.runtime_id for runtime in self.runtimes]

    def get(self, runtime_id: RuntimeId | str) -> RuntimeAdapter:
        resolved = RuntimeId(runtime_id)
        for runtime in self.runtimes:
            if runtime.runtime_id == resolved:
                return runtime
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
                RuntimeSupportTier.tier_1,
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
                known_limitations=["AGENTS.md e consumido como manifesto compartilhado."],
            ),
            _runtime(
                RuntimeId.opencode,
                "OpenCode",
                RuntimeSupportTier.tier_1,
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
                known_limitations=["Nao possui ownership de escrita de AGENTS.md."],
            ),
            _runtime(
                RuntimeId.codex,
                "Codex/OpenAI-class",
                RuntimeSupportTier.tier_1,
                global_config_path=".codex/config.toml",
                project_config_path=".codex/config.toml",
                instruction_targets=[_agents_md_target()],
                native_skill_targets=[],
                mcp_config_method="codex_toml_mcp_config",
                read_validation_method="agents_md_compact_validator",
                write_validation_method="safe_write_use_case",
                known_limitations=["Runtime owner unico do manifesto compartilhado AGENTS.md."],
            ),
            _runtime(
                RuntimeId.cursor,
                "Cursor",
                RuntimeSupportTier.tier_2,
                global_config_path=".cursor/mcp.json",
                project_config_path=".cursor/mcp.json",
                instruction_targets=[_cursor_rules_target()],
                native_skill_targets=[
                    _native_skill_target(".cursor/rules", "mdc-directory", "sync_directory")
                ],
                mcp_config_method="cursor_mcp_json_config",
                read_validation_method="cursor_rules_validator",
                write_validation_method="safe_write_use_case_rules_only",
                known_limitations=["Suporte Tier 2: validacao menos completa que Tier 1."],
            ),
            _runtime(
                RuntimeId.antigravity,
                "Antigravity",
                RuntimeSupportTier.tier_2,
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
                known_limitations=["Suporte Tier 2: contrato sujeito a mudancas do runtime."],
            ),
        ]
    )


def _runtime(  # noqa: PLR0913
    runtime_id: RuntimeId,
    display_name: str,
    support_tier: RuntimeSupportTier,
    *,
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
