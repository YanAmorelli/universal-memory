from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.application.host.sync_instructions_use_case import (
    SyncInstructionsCommand,
    SyncInstructionsUseCase,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain import SecretDetectedError, StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    Rule,
    RuleScope,
    RuleStatus,
    Snapshot,
    SnapshotStatus,
)
from universal_memory.domain.ports import (
    AuditLogRepository,
    RuleRepository,
    SecretScannerPort,
    SnapshotRepository,
)


class InMemoryRuleRepository(RuleRepository):
    def __init__(self, rules: list[Rule]) -> None:
        self.rules = rules

    def read(self, id: str) -> Rule:
        for rule in self.rules:
            if rule.id == id:
                return rule
        raise StorageError(f"Rule not found: {id}")

    def list(self, scope: RuleScope | None = None, status: RuleStatus | None = None) -> list[Rule]:
        rules = self.rules
        if scope is not None:
            rules = [rule for rule in rules if rule.scope == scope]
        if status is not None:
            rules = [rule for rule in rules if rule.status == status]
        return rules

    def write(self, entity: Rule) -> None:
        self.rules.append(entity)

    def delete(self, id: str) -> None:
        self.rules = [rule for rule in self.rules if rule.id != id]

    def migrate(self, target_version: int) -> None:
        return None


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


def _rule(name: str, content: str, classification: str) -> Rule:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    return Rule(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name=name,
        content=content,
        scope=RuleScope.project,
        status=RuleStatus.active,
        metadata={"classification": classification},
    )


@pytest.fixture()
def repositories() -> tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository]:
    return InMemorySnapshotRepository(), InMemoryAuditLogRepository()


def _use_case(
    tmp_path: Path,
    rules: list[Rule],
    repositories: tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository],
) -> SyncInstructionsUseCase:
    snapshot_repository, audit_log_repository = repositories
    safe_write_use_case = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=InMemorySecretScanner(),
        snapshot_repository=snapshot_repository,
        audit_log_repository=audit_log_repository,
    )
    return SyncInstructionsUseCase(
        project_root=tmp_path,
        safe_write_use_case=safe_write_use_case,
        rule_repository=InMemoryRuleRepository(rules),
    )


def test_sync_routes_rules_writes_agents_once_and_keeps_canonical_docs_compact(
    tmp_path: Path,
    repositories: tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository],
) -> None:
    use_case = _use_case(
        tmp_path,
        [
            _rule("Shared Policy", "Use relative paths in specs, code and docs.", "shared_policy"),
            _rule(
                "Claude Delta",
                "Use CLAUDE.md only for Claude-specific deltas.",
                "provider_delta",
            ),
            _rule("Scoped Rule", "Apply host sync only inside the project root.", "scoped_rule"),
            _rule("Long Guide", "Long guidance " * 90, "canonical_doc"),
        ],
        repositories,
    )

    result = use_case.execute(
        SyncInstructionsCommand(host_ids=["codex", "claude_code"], apply=True)
    )

    agents_content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    claude_content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    guide_content = (tmp_path / "docs" / "long-guide.md").read_text(encoding="utf-8")
    snapshot_repository, audit_log_repository = repositories

    assert result.validation_status == "success"
    assert result.instruction_targets == ["AGENTS.md", "CLAUDE.md", "docs/long-guide.md"]
    assert [change["path"] for change in result.planned_changes] == [
        "docs/long-guide.md",
        "AGENTS.md",
        "CLAUDE.md",
    ]
    assert "Use relative paths in specs, code and docs." in agents_content
    assert "Use CLAUDE.md only for Claude-specific deltas." in agents_content
    assert "[docs/long-guide.md](file:///docs/long-guide.md)" in agents_content
    assert "Long guidance" not in agents_content
    assert "Use relative paths in specs, code and docs." not in claude_content
    assert "Use CLAUDE.md only for Claude-specific deltas." in claude_content
    assert "Apply host sync only inside the project root." in claude_content
    assert "Long guidance" in guide_content
    snapshot_paths = [snapshot.relative_path for snapshot in snapshot_repository.snapshots]
    assert snapshot_paths.count("AGENTS.md") == 1
    assert [event.action for event in audit_log_repository.events].count("host_sync.AGENTS.md") == 1


def test_sync_preview_returns_paths_without_mutating_files(
    tmp_path: Path,
    repositories: tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository],
) -> None:
    use_case = _use_case(
        tmp_path,
        [_rule("Shared Policy", "Use relative paths in specs, code and docs.", "shared_policy")],
        repositories,
    )

    result = use_case.execute(SyncInstructionsCommand(host_ids=["codex"], apply=False))

    assert result.validation_status == "planned"
    assert result.audit_reference == "not-applied"
    assert result.snapshot_reference == "planned"
    assert result.planned_changes == [
        {"target": "agents_md", "action": "create", "path": "AGENTS.md"}
    ]
    assert not (tmp_path / "AGENTS.md").exists()
    assert json.dumps(result.to_payload(), sort_keys=True)


