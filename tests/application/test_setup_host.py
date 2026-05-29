import json
from pathlib import Path

import pytest

from universal_memory.application.host.setup_host_use_case import (
    ConfigureHostCommand,
    ConfigureHostUseCase,
    InstructionBlock,
    partition_instruction_blocks,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain import SecretDetectedError, StorageError
from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    HostName,
    InstructionClassification,
    InstructionTargetOwnership,
    InstructionTargetType,
    Snapshot,
    SnapshotStatus,
)
from universal_memory.domain.ports import AuditLogRepository, SecretScannerPort, SnapshotRepository


class InMemorySecretScanner(SecretScannerPort):
    def scan(self, content: str, *, origin: str | None = None) -> None:
        if "SECRET_TOKEN=" in content:
            raise SecretDetectedError("Secret detected; persistence was blocked.")


class InMemorySnapshotRepository(SnapshotRepository):
    def __init__(self) -> None:
        self.snapshots: list[Snapshot] = []

    def read(self, id: str) -> Snapshot:
        for snapshot in self.snapshots:
            if snapshot.id == id:
                return snapshot
        raise StorageError(f"Snapshot not found: {id}")

    def list(self, scope=None, status: SnapshotStatus | None = None) -> list[Snapshot]:
        snapshots = self.snapshots
        if status is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.status == status]
        return snapshots

    def get_content(self, id: str) -> bytes:
        return b""

    def write(self, entity: Snapshot) -> None:
        self.snapshots.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


class InMemoryAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def read(self, id: str) -> AuditEvent:
        for event in self.events:
            if event.id == id:
                return event
        raise StorageError(f"Audit event not found: {id}")

    def list(self, scope: AuditEventScope | None = None) -> list[AuditEvent]:
        if scope is None:
            return self.events
        return [event for event in self.events if event.scope == scope]

    def write(self, entity: AuditEvent) -> None:
        self.events.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


@pytest.fixture()
def configured_use_case(tmp_path: Path) -> ConfigureHostUseCase:
    (tmp_path / ".umem").mkdir()
    return ConfigureHostUseCase(
        project_root=tmp_path,
        safe_write_use_case=SafeWriteUseCase(
            project_root=tmp_path,
            secret_scanner=InMemorySecretScanner(),
            snapshot_repository=InMemorySnapshotRepository(),
            audit_log_repository=InMemoryAuditLogRepository(),
        ),
    )


@pytest.fixture()
def configured_use_case_with_audit(
    tmp_path: Path,
) -> tuple[ConfigureHostUseCase, InMemoryAuditLogRepository]:
    (tmp_path / ".umem").mkdir()
    audit_log_repository = InMemoryAuditLogRepository()
    use_case = ConfigureHostUseCase(
        project_root=tmp_path,
        safe_write_use_case=SafeWriteUseCase(
            project_root=tmp_path,
            secret_scanner=InMemorySecretScanner(),
            snapshot_repository=InMemorySnapshotRepository(),
            audit_log_repository=audit_log_repository,
        ),
    )
    return use_case, audit_log_repository


def test_partition_instruction_blocks_moves_canonical_docs_to_docs_pointer() -> None:
    partition = partition_instruction_blocks(
        [
            InstructionBlock(
                title="Operational rules",
                content="Always run tests before review.",
                classification="shared_policy",
            ),
            InstructionBlock(
                title="Project Guide",
                content="A" * 500,
                classification="canonical_doc",
            ),
        ],
        docs_directory="docs",
    )

    assert partition.manifest_blocks[0].classification.value == "shared_policy"
    assert partition.canonical_documents[0].relative_path == "docs/project-guide.md"
    assert "- [docs/project-guide.md](file:///docs/project-guide.md)" in partition.pointer_lines


def test_setup_creates_agents_md_docs_pointer_audit_and_snapshot(
    tmp_path: Path,
    configured_use_case: ConfigureHostUseCase,
) -> None:
    result = configured_use_case.execute(
        ConfigureHostCommand(
            host_id="codex",
            apply=True,
            instruction_blocks=[
                InstructionBlock(
                    title="Shared Policy",
                    content="Use relative paths in specs, code and docs.",
                    classification="shared_policy",
                ),
                InstructionBlock(
                    title="Project Guide",
                    content="Long project guidance " * 60,
                    classification="canonical_doc",
                ),
            ],
            origin="test",
        )
    )

    agents_content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    guide_content = (tmp_path / "docs" / "project-guide.md").read_text(encoding="utf-8")
    assert result.validation_status == "success"
    assert result.audit_reference != "not-applied"
    assert result.snapshot_reference != "planned"
    assert result.planned_changes == [
        {"target": "canonical_doc", "action": "create", "path": "docs/project-guide.md"},
        {"target": "agents_md", "action": "create", "path": "AGENTS.md"},
    ]
    assert "<!-- UMEM: START -->" in agents_content
    assert "<!-- UMEM: END -->" in agents_content
    assert "[docs/project-guide.md](file:///docs/project-guide.md)" in agents_content
    assert "Long project guidance" not in agents_content
    assert "Long project guidance" in guide_content


