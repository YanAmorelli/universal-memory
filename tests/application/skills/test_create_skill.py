from __future__ import annotations

from pathlib import Path

from tests.application.skills.test_generate_skill import (
    RecordingAuditRepository,
    RecordingScanner,
    RecordingSnapshotRepository,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    CreateSkillCommand,
    CreateSkillUseCase,
)
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import AgentSkillStatus, LatentSkillScope, LatentSkillStatus
from universal_memory.domain.ports import AgentSkillRepository
from universal_memory.infrastructure.storage import (
    LocalAgentSkillRepository,
    LocalLatentSkillRepository,
)


def make_shared_project_root(tmp_path: Path) -> Path:
    (tmp_path / ".umem").mkdir()
    (tmp_path / "umem").mkdir()
    (tmp_path / "umem" / "project.toml").write_text(
        "[project]\nlayout = \"shared\"\nversion = \"1\"\n",
        encoding="utf-8",
    )
    return tmp_path


def test_create_skill_directly_writes_canonical_quoted_yaml_without_native_sync(
    tmp_path: Path,
) -> None:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    repository = LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    latent_repository = LocalLatentSkillRepository(
        project_root=tmp_path, safe_write_use_case=safe_write
    )
    use_case = CreateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    )

    result = use_case.execute(
        CreateSkillCommand(
            name="Launch Funnel Operator",
            description="Operate launch funnel: CTAs, UTMs, metrics, and readiness gates.",
            scope=LatentSkillScope.project,
            origin="test",
            triggers=["when creating launch schedules"],
        )
    )

    skill_file = tmp_path / ".umem" / "skills" / "launch-funnel-operator" / "SKILL.md"
    markdown = skill_file.read_text(encoding="utf-8")
    stored = repository.read(result.agent_skill.id)

    assert (
        'description: "Operate launch funnel: CTAs, UTMs, metrics, and readiness gates."'
        in markdown
    )
    assert 'name: "Launch Funnel Operator"' in markdown
    assert result.skill_file == ".umem/skills/launch-funnel-operator/SKILL.md"
    assert stored.status == AgentSkillStatus.active
    assert stored.metadata["creation_flow"] == "direct"
    assert stored.metadata["recommendation_flow"] is False
    assert stored.metadata["triggers"] == ["when creating launch schedules"]
    assert stored.canonical_path == ".umem/skills/launch-funnel-operator/SKILL.md"
    assert "raw_markdown" not in stored.metadata
    assert latent_repository.list() == []
    assert (tmp_path / ".umem" / "memory" / "skills.jsonl").is_file()
    assert not (tmp_path / ".umem" / "memory" / "latent_skills.jsonl").is_file()
    assert result.native_installations == []
    assert not (tmp_path / ".agents" / "skills" / "launch-funnel-operator").exists()
    assert "sync_native_skill" not in {event.action for event in audit.written}
    assert result.latent_skill.status == LatentSkillStatus.active


def test_create_project_skill_defaults_to_shared_canonical_path_in_shared_layout(
    tmp_path: Path,
) -> None:
    shared_project_root = make_shared_project_root(tmp_path)
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=shared_project_root,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    repository = LocalAgentSkillRepository(
        project_root=shared_project_root,
        safe_write_use_case=safe_write,
    )
    use_case = CreateSkillUseCase(
        project_root=shared_project_root,
        repository=repository,
        safe_write_use_case=safe_write,
    )

    result = use_case.execute(
        CreateSkillCommand(
            name="Review Helper",
            description="Guide repository reviews.",
            scope=LatentSkillScope.project,
            origin="test",
        )
    )

    assert result.skill_file == "umem/skills/review-helper/SKILL.md"
    assert result.agent_skill.canonical_path == "umem/skills/review-helper/SKILL.md"
    assert result.agent_skill.metadata["visibility"] == "shared"
    assert result.agent_skill.metadata["category"] == "user-facing"
    assert (shared_project_root / "umem" / "skills" / "review-helper" / "SKILL.md").is_file()
    assert (shared_project_root / "umem" / "skills" / "skills.jsonl").is_file()
    assert not (shared_project_root / ".umem" / "skills" / "review-helper").exists()


def test_create_operational_project_skill_stays_private_in_shared_layout(
    tmp_path: Path,
) -> None:
    shared_project_root = make_shared_project_root(tmp_path)
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
    use_case = CreateSkillUseCase(
        project_root=shared_project_root,
        repository=repository,
        safe_write_use_case=safe_write,
    )

    result = use_case.execute(
        CreateSkillCommand(
            name="Local Bootstrap Helper",
            description="Local agent bootstrap.",
            scope=LatentSkillScope.project,
            origin="test",
            category="operational",
        )
    )

    assert result.skill_file == ".umem/skills/local-bootstrap-helper/SKILL.md"
    assert result.agent_skill.metadata["visibility"] == "private"
    assert result.agent_skill.metadata["category"] == "operational"
    assert (
        shared_project_root / ".umem" / "skills" / "local-bootstrap-helper" / "SKILL.md"
    ).is_file()
    assert not (shared_project_root / "umem" / "skills" / "local-bootstrap-helper").exists()


