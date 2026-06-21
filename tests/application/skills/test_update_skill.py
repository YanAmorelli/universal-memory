from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.application.skills import (
    ActivateSkillCommand,
    ActivateSkillUseCase,
    DeactivateSkillCommand,
    DeactivateSkillUseCase,
    UpdateSkillCommand,
    UpdateSkillUseCase,
)
from universal_memory.domain import SecretDetectedError, StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    SafeWriteResult,
    Snapshot,
)
from universal_memory.domain.ports import AuditLogRepository, SecretScannerPort, SnapshotRepository
from universal_memory.infrastructure.storage import LocalLatentSkillRepository


class RecordingScanner(SecretScannerPort):
    def __init__(
        self,
        error: SecretDetectedError | None = None,
        *,
        reject_when: str | None = None,
    ) -> None:
        self.error = error
        self.reject_when = reject_when
        self.scanned: list[tuple[str, str | None]] = []

    def scan(self, content: str, *, origin: str | None = None) -> None:
        self.scanned.append((content, origin))
        if self.error is not None and (self.reject_when is None or self.reject_when in content):
            raise self.error


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


class FailingSafeWriteUseCase:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.commands: list[SafeWriteCommand] = []

    def execute(self, command: SafeWriteCommand) -> SafeWriteResult:
        self.commands.append(command)
        raise OSError("simulated write failure")


class FlakySafeWriteUseCase:
    def __init__(self, delegate: SafeWriteUseCase, *, fail_on_call: int) -> None:
        self.project_root = delegate.project_root
        self.delegate = delegate
        self.fail_on_call = fail_on_call
        self.calls = 0

    def execute(self, command: SafeWriteCommand) -> SafeWriteResult:
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise OSError("simulated rollback failure")
        return self.delegate.execute(command)


def build_safe_write(
    tmp_path: Path,
    *,
    scanner: RecordingScanner | None = None,
) -> tuple[
    SafeWriteUseCase,
    LocalLatentSkillRepository,
    RecordingSnapshotRepository,
    RecordingAuditRepository,
    RecordingScanner,
]:
    resolved_scanner = scanner or RecordingScanner()
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    safe_write = SafeWriteUseCase(
        project_root=tmp_path,
        secret_scanner=resolved_scanner,
        snapshot_repository=snapshots,
        audit_log_repository=audit,
    )
    repository = LocalLatentSkillRepository(project_root=tmp_path, safe_write_use_case=safe_write)
    return safe_write, repository, snapshots, audit, resolved_scanner


def make_skill(
    *,
    status: LatentSkillStatus = LatentSkillStatus.active,
    scope: LatentSkillScope = LatentSkillScope.project,
    name: str = "TDD Recorrente",
    description: str = "Executa red green refactor para mudancas de codigo.",
) -> LatentSkill:
    timestamp = datetime.now(UTC)
    return LatentSkill(
        id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        name=name,
        description=description,
        scope=scope,
        status=status,
        recurrence_count=4,
        metadata={
            "triggers": ["red green refactor", "implementar story"],
            "instructions": ["Escreva testes antes de alterar src/."],
        },
    )


