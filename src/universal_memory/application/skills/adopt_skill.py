from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills.create_skill import _hash_text
from universal_memory.application.skills.import_skill import ImportSkillCommand, ImportSkillUseCase
from universal_memory.application.skills.update_skill import _parse_skill_markdown, _slug
from universal_memory.application.skills.validate_skill import (
    assert_validation_passes,
    validate_skill_tree,
    validate_slug,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    LatentSkillScope,
    RuntimeRegistry,
)
from universal_memory.domain.ports import AgentSkillRepository


@dataclass(frozen=True, slots=True)
class AdoptSkillCommand:
    path: str | Path
    scope: LatentSkillScope
    origin: str
    slug: str | None = None
    replace_native: bool = False
    sync_after_adopt: bool = False
    visibility: str | None = None
    category: str = "user-facing"


@dataclass(frozen=True, slots=True)
class AdoptSkillResult:
    agent_skill: AgentSkill
    slug: str
    skill_dir: str
    skill_file: str
    adopted_source: str
    affected_paths: list[str]
    audit_reference: str
    snapshot_reference: str
    native_installations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "skill_id": self.agent_skill.id,
            "name": self.agent_skill.name,
            "slug": self.slug,
            "skill_dir": self.skill_dir,
            "skill_file": self.skill_file,
            "adopted_source": self.adopted_source,
            "affected_paths": self.affected_paths,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "native_installations": self.native_installations,
            "warnings": self.warnings,
            "canonical_skill": {
                "id": self.agent_skill.id,
                "name": self.agent_skill.name,
                "description": self.agent_skill.description,
                "scope": self.agent_skill.scope.value,
                "status": self.agent_skill.status.value,
                "canonical_path": self.agent_skill.canonical_path,
                "origin": self.agent_skill.origin,
                "content_hash": self.agent_skill.content_hash,
                "visibility": self.agent_skill.visibility,
                "category": self.agent_skill.category,
            },
            "visibility": self.agent_skill.visibility,
            "category": self.agent_skill.category,
        }


class _AdoptSkillSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    path: str | Path
    scope: LatentSkillScope
    origin: str = Field(min_length=1)
    slug: str | None = None
    replace_native: bool = False
    sync_after_adopt: bool = False
    visibility: str | None = None
    category: str = "user-facing"


