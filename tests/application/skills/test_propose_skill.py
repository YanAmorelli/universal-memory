from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    ProposeSkillCommand,
    ProposeSkillDecision,
    ProposeSkillUseCase,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import (
    AuditEvent,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    Snapshot,
)
from universal_memory.domain.ports import AuditLogRepository, SecretScannerPort, SnapshotRepository
from universal_memory.infrastructure.config.toml_loader import load_config
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


def make_skill(*, status: LatentSkillStatus = LatentSkillStatus.proposed) -> LatentSkill:
    timestamp = datetime.now(UTC)
    return LatentSkill(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        name="TDD recorrente",
        description="Usuario pede sempre ciclo red green refactor antes de implementar",
        scope=LatentSkillScope.project,
        status=status,
        recurrence_count=3,
        metadata={
            "tags": ["tdd", "story"],
            "evidence": [
                {"origin": "cli", "summary": "Pedido em story anterior"},
                {"origin": "mcp", "summary": "Pedido recorrente em review"},
            ],
        },
    )


def build_use_case(
    tmp_path: Path,
) -> tuple[
    ProposeSkillUseCase,
    LocalLatentSkillRepository,
    RecordingSnapshotRepository,
    RecordingAuditRepository,
]:
    safe_write, snapshots, audit = build_safe_write(tmp_path)
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    return (
        ProposeSkillUseCase(
            project_root=tmp_path,
            repository=repository,
            safe_write_use_case=safe_write,
        ),
        repository,
        snapshots,
        audit,
    )


def test_preview_presents_explicit_choices_and_evidence_without_mutation(tmp_path: Path) -> None:
    use_case, repository, snapshots, audit = build_use_case(tmp_path)
    skill = make_skill()
    repository.write(skill)
    snapshots.written.clear()
    audit.written.clear()

    result = use_case.execute(ProposeSkillCommand(latent_skill_id=skill.id, origin="cli"))

    assert result.requires_decision is True
    assert result.choices == ["yes", "always", "no"]
    assert result.proposal["suggested_name"] == "TDD recorrente"
    assert result.proposal["purpose"] == skill.description
    assert result.proposal["scope"] == "project"
    assert result.proposal["evidence"] == [
        "Pedido em story anterior",
        "Pedido recorrente em review",
    ]
    assert repository.read(skill.id).status == LatentSkillStatus.proposed
    assert snapshots.written == []
    assert audit.written == []


def test_sim_accepts_once_and_keeps_future_occurrences_subject_to_confirmation(
    tmp_path: Path,
) -> None:
    use_case, repository, _snapshots, audit = build_use_case(tmp_path)
    skill = make_skill()
    repository.write(skill)

    result = use_case.execute(
        ProposeSkillCommand(
            latent_skill_id=skill.id,
            decision=ProposeSkillDecision.sim,
            origin="cli",
        )
    )

    stored = repository.read(skill.id)
    assert stored.status == LatentSkillStatus.active
    assert stored.metadata["approval"]["decision"] == "yes"
    assert result.accepted is True
    assert result.auto_approval_recorded is False
    assert load_config(tmp_path).project_data.get("skills", {}) == {}
    assert audit.written[-1].action == "propose_skill_decision"


def test_sempre_accepts_and_records_reversible_auto_approval_preference(
    tmp_path: Path,
) -> None:
    use_case, repository, snapshots, audit = build_use_case(tmp_path)
    skill = make_skill()
    repository.write(skill)

    result = use_case.execute(
        ProposeSkillCommand(
            latent_skill_id=skill.id,
            decision=ProposeSkillDecision.sempre,
            origin="cli",
        )
    )

    stored = repository.read(skill.id)
    config = load_config(tmp_path).project_data
    preference = config["skills"]["auto_approval"]["project:tdd-recorrente"]
    assert stored.status == LatentSkillStatus.active
    assert preference["name"] == "TDD recorrente"
    assert preference["scope"] == "project"
    assert preference["decision"] == "always"
    assert preference["reversible"] is True
    assert result.accepted is True
    assert result.auto_approval_recorded is True
    assert ".umem/config.toml" in {snapshot.relative_path for snapshot in snapshots.written}
    assert "update_skill_auto_approval" in {event.action for event in audit.written}
    assert result.rollback_hint == "Use the recorded snapshot to revert the preference."


def test_nao_ignores_latent_skill_without_creating_skill_files(tmp_path: Path) -> None:
    use_case, repository, _snapshots, _audit = build_use_case(tmp_path)
    skill = make_skill()
    repository.write(skill)

    result = use_case.execute(
        ProposeSkillCommand(
            latent_skill_id=skill.id,
            decision=ProposeSkillDecision.nao,
            origin="cli",
        )
    )

    stored = repository.read(skill.id)
    assert stored.status == LatentSkillStatus.ignored
    assert stored.metadata["approval"]["decision"] == "no"
    assert result.accepted is False
    assert not (tmp_path / ".umem" / "skills").exists()


def test_slug_fallback_for_special_characters() -> None:
    assert ProposeSkillUseCase._slug("!!!") == "skill-6dd07555"
    assert ProposeSkillUseCase._slug("???") == "skill-0d1b08c3"
    assert ProposeSkillUseCase._slug("Normal-Name") == "normal-name"


def test_propose_skill_validation_raises_on_invalid_initial_status(tmp_path: Path) -> None:
    use_case, repository, _snapshots, _audit = build_use_case(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)

    with pytest.raises(ValidationFailedError) as exc:
        use_case.execute(
            ProposeSkillCommand(
                latent_skill_id=skill.id,
                decision=ProposeSkillDecision.sim,
                origin="cli",
            )
        )
    assert "Cannot propose or decide" in str(exc.value)


def test_record_auto_approval_transaction_rollback_on_failure(tmp_path: Path) -> None:
    use_case, repository, _snapshots, _audit = build_use_case(tmp_path)
    skill = make_skill()
    repository.write(skill)

    # Monkeypatch to simulate failure during config write
    def failing_record(*args, **kwargs):
        raise OSError("Simulated config write failure")

    use_case._record_auto_approval = failing_record

    with pytest.raises(OSError):
        use_case.execute(
            ProposeSkillCommand(
                latent_skill_id=skill.id,
                decision=ProposeSkillDecision.sempre,
                origin="cli",
            )
        )

    # State of the latent skill must remain 'proposed' due to transaction rollback
    assert repository.read(skill.id).status == LatentSkillStatus.proposed
