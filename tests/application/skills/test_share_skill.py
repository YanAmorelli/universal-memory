from __future__ import annotations

import tomllib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from tests.application.skills.test_create_skill import make_shared_project_root
from tests.application.skills.test_generate_skill import (
    RecordingAuditRepository,
    RecordingScanner,
    RecordingSnapshotRepository,
)
from universal_memory.application.onboarding.setup_project import setup_project
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    CreateSkillCommand,
    CreateSkillUseCase,
    ShareSkillCommand,
    ShareSkillUseCase,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import AgentSkill, AgentSkillStatus, LatentSkillScope
from universal_memory.infrastructure.config import (
    LocalConfigValidationPort,
    LocalProjectLayoutPort,
)
from universal_memory.infrastructure.storage import LocalAgentSkillRepository


def build_shared_use_cases(tmp_path: Path):
    project_root = make_shared_project_root(tmp_path)
    safe_write = SafeWriteUseCase(
        project_root=project_root,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(
        project_root=project_root,
        safe_write_use_case=safe_write,
    )
    create = CreateSkillUseCase(
        project_root=project_root,
        repository=repository,
        safe_write_use_case=safe_write,
    )
    share = ShareSkillUseCase(
        project_root=project_root,
        repository=repository,
        safe_write_use_case=safe_write,
    )
    return project_root, repository, create, share


def test_share_user_facing_skill_copies_private_skill_to_shared_root(tmp_path: Path) -> None:
    project_root, repository, create, share = build_shared_use_cases(tmp_path)
    private_skill = create.execute(
        CreateSkillCommand(
            name="Private Review Helper",
            description="Review implementation changes safely.",
            scope=LatentSkillScope.project,
            origin="test",
            visibility="private",
        )
    )

    result = share.execute(
        ShareSkillCommand(skill_id_or_name=private_skill.slug, origin="test")
    )

    stored = repository.read(result.agent_skill.id)
    assert result.old_canonical_path == ".umem/skills/private-review-helper/SKILL.md"
    assert result.new_canonical_path == "umem/skills/private-review-helper/SKILL.md"
    assert stored.canonical_path == "umem/skills/private-review-helper/SKILL.md"
    assert stored.visibility == "shared"
    assert stored.category == "user-facing"
    assert (project_root / "umem" / "skills" / "private-review-helper" / "SKILL.md").is_file()
    assert (project_root / "umem" / "skills" / "skills.jsonl").is_file()


def test_share_operational_skill_requires_confirmation_and_updates_allowlist(
    tmp_path: Path,
) -> None:
    project_root, repository, create, share = build_shared_use_cases(tmp_path)
    operational = create.execute(
        CreateSkillCommand(
            name="Use Universal Memory",
            description="Operational bootstrap guidance.",
            scope=LatentSkillScope.project,
            origin="test",
            slug="use-universal-memory",
            category="operational",
        )
    )

    with pytest.raises(ValidationFailedError, match="explicit confirmation"):
        share.execute(
            ShareSkillCommand(
                skill_id_or_name=operational.slug,
                category="operational",
                origin="test",
            )
        )

    result = share.execute(
        ShareSkillCommand(
            skill_id_or_name=operational.slug,
            category="operational",
            confirm_operational=True,
            origin="test",
        )
    )

    policy = tomllib.loads((project_root / "umem" / "project.toml").read_text(encoding="utf-8"))
    stored = repository.read(result.agent_skill.id)
    assert policy["shared_operational_skills"] == ["use-universal-memory"]
    assert stored.visibility == "shared"
    assert stored.category == "operational"
    assert stored.metadata["shared_allowed"] is True
    assert stored.canonical_path == "umem/skills/use-universal-memory/SKILL.md"
    assert (project_root / "umem" / "skills" / "use-universal-memory" / "SKILL.md").is_file()


def test_share_default_umem_skill_after_shared_setup_registers_and_allowlists(
    tmp_path: Path,
) -> None:
    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        layout="shared",
    )
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )
    repository = LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    assert repository.list(scope=LatentSkillScope.project) == []

    result = ShareSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    ).execute(
        ShareSkillCommand(
            skill_id_or_name="use-universal-memory",
            category="operational",
            confirm_operational=True,
            origin="test",
        )
    )

    policy = tomllib.loads((tmp_path / "umem" / "project.toml").read_text(encoding="utf-8"))
    stored = repository.read(result.agent_skill.id)
    assert policy["shared_operational_skills"] == ["use-universal-memory"]
    assert stored.slug == "use-universal-memory"
    assert stored.category == "operational"
    assert stored.visibility == "shared"
    assert stored.canonical_path == "umem/skills/use-universal-memory/SKILL.md"


