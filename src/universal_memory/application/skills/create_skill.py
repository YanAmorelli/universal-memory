from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.application.skills.native_skill_sync import NativeSkillSync
from universal_memory.application.skills.update_skill import _parse_skill_markdown
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    AuditEventScope,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    RuntimeRegistry,
)
from universal_memory.domain.ports import AgentSkillRepository


@dataclass(frozen=True, slots=True)
class CreateSkillCommand:
    name: str
    description: str
    scope: LatentSkillScope
    origin: str
    triggers: list[str] | None = None
    raw_markdown: str | None = None
    targets: list[str] | None = None
    source_recommendation_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CreateSkillResult:
    agent_skill: AgentSkill
    slug: str
    skill_dir: str
    skill_file: str
    created_paths: list[str]
    affected_paths: list[str]
    audit_reference: str
    snapshot_reference: str
    native_installations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def latent_skill(self) -> LatentSkill:
        return LatentSkill(
            id=self.agent_skill.id,
            created_at=self.agent_skill.created_at,
            updated_at=self.agent_skill.updated_at,
            name=self.agent_skill.name,
            description=self.agent_skill.description,
            scope=self.agent_skill.scope,
            status=LatentSkillStatus.active
            if self.agent_skill.status == AgentSkillStatus.active
            else LatentSkillStatus.ignored,
            recurrence_count=1,
            metadata={
                **self.agent_skill.metadata,
                "origin": self.agent_skill.origin,
                "audit_reference": self.agent_skill.audit_reference,
                "canonical_path": self.agent_skill.canonical_path,
                "native_installations": self.agent_skill.native_installations,
                "creation_flow": "direct",
                "recommendation_flow": False,
            },
        )

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "skill_id": self.agent_skill.id,
            "name": self.agent_skill.name,
            "slug": self.slug,
            "skill_dir": self.skill_dir,
            "skill_file": self.skill_file,
            "created_paths": self.created_paths,
            "affected_paths": self.affected_paths,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "native_installations": self.native_installations,
            "canonical_skill": {
                "id": self.agent_skill.id,
                "name": self.agent_skill.name,
                "description": self.agent_skill.description,
                "scope": self.agent_skill.scope.value,
                "status": self.agent_skill.status.value,
                "canonical_path": self.agent_skill.canonical_path,
                "origin": self.agent_skill.origin,
                "content_hash": self.agent_skill.content_hash,
            },
        }
        if self.agent_skill.source_recommendation_id is not None:
            payload["source_recommendation_id"] = self.agent_skill.source_recommendation_id
            payload["canonical_skill"]["source_recommendation_id"] = (
                self.agent_skill.source_recommendation_id
            )
        return payload


class _CreateSkillSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    scope: LatentSkillScope
    origin: str = Field(min_length=1)
    triggers: list[str] | None = None
    raw_markdown: str | None = None
    targets: list[str] | None = None
    source_recommendation_id: str | None = None
    metadata: dict[str, Any] | None = None


class CreateSkillUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        repository: AgentSkillRepository,
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

    def execute(self, command: CreateSkillCommand) -> CreateSkillResult:
        validated = _CreateSkillSchema.model_validate(command)
        triggers = _normalize_triggers(validated.triggers)
        name = validated.name.strip()
        description = validated.description.strip()
        raw_markdown = validated.raw_markdown
        if raw_markdown is not None:
            parsed = _parse_skill_markdown(raw_markdown)
            if parsed.name != name:
                raise ValidationFailedError("raw_markdown frontmatter name conflicts with name.")
            if parsed.description != description:
                raise ValidationFailedError(
                    "raw_markdown frontmatter description conflicts with description."
                )
            if triggers and parsed.triggers != triggers:
                raise ValidationFailedError(
                    "raw_markdown frontmatter triggers conflict with triggers."
                )
            triggers = parsed.triggers or triggers

        slug = self._resolve_slug(validated.scope, self._slug(name))
        skill_dir = self._skill_dir_for(validated.scope, slug)
        skill_file = f"{skill_dir}/SKILL.md"
        content = self._render_skill_markdown(
            name=name,
            description=description,
            triggers=triggers,
            raw_markdown=raw_markdown,
        )
        write = self._safe_write_for(validated.scope)
        audit_scope = (
            AuditEventScope.global_
            if validated.scope == LatentSkillScope.global_
            else AuditEventScope.project
        )
        write_result = None
        native_result = None
        try:
            write_result = write.execute(
                SafeWriteCommand(
                    relative_path=skill_file,
                    content=content,
                    scope=audit_scope,
                    origin=validated.origin,
                    action="create_skill",
                )
            )
            now = datetime.now(UTC)
            metadata = {
                "triggers": triggers,
                "creation_flow": "direct",
                "recommendation_flow": False,
                **(validated.metadata or {}),
            }
            if validated.source_recommendation_id is not None:
                metadata["source_recommendation_id"] = validated.source_recommendation_id
            agent_skill = AgentSkill(
                id=str(uuid4()),
                created_at=now,
                updated_at=now,
                name=name,
                slug=slug,
                description=description,
                scope=validated.scope,
                status=AgentSkillStatus.active,
                canonical_path=skill_file,
                origin=validated.origin,
                audit_reference=write_result.audit_reference,
                content_hash=_hash_text(content),
                source_recommendation_id=validated.source_recommendation_id,
                metadata=metadata,
            )
            native_result = self.native_skill_sync.sync(
                skill=agent_skill,  # type: ignore[arg-type]
                slug=slug,
                canonical_skill_file=skill_file,
                origin=validated.origin,
                drift_decision="keep",
                canonical_base_path=write.project_root,
                targets=validated.targets,
            )
            agent_skill = agent_skill.model_copy(
                update={
                    "native_installations": native_result.installations,
                    "audit_reference": ", ".join(
                        ref
                        for ref in [write_result.audit_reference, *native_result.audit_references]
                        if ref
                    ),
                }
            )
            registry_write = self.repository.write(agent_skill, origin=validated.origin)
            audit_references = [agent_skill.audit_reference]
            snapshot_references = [
                write_result.snapshot_reference,
                *native_result.snapshot_references,
            ]
            if registry_write is not None:
                audit_references.append(registry_write.audit_reference)
                snapshot_references.append(registry_write.snapshot_reference)
            return CreateSkillResult(
                agent_skill=agent_skill,
                slug=slug,
                skill_dir=skill_dir,
                skill_file=skill_file,
                created_paths=[write_result.relative_path],
                affected_paths=[write_result.relative_path, *native_result.affected_paths],
                audit_reference=", ".join(ref for ref in audit_references if ref),
                snapshot_reference=", ".join(ref for ref in snapshot_references if ref),
                native_installations=native_result.installations,
                warnings=native_result.warnings,
            )
        except Exception:
            if write_result is not None:
                _cleanup_created_file(write.project_root / write_result.relative_path)
            if native_result is not None:
                for affected_path in native_result.affected_paths:
                    _cleanup_created_file(self.project_root / affected_path)
            raise

    def _resolve_slug(self, scope: LatentSkillScope, base_slug: str) -> str:
        base_dir = self._absolute_skill_dir_for(scope, base_slug)
        if base_dir.exists() and not base_dir.is_dir():
            raise StorageError(f"Caminho ocupado por um arquivo regular: {base_dir}")
        if not base_dir.exists():
            return base_slug
        suffix = 2
        while True:
            candidate = f"{base_slug}-{suffix}"
            candidate_dir = self._absolute_skill_dir_for(scope, candidate)
            if candidate_dir.exists() and not candidate_dir.is_dir():
                raise StorageError(f"Caminho ocupado por um arquivo regular: {candidate_dir}")
            if not candidate_dir.exists():
                return candidate
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
        return self._safe_write_for(scope).project_root / self._skill_dir_for(scope, slug)

    def _render_skill_markdown(
        self,
        *,
        name: str,
        description: str,
        triggers: list[str],
        raw_markdown: str | None,
    ) -> str:
        if raw_markdown is not None:
            return self._strip_absolute_project_paths(raw_markdown)
        active_triggers = triggers or [name]
        lines = [
            "---",
            f"name: {self._yaml_scalar(name)}",
            f"description: {self._yaml_scalar(description)}",
            "triggers:",
            *(f"  - {self._yaml_scalar(trigger)}" for trigger in active_triggers),
            "---",
            "",
            f"# {name}",
            "",
            "## Quando Usar",
            "",
            *[f"- {trigger}" for trigger in active_triggers],
            "",
            "## Instrucoes Operacionais",
            "",
            f"- {description}",
            "- Aplique a metodologia somente quando os gatilhos acima aparecerem no contexto.",
            "- Registre arquivos e referencias usando caminhos relativos ao projeto.",
            "",
        ]
        return self._strip_absolute_project_paths("\n".join(lines))

    def _strip_absolute_project_paths(self, value: str) -> str:
        if self.project_root.as_posix() == "/":
            return value
        value = value.replace(self.project_root.as_posix(), ".")
        value = value.replace(self.project_root.resolve().as_posix(), ".")
        return value.replace(str(self.project_root), ".")

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


def _normalize_triggers(triggers: list[str] | None) -> list[str]:
    return [trigger.strip() for trigger in triggers or [] if trigger.strip()]


def _hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _cleanup_created_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
