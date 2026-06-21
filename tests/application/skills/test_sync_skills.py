from __future__ import annotations

from pathlib import Path

import pytest

from tests.application.skills.test_generate_skill import (
    RecordingAuditRepository,
    RecordingScanner,
    RecordingSnapshotRepository,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    CreateSkillCommand,
    CreateSkillUseCase,
    SyncSkillsCommand,
    SyncSkillsUseCase,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkillScope
from universal_memory.infrastructure.storage import LocalAgentSkillRepository


def _safe_write(tmp_path: Path) -> SafeWriteUseCase:
    return SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=RecordingSnapshotRepository(),
        audit_log_repository=RecordingAuditRepository(),
    )


def _create_skill(tmp_path: Path, *, name: str = "Repair Skill"):
    safe_write = _safe_write(tmp_path)
    repository = LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    result = CreateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    ).execute(
        CreateSkillCommand(
            name=name,
            description="Repair native targets from canonical skill content.",
            scope=LatentSkillScope.project,
            origin="test",
            targets=[],
        )
    )
    return safe_write, repository, result.agent_skill.id


def test_sync_skills_materializes_missing_native_target_and_persists_installation(
    tmp_path: Path,
) -> None:
    safe_write, repository, skill_id = _create_skill(tmp_path)

    result = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    ).execute(SyncSkillsCommand(origin="test", targets=["opencode"]))

    native_file = tmp_path / ".opencode" / "skills" / "repair-skill" / "SKILL.md"
    stored = repository.read(skill_id)
    assert native_file.is_file()
    assert result.skills[0].targets[0]["runtime"] == "opencode"
    assert result.skills[0].targets[0]["status"] == "synced"
    assert stored.native_installations[0]["path"] == ".opencode/skills/repair-skill"
    assert result.affected_paths == [".opencode/skills/repair-skill/SKILL.md"]


def test_sync_skills_default_materializes_agents_native_target(tmp_path: Path) -> None:
    safe_write, repository, skill_id = _create_skill(tmp_path)

    result = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    ).execute(SyncSkillsCommand(origin="test"))

    native_file = tmp_path / ".agents" / "skills" / "repair-skill" / "SKILL.md"
    paths = {
        installation["path"] for installation in repository.read(skill_id).native_installations
    }
    assert native_file.is_file()
    assert ".agents/skills/repair-skill" in paths
    assert ".agents/skills/repair-skill/SKILL.md" in result.affected_paths


def test_sync_skills_codex_target_materializes_agents_native_target(tmp_path: Path) -> None:
    safe_write, repository, skill_id = _create_skill(tmp_path)

    result = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    ).execute(SyncSkillsCommand(origin="test", targets=["codex"]))

    native_file = tmp_path / ".agents" / "skills" / "repair-skill" / "SKILL.md"
    stored = repository.read(skill_id)
    assert native_file.is_file()
    assert result.skills[0].targets[0]["runtime"] == "codex"
    assert result.skills[0].targets[0]["status"] == "synced"
    assert stored.native_installations[0]["path"] == ".agents/skills/repair-skill"
    assert result.affected_paths == [".agents/skills/repair-skill/SKILL.md"]


def test_sync_one_skill_by_exact_name_only_syncs_selected_skill(tmp_path: Path) -> None:
    safe_write, repository, first_id = _create_skill(tmp_path, name="First Skill")
    _create_skill(tmp_path, name="Second Skill")

    result = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    ).execute(
        SyncSkillsCommand(
            skill_id_or_name="first skill",
            origin="test",
            targets=["opencode"],
        )
    )

    assert [skill.skill_id for skill in result.skills] == [first_id]
    assert (tmp_path / ".opencode" / "skills" / "first-skill" / "SKILL.md").is_file()
    assert not (tmp_path / ".opencode" / "skills" / "second-skill").exists()


def test_sync_keeps_managed_drift_by_default(tmp_path: Path) -> None:
    safe_write, repository, skill_id = _create_skill(tmp_path)
    use_case = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    )
    use_case.execute(SyncSkillsCommand(origin="test", targets=["opencode"]))
    native_file = tmp_path / ".opencode" / "skills" / "repair-skill" / "SKILL.md"
    native_file.write_text("manual drift", encoding="utf-8")

    result = use_case.execute(SyncSkillsCommand(origin="test", targets=["opencode"]))

    assert native_file.read_text(encoding="utf-8") == "manual drift"
    assert result.skills[0].targets[0]["status"] == "drift_kept"
    assert result.warnings
    assert repository.read(skill_id).native_installations[0]["drift_detected"] is True


def test_sync_preserves_unmanaged_native_target_without_persisting_baseline(tmp_path: Path) -> None:
    safe_write, repository, skill_id = _create_skill(tmp_path)
    native_file = tmp_path / ".opencode" / "skills" / "repair-skill" / "SKILL.md"
    native_file.parent.mkdir(parents=True)
    native_file.write_text("manual native", encoding="utf-8")
    use_case = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    )

    result = use_case.execute(SyncSkillsCommand(origin="test", targets=["opencode"]))
    overwrite_result = use_case.execute(
        SyncSkillsCommand(origin="test", targets=["opencode"], drift_decision="overwrite")
    )

    assert native_file.read_text(encoding="utf-8") == "manual native"
    assert result.skills[0].targets[0]["status"] == "unmanaged_native"
    assert overwrite_result.skills[0].targets[0]["status"] == "unmanaged_native"
    assert any("not managed by UMEM" in warning for warning in result.warnings)
    assert repository.read(skill_id).native_installations == []


def test_target_filtered_sync_preserves_omitted_managed_installations(tmp_path: Path) -> None:
    safe_write, repository, skill_id = _create_skill(tmp_path)
    use_case = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    )

    use_case.execute(SyncSkillsCommand(origin="test", targets=["opencode"]))
    use_case.execute(SyncSkillsCommand(origin="test", targets=["claude_code"]))

    paths = {
        installation["path"] for installation in repository.read(skill_id).native_installations
    }
    assert paths == {
        ".opencode/skills/repair-skill",
        ".claude/skills/repair-skill",
    }


def test_sync_rejects_missing_canonical_file_before_native_write(tmp_path: Path) -> None:
    safe_write, repository, _skill_id = _create_skill(tmp_path)
    (tmp_path / ".umem" / "skills" / "repair-skill" / "SKILL.md").unlink()

    with pytest.raises(ValidationFailedError):
        SyncSkillsUseCase(
            project_root=tmp_path,
            repository=repository,
            safe_write_use_case=safe_write,
        ).execute(SyncSkillsCommand(origin="test", targets=["opencode"]))

    assert not (tmp_path / ".opencode" / "skills" / "repair-skill").exists()


def test_sync_rejects_missing_selector_and_unsupported_target_before_write(tmp_path: Path) -> None:
    safe_write, repository, _skill_id = _create_skill(tmp_path)
    use_case = SyncSkillsUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    )

    with pytest.raises(ValidationFailedError):
        use_case.execute(SyncSkillsCommand(skill_id_or_name="missing", origin="test"))
    with pytest.raises(ValidationFailedError):
        use_case.execute(SyncSkillsCommand(origin="test", targets=["unsupported"]))

    assert not (tmp_path / ".opencode" / "skills" / "repair-skill").exists()