def test_setup_preserves_manual_content_outside_managed_block(
    tmp_path: Path,
    configured_use_case: ConfigureHostUseCase,
) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "# Manual heading\n\nKeep this.\n\n"
        "<!-- UMEM: START -->\nold\n<!-- UMEM: END -->\n\n"
        "Tail note.\n",
        encoding="utf-8",
    )

    configured_use_case.execute(ConfigureHostCommand(host_id="codex", apply=True, origin="test"))

    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert content.startswith("# Manual heading\n\nKeep this.")
    assert content.endswith("Tail note.\n")
    assert "old" not in content
    assert "Universal Memory Active Policy" in content


def test_check_rejects_massive_agents_md_dump(
    tmp_path: Path,
    configured_use_case: ConfigureHostUseCase,
) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "<!-- UMEM: START -->\n" + ("raw memory fact\n" * 120) + "<!-- UMEM: END -->\n",
        encoding="utf-8",
    )

    result = configured_use_case.execute(ConfigureHostCommand(host_id="codex", check=True))

    assert result.validation_status == "failure"
    assert any("compact" in warning for warning in result.warnings)


def test_secret_detection_blocks_agents_md_write(
    configured_use_case: ConfigureHostUseCase,
) -> None:
    with pytest.raises(SecretDetectedError):
        configured_use_case.execute(
            ConfigureHostCommand(
                host_id="codex",
                apply=True,
                instruction_blocks=[
                    InstructionBlock(
                        title="Unsafe",
                        content="SECRET_TOKEN=abcdef123456",
                        classification="shared_policy",
                    )
                ],
                origin="test",
            )
        )


def test_result_payload_matches_host_setup_contract(
    configured_use_case: ConfigureHostUseCase,
) -> None:
    result = configured_use_case.execute(ConfigureHostCommand(host_id="codex", apply=True))

    payload = result.to_payload()
    json.dumps(payload)
    assert payload["host_id"] == "codex"
    assert payload["instruction_targets"] == ["agents_md"]
    assert payload["planned_changes"] == [
        {"target": "agents_md", "action": "create", "path": "AGENTS.md"}
    ]
    assert payload["manual_steps"] == []
    assert payload["validation_status"] == "success"
    assert payload["audit_reference"]


def test_claude_code_host_maps_to_claude_delta_target(
    configured_use_case: ConfigureHostUseCase,
) -> None:
    host = configured_use_case._host_for("claude_code")

    assert host.name == HostName.claude_code
    assert host.supported_targets == [InstructionTargetType.claude_md]
    assert host.read_validation_method == "claude_md_delta_validator"
    assert host.write_validation_method == "safe_write_use_case"
    assert host.rollback_behavior == "snapshot_rollback"
    assert host.audit_event_type == "host_setup"


def test_claude_md_target_allows_only_delta_classifications(
    configured_use_case: ConfigureHostUseCase,
) -> None:
    host = configured_use_case._host_for("claude_code")
    target = configured_use_case._instruction_target_for(
        host,
        InstructionTargetType.claude_md,
    )

    assert target.name == InstructionTargetType.claude_md
    assert target.relative_path == "CLAUDE.md"
    assert target.ownership == InstructionTargetOwnership.delta_consumer
    assert target.supported_classifications == [
        InstructionClassification.provider_delta,
        InstructionClassification.scoped_rule,
    ]


def test_claude_code_setup_writes_only_delta_blocks_to_claude_md(
    tmp_path: Path,
    configured_use_case: ConfigureHostUseCase,
) -> None:
    result = configured_use_case.execute(
        ConfigureHostCommand(
            host_id="claude_code",
            apply=True,
            instruction_blocks=[
                InstructionBlock(
                    title="Shared Policy",
                    content="Use relative paths in specs, code and docs.",
                    classification="shared_policy",
                ),
                InstructionBlock(
                    title="Claude Delta",
                    content="Use CLAUDE.md only for Claude-specific deltas.",
                    classification="provider_delta",
                ),
                InstructionBlock(
                    title="Claude Scope",
                    content="When editing Claude instructions, preserve manual content.",
                    classification="scoped_rule",
                ),
            ],
            origin="test",
        )
    )

    claude_content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert result.host_id == "claude_code"
    assert result.instruction_targets == ["claude_md"]
    assert result.audit_reference != "not-applied"
    assert result.snapshot_reference != "planned"
    assert result.planned_changes == [
        {"target": "claude_md", "action": "create", "path": "CLAUDE.md"}
    ]
    assert "<!-- UMEM: START -->" in claude_content
    assert "<!-- UMEM: END -->" in claude_content
    assert "Use CLAUDE.md only for Claude-specific deltas." in claude_content
    assert "When editing Claude instructions, preserve manual content." in claude_content
    assert "Use relative paths in specs, code and docs." not in claude_content