def test_sync_default_hosts_respects_enabled_hosts_from_project_config(
    tmp_path: Path,
    repositories: tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository],
) -> None:
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('[hosts]\nenabled = ["codex"]\n', encoding="utf-8")
    use_case = _use_case(
        tmp_path,
        [
            _rule("Shared Policy", "Use relative paths in specs, code and docs.", "shared_policy"),
            _rule("Claude Delta", "Claude-only note.", "provider_delta"),
        ],
        repositories,
    )

    result = use_case.execute(SyncInstructionsCommand(apply=True))

    assert result.host_ids == ["codex"]
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_sync_claude_without_agents_md_keeps_shared_policy_in_claude_md(
    tmp_path: Path,
    repositories: tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository],
) -> None:
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('[runtimes]\nenabled = ["claude_code"]\n', encoding="utf-8")
    use_case = _use_case(
        tmp_path,
        [
            _rule("Shared Policy", "Use relative paths in specs, code and docs.", "shared_policy"),
            _rule("Claude Delta", "Claude-only note.", "provider_delta"),
        ],
        repositories,
    )

    result = use_case.execute(SyncInstructionsCommand(apply=True))

    claude_content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert result.host_ids == ["claude_code"]
    assert not (tmp_path / "AGENTS.md").exists()
    assert "Use relative paths in specs, code and docs." in claude_content
    assert "Claude-only note." in claude_content
    assert "Claude Code Universal Memory Instructions" in claude_content
    assert "mandatory preflight before any planning" in claude_content
    assert "If `umem` is unavailable or not initialized" in claude_content


def test_sync_ignores_enabled_runtimes_without_legacy_instruction_support(
    tmp_path: Path,
    repositories: tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository],
) -> None:
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '[runtimes]\nenabled = ["opencode", "cursor", "codex", "antigravity"]\n',
        encoding="utf-8",
    )
    use_case = _use_case(
        tmp_path,
        [_rule("Shared Policy", "Use relative paths in specs, code and docs.", "shared_policy")],
        repositories,
    )

    result = use_case.execute(SyncInstructionsCommand(apply=True))

    assert result.host_ids == ["codex"]
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_sync_noops_when_config_has_only_unsupported_runtime_targets(
    tmp_path: Path,
    repositories: tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository],
) -> None:
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '[runtimes]\nenabled = ["opencode", "cursor", "antigravity"]\n',
        encoding="utf-8",
    )
    use_case = _use_case(
        tmp_path,
        [_rule("Shared Policy", "Use relative paths in specs, code and docs.", "shared_policy")],
        repositories,
    )

    result = use_case.execute(SyncInstructionsCommand(apply=True))

    assert result.host_ids == []
    assert result.planned_changes == []
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_sync_explicit_disabled_host_is_allowed_with_warning(
    tmp_path: Path,
    repositories: tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository],
) -> None:
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('[hosts]\nenabled = ["codex"]\n', encoding="utf-8")
    use_case = _use_case(
        tmp_path,
        [_rule("Claude Delta", "Claude-only note.", "provider_delta")],
        repositories,
    )

    result = use_case.execute(SyncInstructionsCommand(host_ids=["claude_code"], apply=False))

    assert result.host_ids == ["claude_code"]
    assert result.warnings == [
        "Host 'claude_code' nao esta habilitado em .umem/config.toml; ativando automaticamente."
    ]


def test_sync_respects_limits_from_project_config(
    tmp_path: Path,
    repositories: tuple[InMemorySnapshotRepository, InMemoryAuditLogRepository],
) -> None:
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '[runtimes]\nenabled = ["codex"]\nmax_managed_lines = 150\nmax_managed_chars = 6000\n',
        encoding="utf-8",
    )
    # Default max_managed_chars is 4000. Template boilerplate is ~3000.
    # ~3000 + 1500 = 4500, which exceeds 4000 but fits in 6000 config limit.
    use_case = _use_case(
        tmp_path,
        [
            _rule("Shared Policy", "A" * 1500, "shared_policy"),
        ],
        repositories,
    )

    result = use_case.execute(SyncInstructionsCommand(apply=True))
    assert result.validation_status == "success"

    # Rule is too large (exceeding even the override of 6000: ~3000 + 4000 = 7000 chars)
    use_case_too_large = _use_case(
        tmp_path,
        [
            _rule("Shared Policy", "A" * 4000, "shared_policy"),
        ],
        repositories,
    )
    with pytest.raises(ValidationFailedError):
        use_case_too_large.execute(SyncInstructionsCommand(apply=True))