def write_skill_markdown(tmp_path: Path, slug: str = "tdd-recorrente") -> Path:
    skill_file = tmp_path / ".umem" / "skills" / slug / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "\n".join(
            [
                "---",
                'name: "TDD Recorrente"',
                'description: "Executa red green refactor para mudancas de codigo."',
                "triggers:",
                '  - "red green refactor"',
                '  - "implementar story"',
                "---",
                "",
                "# TDD Recorrente",
                "",
                "Conteudo operacional.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return skill_file


def test_deactivate_skill_marks_repository_ignored_audits_and_keeps_skill_file(
    tmp_path: Path,
) -> None:
    _safe_write, repository, snapshots, audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    skill_file = write_skill_markdown(tmp_path)
    snapshots.written.clear()
    audit.written.clear()

    result = DeactivateSkillUseCase(repository=repository).execute(
        DeactivateSkillCommand(latent_skill_id=skill.id, origin="cli")
    )

    stored = repository.read(skill.id)
    assert stored.status == LatentSkillStatus.ignored
    assert result.latent_skill.status == LatentSkillStatus.ignored
    assert skill_file.is_file()
    assert "deactivate_skill" in {event.action for event in audit.written}
    assert "cli" in {event.origin for event in audit.written}
    assert ".umem/memory/latent_skills.jsonl" in {
        snapshot.relative_path for snapshot in snapshots.written
    }


def test_deactivate_skill_disables_native_targets_and_keeps_canonical_skill(
    tmp_path: Path,
) -> None:
    safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    canonical = write_skill_markdown(tmp_path)
    native = tmp_path / ".opencode" / "skills" / "tdd-recorrente" / "SKILL.md"
    native.parent.mkdir(parents=True)
    native.write_text(canonical.read_text(encoding="utf-8"), encoding="utf-8")
    skill = skill.model_copy(
        update={
            "metadata": {
                **skill.metadata,
                "native_installations": [
                    {
                        "runtime": "opencode",
                        "path": ".opencode/skills/tdd-recorrente",
                        "canonical_hash": "previous",
                        "target_hash": "previous",
                        "timestamp": "2026-01-01T00:00:00+00:00",
                        "audit_reference": "audit-1",
                    }
                ],
            }
        }
    )
    repository.write(skill)

    result = DeactivateSkillUseCase(
        repository=repository,
        project_root=tmp_path,
        safe_write_use_case=safe_write,
    ).execute(DeactivateSkillCommand(latent_skill_id=skill.id, origin="cli"))

    assert canonical.is_file()
    assert result.latent_skill.status == LatentSkillStatus.ignored
    assert result.affected_paths == [".opencode/skills/tdd-recorrente"]
    assert not native.parent.exists()


def test_activate_skill_requires_existing_valid_skill_file_and_audits(
    tmp_path: Path,
) -> None:
    _safe_write, repository, _snapshots, audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.ignored)
    repository.write(skill)
    write_skill_markdown(tmp_path)
    audit.written.clear()

    result = ActivateSkillUseCase(project_root=tmp_path, repository=repository).execute(
        ActivateSkillCommand(latent_skill_id=skill.id, origin="mcp")
    )

    stored = repository.read(skill.id)
    assert stored.status == LatentSkillStatus.active
    assert result.latent_skill.status == LatentSkillStatus.active
    assert "activate_skill" in {event.action for event in audit.written}
    assert "mcp" in {event.origin for event in audit.written}


def test_activate_skill_finds_renamed_skill_file_by_frontmatter_name(tmp_path: Path) -> None:
    _safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.ignored, name="TDD Avancado")
    repository.write(skill)
    write_skill_markdown(tmp_path).write_text(
        "\n".join(
            [
                "---",
                'name: "TDD Avancado"',
                'description: "Executa red green refactor para mudancas de codigo."',
                "triggers:",
                '  - "red green refactor"',
                "---",
                "",
                "# TDD Avancado",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = ActivateSkillUseCase(project_root=tmp_path, repository=repository).execute(
        ActivateSkillCommand(latent_skill_id=skill.id, origin="cli")
    )

    assert result.skill_file == ".umem/skills/tdd-recorrente/SKILL.md"
    assert repository.read(skill.id).status == LatentSkillStatus.active


def test_activate_skill_accepts_bom_and_crlf_frontmatter(tmp_path: Path) -> None:
    _safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.ignored)
    repository.write(skill)
    skill_file = tmp_path / ".umem" / "skills" / "tdd-recorrente" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "\ufeff---\r\n"
        'name: "TDD Recorrente"\r\n'
        'description: "Executa red green refactor para mudancas de codigo."\r\n'
        "triggers:\r\n"
        '  - "red green refactor"\r\n'
        "---\r\n",
        encoding="utf-8",
    )

    result = ActivateSkillUseCase(project_root=tmp_path, repository=repository).execute(
        ActivateSkillCommand(latent_skill_id=skill.id, origin="cli")
    )

    assert result.latent_skill.status == LatentSkillStatus.active


def test_activate_skill_keeps_ignored_when_skill_file_is_missing(tmp_path: Path) -> None:
    _safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.ignored)
    repository.write(skill)

    with pytest.raises(ValidationFailedError, match=r"SKILL\.md"):
        ActivateSkillUseCase(project_root=tmp_path, repository=repository).execute(
            ActivateSkillCommand(latent_skill_id=skill.id, origin="cli")
        )

    assert repository.read(skill.id).status == LatentSkillStatus.ignored


