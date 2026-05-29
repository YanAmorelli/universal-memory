from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    TrackLatentSkillCommand,
    TrackLatentSkillUseCase,
)
from universal_memory.domain import SecretDetectedError, StorageError
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

EXPECTED_INCREMENTED_RECURRENCE = 3
EXPECTED_AMBIGUOUS_CANDIDATE_COUNT = 2


class RecordingScanner(SecretScannerPort):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.scanned: list[str] = []

    def scan(self, content: str, *, origin: str | None = None) -> None:
        self.scanned.append(f"{origin}:{content}")
        if self.error is not None:
            raise self.error


class RecordingSnapshotRepository(SnapshotRepository):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.written: list[Snapshot] = []

    def read(self, id: str) -> Snapshot:
        raise KeyError(id)

    def get_content(self, id: str) -> bytes:
        raise KeyError(id)

    def list(self, scope=None, status=None) -> list[Snapshot]:
        return self.written

    def write(self, entity: Snapshot) -> None:
        if self.error is not None:
            raise self.error
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


class RecordingLatentSkillRepository(LatentSkillRepository):
    def __init__(self, skills: list[LatentSkill] | None = None) -> None:
        self.skills = skills or []

    def read(self, id: str) -> LatentSkill:
        for skill in self.skills:
            if skill.id == id:
                return skill
        raise StorageError(f"Latent skill not found: {id}")

    def list(
        self, scope: LatentSkillScope | None = None, status: LatentSkillStatus | None = None
    ) -> list[LatentSkill]:
        skills = self.skills
        if scope is not None:
            skills = [skill for skill in skills if skill.scope == scope]
        if status is not None:
            skills = [skill for skill in skills if skill.status == status]
        return sorted(skills, key=lambda skill: skill.created_at)

    def write(self, entity: LatentSkill, *, origin: str = "repository"):
        self.skills = [skill for skill in self.skills if skill.id != entity.id]
        self.skills.append(entity)

    def delete(self, id: str) -> None:
        raise NotImplementedError

    def migrate(self, target_version: int) -> None:
        return None


def make_skill(
    *,
    name: str = "TDD recorrente",
    description: str = "Usuario pede sempre red green refactor antes de implementar",
    scope: LatentSkillScope = LatentSkillScope.project,
    tags: list[str] | None = None,
    recurrence_count: int = 1,
) -> LatentSkill:
    timestamp = datetime.now(UTC)
    return LatentSkill(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        name=name,
        description=description,
        scope=scope,
        status=LatentSkillStatus.proposed,
        recurrence_count=recurrence_count,
        metadata={
            "tags": tags or ["tdd"],
            "evidence": [{"origin": "cli", "summary": "primeira ocorrencia"}],
        },
    )


def build_safe_write(
    tmp_path,
    *,
    scanner: RecordingScanner | None = None,
    snapshots: RecordingSnapshotRepository | None = None,
) -> tuple[
    SafeWriteUseCase, RecordingScanner, RecordingSnapshotRepository, RecordingAuditRepository
]:
    resolved_scanner = scanner or RecordingScanner()
    resolved_snapshots = snapshots or RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    return (
        SafeWriteUseCase(
            project_root=tmp_path,
            secret_scanner=resolved_scanner,
            snapshot_repository=resolved_snapshots,
            audit_log_repository=audit,
        ),
        resolved_scanner,
        resolved_snapshots,
        audit,
    )


