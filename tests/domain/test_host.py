import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from universal_memory.domain import entities
from universal_memory.domain.entities.host import Host, HostName
from universal_memory.domain.entities.instruction_target import (
    InstructionClassification,
    InstructionTarget,
    InstructionTargetOwnership,
    InstructionTargetType,
)


def base_entity_data() -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "schema_version": 1,
        "id": str(uuid.uuid4()),
        "created_at": now,
        "updated_at": now,
    }


def agents_md_target_data() -> dict[str, Any]:
    return {
        **base_entity_data(),
        "name": InstructionTargetType.agents_md,
        "relative_path": "AGENTS.md",
        "ownership": InstructionTargetOwnership.single_writer,
        "supported_classifications": [
            InstructionClassification.shared_policy,
            InstructionClassification.canonical_doc,
        ],
        "metadata": {"description": "Shared agent instruction manifest"},
    }


def claude_md_target_data() -> dict[str, Any]:
    return {
        **base_entity_data(),
        "name": InstructionTargetType.claude_md,
        "relative_path": "CLAUDE.md",
        "ownership": InstructionTargetOwnership.delta_consumer,
        "supported_classifications": [InstructionClassification.provider_delta],
        "metadata": {"description": "Claude-specific instruction deltas"},
    }


def codex_host_data() -> dict[str, Any]:
    return {
        **base_entity_data(),
        "name": HostName.codex,
        "supported_targets": [InstructionTargetType.agents_md],
        "mcp_config_method": "agents_md_manifest",
        "read_validation_method": "validate_agents_md_readable",
        "write_validation_method": "single_writer_target_only",
        "rollback_behavior": "restore_last_instruction_snapshot",
        "audit_event_type": "instruction_target_mutation",
        "metadata": {"shared_manifest": True},
    }


def claude_code_host_data() -> dict[str, Any]:
    return {
        **base_entity_data(),
        "name": HostName.claude_code,
        "supported_targets": [InstructionTargetType.agents_md, InstructionTargetType.claude_md],
        "mcp_config_method": "claude_code_mcp_config",
        "read_validation_method": "validate_claude_reads_instruction_files",
        "write_validation_method": "validate_provider_delta_only",
        "rollback_behavior": "restore_last_instruction_snapshot",
        "audit_event_type": "instruction_target_mutation",
        "metadata": {"provider_delta_target": "CLAUDE.md"},
    }


def test_instruction_target_valid_creation_for_agents_md() -> None:
    target = InstructionTarget.model_validate(agents_md_target_data())

    assert target.name == InstructionTargetType.agents_md
    assert target.relative_path == "AGENTS.md"
    assert target.ownership == InstructionTargetOwnership.single_writer
    assert InstructionClassification.shared_policy in target.supported_classifications
    assert target.metadata == {"description": "Shared agent instruction manifest"}


def test_instruction_target_valid_creation_for_provider_delta() -> None:
    target = InstructionTarget.model_validate(claude_md_target_data())

    assert target.name == InstructionTargetType.claude_md
    assert target.relative_path == "CLAUDE.md"
    assert target.ownership == InstructionTargetOwnership.delta_consumer
    assert target.supported_classifications == [InstructionClassification.provider_delta]


def test_instruction_target_rejects_invalid_uuid() -> None:
    data = agents_md_target_data() | {"id": "not-a-uuid"}

    with pytest.raises(ValidationError):
        InstructionTarget.model_validate(data)


def test_instruction_target_rejects_non_v4_uuid() -> None:
    data = agents_md_target_data() | {"id": str(uuid.uuid1())}

    with pytest.raises(ValidationError):
        InstructionTarget.model_validate(data)


def test_instruction_target_rejects_non_utc_timestamps() -> None:
    data = agents_md_target_data() | {"created_at": datetime.now()}

    with pytest.raises(ValidationError):
        InstructionTarget.model_validate(data)


def test_instruction_target_rejects_unsafe_relative_path() -> None:
    data = agents_md_target_data() | {"relative_path": "../AGENTS.md"}

    with pytest.raises(ValidationError):
        InstructionTarget.model_validate(data)


def test_agents_md_target_enforces_single_writer_ownership() -> None:
    data = agents_md_target_data() | {"ownership": InstructionTargetOwnership.delta_consumer}

    with pytest.raises(ValidationError):
        InstructionTarget.model_validate(data)