def test_activate_skill_keeps_ignored_when_frontmatter_is_invalid(tmp_path: Path) -> None:
    _safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.ignored)
    repository.write(skill)
    skill_file = tmp_path / ".umem" / "skills" / "tdd-recorrente" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("---\nname:\n---\n# broken\n", encoding="utf-8")

    with pytest.raises(ValidationFailedError, match="frontmatter"):
        ActivateSkillUseCase(project_root=tmp_path, repository=repository).execute(
            ActivateSkillCommand(latent_skill_id=skill.id, origin="cli")
        )

    assert repository.read(skill.id).status == LatentSkillStatus.ignored


def test_update_skill_writes_markdown_safely_updates_repository_and_keeps_rollback_scope(
    tmp_path: Path,
) -> None:
    safe_write, repository, snapshots, audit, scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    write_skill_markdown(tmp_path)
    snapshots.written.clear()
    audit.written.clear()

    result = UpdateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    ).execute(
        UpdateSkillCommand(
            latent_skill_id=skill.id,
            origin="cli",
            name="TDD Avancado",
            description="Executa red green refactor com revisao final.",
            triggers=["red green refactor", "code review"],
        )
    )

    skill_file = tmp_path / ".umem" / "skills" / "tdd-recorrente" / "SKILL.md"
    stored = repository.read(skill.id)
    markdown = skill_file.read_text(encoding="utf-8")
    assert result.skill_file == ".umem/skills/tdd-recorrente/SKILL.md"
    assert result.latent_skill.name == "TDD Avancado"
    assert stored.name == "TDD Avancado"
    assert stored.description == "Executa red green refactor com revisao final."
    assert stored.metadata["triggers"] == ["red green refactor", "code review"]
    assert 'name: "TDD Avancado"' in markdown
    assert "code review" in markdown
    assert "cli" in {origin for _content, origin in scanner.scanned}
    assert ".umem/skills/tdd-recorrente/SKILL.md" in {
        snapshot.relative_path for snapshot in snapshots.written
    }
    assert "update_skill" in {event.action for event in audit.written}


def test_update_skill_rejects_secret_markdown_without_mutating_repository(
    tmp_path: Path,
) -> None:
    scanner = RecordingScanner(
        SecretDetectedError("blocked", metadata={"kind": "token"}),
        reject_when="api_key",
    )
    safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(
        tmp_path,
        scanner=scanner,
    )
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    write_skill_markdown(tmp_path)

    with pytest.raises(SecretDetectedError):
        UpdateSkillUseCase(
            project_root=tmp_path,
            repository=repository,
            safe_write_use_case=safe_write,
        ).execute(
            UpdateSkillCommand(
                latent_skill_id=skill.id,
                origin="cli",
                raw_markdown="---\nname: X\ndescription: Y\n---\napi_key=secret\n",
            )
        )

    assert repository.read(skill.id).name == "TDD Recorrente"


def test_update_skill_raw_markdown_can_clear_triggers(tmp_path: Path) -> None:
    safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    write_skill_markdown(tmp_path)

    result = UpdateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    ).execute(
        UpdateSkillCommand(
            latent_skill_id=skill.id,
            origin="cli",
            raw_markdown='---\nname: "TDD Recorrente"\ndescription: "Atualizada"\ntriggers:\n---\n',
        )
    )

    assert result.latent_skill.metadata["triggers"] == []
    assert repository.read(skill.id).metadata["triggers"] == []