class AdoptSkillUseCase:
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
        self.import_use_case = ImportSkillUseCase(
            project_root=project_root,
            repository=repository,
            safe_write_use_case=safe_write_use_case,
            global_safe_write_use_case=global_safe_write_use_case,
            runtime_registry=runtime_registry,
        )

    def execute(self, command: AdoptSkillCommand) -> AdoptSkillResult:
        validated = _AdoptSkillSchema.model_validate(command)
        source_dir = _source_dir(self.project_root, Path(validated.path))
        skill_file = source_dir / "SKILL.md"
        markdown = skill_file.read_text(encoding="utf-8")
        parsed = _parse_skill_markdown(markdown)
        slug = validate_slug(validated.slug.strip() if validated.slug else _slug(parsed.name))
        category = _normalize_category(validated.category)
        visibility = self._resolve_visibility(
            scope=validated.scope,
            requested_visibility=validated.visibility,
            category=category,
        )
        canonical_dir = self._skill_dir_for(validated.scope, slug, visibility, category)
        canonical_file = f"{canonical_dir}/SKILL.md"
        report = validate_skill_tree(skill_file, project_root=self.project_root, subject=slug)
        assert_validation_passes(report)
        for existing in self.repository.list(scope=validated.scope):
            if existing.slug == slug:
                raise ValidationFailedError(f"Skill slug already exists: {slug}")

        if _is_canonical_source(self.project_root, source_dir, canonical_dir):
            now = datetime.now(UTC)
            skill = AgentSkill(
                id=str(uuid4()),
                created_at=now,
                updated_at=now,
                name=parsed.name,
                slug=slug,
                description=parsed.description,
                scope=validated.scope,
                status=AgentSkillStatus.active,
                canonical_path=canonical_file,
                origin=validated.origin,
                audit_reference="",
                content_hash=_hash_text(markdown),
                metadata={
                    "triggers": parsed.triggers,
                    "creation_flow": "adopt",
                    "adopt_source": _relative_display(self.project_root, source_dir),
                    "validation": report.to_payload(),
                    **_placement_metadata(validated.scope, visibility, category),
                },
            )
            registry_write = self.repository.write(skill, origin=validated.origin)
            return AdoptSkillResult(
                agent_skill=skill,
                slug=slug,
                skill_dir=canonical_dir,
                skill_file=canonical_file,
                adopted_source=_relative_display(self.project_root, source_dir),
                affected_paths=[canonical_file],
                audit_reference=registry_write.audit_reference
                if registry_write is not None
                else "",
                snapshot_reference=registry_write.snapshot_reference
                if registry_write is not None
                else "",
                warnings=report.warnings,
            )

        imported = self.import_use_case.execute(
            ImportSkillCommand(
                path=source_dir,
                scope=validated.scope,
                origin=validated.origin,
                replace_native=validated.replace_native,
                sync_after_import=validated.sync_after_adopt,
                slug=slug,
                visibility=visibility,
                category=category,
            )
        )
        skill = imported.agent_skill.model_copy(
            update={"metadata": {**imported.agent_skill.metadata, "creation_flow": "adopt"}}
        )
        self.repository.replace(skill, origin=validated.origin)
        return AdoptSkillResult(
            agent_skill=skill,
            slug=imported.slug,
            skill_dir=imported.skill_dir,
            skill_file=imported.skill_file,
            adopted_source=_relative_display(self.project_root, source_dir),
            affected_paths=imported.affected_paths,
            audit_reference=imported.audit_reference,
            snapshot_reference=imported.snapshot_reference,
            native_installations=imported.native_installations,
            warnings=[*report.warnings, *imported.warnings],
        )

    def _resolve_visibility(
        self,
        *,
        scope: LatentSkillScope,
        requested_visibility: str | None,
        category: str,
    ) -> str | None:
        if scope == LatentSkillScope.global_:
            if requested_visibility is not None:
                raise ValidationFailedError("visibility is only supported for project skills.")
            return None
        if requested_visibility is not None:
            visibility = requested_visibility.strip().lower()
            if visibility not in {"shared", "private"}:
                raise ValidationFailedError("visibility must be shared or private.")
            if visibility == "shared" and category == "operational":
                raise ValidationFailedError(
                    "operational skills cannot be shared by adopt; use skills share with "
                    "operational confirmation."
                )
            return visibility
        if self._project_uses_shared_layout():
            return "private" if category == "operational" else "shared"
        return None

    def _project_uses_shared_layout(self) -> bool:
        layout = getattr(self.repository, "layout", None)
        return bool(getattr(layout, "is_shared", False))

    def _skill_dir_for(
        self,
        scope: LatentSkillScope,
        slug: str,
        visibility: str | None,
        category: str,
    ) -> str:
        if scope == LatentSkillScope.global_:
            return f"skills/{slug}"
        if (
            self._project_uses_shared_layout()
            and visibility == "shared"
            and category != "operational"
        ):
            return f"umem/skills/{slug}"
        return f".umem/skills/{slug}"


def _source_dir(project_root: Path, path: Path) -> Path:
    source = path if path.is_absolute() else project_root / path
    if source.is_file():
        source = source.parent
    if not (source / "SKILL.md").is_file():
        raise ValidationFailedError("Adopt path must be a skill directory or SKILL.md file.")
    return source.resolve()


def _is_canonical_source(project_root: Path, source_dir: Path, canonical_dir: str) -> bool:
    return source_dir == (project_root / canonical_dir).resolve()


def _relative_display(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_category(category: str) -> str:
    normalized = category.strip().lower().replace("_", "-")
    if normalized not in {"user-facing", "operational"}:
        raise ValidationFailedError("category must be user-facing or operational.")
    return normalized


def _placement_metadata(
    scope: LatentSkillScope,
    visibility: str | None,
    category: str,
) -> dict[str, str]:
    if scope == LatentSkillScope.project and visibility is not None:
        return {"visibility": visibility, "category": category}
    return {}
