from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from tests.application.skills.test_generate_skill import (
    RecordingAuditRepository,
    RecordingScanner,
    RecordingSnapshotRepository,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain.entities import AgentSkill, AgentSkillStatus, LatentSkillScope
from universal_memory.infrastructure.storage import LocalAgentSkillRepository


def test_local_agent_skill_repository_writes_project_skills_jsonl(tmp_path: Path) -> None:
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Launch Funnel Operator",
        slug="launch-funnel-operator",
        description="Operate launch funnel.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/launch-funnel-operator/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
    )

    repository.write(skill, origin="test")

    assert repository.read(skill.id) == skill
    assert repository.list(scope=LatentSkillScope.project) == [skill]
    assert (tmp_path / ".umem" / "memory" / "skills.jsonl").read_text(encoding="utf-8")


def test_shared_layout_writes_user_facing_skill_registry_to_visible_root(
    shared_project_root: Path,
) -> None:
    safe_write = SafeWriteUseCase(
        project_root=shared_project_root,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(
        project_root=shared_project_root,
        safe_write_use_case=safe_write,
    )
    now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Review Helper",
        slug="review-helper",
        description="Guide repository reviews.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path="umem/skills/review-helper/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"visibility": "shared", "category": "user-facing"},
    )

    repository.write(skill, origin="test")

    assert repository.read(skill.id) == skill
    assert (shared_project_root / "umem" / "skills" / "skills.jsonl").is_file()
    assert not (shared_project_root / ".umem" / "memory" / "skills.jsonl").exists()


def test_shared_layout_operational_skill_registry_stays_private(
    shared_project_root: Path,
) -> None:
    safe_write = SafeWriteUseCase(
        project_root=shared_project_root,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(
        project_root=shared_project_root,
        safe_write_use_case=safe_write,
    )
    now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Universal Memory Bootstrap",
        slug="use-universal-memory",
        description="Local agent bootstrap.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/use-universal-memory/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"visibility": "private", "category": "operational"},
    )

    repository.write(skill, origin="test")

    assert repository.read(skill.id) == skill
    assert (shared_project_root / ".umem" / "memory" / "skills.jsonl").is_file()
    assert not (shared_project_root / "umem" / "skills" / "skills.jsonl").exists()


def test_shared_layout_reads_shared_skill_before_legacy_with_overlap_label(
    shared_project_root: Path,
) -> None:
    safe_write = SafeWriteUseCase(
        project_root=shared_project_root,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(
        project_root=shared_project_root,
        safe_write_use_case=safe_write,
    )
    now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    legacy = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Review Helper",
        slug="review-helper",
        description="Legacy helper.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/review-helper/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-legacy",
        native_installations=[],
        metadata={"visibility": "private", "category": "user-facing"},
    )
    shared = legacy.model_copy(
        update={
            "id": str(uuid4()),
            "description": "Shared helper.",
            "canonical_path": "umem/skills/review-helper/SKILL.md",
            "content_hash": "hash-shared",
            "metadata": {"visibility": "shared", "category": "user-facing"},
        }
    )
    private_path = shared_project_root / ".umem" / "memory" / "skills.jsonl"
    shared_path = shared_project_root / "umem" / "skills" / "skills.jsonl"
    private_path.write_text(legacy.model_dump_json() + "\n", encoding="utf-8")
    shared_path.write_text(shared.model_dump_json() + "\n", encoding="utf-8")

    skills = repository.list(scope=LatentSkillScope.project)

    assert len(skills) == 1
    assert skills[0].model_dump(exclude={"metadata"}) == shared.model_dump(exclude={"metadata"})
    assert skills[0].metadata["layout_overlap"] == {
        "active_path": "umem/skills/skills.jsonl",
        "shadowed_path": ".umem/memory/skills.jsonl",
        "active_precedence": "shared_over_legacy",
    }