def test_claude_md_target_enforces_provider_delta_without_shared_manifest_copy() -> None:
    data = claude_md_target_data() | {
        "ownership": InstructionTargetOwnership.single_writer,
        "supported_classifications": [
            InstructionClassification.shared_policy,
            InstructionClassification.provider_delta,
        ],
    }

    with pytest.raises(ValidationError):
        InstructionTarget.model_validate(data)


def test_host_valid_creation_for_codex() -> None:
    host = Host.model_validate(codex_host_data())

    assert host.name == HostName.codex
    assert host.supported_targets == [InstructionTargetType.agents_md]
    assert host.mcp_config_method == "agents_md_manifest"
    assert host.audit_event_type == "instruction_target_mutation"


def test_host_valid_creation_for_claude_code() -> None:
    host = Host.model_validate(claude_code_host_data())

    assert host.name == HostName.claude_code
    assert host.supported_targets == [
        InstructionTargetType.agents_md,
        InstructionTargetType.claude_md,
    ]
    assert host.write_validation_method == "validate_provider_delta_only"


def test_host_rejects_invalid_uuid() -> None:
    data = codex_host_data() | {"id": "not-a-uuid"}

    with pytest.raises(ValidationError):
        Host.model_validate(data)


def test_host_rejects_non_v4_uuid() -> None:
    data = codex_host_data() | {"id": str(uuid.uuid1())}

    with pytest.raises(ValidationError):
        Host.model_validate(data)


def test_host_rejects_non_utc_timestamps() -> None:
    data = codex_host_data() | {"updated_at": datetime.now()}

    with pytest.raises(ValidationError):
        Host.model_validate(data)


def test_host_rejects_unsupported_mvp_host_name() -> None:
    data = codex_host_data() | {"name": "future_host"}

    with pytest.raises(ValidationError):
        Host.model_validate(data)


def test_host_rejects_empty_supported_targets() -> None:
    data = codex_host_data() | {"supported_targets": []}

    with pytest.raises(ValidationError):
        Host.model_validate(data)


def test_host_rejects_blank_operational_methods() -> None:
    data = codex_host_data() | {"read_validation_method": " "}

    with pytest.raises(ValidationError):
        Host.model_validate(data)


def test_host_strips_operational_method_whitespace() -> None:
    data = codex_host_data() | {"read_validation_method": "  validate_agents_md_readable  "}
    host = Host.model_validate(data)
    assert host.read_validation_method == "validate_agents_md_readable"


def test_host_rejects_duplicate_supported_targets() -> None:
    data = codex_host_data() | {
        "supported_targets": [
            InstructionTargetType.agents_md,
            InstructionTargetType.agents_md,
        ]
    }
    with pytest.raises(
        ValidationError, match="supported_targets must not contain duplicate targets"
    ):
        Host.model_validate(data)


def test_instruction_target_rejects_duplicate_classifications() -> None:
    data = agents_md_target_data() | {
        "supported_classifications": [
            InstructionClassification.shared_policy,
            InstructionClassification.shared_policy,
        ]
    }
    with pytest.raises(
        ValidationError,
        match="supported_classifications must not contain duplicate classifications",
    ):
        InstructionTarget.model_validate(data)


def test_instruction_target_rejects_backslashes_relative_path() -> None:
    data = agents_md_target_data() | {"relative_path": "foo\\AGENTS.md"}
    with pytest.raises(ValidationError, match="relative_path must not contain backslashes"):
        InstructionTarget.model_validate(data)


def test_host_provides_granular_error_messages_for_blank_methods() -> None:
    data = codex_host_data() | {"read_validation_method": "   "}
    with pytest.raises(ValidationError, match="read_validation_method must not be blank"):
        Host.model_validate(data)


def test_host_and_instruction_target_exports_are_public() -> None:
    assert entities.Host is Host
    assert entities.HostName is HostName
    assert entities.InstructionTarget is InstructionTarget
    assert entities.InstructionTargetType is InstructionTargetType
    assert entities.InstructionClassification is InstructionClassification
    assert entities.InstructionTargetOwnership is InstructionTargetOwnership
    assert "Host" in entities.__all__
    assert "InstructionTarget" in entities.__all__