def test_claude_code_setup_preserves_manual_content_outside_managed_block(
    tmp_path: Path,
    configured_use_case: ConfigureHostUseCase,
) -> None:
    (tmp_path / "CLAUDE.md").write_text(
        "# Claude manual notes\n\nKeep this.\n\n"
        "<!-- UMEM: START -->\nold\n<!-- UMEM: END -->\n\n"
        "Tail note.\n",
        encoding="utf-8",
    )

    configured_use_case.execute(
        ConfigureHostCommand(
            host_id="claude_code",
            apply=True,
            instruction_blocks=[
                InstructionBlock(
                    title="Claude Delta",
                    content="Prefer CLAUDE.md deltas over duplicated shared policy.",
                    classification="provider_delta",
                )
            ],
            origin="test",
        )
    )

    content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert content.startswith("# Claude manual notes\n\nKeep this.")
    assert content.endswith("Tail note.\n")
    assert "old" not in content
    assert "Claude Delta Instructions" in content
    assert "Prefer CLAUDE.md deltas over duplicated shared policy." in content


def test_claude_code_check_reports_drift_warnings_without_mutation(
    tmp_path: Path,
    configured_use_case: ConfigureHostUseCase,
) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "<!-- UMEM: START -->\n"
        "- (shared_policy) Use relative paths in specs, code and docs.\n"
        "<!-- UMEM: END -->\n",
        encoding="utf-8",
    )
    (tmp_path / "CLAUDE.md").write_text(
        "<!-- UMEM: START -->\n"
        "- (provider_delta) Use relative paths in specs, code and docs.\n"
        "- Use the universal-memory MCP server.\n"
        "<!-- UMEM: END -->\n",
        encoding="utf-8",
    )

    result = configured_use_case.execute(
        ConfigureHostCommand(host_id="claude_code", check=True, origin="test")
    )

    assert result.warnings == [
        "Instrucao duplicada em AGENTS.md e CLAUDE.md: Use relative paths in specs, code and docs."
    ]
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").count("Use relative paths") == 1


def test_host_check_records_failure_when_instruction_file_is_missing(
    configured_use_case_with_audit: tuple[ConfigureHostUseCase, InMemoryAuditLogRepository],
) -> None:
    use_case, audit_log_repository = configured_use_case_with_audit

    result = use_case.execute(ConfigureHostCommand(host_id="codex", check=True, origin="cli"))

    assert result.validation_status == "failure"
    assert result.planned_changes == []
    assert result.snapshot_reference == "planned"
    assert result.audit_reference != "not-applied"
    assert any("Falha de Arquivo de Instrução" in warning for warning in result.warnings)
    assert len(audit_log_repository.events) == 1
    event = audit_log_repository.events[0]
    assert event.action == "host_validation.codex"
    assert event.result == "failure"
    assert event.scope == AuditEventScope.project
    assert event.origin == "cli"
    assert event.details is not None
    details = json.loads(event.details)
    assert details["method"] == "agents_md_compact_validator"
    assert details["checks"]["instruction_file_exists"] is False


def test_host_check_records_success_for_valid_agents_md(
    tmp_path: Path,
    configured_use_case_with_audit: tuple[ConfigureHostUseCase, InMemoryAuditLogRepository],
) -> None:
    use_case, audit_log_repository = configured_use_case_with_audit
    (tmp_path / "AGENTS.md").write_text(
        "<!-- UMEM: START -->\n"
        "Use the universal-memory MCP server and run `umem context` before coding.\n"
        "<!-- UMEM: END -->\n",
        encoding="utf-8",
    )

    result = use_case.execute(ConfigureHostCommand(host_id="codex", check=True, origin="mcp"))

    assert result.validation_status == "success"
    assert result.planned_changes == []
    assert result.manual_steps == []
    assert result.warnings == []
    event = audit_log_repository.events[0]
    assert event.action == "host_validation.codex"
    assert event.result == "success"
    details = json.loads(event.details or "{}")
    assert details["method"] == "agents_md_compact_validator"
    assert details["checks"]["managed_block_has_mcp_reference"] is True


def test_host_check_records_failure_for_corrupted_umem_delimiters(
    tmp_path: Path,
    configured_use_case_with_audit: tuple[ConfigureHostUseCase, InMemoryAuditLogRepository],
) -> None:
    use_case, audit_log_repository = configured_use_case_with_audit
    (tmp_path / "CLAUDE.md").write_text(
        "<!-- UMEM: START -->\nUse mcp server universal-memory.\n",
        encoding="utf-8",
    )

    result = use_case.execute(ConfigureHostCommand(host_id="claude_code", check=True, origin="cli"))

    assert result.validation_status == "failure"
    assert any("delimitadores UMEM" in warning for warning in result.warnings)
    event = audit_log_repository.events[0]
    assert event.action == "host_validation.claude_code"
    details = json.loads(event.details or "{}")
    assert details["method"] == "claude_md_delta_validator"
    assert details["checks"]["managed_block_has_valid_delimiters"] is False
