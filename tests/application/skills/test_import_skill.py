from __future__ import annotations

from pathlib import Path

import pytest

from tests.application.skills.test_create_skill import FailingAgentSkillRepository
from tests.application.skills.test_generate_skill import (
    RecordingAuditRepository,
    RecordingScanner,
    RecordingSnapshotRepository,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import (
    GetSkillDetailCommand,
    GetSkillDetailUseCase,
    ImportSkillCommand,
    ImportSkillUseCase,
    ListSkillsCommand,
    ListSkillsUseCase,
)
from universal_memory.domain import SecretDetectedError, StorageError, ValidationFailedError
from universal_memory.domain.entities import AgentSkillStatus, LatentSkillScope
from universal_memory.domain.ports import SecretScannerPort
from universal_memory.infrastructure.storage import (
    LocalAgentSkillRepository,
    LocalLatentSkillRepository,
)


def test_import_skill_copies_directory_and_registers_canonical_record(tmp_path: Path) -> None:
    use_case, repository, _safe_write = build_use_case(tmp_path)
    source = write_source_skill(tmp_path / "native" / "skills" / "review-helper")
    (source / "references").mkdir()
    (source / "references" / "guide.md").write_text("Use careful review.\n", encoding="utf-8")

    result = use_case.execute(
        ImportSkillCommand(path=source, scope=LatentSkillScope.project, origin="test")
    )

    stored = repository.read(result.agent_skill.id)
    assert (tmp_path / ".umem" / "skills" / "review-helper" / "SKILL.md").is_file()
    assert (tmp_path / ".umem" / "skills" / "review-helper" / "references" / "guide.md").is_file()
    assert stored.status == AgentSkillStatus.active
    assert stored.origin == "test"
    assert stored.metadata["creation_flow"] == "import"
    assert stored.metadata["recommendation_flow"] is False
    assert stored.metadata["triggers"] == ["when reviewing code"]
    assert stored.metadata["import_source"] == "native/skills/review-helper"
    assert result.skill_file == ".umem/skills/review-helper/SKILL.md"
    assert ".umem/skills/review-helper/references/guide.md" in result.created_paths
    assert not (tmp_path / ".umem" / "memory" / "latent_skills.jsonl").exists()


def test_import_skill_accepts_skill_file_input_and_list_detail_surface_it(tmp_path: Path) -> None:
    use_case, agent_repository, _safe_write = build_use_case(tmp_path)
    latent_repository = LocalLatentSkillRepository(
        project_root=tmp_path, safe_write_use_case=_safe_write
    )
    source = write_source_skill(tmp_path / "local-skill")

    result = use_case.execute(
        ImportSkillCommand(
            path=source / "SKILL.md",
            scope=LatentSkillScope.project,
            origin="test",
        )
    )
    listed = ListSkillsUseCase(
        project_root=tmp_path,
        repository=latent_repository,
        agent_skill_repository=agent_repository,
    ).execute(ListSkillsCommand())
    detail = GetSkillDetailUseCase(
        project_root=tmp_path,
        repository=latent_repository,
        agent_skill_repository=agent_repository,
    ).execute(GetSkillDetailCommand(name_or_id="review-helper"))

    assert [skill.name for skill in listed.skills] == ["Review Helper"]
    assert detail.name == "Review Helper"
    assert detail.relative_path == result.skill_file


@pytest.mark.parametrize(
    "markdown",
    [
        "# Missing frontmatter\n",
        '---\nname: ""\ndescription: "Valid"\n---\n',
        "---\nname: Valid\n description: Broken\n---\n",
    ],
)
def test_import_skill_rejects_invalid_frontmatter_before_writing(
    tmp_path: Path, markdown: str
) -> None:
    use_case, _repository, _safe_write = build_use_case(tmp_path)
    source = tmp_path / "bad-skill"
    source.mkdir()
    (source / "SKILL.md").write_text(markdown, encoding="utf-8")

    with pytest.raises(ValidationFailedError):
        use_case.execute(
            ImportSkillCommand(path=source, scope=LatentSkillScope.project, origin="test")
        )

    assert not (tmp_path / ".umem" / "skills").exists()
    assert not (tmp_path / ".umem" / "memory" / "skills.jsonl").exists()


def test_import_skill_rejects_duplicate_slug_without_overwrite(tmp_path: Path) -> None:
    use_case, _repository, _safe_write = build_use_case(tmp_path)
    source = write_source_skill(tmp_path / "source")
    use_case.execute(ImportSkillCommand(path=source, scope=LatentSkillScope.project, origin="test"))
    duplicate = write_source_skill(tmp_path / "duplicate")

    with pytest.raises(ValidationFailedError, match="conflict"):
        use_case.execute(
            ImportSkillCommand(path=duplicate, scope=LatentSkillScope.project, origin="test")
        )


def test_import_skill_blocks_secret_before_persistence(tmp_path: Path) -> None:
    scanner = BlockingScanner()
    use_case, _repository, _safe_write = build_use_case(tmp_path, scanner=scanner)
    source = write_source_skill(tmp_path / "source")

    with pytest.raises(SecretDetectedError):
        use_case.execute(
            ImportSkillCommand(path=source, scope=LatentSkillScope.project, origin="test")
        )

    assert not (tmp_path / ".umem" / "skills" / "review-helper").exists()
    assert not (tmp_path / ".umem" / "memory" / "skills.jsonl").exists()


def test_import_skill_cleans_up_canonical_files_when_registry_write_fails(tmp_path: Path) -> None:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    use_case = ImportSkillUseCase(
        project_root=tmp_path,
        repository=FailingAgentSkillRepository(),
        safe_write_use_case=safe_write,
    )
    source = write_source_skill(tmp_path / "source")
    (source / "references").mkdir()
    (source / "references" / "guide.md").write_text("Guide\n", encoding="utf-8")

    with pytest.raises(StorageError):
        use_case.execute(
            ImportSkillCommand(path=source, scope=LatentSkillScope.project, origin="test")
        )

    assert not (tmp_path / ".umem" / "skills" / "review-helper").exists()
    assert not (tmp_path / ".umem" / "memory" / "skills.jsonl").exists()


def test_import_skill_preserves_native_source_when_replace_native_registry_fails(
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
    use_case = ImportSkillUseCase(
        project_root=tmp_path,
        repository=FailingAgentSkillRepository(),
        safe_write_use_case=safe_write,
    )
    source = write_source_skill(tmp_path / ".opencode" / "skills" / "review-helper")
    native_skill = source / "SKILL.md"
    original_native_content = native_skill.read_text(encoding="utf-8")

    with pytest.raises(StorageError):
        use_case.execute(
            ImportSkillCommand(
                path=source,
                scope=LatentSkillScope.project,
                origin="test",
                replace_native=True,
            )
        )

    assert native_skill.read_text(encoding="utf-8") == original_native_content
    assert not (tmp_path / ".umem" / "skills" / "review-helper").exists()
    assert not (tmp_path / ".umem" / "memory" / "skills.jsonl").exists()


@pytest.mark.parametrize("path_suffix", ["", "SKILL.md"])
def test_import_skill_rejects_root_source_directory_symlink(
    tmp_path: Path, path_suffix: str
) -> None:
    use_case, _repository, _safe_write = build_use_case(tmp_path)
    source = write_source_skill(tmp_path / "real-source")
    symlink = tmp_path / "linked-source"
    try:
        symlink.symlink_to(source, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(ValidationFailedError, match="symlink"):
        use_case.execute(
            ImportSkillCommand(
                path=symlink / path_suffix if path_suffix else symlink,
                scope=LatentSkillScope.project,
                origin="test",
            )
        )

    assert not (tmp_path / ".umem" / "skills").exists()


def test_import_skill_adopts_matching_supported_native_source_by_default(tmp_path: Path) -> None:
    use_case, repository, _safe_write = build_use_case(tmp_path)
    source = write_source_skill(tmp_path / ".opencode" / "skills" / "review-helper")

    result = use_case.execute(
        ImportSkillCommand(path=source, scope=LatentSkillScope.project, origin="test")
    )

    stored = repository.read(result.agent_skill.id)
    assert result.native_installations[0]["runtime"] == "opencode"
    assert result.native_installations[0]["path"] == ".opencode/skills/review-helper"
    assert stored.native_installations[0]["runtime"] == "opencode"
    assert stored.native_installations[0]["path"] == ".opencode/skills/review-helper"
    assert result.warnings == []


@pytest.mark.parametrize("path_suffix", ["", "SKILL.md"])
def test_import_skill_adopts_agents_native_source_by_default(
    tmp_path: Path, path_suffix: str
) -> None:
    use_case, repository, _safe_write = build_use_case(tmp_path)
    source = write_source_skill(tmp_path / ".agents" / "skills" / "review-helper")

    result = use_case.execute(
        ImportSkillCommand(
            path=source / path_suffix if path_suffix else source,
            scope=LatentSkillScope.project,
            origin="test",
        )
    )

    stored = repository.read(result.agent_skill.id)
    assert result.native_installations[0]["runtime"] == "codex"
    assert result.native_installations[0]["path"] == ".agents/skills/review-helper"
    assert stored.native_installations[0]["runtime"] == "codex"
    assert stored.native_installations[0]["path"] == ".agents/skills/review-helper"
    assert result.warnings == []


def test_import_skill_replace_native_rewrites_matching_source(tmp_path: Path) -> None:
    use_case, _repository, _safe_write = build_use_case(tmp_path)
    source = write_source_skill(tmp_path / ".opencode" / "skills" / "review-helper")

    result = use_case.execute(
        ImportSkillCommand(
            path=source,
            scope=LatentSkillScope.project,
            origin="test",
            replace_native=True,
        )
    )

    assert ".opencode/skills/review-helper/SKILL.md" in result.affected_paths
    assert result.native_installations[0]["runtime"] == "opencode"


def test_import_skill_replace_native_rewrites_agents_source(tmp_path: Path) -> None:
    use_case, _repository, _safe_write = build_use_case(tmp_path)
    source = write_source_skill(tmp_path / ".agents" / "skills" / "review-helper")

    result = use_case.execute(
        ImportSkillCommand(
            path=source,
            scope=LatentSkillScope.project,
            origin="test",
            replace_native=True,
        )
    )

    assert ".agents/skills/review-helper/SKILL.md" in result.affected_paths
    assert result.native_installations[0]["runtime"] == "codex"


def test_import_skill_can_sync_configured_native_targets_after_import(tmp_path: Path) -> None:
    use_case, repository, _safe_write = build_use_case(tmp_path)
    source = write_source_skill(tmp_path / ".agents" / "skills" / "review-helper")

    result = use_case.execute(
        ImportSkillCommand(
            path=source,
            scope=LatentSkillScope.project,
            origin="test",
            sync_after_import=True,
        )
    )

    canonical_file = tmp_path / ".umem" / "skills" / "review-helper" / "SKILL.md"
    agents_file = tmp_path / ".agents" / "skills" / "review-helper" / "SKILL.md"
    opencode_file = tmp_path / ".opencode" / "skills" / "review-helper" / "SKILL.md"
    stored = repository.read(result.agent_skill.id)
    installation_paths = {installation["path"] for installation in result.native_installations}

    assert agents_file.read_text(encoding="utf-8") == canonical_file.read_text(encoding="utf-8")
    assert opencode_file.read_text(encoding="utf-8") == canonical_file.read_text(encoding="utf-8")
    assert ".agents/skills/review-helper" in installation_paths
    assert ".opencode/skills/review-helper" in installation_paths
    assert ".agents/skills/review-helper/SKILL.md" in result.affected_paths
    assert stored.metadata["sync_after_import"] is True


class BlockingScanner(SecretScannerPort):
    def scan(self, content: str, *, origin: str | None = None) -> None:
        raise SecretDetectedError("blocked sk-test-secret-value")


def build_use_case(
    tmp_path: Path,
    *,
    scanner: SecretScannerPort | None = None,
) -> tuple[ImportSkillUseCase, LocalAgentSkillRepository, SafeWriteUseCase]:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=scanner or RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    repository = LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    return (
        ImportSkillUseCase(
            project_root=tmp_path,
            repository=repository,
            safe_write_use_case=safe_write,
            global_safe_write_use_case=repository.global_safe_write_use_case,
        ),
        repository,
        safe_write,
    )


def write_source_skill(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        "---\n"
        'name: "Review Helper"\n'
        'description: "Review code with focused checks."\n'
        "triggers:\n"
        '  - "when reviewing code"\n'
        "---\n"
        "\n"
        "# Review Helper\n",
        encoding="utf-8",
    )
    return path