def test_create_operational_project_skill_rejects_shared_visibility_in_shared_layout(
    tmp_path: Path,
) -> None:
    shared_project_root = make_shared_project_root(tmp_path)
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
    use_case = CreateSkillUseCase(
        project_root=shared_project_root,
        repository=repository,
        safe_write_use_case=safe_write,
    )

    try:
        use_case.execute(
            CreateSkillCommand(
                name="Shared Bootstrap Helper",
                description="Local agent bootstrap.",
                scope=LatentSkillScope.project,
                origin="test",
                visibility="shared",
                category="operational",
            )
        )
    except ValidationFailedError as error:
        assert "operational skills cannot be shared by create" in str(error)
    else:
        raise AssertionError("expected validation error for shared operational skill create")

    assert not (shared_project_root / "umem" / "skills" / "shared-bootstrap-helper").exists()


def test_create_global_skill_reads_canonical_content_from_global_root(tmp_path: Path) -> None:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    repository = LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    use_case = CreateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
        global_safe_write_use_case=repository.global_safe_write_use_case,
    )

    result = use_case.execute(
        CreateSkillCommand(
            name="Global Review Operator",
            description="Review global workflows.",
            scope=LatentSkillScope.global_,
            origin="test",
            triggers=["when reviewing global workflows"],
        )
    )

    global_skill_file = (
        repository.global_data_root / "skills" / "global-review-operator" / "SKILL.md"
    )
    assert global_skill_file.is_file()
    assert not (tmp_path / "skills" / "global-review-operator" / "SKILL.md").exists()
    assert result.skill_file == "skills/global-review-operator/SKILL.md"
    assert repository.read(result.agent_skill.id).scope == LatentSkillScope.global_
    assert result.native_installations == []


class FailingAgentSkillRepository(AgentSkillRepository):
    def read(self, id: str):
        raise KeyError(id)

    def list(self, scope=None, status=None):
        return []

    def write(self, entity, *, origin: str = "repository"):
        raise StorageError("simulated registry failure")


def test_create_skill_removes_canonical_file_when_registry_write_fails(tmp_path: Path) -> None:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    use_case = CreateSkillUseCase(
        project_root=tmp_path,
        repository=FailingAgentSkillRepository(),
        safe_write_use_case=safe_write,
    )

    try:
        use_case.execute(
            CreateSkillCommand(
                name="Broken Skill",
                description="Fails registry write.",
                scope=LatentSkillScope.project,
                origin="test",
            )
        )
    except StorageError:
        pass
    else:
        raise AssertionError("Expected registry failure")

    assert not (tmp_path / ".umem" / "skills" / "broken-skill" / "SKILL.md").exists()
    assert not (tmp_path / ".claude" / "skills" / "broken-skill" / "SKILL.md").exists()
    assert not (tmp_path / ".opencode" / "skills" / "broken-skill" / "SKILL.md").exists()
    assert not (tmp_path / ".agents" / "skills" / "broken-skill" / "SKILL.md").exists()
    assert not (tmp_path / ".umem" / "memory" / "skills.jsonl").exists()


def test_create_skill_keeps_unmanaged_native_target_without_overwrite(tmp_path: Path) -> None:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    repository = LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    use_case = CreateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    )
    native_file = tmp_path / ".opencode" / "skills" / "existing-skill" / "SKILL.md"
    native_file.parent.mkdir(parents=True)
    native_file.write_text("manual native content", encoding="utf-8")

    result = use_case.execute(
        CreateSkillCommand(
            name="Existing Skill",
            description="Should not overwrite unmanaged native target.",
            scope=LatentSkillScope.project,
            origin="test",
            sync=True,
        )
    )

    assert native_file.read_text(encoding="utf-8") == "manual native content"
    assert any("not managed by UMEM" in warning for warning in result.warnings)
    assert (tmp_path / ".umem" / "skills" / "existing-skill" / "SKILL.md").is_file()


def test_create_skill_can_disable_native_targets(tmp_path: Path) -> None:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    repository = LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    use_case = CreateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    )

    result = use_case.execute(
        CreateSkillCommand(
            name="Canonical Only",
            description="Create only the canonical UMEM skill.",
            scope=LatentSkillScope.project,
            origin="test",
            targets=[],
        )
    )

    assert result.native_installations == []
    assert result.affected_paths == [".umem/skills/canonical-only/SKILL.md"]
    assert not (tmp_path / ".opencode" / "skills" / "canonical-only").exists()
    assert not (tmp_path / ".agents" / "skills" / "canonical-only").exists()