def test_shared_layout_remove_operational_skill_updates_private_registry_only(
    shared_project_root: Path,
) -> None:
    safe_write = SafeWriteUseCase(
        project_root=shared_project_root,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(
        project_root=shared_project_root,
        safe_write_use_case=safe_write,
    )
    now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Universal Memory Bootstrap",
        slug="use-universal-memory",
        description="Local agent bootstrap.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/use-universal-memory/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"visibility": "private", "category": "operational"},
    )
    repository.write(skill, origin="test")

    repository.remove(skill.id, scope=LatentSkillScope.project, origin="test")

    private_path = shared_project_root / ".umem" / "memory" / "skills.jsonl"
    assert private_path.read_text(encoding="utf-8") == ""
    assert not (shared_project_root / "umem" / "skills" / "skills.jsonl").exists()


def test_shared_layout_replace_existing_private_skill_preserves_private_registry(
    shared_project_root: Path,
) -> None:
    safe_write = SafeWriteUseCase(
        project_root=shared_project_root,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(
        project_root=shared_project_root,
        safe_write_use_case=safe_write,
    )
    now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Private Helper",
        slug="private-helper",
        description="Private helper.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/private-helper/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"visibility": "private", "category": "user-facing"},
    )
    repository.write(skill, origin="test")
    updated = skill.model_copy(update={"description": "Updated private helper."})

    repository.replace(updated, origin="test")

    private_path = shared_project_root / ".umem" / "memory" / "skills.jsonl"
    stored = json.loads(private_path.read_text(encoding="utf-8").splitlines()[0])
    assert stored["description"] == "Updated private helper."
    assert not (shared_project_root / "umem" / "skills" / "skills.jsonl").exists()


def test_shared_layout_write_existing_private_skill_ignores_incoming_shared_path(
    shared_project_root: Path,
) -> None:
    safe_write = SafeWriteUseCase(
        project_root=shared_project_root,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(
        project_root=shared_project_root,
        safe_write_use_case=safe_write,
    )
    now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Private Helper",
        slug="private-helper",
        description="Private helper.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/private-helper/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"visibility": "private", "category": "user-facing"},
    )
    repository.write(skill, origin="test")
    incoming = skill.model_copy(
        update={
            "description": "Incoming shared helper.",
            "canonical_path": "umem/skills/private-helper/SKILL.md",
            "metadata": {"visibility": "shared", "category": "user-facing"},
        }
    )

    repository.write(incoming, origin="test")

    private_path = shared_project_root / ".umem" / "memory" / "skills.jsonl"
    shared_path = shared_project_root / "umem" / "skills" / "skills.jsonl"
    private_records = [
        json.loads(line) for line in private_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["id"] for record in private_records] == [skill.id]
    assert private_records[0]["description"] == "Incoming shared helper."
    assert private_records[0]["canonical_path"] == "umem/skills/private-helper/SKILL.md"
    assert private_records[0]["metadata"]["visibility"] == "shared"
    assert not shared_path.exists()
    assert [stored.id for stored in repository.list(scope=LatentSkillScope.project)] == [skill.id]


def test_shared_layout_replace_existing_private_skill_ignores_incoming_shared_path(
    shared_project_root: Path,
) -> None:
    safe_write = SafeWriteUseCase(
        project_root=shared_project_root,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(
        project_root=shared_project_root,
        safe_write_use_case=safe_write,
    )
    now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    skill = AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Private Helper",
        slug="private-helper",
        description="Private helper.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/private-helper/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=[],
        metadata={"visibility": "private", "category": "user-facing"},
    )
    repository.write(skill, origin="test")
    incoming = skill.model_copy(
        update={
            "description": "Incoming shared helper.",
            "canonical_path": "umem/skills/private-helper/SKILL.md",
            "metadata": {"visibility": "shared", "category": "user-facing"},
        }
    )

    repository.replace(incoming, origin="test")

    private_path = shared_project_root / ".umem" / "memory" / "skills.jsonl"
    shared_path = shared_project_root / "umem" / "skills" / "skills.jsonl"
    private_records = [
        json.loads(line) for line in private_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["id"] for record in private_records] == [skill.id]
    assert private_records[0]["description"] == "Incoming shared helper."
    assert private_records[0]["canonical_path"] == "umem/skills/private-helper/SKILL.md"
    assert private_records[0]["metadata"]["visibility"] == "shared"
    assert not shared_path.exists()
    assert [stored.id for stored in repository.list(scope=LatentSkillScope.project)] == [skill.id]
