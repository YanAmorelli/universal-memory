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


def test_shared_layout_writes_project_rules_to_visible_root(shared_project_root: Path) -> None:
    repository = LocalRuleRepository(project_root=shared_project_root)
    rule = make_rule(scope=RuleScope.project)

    repository.write(rule)

    shared_path = shared_project_root / "umem" / "memory" / "rules.jsonl"
    assert json.loads(shared_path.read_text(encoding="utf-8").splitlines()[0])["id"] == rule.id
    assert not (shared_project_root / ".umem" / "memory" / "rules.jsonl").exists()


def test_shared_layout_reads_shared_rules_before_legacy_rules(shared_project_root: Path) -> None:
    repository = LocalRuleRepository(project_root=shared_project_root)
    base = make_rule(scope=RuleScope.project)
    shared = base.model_copy(update={"content": "shared rule"})
    legacy_path = shared_project_root / ".umem" / "memory" / "rules.jsonl"
    shared_path = shared_project_root / "umem" / "memory" / "rules.jsonl"
    legacy_path.write_text(base.model_dump_json() + "\n", encoding="utf-8")
    shared_path.write_text(shared.model_dump_json() + "\n", encoding="utf-8")

    assert repository.list(scope=RuleScope.project) == [shared]


def test_shared_layout_write_updates_existing_legacy_rule_without_creating_shared_file(
    shared_project_root: Path,
) -> None:
    repository = LocalRuleRepository(project_root=shared_project_root)
    legacy = make_rule(scope=RuleScope.project)
    updated = legacy.model_copy(update={"content": "updated legacy rule"})
    legacy_path = shared_project_root / ".umem" / "memory" / "rules.jsonl"
    legacy_path.write_text(legacy.model_dump_json() + "\n", encoding="utf-8")

    repository.write(updated)

    stored = json.loads(legacy_path.read_text(encoding="utf-8").splitlines()[0])
    assert stored["id"] == legacy.id
    assert stored["content"] == "updated legacy rule"
    assert not (shared_project_root / "umem" / "memory" / "rules.jsonl").exists()


def test_shared_layout_writes_private_project_rules_to_operational_root(
    shared_project_root: Path,
) -> None:
    repository = LocalRuleRepository(project_root=shared_project_root)
    rule = make_rule(scope=RuleScope.project).model_copy(
        update={"metadata": {"visibility": "private"}}
    )

    repository.write(rule)

    private_path = shared_project_root / ".umem" / "memory" / "private_rules.jsonl"
    assert json.loads(private_path.read_text(encoding="utf-8").splitlines()[0])["id"] == rule.id
    assert not (shared_project_root / "umem" / "memory" / "rules.jsonl").exists()


def test_shared_layout_delete_updates_private_rule_source_without_leaking(
    shared_project_root: Path,
) -> None:
    repository = LocalRuleRepository(project_root=shared_project_root)
    rule = make_rule(scope=RuleScope.project).model_copy(
        update={"metadata": {"visibility": "private"}}
    )
    repository.write(rule)

    repository.delete(rule.id)

    private_path = shared_project_root / ".umem" / "memory" / "private_rules.jsonl"
    stored = json.loads(private_path.read_text(encoding="utf-8").splitlines()[0])
    assert stored["status"] == "inactive"
    assert not (shared_project_root / "umem" / "memory" / "rules.jsonl").exists()


def test_list_missing_global_storage_does_not_create_read_lock(tmp_path: Path) -> None:
    global_home = tmp_path / "home"
    global_home.write_text("not a directory", encoding="utf-8")
    repository = LocalRuleRepository(project_root=tmp_path, global_home=global_home)
    global_data_root = global_home / ".local" / "share" / "umem"

    assert repository.list(scope=RuleScope.global_) == []
    assert repository.list() == []
    assert not global_data_root.exists()
    assert not (global_data_root / "memory" / "rules.jsonl.lock").exists()
