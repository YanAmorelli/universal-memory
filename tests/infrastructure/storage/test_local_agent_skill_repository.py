from __future__ import annotations

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
