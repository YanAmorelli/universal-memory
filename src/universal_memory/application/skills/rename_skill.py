from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.skills.validate_skill import validate_slug
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import AgentSkillStatus
from universal_memory.domain.ports import AgentSkillRepository


@dataclass(frozen=True, slots=True)
class RenameSkillCommand:
    skill_id_or_name: str
    slug: str
    origin: str


@dataclass(frozen=True, slots=True)
class RenameSkillResult:
    agent_skill: Any
    old_path: str
    new_path: str
    affected_paths: list[str]
    warnings: list[str] = field(default_factory=list)
    audit_reference: str = ""
    snapshot_reference: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "skill_id": self.agent_skill.id,
            "name": self.agent_skill.name,
            "slug": self.agent_skill.slug,
            "old_path": self.old_path,
            "new_path": self.new_path,
            "affected_paths": self.affected_paths,
            "warnings": self.warnings,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
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


class _RenameSkillSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    skill_id_or_name: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    origin: str = Field(min_length=1)


class RenameSkillUseCase:
    def __init__(self, *, project_root: Path, repository: AgentSkillRepository) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository

    def execute(self, command: RenameSkillCommand) -> RenameSkillResult:
        validated = _RenameSkillSchema.model_validate(command)
        new_slug = validate_slug(validated.slug)
        skill = _resolve_skill(self.repository, validated.skill_id_or_name)
        for other in self.repository.list(scope=skill.scope):
            if other.id != skill.id and other.slug == new_slug:
                raise ValidationFailedError(f"Skill slug already exists: {new_slug}")
        old_dir = (self.project_root / skill.canonical_path).parent
        new_dir = old_dir.parent / new_slug
        if new_dir.exists():
            raise StorageError(f"Destination skill directory already exists: {new_dir.as_posix()}")
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(old_dir.as_posix(), new_dir.as_posix())
        new_path = f"{new_dir.relative_to(self.project_root).as_posix()}/SKILL.md"
        updated = skill.model_copy(
            update={
                "updated_at": datetime.now(UTC),
                "slug": new_slug,
                "canonical_path": new_path,
                "origin": validated.origin,
            }
        )
        registry_write = self.repository.replace(updated, origin=validated.origin)
        return RenameSkillResult(
            agent_skill=updated,
            old_path=skill.canonical_path,
            new_path=new_path,
            affected_paths=[skill.canonical_path, new_path],
            audit_reference=registry_write.audit_reference if registry_write is not None else "",
            snapshot_reference=registry_write.snapshot_reference
            if registry_write is not None
            else "",
        )


def _resolve_skill(repository: AgentSkillRepository, selector: str):
    normalized = selector.strip().casefold()
    matches = []
    for skill in repository.list(status=AgentSkillStatus.active):
        if selector in {skill.id, skill.slug}:
            return skill
        if skill.name.casefold() == normalized:
            matches.append(skill)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValidationFailedError(f"Ambiguous skill selector: {selector}")
    raise ValidationFailedError(f"Canonical skill not found: {selector}")