def test_update_skill_finds_existing_skill_file_with_noncanonical_slug(tmp_path: Path) -> None:
    safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active, name="TDD Avancado")
    repository.write(skill)
    write_skill_markdown(tmp_path).write_text(
        "\n".join(
            [
                "---",
                'name: "TDD Avancado"',
                'description: "Executa red green refactor para mudancas de codigo."',
                "triggers:",
                '  - "red green refactor"',
                "---",
                "",
                "# TDD Avancado",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = UpdateSkillUseCase(
        project_root=tmp_path,
        repository=repository,
        safe_write_use_case=safe_write,
    ).execute(
        UpdateSkillCommand(
            latent_skill_id=skill.id,
            origin="cli",
            description="Executa red green refactor com revisao final.",
        )
    )

    assert result.skill_file == ".umem/skills/tdd-recorrente/SKILL.md"
    assert "revisao final" in (tmp_path / result.skill_file).read_text(encoding="utf-8")


def test_update_skill_rejects_conflicting_explicit_fields_with_raw_markdown(tmp_path: Path) -> None:
    safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    write_skill_markdown(tmp_path)

    with pytest.raises(ValidationFailedError, match="Campos explicitos conflitam"):
        UpdateSkillUseCase(
            project_root=tmp_path,
            repository=repository,
            safe_write_use_case=safe_write,
        ).execute(
            UpdateSkillCommand(
                latent_skill_id=skill.id,
                origin="cli",
                name="Outro nome",
                raw_markdown='---\nname: "TDD Recorrente"\ndescription: "Atualizada"\n---\n',
            )
        )


def test_update_skill_keeps_repository_unchanged_when_skill_file_write_fails(
    tmp_path: Path,
) -> None:
    _safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    write_skill_markdown(tmp_path)
    failing_write = FailingSafeWriteUseCase(tmp_path)

    with pytest.raises(OSError, match="simulated write failure"):
        UpdateSkillUseCase(
            project_root=tmp_path,
            repository=repository,
            safe_write_use_case=failing_write,  # type: ignore[arg-type]
        ).execute(
            UpdateSkillCommand(
                latent_skill_id=skill.id,
                origin="cli",
                name="Novo Nome",
            )
        )

    assert repository.read(skill.id).name == "TDD Recorrente"
    assert failing_write.commands[0].action == "update_skill"
    assert failing_write.commands[0].scope == AuditEventScope.project


def test_deactivate_skill_requires_active_status(tmp_path: Path) -> None:
    _safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.ignored)
    repository.write(skill)

    with pytest.raises(ValidationFailedError):
        DeactivateSkillUseCase(repository=repository).execute(
            DeactivateSkillCommand(latent_skill_id=skill.id, origin="cli")
        )


def test_activate_skill_requires_ignored_status(tmp_path: Path) -> None:
    _safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)

    with pytest.raises(ValidationFailedError):
        ActivateSkillUseCase(project_root=tmp_path, repository=repository).execute(
            ActivateSkillCommand(latent_skill_id=skill.id, origin="cli")
        )


def test_update_skill_rolls_back_file_when_repository_write_fails(tmp_path: Path) -> None:
    safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    skill_file = write_skill_markdown(tmp_path)
    original_content = skill_file.read_text(encoding="utf-8")

    def failing_write(_entity: LatentSkill, *, origin: str = "repository"):
        raise StorageError("simulated repository failure")

    repository.write = failing_write  # type: ignore[method-assign]

    with pytest.raises(StorageError, match="simulated repository failure"):
        UpdateSkillUseCase(
            project_root=tmp_path,
            repository=repository,
            safe_write_use_case=safe_write,
        ).execute(
            UpdateSkillCommand(
                latent_skill_id=skill.id,
                origin="cli",
                name="Nome Persistido Apenas no Arquivo",
            )
        )

    assert skill_file.read_text(encoding="utf-8") == original_content


def test_update_skill_preserves_original_error_when_rollback_fails(tmp_path: Path) -> None:
    safe_write, repository, _snapshots, _audit, _scanner = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    write_skill_markdown(tmp_path)

    def failing_write(_entity: LatentSkill, *, origin: str = "repository"):
        raise StorageError("simulated repository failure")

    repository.write = failing_write  # type: ignore[method-assign]
    flaky_write = FlakySafeWriteUseCase(safe_write, fail_on_call=2)

    with pytest.raises(StorageError, match="simulated repository failure") as exc_info:
        UpdateSkillUseCase(
            project_root=tmp_path,
            repository=repository,
            safe_write_use_case=flaky_write,  # type: ignore[arg-type]
        ).execute(
            UpdateSkillCommand(
                latent_skill_id=skill.id,
                origin="cli",
                name="Nome Persistido Apenas no Arquivo",
            )
        )

    assert any("Skill file rollback failed" in note for note in exc_info.value.__notes__)