def test_creates_new_proposed_latent_skill_with_initial_recurrence(tmp_path) -> None:
    safe_write, scanner, snapshots, audit = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    use_case = TrackLatentSkillUseCase(repository=repository)

    result = use_case.execute(
        TrackLatentSkillCommand(
            name="TDD recorrente",
            description="Usuario sempre pede para escrever testes RED antes de implementar",
            scope=LatentSkillScope.project,
            origin="cli",
            evidence_summary="Pedido em conversa sobre nova story",
            tags=["tdd", "story"],
            metadata={"source": "agent"},
        )
    )

    stored = repository.read(result.latent_skill.id)
    assert stored.status == LatentSkillStatus.proposed
    assert stored.recurrence_count == 1
    assert stored.metadata["source"] == "agent"
    assert stored.metadata["tags"] == ["tdd", "story"]
    assert stored.metadata["evidence"] == [
        {"origin": "cli", "summary": "Pedido em conversa sobre nova story"}
    ]
    assert result.matched_existing is False
    assert scanner.scanned
    assert snapshots.written
    assert result.audit_reference == audit.written[0].audit_reference


def test_increments_recurrence_for_high_confidence_match(tmp_path) -> None:
    existing = make_skill(recurrence_count=2)
    safe_write, _scanner, _snapshots, audit = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    repository.write(existing)
    use_case = TrackLatentSkillUseCase(repository=repository)

    result = use_case.execute(
        TrackLatentSkillCommand(
            name="TDD recorrente",
            description="Usuario pede red green refactor sempre antes da implementacao",
            scope=LatentSkillScope.project,
            origin="mcp",
            evidence_summary="Segundo pedido quase igual",
            tags=["tdd"],
        )
    )

    stored = repository.read(existing.id)
    assert result.latent_skill.id == existing.id
    assert result.matched_existing is True
    assert stored.recurrence_count == EXPECTED_INCREMENTED_RECURRENCE
    assert stored.metadata["evidence"][-1] == {
        "origin": "mcp",
        "summary": "Segundo pedido quase igual",
    }
    assert audit.written[0].action == "write_latent_skill"


def test_ambiguous_occurrence_creates_separate_candidate(tmp_path) -> None:
    existing = make_skill(
        name="Checklist de QA",
        description="Usuario sempre pede checklist de QA antes de revisar",
        tags=["qa"],
    )
    repository = RecordingLatentSkillRepository([existing])
    use_case = TrackLatentSkillUseCase(repository=repository)

    result = use_case.execute(
        TrackLatentSkillCommand(
            name="Briefing de arquitetura",
            description="Usuario pede decomposicao arquitetural detalhada",
            scope=LatentSkillScope.project,
            origin="cli",
            evidence_summary="Pedido com escopo diferente",
            tags=["architecture"],
        )
    )

    assert result.matched_existing is False
    assert len(repository.skills) == EXPECTED_AMBIGUOUS_CANDIDATE_COUNT
    assert repository.read(existing.id).recurrence_count == 1


def test_blocks_secret_in_evidence_before_persisting(tmp_path) -> None:
    safe_write, _scanner, snapshots, audit = build_safe_write(
        tmp_path,
        scanner=RecordingScanner(
            SecretDetectedError("blocked", metadata={"kind": "token", "span": (0, 10)})
        ),
    )
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    use_case = TrackLatentSkillUseCase(repository=repository)

    with pytest.raises(SecretDetectedError):
        use_case.execute(
            TrackLatentSkillCommand(
                name="Token workflow",
                description="Usar token abc",
                scope=LatentSkillScope.project,
                origin="cli",
                evidence_summary="token secreto",
            )
        )

    assert repository.list() == []
    assert snapshots.written == []
    assert audit.written[0].result == "blocked"


def test_snapshot_failure_aborts_write(tmp_path) -> None:
    safe_write, _scanner, snapshots, audit = build_safe_write(
        tmp_path,
        snapshots=RecordingSnapshotRepository(StorageError("snapshot unavailable")),
    )
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    use_case = TrackLatentSkillUseCase(repository=repository)

    with pytest.raises(StorageError, match="snapshot unavailable"):
        use_case.execute(
            TrackLatentSkillCommand(
                name="Falha snapshot",
                description="Padrao recorrente",
                scope=LatentSkillScope.project,
                origin="cli",
                evidence_summary="evidencia",
            )
        )

    assert repository.list() == []
    assert snapshots.written == []
    assert audit.written[0].result == "failure"
