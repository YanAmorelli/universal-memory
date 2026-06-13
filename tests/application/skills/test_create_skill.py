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
from universal_memory.domain import StorageError
from universal_memory.domain.entities import AgentSkillStatus, LatentSkillScope, LatentSkillStatus
from universal_memory.domain.ports import AgentSkillRepository
from universal_memory.infrastructure.storage import (
    LocalAgentSkillRepository,
    LocalLatentSkillRepository,
)


def test_create_skill_directly_writes_canonical_quoted_yaml_and_syncs_native(
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
    assert result.native_installations
    assert "sync_native_skill" in {event.action for event in audit.written}
    assert result.latent_skill.status == LatentSkillStatus.active


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
    assert result.native_installations


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
