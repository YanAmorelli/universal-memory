import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain.entities import Rule, RuleScope, RuleStatus
from universal_memory.infrastructure.security import (
    EntropySecretScanner,
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)
from universal_memory.infrastructure.storage import LocalRuleRepository


def make_rule(*, scope: RuleScope = RuleScope.project) -> Rule:
    timestamp = datetime.now(UTC)
    return Rule(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        name="Preferencias de teste",
        content="Sempre proteger caminhos globais com teste unitario",
        scope=scope,
        status=RuleStatus.active,
        metadata={"origin": "unit-test"},
    )


def test_write_project_rule_uses_project_umem_path(tmp_path: Path) -> None:
    repository = LocalRuleRepository(project_root=tmp_path)
    rule = make_rule(scope=RuleScope.project)

    repository.write(rule)

    project_path = tmp_path / ".umem" / "memory" / "rules.jsonl"
    assert json.loads(project_path.read_text(encoding="utf-8").splitlines()[0])["id"] == rule.id


def test_write_global_rule_uses_xdg_umem_data_path(tmp_path: Path) -> None:
    global_home = tmp_path / "home"
    data_root = tmp_path / ".umem"
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=EntropySecretScanner(),
        snapshot_repository=LocalSnapshotRepository(project_root=tmp_path, data_root=data_root),
        audit_log_repository=LocalAuditLogRepository(project_root=tmp_path, data_root=data_root),
    )
    repository = LocalRuleRepository(
        project_root=tmp_path,
        global_home=global_home,
        safe_write_use_case=safe_write,
    )
    rule = make_rule(scope=RuleScope.global_)

    repository.write(rule)

    global_data_root = global_home / ".local" / "share" / "umem"
    global_path = global_data_root / "memory" / "rules.jsonl"
    assert json.loads(global_path.read_text(encoding="utf-8").splitlines()[0])["id"] == rule.id
    assert (global_data_root / "audit" / "events.jsonl").is_file()
    assert (global_data_root / "snapshots" / "manifest.json").is_file()
    assert not (global_home / ".umem" / "memory" / "rules.jsonl").exists()
    assert not (data_root / "audit" / "events.jsonl").exists()


def test_list_missing_global_storage_does_not_create_read_lock(tmp_path: Path) -> None:
    global_home = tmp_path / "home"
    global_home.write_text("not a directory", encoding="utf-8")
    repository = LocalRuleRepository(project_root=tmp_path, global_home=global_home)
    global_data_root = global_home / ".local" / "share" / "umem"

    assert repository.list(scope=RuleScope.global_) == []
    assert repository.list() == []
    assert not global_data_root.exists()
    assert not (global_data_root / "memory" / "rules.jsonl.lock").exists()
