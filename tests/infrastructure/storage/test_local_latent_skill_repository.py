import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain import StorageError
from universal_memory.domain.entities import (
    AuditEvent,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    Snapshot,
)
from universal_memory.domain.ports import (
    AuditLogRepository,
    LatentSkillRepository,
    SecretScannerPort,
    SnapshotRepository,
)
from universal_memory.infrastructure.storage import LocalLatentSkillRepository


class RecordingScanner(SecretScannerPort):
    def scan(self, content: str, *, origin: str | None = None) -> None:
        return None


class RecordingSnapshotRepository(SnapshotRepository):
    def __init__(self) -> None:
        self.written: list[Snapshot] = []

    def read(self, id: str) -> Snapshot:
        raise KeyError(id)

    def get_content(self, id: str) -> bytes:
        raise KeyError(id)

    def list(self, scope=None, status=None) -> list[Snapshot]:
        return self.written

    def write(self, entity: Snapshot) -> None:
        self.written.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


class RecordingAuditRepository(AuditLogRepository):
    def __init__(self) -> None:
        self.written: list[AuditEvent] = []

    def read(self, id: str) -> AuditEvent:
        raise KeyError(id)

    def list(self, scope=None) -> list[AuditEvent]:
        return self.written

    def write(self, entity: AuditEvent) -> None:
        self.written.append(entity)

    def migrate(self, target_version: int) -> None:
        return None


def make_skill(
    *,
    scope: LatentSkillScope = LatentSkillScope.project,
    status: LatentSkillStatus = LatentSkillStatus.proposed,
    name: str = "TDD recorrente",
    description: str = "Usuario sempre pede ciclo red green refactor",
    created_at: datetime | None = None,
) -> LatentSkill:
    timestamp = created_at or datetime.now(UTC)
    return LatentSkill(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        name=name,
        description=description,
        scope=scope,
        status=status,
        recurrence_count=1,
        metadata={"origin": "unit-test"},
    )


def build_safe_write(
    tmp_path: Path,
) -> tuple[SafeWriteUseCase, RecordingSnapshotRepository, RecordingAuditRepository]:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    return (
        SafeWriteUseCase(
            project_root=tmp_path,
            secret_scanner=RecordingScanner(),
            snapshot_repository=snapshots,
            audit_log_repository=audit,
        ),
        snapshots,
        audit,
    )


def test_repository_implements_domain_port(tmp_path: Path) -> None:
    safe_write, _, _ = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)

    assert isinstance(repository, LatentSkillRepository)


def test_write_read_and_list_filters_project_latent_skills(tmp_path: Path) -> None:
    safe_write, _, _ = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    base = datetime(2026, 5, 29, tzinfo=UTC)
    proposed = make_skill(created_at=base, status=LatentSkillStatus.proposed)
    active = make_skill(
        created_at=base + timedelta(minutes=1),
        status=LatentSkillStatus.active,
        name="Prompt de research",
    )

    repository.write(active)
    repository.write(proposed)

    assert repository.read(proposed.id) == proposed
    assert repository.list(scope=LatentSkillScope.project) == [proposed, active]
    assert repository.list(status=LatentSkillStatus.active) == [active]


def test_write_uses_project_and_global_jsonl_paths(tmp_path: Path) -> None:
    safe_write, _, _ = build_safe_write(tmp_path)
    global_home = tmp_path / "home"
    repository = LocalLatentSkillRepository(
        project_root=tmp_path, global_home=global_home, safe_write_use_case=safe_write
    )
    project_skill = make_skill(scope=LatentSkillScope.project)
    global_skill = make_skill(scope=LatentSkillScope.global_, name="Padrao global")

    repository.write(project_skill)
    repository.write(global_skill)

    project_path = tmp_path / ".umem" / "memory" / "latent_skills.jsonl"
    global_path = (
        global_home / ".local" / "share" / "universal-memory" / "memory" / "latent_skills.jsonl"
    )
    assert (
        json.loads(project_path.read_text(encoding="utf-8").splitlines()[0])["id"]
        == project_skill.id
    )
    assert (
        json.loads(global_path.read_text(encoding="utf-8").splitlines()[0])["id"] == global_skill.id
    )


def test_write_updates_existing_latent_skill_in_place(tmp_path: Path) -> None:
    safe_write, _, _ = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    skill = make_skill(description="Inicial")
    updated = skill.model_copy(update={"description": "Atualizada", "recurrence_count": 2})

    repository.write(skill)
    repository.write(updated)

    assert repository.list() == [updated]
    assert len(repository.latent_skills_path.read_text(encoding="utf-8").splitlines()) == 1


def test_delete_marks_latent_skill_as_ignored(tmp_path: Path) -> None:
    safe_write, _snapshots, audit = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    skill = make_skill()
    repository.write(skill)

    repository.delete(skill.id)

    deleted = repository.read(skill.id)
    assert deleted.status == LatentSkillStatus.ignored
    assert deleted.updated_at >= skill.updated_at
    assert audit.written[-1].action == "delete_latent_skill"


def test_migrate_accepts_only_schema_version_one(tmp_path: Path) -> None:
    safe_write, _, _ = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)

    repository.migrate(1)

    with pytest.raises(StorageError, match="Unsupported latent skill repository schema version"):
        repository.migrate(2)


def test_corrupt_lines_raise_error_on_read_and_write(tmp_path: Path) -> None:
    safe_write, _snapshots, _audit = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    skill = make_skill()
    repository.latent_skills_path.parent.mkdir(parents=True)
    repository.latent_skills_path.write_text(
        "\n".join(["{not-json}", skill.model_dump_json(), '{"id":"invalid"}']),
        encoding="utf-8",
    )

    with pytest.raises(StorageError, match="Corrupt latent skill line detected"):
        repository.list(scope=LatentSkillScope.project)

    with pytest.raises(StorageError, match="Corrupt latent skill line detected"):
        repository.write(make_skill(name="Nova skill"))


def test_lock_file_blocks_concurrent_project_writes(tmp_path: Path) -> None:
    safe_write, _, _ = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    repository.latent_skills_path.parent.mkdir(parents=True)
    repository.latent_skills_path.with_suffix(".jsonl.lock").write_text("held", encoding="utf-8")

    with pytest.raises(StorageError, match="Failed to acquire lock on latent skills storage"):
        repository.write(make_skill())


def test_safe_write_pipeline_records_snapshot_and_audit(tmp_path: Path) -> None:
    safe_write, snapshots, audit = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)

    result = repository.write(make_skill(), origin="cli")

    assert result is not None
    assert result.relative_path == ".umem/memory/latent_skills.jsonl"
    assert snapshots.written
    assert audit.written[0].action == "write_latent_skill"
    assert audit.written[0].origin == "cli"
