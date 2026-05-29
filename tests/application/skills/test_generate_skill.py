from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills import GenerateSkillCommand, GenerateSkillUseCase
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEvent,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    Snapshot,
)
from universal_memory.domain.ports import AuditLogRepository, SecretScannerPort, SnapshotRepository
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


def build_use_case(
    tmp_path: Path,
) -> tuple[
    GenerateSkillUseCase,
    LocalLatentSkillRepository,
    RecordingSnapshotRepository,
    RecordingAuditRepository,
]:
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=RecordingScanner(),
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    return (
        GenerateSkillUseCase(
            project_root=tmp_path,
            repository=repository,
            safe_write_use_case=safe_write,
        ),
        repository,
        snapshots,
        audit,
    )


def make_skill(*, status: LatentSkillStatus = LatentSkillStatus.active) -> LatentSkill:
    now = datetime.now(UTC)
    return LatentSkill(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        name="TDD Recorrente",
        description="Executa red green refactor para mudancas de codigo.",
        scope=LatentSkillScope.project,
        status=status,
        recurrence_count=4,
        metadata={
            "triggers": ["red green refactor", "implementar story"],
            "instructions": [
                "Escreva o teste falhando antes de alterar src/.",
                "Use caminhos relativos ao registrar artefatos.",
            ],
            "include_scripts": True,
            "references": ["docs/tdd.md"],
        },
    )


def parse_frontmatter(markdown: str) -> dict[str, object]:
    assert markdown.startswith("---\n")
    raw = markdown.split("---\n", 2)[1]
    parsed: dict[str, object] = {}
    current_list: str | None = None
    for line in raw.splitlines():
        if line.startswith("  - ") and current_list is not None:
            parsed[current_list].append(line.removeprefix("  - ").strip().strip('"'))  # type: ignore[index]
            continue
        key, value = line.split(":", 1)
        if not value.strip():
            parsed[key] = []
            current_list = key
        else:
            parsed[key] = value.strip().strip('"')
            current_list = None
    return parsed


def test_generate_skill_creates_project_structure_and_skill_markdown(tmp_path: Path) -> None:
    use_case, repository, snapshots, audit = build_use_case(tmp_path)
    skill = make_skill()
    repository.write(skill)
    snapshots.written.clear()
    audit.written.clear()

    result = use_case.execute(GenerateSkillCommand(latent_skill_id=skill.id, origin="test"))

    skill_file = tmp_path / ".umem" / "skills" / "tdd-recorrente" / "SKILL.md"
    markdown = skill_file.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(markdown)
    assert result.slug == "tdd-recorrente"
    assert result.skill_file == ".umem/skills/tdd-recorrente/SKILL.md"
    assert result.created_paths == [
        ".umem/skills/tdd-recorrente/SKILL.md",
        ".umem/skills/tdd-recorrente/scripts/.gitkeep",
        ".umem/skills/tdd-recorrente/references/.gitkeep",
    ]
    assert frontmatter["name"] == "TDD Recorrente"
    assert frontmatter["description"] == "Executa red green refactor para mudancas de codigo."
    assert frontmatter["triggers"] == ["red green refactor", "implementar story"]
    assert "Escreva o teste falhando antes de alterar src/." in markdown
    assert str(tmp_path) not in markdown
    assert (tmp_path / ".umem" / "skills" / "tdd-recorrente" / "scripts").is_dir()
    assert (tmp_path / ".umem" / "skills" / "tdd-recorrente" / "references").is_dir()
    assert {snapshot.relative_path for snapshot in snapshots.written} == set(result.created_paths)
    assert {event.action for event in audit.written} == {"generate_skill"}


