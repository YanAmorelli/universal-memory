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
from universal_memory.domain import SecretDetectedError, StorageError, ValidationFailedError
from universal_memory.domain.entities import AuditEvent, AuditEventScope, Snapshot, SnapshotStatus
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

    with pytest.raises(ValidationFailedError, match="compact"):
        configured_use_case.execute(ConfigureHostCommand(host_id="codex", apply=False))


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
