from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.application.skills.native_skill_sync import (
    NativeDriftDecision,
    NativeSkillSync,
    merge_native_installations,
)
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEventScope,
    LatentSkill,
    LatentSkillScope,
    RuntimeRegistry,
)
from universal_memory.domain.entities.latent_skill import LatentSkillStatus
from universal_memory.domain.ports import LatentSkillRepository


@dataclass(frozen=True, slots=True)
class GenerateSkillCommand:
    latent_skill_id: str
    origin: str
    update_existing: bool = False
    dry_run: bool = False
    native_drift_decision: NativeDriftDecision | None = None


@dataclass(frozen=True, slots=True)
class GenerateSkillResult:
    latent_skill: LatentSkill
    slug: str
    skill_dir: str
    skill_file: str
    created_paths: list[str]
    affected_paths: list[str]
    audit_reference: str
    snapshot_reference: str
    native_installations: list[dict[str, Any]] = field(default_factory=list)
    collision_detected: bool = False
    suggested_slug: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "skill_id": self.latent_skill.id,
            "name": self.latent_skill.name,
            "slug": self.slug,
            "skill_dir": self.skill_dir,
            "skill_file": self.skill_file,
            "created_paths": self.created_paths,
            "affected_paths": self.affected_paths,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "native_installations": self.native_installations,
            "collision_detected": self.collision_detected,
            "suggested_slug": self.suggested_slug,
        }


class _GenerateSkillSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    latent_skill_id: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    update_existing: bool = False
    dry_run: bool = False
    native_drift_decision: NativeDriftDecision | None = None


class GenerateSkillUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        repository: LatentSkillRepository,
        safe_write_use_case: SafeWriteUseCase,
        global_safe_write_use_case: SafeWriteUseCase | None = None,
        runtime_registry: RuntimeRegistry | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository
        self.safe_write_use_case = safe_write_use_case
        self.global_safe_write_use_case = global_safe_write_use_case or safe_write_use_case
        self.native_skill_sync = NativeSkillSync(
            project_root=self.project_root,
            safe_write_use_case=safe_write_use_case,
            runtime_registry=runtime_registry,
        )

    def execute(self, command: GenerateSkillCommand) -> GenerateSkillResult:
        validated = _GenerateSkillSchema.model_validate(command)
        skill = self.repository.read(validated.latent_skill_id)
        if skill.status != LatentSkillStatus.active:
            raise ValidationFailedError(
                f"A latent skill {skill.id} precisa estar active antes da geracao."
            )

        base_slug = self._slug(skill.name)
        target_slug, collision_detected = self._resolve_slug(
            skill.scope,
            base_slug,
            update_existing=validated.update_existing,
        )
        skill_dir = self._skill_dir_for(skill.scope, target_slug)
        skill_file = f"{skill_dir}/SKILL.md"
        optional_paths = self._optional_paths(skill, skill_dir)
        warnings = []
        if collision_detected and not validated.update_existing:
            warnings.append(f"Slug existente preservado; gerado slug alternativo '{target_slug}'.")

        if validated.dry_run:
            return GenerateSkillResult(
                latent_skill=skill,
                slug=target_slug,
                skill_dir=skill_dir,
                skill_file=skill_file,
                created_paths=[],
                affected_paths=[],
                audit_reference="",
                snapshot_reference="",
                collision_detected=collision_detected,
                suggested_slug=target_slug if collision_detected else None,
                warnings=warnings,
            )

        content = self._render_skill_markdown(skill)
        write = self._safe_write_for(skill.scope)
        audit_scope = self._audit_scope_for(skill.scope)

        write_results = []
        try:
            write_results.append(
                write.execute(
                    SafeWriteCommand(
                        relative_path=skill_file,
                        content=content,
                        scope=audit_scope,
                        origin=validated.origin,
                        action="generate_skill",
                    )
                )
            )
            for optional_path in optional_paths:
                write_results.append(
                    write.execute(
                        SafeWriteCommand(
                            relative_path=optional_path,
                            content="",
                            scope=audit_scope,
                            origin=validated.origin,
                            action="generate_skill",
                        )
                    )
                )
        except Exception:
            # Clean up any files created in this execution to prevent dirty state
            for result in write_results:
                absolute_path = self.project_root / result.relative_path
                try:
                    absolute_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

        created_paths = [result.relative_path for result in write_results]
        affected_paths = list(created_paths)
        native_result = self.native_skill_sync.sync(
            skill=skill,
            slug=target_slug,
            canonical_skill_file=skill_file,
            origin=validated.origin,
            drift_decision=validated.native_drift_decision,
            canonical_base_path=write.project_root,
        )
        affected_paths.extend(native_result.affected_paths)
        if native_result.installations:
            updated_skill = skill.model_copy(
                update={
                    "metadata": merge_native_installations(
                        skill.metadata,
                        native_result.installations,
                    )
                }
            )
            repository_write = self.repository.write(updated_skill, origin=validated.origin)
            skill = updated_skill
            if repository_write is not None:
                write_results.append(repository_write)
        audit_references = [result.audit_reference for result in write_results]
        audit_references.extend(native_result.audit_references)
        snapshot_references = [result.snapshot_reference for result in write_results]
        snapshot_references.extend(native_result.snapshot_references)
        return GenerateSkillResult(
            latent_skill=skill,
            slug=target_slug,
            skill_dir=skill_dir,
            skill_file=skill_file,
            created_paths=created_paths,
            affected_paths=affected_paths,
            audit_reference=", ".join(audit_references),
            snapshot_reference=", ".join(snapshot_references),
            native_installations=native_result.installations,
            collision_detected=collision_detected,
            suggested_slug=target_slug if collision_detected else None,
            warnings=[*warnings, *native_result.warnings],
        )

    def _resolve_slug(
        self,
        scope: LatentSkillScope,
        base_slug: str,
        *,
        update_existing: bool,
    ) -> tuple[str, bool]:
        base_dir = self._absolute_skill_dir_for(scope, base_slug)
        if base_dir.exists() and not base_dir.is_dir():
            raise StorageError(f"Caminho ocupado por um arquivo regular: {base_dir}")
        if not base_dir.exists():
            return base_slug, False
        if update_existing:
            return base_slug, True
        suffix = 2
        while True:
            candidate = f"{base_slug}-{suffix}"
            candidate_dir = self._absolute_skill_dir_for(scope, candidate)
            if candidate_dir.exists() and not candidate_dir.is_dir():
                raise StorageError(f"Caminho ocupado por um arquivo regular: {candidate_dir}")
            if not candidate_dir.exists():
                return candidate, True
            suffix += 1

    def _safe_write_for(self, scope: LatentSkillScope) -> SafeWriteUseCase:
        if scope == LatentSkillScope.global_:
            return self.global_safe_write_use_case
        return self.safe_write_use_case

    def _skill_dir_for(self, scope: LatentSkillScope, slug: str) -> str:
        if scope == LatentSkillScope.global_:
            return f"skills/{slug}"
        return f".umem/skills/{slug}"

    def _absolute_skill_dir_for(self, scope: LatentSkillScope, slug: str) -> Path:
        safe_write = self._safe_write_for(scope)
        return safe_write.project_root / self._skill_dir_for(scope, slug)

    @staticmethod
    def _audit_scope_for(scope: LatentSkillScope) -> AuditEventScope:
        if scope == LatentSkillScope.global_:
            return AuditEventScope.global_
        return AuditEventScope.project

    @classmethod
    def _optional_paths(cls, skill: LatentSkill, skill_dir: str) -> list[str]:
        metadata = skill.metadata or {}
        paths = []
        if bool(metadata.get("include_scripts") or metadata.get("scripts")):
            paths.append(f"{skill_dir}/scripts/.gitkeep")
        if bool(metadata.get("include_references") or metadata.get("references")):
            paths.append(f"{skill_dir}/references/.gitkeep")
        return paths

    def _render_skill_markdown(self, skill: LatentSkill) -> str:
        raw_markdown = (skill.metadata or {}).get("raw_markdown")
        if isinstance(raw_markdown, str):
            return self._strip_absolute_project_paths(raw_markdown)

        triggers = self._triggers_for(skill)
        instructions = self._instructions_for(skill)
        lines = [
            "---",
            f"name: {self._yaml_scalar(skill.name)}",
            f"description: {self._yaml_scalar(skill.description)}",
            "triggers:",
            *(f"  - {self._yaml_scalar(trigger)}" for trigger in triggers),
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
            "## Evidencias",
            "",
            *[f"- {evidence}" for evidence in self._evidence_for(skill)],
            "",
        ]
        return self._strip_absolute_project_paths("\n".join(lines))

    def _strip_absolute_project_paths(self, value: str) -> str:
        if self.project_root.as_posix() == "/":
            return value
        posix_stripped = value.replace(self.project_root.as_posix(), ".")
        resolved_posix = self.project_root.resolve().as_posix()
        resolved_posix_stripped = posix_stripped.replace(resolved_posix, ".")
        return resolved_posix_stripped.replace(str(self.project_root), ".")

    @classmethod
    def _triggers_for(cls, skill: LatentSkill) -> list[str]:
        metadata = skill.metadata or {}
        raw_triggers = metadata.get("triggers") or metadata.get("tags") or [skill.name]
        triggers = [
            str(item).strip()
            for item in cls._as_list(raw_triggers)
            if item is not None and str(item).strip()
        ]
        return triggers or [skill.name]

    @classmethod
    def _instructions_for(cls, skill: LatentSkill) -> list[str]:
        metadata = skill.metadata or {}
        raw_instructions = metadata.get("instructions") or metadata.get("guidelines")
        instructions = [
            str(item).strip()
            for item in cls._as_list(raw_instructions)
            if item is not None and str(item).strip()
        ]
        if instructions:
            return instructions
        return [
            skill.description,
            "Aplique a metodologia somente quando os gatilhos acima aparecerem no contexto.",
            "Registre arquivos e referencias usando caminhos relativos ao projeto.",
        ]

    @classmethod
    def _evidence_for(cls, skill: LatentSkill) -> list[str]:
        evidence = []
        for item in cls._as_list((skill.metadata or {}).get("evidence")):
            if isinstance(item, dict):
                if item.get("summary"):
                    evidence.append(str(item["summary"]))
            elif item is not None:
                evidence.append(str(item))
        return evidence or ["Gerada a partir da latent skill aprovada."]

    @staticmethod
    def _as_list(value: object) -> list[object]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple | set):
            return list(value)
        return [value]

    @staticmethod
    def _yaml_scalar(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'

    @staticmethod
    def _slug(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value)
        ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
        if not slug:
            h = hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
            return f"skill-{h}"
        return slug
