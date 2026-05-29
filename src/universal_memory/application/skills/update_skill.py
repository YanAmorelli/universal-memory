from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import AuditEventScope, LatentSkill, LatentSkillScope
from universal_memory.domain.entities.latent_skill import LatentSkillStatus
from universal_memory.domain.ports import LatentSkillRepository

FRONTMATTER_PART_COUNT = 3
MIN_QUOTED_SCALAR_LENGTH = 2


@dataclass(frozen=True, slots=True)
class ActivateSkillCommand:
    latent_skill_id: str
    origin: str


@dataclass(frozen=True, slots=True)
class ActivateSkillResult:
    latent_skill: LatentSkill
    skill_file: str
    audit_reference: str = ""
    snapshot_reference: str = ""


@dataclass(frozen=True, slots=True)
class DeactivateSkillCommand:
    latent_skill_id: str
    origin: str


@dataclass(frozen=True, slots=True)
class DeactivateSkillResult:
    latent_skill: LatentSkill
    audit_reference: str = ""
    snapshot_reference: str = ""


@dataclass(frozen=True, slots=True)
class UpdateSkillCommand:
    latent_skill_id: str
    origin: str
    name: str | None = None
    description: str | None = None
    triggers: list[str] | None = None
    metadata: dict[str, Any] | None = None
    raw_markdown: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateSkillResult:
    latent_skill: LatentSkill
    skill_file: str
    audit_reference: str
    snapshot_reference: str
    rollback_hint: str | None = None


class _SkillIdCommandSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    latent_skill_id: str = Field(min_length=1)
    origin: str = Field(min_length=1)


class _UpdateSkillCommandSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    latent_skill_id: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    name: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    triggers: list[str] | None = None
    metadata: dict[str, Any] | None = None
    raw_markdown: str | None = None


@dataclass(frozen=True, slots=True)
class _ParsedSkillMarkdown:
    name: str
    description: str
    triggers: list[str] = field(default_factory=list)


class DeactivateSkillUseCase:
    def __init__(self, *, repository: LatentSkillRepository) -> None:
        self.repository = repository

    def execute(self, command: DeactivateSkillCommand) -> DeactivateSkillResult:
        validated = _SkillIdCommandSchema.model_validate(command)
        skill = self.repository.read(validated.latent_skill_id)
        if skill.status != LatentSkillStatus.active:
            raise ValidationFailedError(
                f"A latent skill {skill.id} precisa estar active para ser desativada."
            )

        updated = _replace_skill(skill, status=LatentSkillStatus.ignored)
        write_result = self.repository.write(updated, origin=validated.origin)
        return DeactivateSkillResult(
            latent_skill=updated,
            audit_reference=write_result.audit_reference if write_result is not None else "",
            snapshot_reference=write_result.snapshot_reference if write_result is not None else "",
        )