def test_share_existing_operational_skill_default_category_still_requires_confirmation(
    tmp_path: Path,
) -> None:
    _project_root, _repository, create, share = build_shared_use_cases(tmp_path)
    operational = create.execute(
        CreateSkillCommand(
            name="Operational Helper",
            description="Local workflow bootstrap.",
            scope=LatentSkillScope.project,
            origin="test",
            category="operational",
        )
    )

    with pytest.raises(ValidationFailedError, match="explicit confirmation"):
        share.execute(ShareSkillCommand(skill_id_or_name=operational.slug, origin="test"))


def test_reshare_already_shared_operational_skill_repairs_allowlist(tmp_path: Path) -> None:
    project_root, repository, create, share = build_shared_use_cases(tmp_path)
    operational = create.execute(
        CreateSkillCommand(
            name="Operational Helper",
            description="Local workflow bootstrap.",
            scope=LatentSkillScope.project,
            origin="test",
            category="operational",
        )
    )
    share.execute(
        ShareSkillCommand(
            skill_id_or_name=operational.slug,
            category="operational",
            confirm_operational=True,
            origin="test",
        )
    )
    policy_path = project_root / "umem" / "project.toml"
    policy = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    policy["shared_operational_skills"] = []
    policy_path.write_text(_render_simple_toml(policy), encoding="utf-8")

    repaired = share.execute(
        ShareSkillCommand(
            skill_id_or_name=operational.slug,
            confirm_operational=True,
            origin="test",
        )
    )

    repaired_policy = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    stored = repository.read(repaired.agent_skill.id)
    assert repaired_policy["shared_operational_skills"] == [operational.slug]
    assert stored.category == "operational"
    assert stored.visibility == "shared"
    assert "umem/project.toml" in repaired.affected_paths


@pytest.mark.parametrize(
    ("slug", "canonical_path", "match"),
    [
        ("unsafe/slug", ".umem/skills/unsafe/SKILL.md", "Skill slug"),
        ("unsafe-slug", "/unsafe/SKILL.md", "canonical_path"),
        ("unsafe-slug", "../unsafe/SKILL.md", "canonical_path"),
    ],
)
def test_share_rejects_unsafe_slug_or_canonical_path(
    tmp_path: Path,
    slug: str,
    canonical_path: str,
    match: str,
) -> None:
    _project_root, repository, _create, share = build_shared_use_cases(tmp_path)
    skill = _agent_skill(slug=slug, canonical_path=canonical_path)
    repository.write(skill, origin="test")

    with pytest.raises(ValidationFailedError, match=match):
        share.execute(
            ShareSkillCommand(
                skill_id_or_name=skill.id,
                confirm_operational=True,
                origin="test",
            )
        )


def _agent_skill(*, slug: str, canonical_path: str) -> AgentSkill:
    now = datetime.now(UTC)
    return AgentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="Unsafe Skill",
        slug=slug,
        description="Unsafe path fixture.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=canonical_path,
        origin="test",
        audit_reference="audit-1",
        content_hash="hash-1",
        metadata={"visibility": "private", "category": "operational"},
    )


def _render_simple_toml(policy: dict[str, object]) -> str:
    lines = []
    for key, value in policy.items():
        if isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        elif isinstance(value, list):
            rendered = ", ".join(f'"{item}"' for item in value)
            lines.append(f"{key} = [{rendered}]")
        elif isinstance(value, dict):
            lines.append(f"[{key}]")
            for nested_key, nested_value in value.items():
                lines.append(f'{nested_key} = "{nested_value}"')
    return "\n".join(lines) + "\n"