def test_generate_skill_omits_optional_directories_when_not_requested(tmp_path: Path) -> None:
    use_case, repository, _snapshots, _audit = build_use_case(tmp_path)
    skill = make_skill().model_copy(update={"metadata": {"triggers": ["manual trigger"]}})
    repository.write(skill)

    result = use_case.execute(GenerateSkillCommand(latent_skill_id=skill.id, origin="test"))

    assert result.created_paths == [".umem/skills/tdd-recorrente/SKILL.md"]
    assert not (tmp_path / ".umem" / "skills" / "tdd-recorrente" / "scripts").exists()
    assert not (tmp_path / ".umem" / "skills" / "tdd-recorrente" / "references").exists()


def test_generate_skill_resolves_colliding_slug_without_overwrite(tmp_path: Path) -> None:
    use_case, repository, _snapshots, _audit = build_use_case(tmp_path)
    skill = make_skill()
    existing = tmp_path / ".umem" / "skills" / "tdd-recorrente" / "SKILL.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("existing content", encoding="utf-8")
    repository.write(skill)

    result = use_case.execute(GenerateSkillCommand(latent_skill_id=skill.id, origin="test"))

    assert result.collision_detected is True
    assert result.slug == "tdd-recorrente-2"
    assert result.suggested_slug == "tdd-recorrente-2"
    assert existing.read_text(encoding="utf-8") == "existing content"
    assert (tmp_path / ".umem" / "skills" / "tdd-recorrente-2" / "SKILL.md").is_file()


def test_generate_skill_requires_active_latent_skill(tmp_path: Path) -> None:
    use_case, repository, _snapshots, _audit = build_use_case(tmp_path)
    skill = make_skill(status=LatentSkillStatus.proposed)
    repository.write(skill)

    with pytest.raises(ValidationFailedError):
        use_case.execute(GenerateSkillCommand(latent_skill_id=skill.id, origin="test"))


def test_generate_skill_high_suffix_collision_loop(tmp_path: Path) -> None:
    use_case, repository, _snapshots, _audit = build_use_case(tmp_path)
    skill = make_skill()
    repository.write(skill)

    # Pre-create folders for base_slug, -2, -3
    (tmp_path / ".umem" / "skills" / "tdd-recorrente").mkdir(parents=True)
    (tmp_path / ".umem" / "skills" / "tdd-recorrente-2").mkdir(parents=True)
    (tmp_path / ".umem" / "skills" / "tdd-recorrente-3").mkdir(parents=True)

    result = use_case.execute(GenerateSkillCommand(latent_skill_id=skill.id, origin="test"))

    assert result.collision_detected is True
    assert result.slug == "tdd-recorrente-4"
    assert (tmp_path / ".umem" / "skills" / "tdd-recorrente-4" / "SKILL.md").is_file()


def test_generate_skill_dry_run_does_not_write(tmp_path: Path) -> None:
    use_case, repository, snapshots, audit = build_use_case(tmp_path)
    skill = make_skill()
    repository.write(skill)
    snapshots.written.clear()
    audit.written.clear()

    command = GenerateSkillCommand(latent_skill_id=skill.id, origin="test", dry_run=True)
    result = use_case.execute(command)

    assert result.slug == "tdd-recorrente"
    assert result.created_paths == []
    assert result.affected_paths == []
    assert not (tmp_path / ".umem" / "skills" / "tdd-recorrente").exists()
    assert len(snapshots.written) == 0
    assert len(audit.written) == 0


def test_generate_skill_fails_when_path_occupied_by_regular_file(tmp_path: Path) -> None:
    use_case, repository, _snapshots, _audit = build_use_case(tmp_path)
    skill = make_skill()
    repository.write(skill)

    # Create a regular file where the skill directory should go
    file_path = tmp_path / ".umem" / "skills" / "tdd-recorrente"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("i am a file, not a directory", encoding="utf-8")

    with pytest.raises(StorageError) as exc_info:
        use_case.execute(GenerateSkillCommand(latent_skill_id=skill.id, origin="test"))

    assert "Caminho ocupado por um arquivo regular" in str(exc_info.value)