class ActivateSkillUseCase:
    def __init__(self, *, project_root: Path, repository: LatentSkillRepository) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository

    def execute(self, command: ActivateSkillCommand) -> ActivateSkillResult:
        validated = _SkillIdCommandSchema.model_validate(command)
        skill = self.repository.read(validated.latent_skill_id)
        if skill.status != LatentSkillStatus.ignored:
            raise ValidationFailedError(
                f"A latent skill {skill.id} precisa estar ignored para ser ativada."
            )

        relative_path = self._skill_file_for(skill)
        absolute_path = self._absolute_skill_file_for(skill, relative_path)
        if not absolute_path.is_file():
            raise ValidationFailedError(f"SKILL.md ausente no caminho esperado: {relative_path}")

        try:
            parsed = _parse_skill_markdown(absolute_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ValidationFailedError(f"Falha ao ler SKILL.md: {relative_path}") from exc

        if not parsed.name or not parsed.description:
            raise ValidationFailedError(f"frontmatter invalido em {relative_path}")

        updated = _replace_skill(skill, status=LatentSkillStatus.active)
        write_result = self.repository.write(updated, origin=validated.origin)
        return ActivateSkillResult(
            latent_skill=updated,
            skill_file=relative_path,
            audit_reference=write_result.audit_reference if write_result is not None else "",
            snapshot_reference=write_result.snapshot_reference if write_result is not None else "",
        )

    def _skill_file_for(self, skill: LatentSkill) -> str:
        return _resolve_skill_file(self.project_root, self.repository, skill)

    def _absolute_skill_file_for(self, skill: LatentSkill, relative_path: str) -> Path:
        if skill.scope == LatentSkillScope.global_:
            global_root = getattr(self.repository, "global_data_root", self.project_root)
            return Path(global_root) / relative_path
        return self.project_root / relative_path


class UpdateSkillUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        repository: LatentSkillRepository,
        safe_write_use_case: SafeWriteUseCase,
        global_safe_write_use_case: SafeWriteUseCase | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository
        self.safe_write_use_case = safe_write_use_case
        self.global_safe_write_use_case = global_safe_write_use_case or safe_write_use_case

    def execute(self, command: UpdateSkillCommand) -> UpdateSkillResult:
        validated = _UpdateSkillCommandSchema.model_validate(command)
        skill = self.repository.read(validated.latent_skill_id)
        relative_path = _skill_file_for(skill.scope, _slug(skill.name))
        absolute_path = self._safe_write_for(skill.scope).project_root / relative_path
        previous_content = self._read_existing_content(absolute_path, relative_path)

        updated, markdown = self._build_update(skill, validated)
        write_result = self._safe_write_for(skill.scope).execute(
            SafeWriteCommand(
                relative_path=relative_path,
                content=markdown,
                scope=_audit_scope_for(skill.scope),
                origin=validated.origin,
                action="update_skill",
            )
        )

        try:
            repository_write = self.repository.write(updated, origin=validated.origin)
        except Exception as exc:
            try:
                self._restore_skill_file(
                    skill.scope,
                    relative_path,
                    previous_content,
                    origin=validated.origin,
                )
            except Exception as rollback_error:
                exc.add_note(f"Rollback do arquivo da skill falhou: {rollback_error}")
            raise

        audit_reference = write_result.audit_reference
        snapshot_reference = write_result.snapshot_reference
        if repository_write is not None:
            audit_reference = f"{audit_reference}, {repository_write.audit_reference}"
            snapshot_reference = f"{snapshot_reference}, {repository_write.snapshot_reference}"

        return UpdateSkillResult(
            latent_skill=updated,
            skill_file=relative_path,
            audit_reference=audit_reference,
            snapshot_reference=snapshot_reference,
            rollback_hint="Use rollback por escopo para restaurar o snapshot anterior.",
        )

    def _build_update(
        self,
        skill: LatentSkill,
        command: _UpdateSkillCommandSchema,
    ) -> tuple[LatentSkill, str]:
        if command.raw_markdown is not None:
            parsed = _parse_skill_markdown(command.raw_markdown)
            metadata = dict(skill.metadata or {})
            metadata["triggers"] = parsed.triggers
            return (
                _replace_skill(
                    skill,
                    name=parsed.name,
                    description=parsed.description,
                    metadata=metadata,
                ),
                _strip_absolute_project_paths(command.raw_markdown, self.project_root),
            )

        metadata = dict(skill.metadata or {})
        if command.metadata is not None:
            metadata.update(command.metadata)
        if command.triggers is not None:
            metadata["triggers"] = [
                trigger.strip() for trigger in command.triggers if trigger.strip()
            ]
        updated = _replace_skill(
            skill,
            name=command.name or skill.name,
            description=command.description or skill.description,
            metadata=metadata,
        )
        return updated, _render_skill_markdown(updated, self.project_root)

    def _safe_write_for(self, scope: LatentSkillScope) -> SafeWriteUseCase:
        if scope == LatentSkillScope.global_:
            return self.global_safe_write_use_case
        return self.safe_write_use_case

    @staticmethod
    def _read_existing_content(path: Path, relative_path: str) -> str:
        if not path.is_file():
            raise ValidationFailedError(f"SKILL.md ausente no caminho esperado: {relative_path}")
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValidationFailedError(f"Falha ao ler SKILL.md: {relative_path}") from exc

    def _restore_skill_file(
        self,
        scope: LatentSkillScope,
        relative_path: str,
        previous_content: str,
        *,
        origin: str,
    ) -> None:
        self._safe_write_for(scope).execute(
            SafeWriteCommand(
                relative_path=relative_path,
                content=previous_content,
                scope=_audit_scope_for(scope),
                origin=origin,
                action="rollback_update_skill",
            )
        )


def _replace_skill(skill: LatentSkill, **updates: Any) -> LatentSkill:
    payload = skill.model_dump()
    payload.update(updates)
    payload["updated_at"] = datetime.now(UTC)
    return LatentSkill.model_validate(payload)


def _parse_skill_markdown(markdown: str) -> _ParsedSkillMarkdown:
    normalized_markdown = markdown.lstrip("\ufeff").replace("\r\n", "\n")
    if not normalized_markdown.startswith("---\n"):
        raise ValidationFailedError("frontmatter invalido: delimitador inicial ausente")
    parts = normalized_markdown.split("---\n", 2)
    if len(parts) < FRONTMATTER_PART_COUNT:
        raise ValidationFailedError("frontmatter invalido: delimitador final ausente")

    data: dict[str, Any] = {}
    current_list: str | None = None
    for raw_line in parts[1].splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("  - ") and current_list is not None:
            data[current_list].append(_unquote_scalar(line.removeprefix("  - ").strip()))
            continue
        if ":" not in line or line.startswith(" "):
            raise ValidationFailedError("frontmatter invalido: linha malformada")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            raise ValidationFailedError("frontmatter invalido: chave vazia")
        if not value:
            data[key] = []
            current_list = key
        else:
            data[key] = _unquote_scalar(value)
            current_list = None

    name = data.get("name")
    description = data.get("description")
    triggers = data.get("triggers", [])
    if not isinstance(name, str) or not name.strip():
        raise ValidationFailedError("frontmatter invalido: name obrigatorio")
    if not isinstance(description, str) or not description.strip():
        raise ValidationFailedError("frontmatter invalido: description obrigatorio")
    if not isinstance(triggers, list):
        raise ValidationFailedError("frontmatter invalido: triggers deve ser lista")
    parsed_triggers = [str(trigger).strip() for trigger in triggers if str(trigger).strip()]
    return _ParsedSkillMarkdown(
        name=name.strip(),
        description=description.strip(),
        triggers=parsed_triggers,
    )


def _render_skill_markdown(skill: LatentSkill, project_root: Path) -> str:
    triggers = _triggers_for(skill)
    instructions = _instructions_for(skill)
    lines = [
        "---",
        f"name: {_yaml_scalar(skill.name)}",
        f"description: {_yaml_scalar(skill.description)}",
        "triggers:",
        *(f"  - {_yaml_scalar(trigger)}" for trigger in triggers),
        "---",
        "",
        f"# {skill.name}",
        "",
        "## Quando Usar",
        "",
        *[f"- {trigger}" for trigger in triggers],
        "",
        "## Instrucoes Operacionais",
        "",
        *[f"- {instruction}" for instruction in instructions],
        "",
    ]
    return _strip_absolute_project_paths("\n".join(lines), project_root)


def _strip_absolute_project_paths(value: str, project_root: Path) -> str:
    if project_root.as_posix() == "/":
        return value
    posix_stripped = value.replace(project_root.as_posix(), ".")
    resolved_posix = project_root.resolve().as_posix()
    resolved_posix_stripped = posix_stripped.replace(resolved_posix, ".")
    return resolved_posix_stripped.replace(str(project_root), ".")


def _triggers_for(skill: LatentSkill) -> list[str]:
    metadata = skill.metadata or {}
    raw_triggers = metadata.get("triggers") or metadata.get("tags") or [skill.name]
    triggers = [str(item).strip() for item in _as_list(raw_triggers) if str(item).strip()]
    return triggers or [skill.name]


def _instructions_for(skill: LatentSkill) -> list[str]:
    metadata = skill.metadata or {}
    raw_instructions = metadata.get("instructions") or metadata.get("guidelines")
    instructions = [str(item).strip() for item in _as_list(raw_instructions) if str(item).strip()]
    if instructions:
        return instructions
    return [
        skill.description,
        "Aplique a metodologia somente quando os gatilhos acima aparecerem no contexto.",
        "Registre arquivos e referencias usando caminhos relativos ao projeto.",
    ]


def _as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    return [value]


def _yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _unquote_scalar(value: str) -> str:
    if len(value) >= MIN_QUOTED_SCALAR_LENGTH and value[0] == value[-1] and value[0] in {"'", '"'}:
        return (
            value[1:-1]
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )
    return value


def _skill_file_for(scope: LatentSkillScope, slug: str) -> str:
    if scope == LatentSkillScope.global_:
        return f"skills/{slug}/SKILL.md"
    return f".umem/skills/{slug}/SKILL.md"


def _resolve_skill_file(
    project_root: Path,
    repository: LatentSkillRepository,
    skill: LatentSkill,
) -> str:
    expected_relative_path = _skill_file_for(skill.scope, _slug(skill.name))
    expected_file = _absolute_skill_file(project_root, repository, skill.scope, expected_relative_path)
    if expected_file.is_file():
        return expected_relative_path

    base_dir = _skill_base_dir(project_root, repository, skill.scope)
    if not base_dir.is_dir():
        return expected_relative_path

    for skill_file in sorted(base_dir.glob("*/SKILL.md")):
        try:
            parsed = _parse_skill_markdown(skill_file.read_text(encoding="utf-8"))
        except (OSError, ValidationFailedError):
            continue
        if parsed.name.casefold() == skill.name.casefold():
            return _relative_skill_path(project_root, repository, skill.scope, skill_file)
    return expected_relative_path


def _absolute_skill_file(
    project_root: Path,
    repository: LatentSkillRepository,
    scope: LatentSkillScope,
    relative_path: str,
) -> Path:
    if scope == LatentSkillScope.global_:
        global_root = getattr(repository, "global_data_root", project_root)
        return Path(global_root) / relative_path
    return project_root / relative_path


def _skill_base_dir(
    project_root: Path,
    repository: LatentSkillRepository,
    scope: LatentSkillScope,
) -> Path:
    if scope == LatentSkillScope.global_:
        return Path(getattr(repository, "global_data_root", project_root)) / "skills"
    return project_root / ".umem" / "skills"


def _relative_skill_path(
    project_root: Path,
    repository: LatentSkillRepository,
    scope: LatentSkillScope,
    skill_file: Path,
) -> str:
    if scope == LatentSkillScope.global_:
        global_root = Path(getattr(repository, "global_data_root", project_root))
        return skill_file.relative_to(global_root).as_posix()
    return skill_file.relative_to(project_root).as_posix()


def _audit_scope_for(scope: LatentSkillScope) -> AuditEventScope:
    if scope == LatentSkillScope.global_:
        return AuditEventScope.global_
    return AuditEventScope.project


def _slug(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    if not slug:
        h = hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
        return f"skill-{h}"
    return slug
