from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from tests.application.skills.test_generate_skill import (
    RecordingAuditRepository,
    RecordingScanner,
    RecordingSnapshotRepository,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    LatentSkillScope,
    RuntimeRegistry,
    default_runtime_registry,
)
from universal_memory.infrastructure.storage import LocalAgentSkillRepository


@pytest.fixture
def skill_safe_write(tmp_path: Path) -> SafeWriteUseCase:
    return SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )


@pytest.fixture
def agent_skill_repository(
    tmp_path: Path, skill_safe_write: SafeWriteUseCase
) -> LocalAgentSkillRepository:
    return LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=skill_safe_write)


@pytest.fixture
def single_runtime_registry() -> RuntimeRegistry:
    return default_runtime_registry()


def write_valid_skill_tree(
    root: Path,
    slug: str = "review-helper",
    *,
    name: str = "Review Helper",
) -> Path:
    skill_dir = root / ".umem" / "skills" / slug
    references = skill_dir / "references"
    references.mkdir(parents=True)
    (references / "checklist.md").write_text("Review checklist.\n", encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f'name: "{name}"',
                'description: "Review implementation changes safely."',
                "triggers:",
                '  - "review changes"',
                "---",
                "",
                "# Review Helper",
                "",
                "Use [checklist](references/checklist.md).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return skill_dir


def write_invalid_skill_tree(root: Path, slug: str = "broken-helper") -> Path:
    skill_dir = root / ".umem" / "skills" / slug
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: Broken Helper\n---\n\nTODO: finish this skill.\n",
        encoding="utf-8",
    )
    return skill_dir


def sample_agent_skill(
    *,
    name: str = "Review Helper",
    slug: str = "review-helper",
    canonical_path: str | None = None,
    native_installations: list[dict[str, object]] | None = None,
) -> AgentSkill:
    now = datetime.now(UTC)
    return AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name=name,
        slug=slug,
        description="Review implementation changes safely.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=canonical_path or f".umem/skills/{slug}/SKILL.md",
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        native_installations=native_installations or [],
        metadata={"triggers": ["review changes"]},
    )
