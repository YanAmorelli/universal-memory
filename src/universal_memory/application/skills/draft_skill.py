from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.application.skills.create_skill import _hash_text
from universal_memory.application.skills.native_skill_sync import NativeSkillSync
from universal_memory.application.skills.update_skill import _parse_skill_markdown, _slug
from universal_memory.application.skills.validate_skill import (
    SkillValidationReport,
    assert_validation_passes,
    validate_skill_tree,
    validate_slug,
)
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    AuditEventScope,
    LatentSkillScope,
    RuntimeRegistry,
)
from universal_memory.domain.ports import AgentSkillRepository


@dataclass(frozen=True, slots=True)
class CreateSkillDraftCommand:
    name: str
    description: str
    scope: LatentSkillScope
    origin: str
    slug: str | None = None
    triggers: list[str] | None = None
    raw_markdown: str | None = None


@dataclass(frozen=True, slots=True)
class PublishSkillCommand:
    draft_or_path: str
    origin: str
    slug: str | None = None
    sync: bool = False
    targets: list[str] | None = None


@dataclass(frozen=True, slots=True)
class DraftSkillResult:
    agent_skill: AgentSkill
    slug: str
    draft_path: str
    affected_paths: list[str]
    audit_reference: str
    snapshot_reference: str
    validation: SkillValidationReport | None = None
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "skill_id": self.agent_skill.id,
            "name": self.agent_skill.name,
            "slug": self.slug,
            "draft_path": self.draft_path,
            "affected_paths": self.affected_paths,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "warnings": self.warnings,
        }
        if self.validation is not None:
            payload["validation"] = self.validation.to_payload()
        return payload


@dataclass(frozen=True, slots=True)
class PublishSkillResult:
    agent_skill: AgentSkill
    slug: str
    skill_dir: str
    skill_file: str
    affected_paths: list[str]
    audit_reference: str
    snapshot_reference: str
    validation: SkillValidationReport
    native_installations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "skill_id": self.agent_skill.id,
            "name": self.agent_skill.name,
            "slug": self.slug,
            "skill_dir": self.skill_dir,
            "skill_file": self.skill_file,
            "affected_paths": self.affected_paths,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "native_installations": self.native_installations,
            "validation": self.validation.to_payload(),
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


class _CreateSkillDraftSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    scope: LatentSkillScope
    origin: str = Field(min_length=1)
    slug: str | None = None
    triggers: list[str] | None = None
    raw_markdown: str | None = None


class _PublishSkillSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    draft_or_path: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    slug: str | None = None
    sync: bool = False
    targets: list[str] | None = None


class CreateSkillDraftUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        repository: AgentSkillRepository,
        safe_write_use_case: SafeWriteUseCase,
    ) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository
        self.safe_write_use_case = safe_write_use_case

    def execute(self, command: CreateSkillDraftCommand) -> DraftSkillResult:
        validated = _CreateSkillDraftSchema.model_validate(command)
        name = validated.name.strip()
        description = validated.description.strip()
        slug = validate_slug(validated.slug.strip() if validated.slug else _slug(name))
        self._ensure_slug_available(validated.scope, slug)
        content = validated.raw_markdown or _draft_markdown(
            name=name,
            description=description,
            triggers=[item.strip() for item in validated.triggers or [] if item.strip()],
        )
        parsed = _parse_skill_markdown(content)
        draft_path = _draft_path(validated.scope, slug)
        write_result = self.safe_write_use_case.execute(
            SafeWriteCommand(
                relative_path=draft_path,
                content=content,
                scope=AuditEventScope.project,
                origin=validated.origin,
                action="create_skill_draft",
            )
        )
        report = validate_skill_tree(
            self.project_root / draft_path,
            project_root=self.project_root,
            subject=slug,
        )
        now = datetime.now(UTC)
        skill = AgentSkill(
            id=str(uuid4()),
            created_at=now,
            updated_at=now,
            name=parsed.name,
            slug=slug,
            description=parsed.description,
            scope=validated.scope,
            status=AgentSkillStatus.draft,
            canonical_path=draft_path,
            origin=validated.origin,
            audit_reference=write_result.audit_reference,
            content_hash=_hash_text(content),
            metadata={
                "triggers": parsed.triggers,
                "creation_flow": "draft",
                "draft_path": draft_path,
                "validation": report.to_payload(),
            },
        )
        registry_write = self.repository.write(skill, origin=validated.origin)
        audit_refs = [write_result.audit_reference]
        snapshot_refs = [write_result.snapshot_reference]
        if registry_write is not None:
            audit_refs.append(registry_write.audit_reference)
            snapshot_refs.append(registry_write.snapshot_reference)
        return DraftSkillResult(
            agent_skill=skill,
            slug=slug,
            draft_path=draft_path,
            affected_paths=[write_result.relative_path],
            audit_reference=", ".join(audit_refs),
            snapshot_reference=", ".join(snapshot_refs),
            validation=report,
            warnings=report.warnings,
        )

    def _ensure_slug_available(self, scope: LatentSkillScope, slug: str) -> None:
        for skill in self.repository.list(scope=scope):
            if skill.slug == slug:
                raise ValidationFailedError(f"Skill slug already exists: {slug}")


class PublishSkillUseCase:
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

    def execute(self, command: PublishSkillCommand) -> PublishSkillResult:
        validated = _PublishSkillSchema.model_validate(command)
        draft_skill, draft_file = self._resolve_draft(validated.draft_or_path)
        content = draft_file.read_text(encoding="utf-8")
        report = validate_skill_tree(
            draft_file, project_root=self.project_root, subject=draft_skill.slug
        )
        assert_validation_passes(report)
        parsed = _parse_skill_markdown(content)
        slug = validate_slug(validated.slug.strip() if validated.slug else draft_skill.slug)
        canonical_dir = _canonical_dir(draft_skill.scope, slug)
        canonical_file = f"{canonical_dir}/SKILL.md"
        if (
            self._base_for(draft_skill.scope) / canonical_file
        ).exists() and canonical_file != draft_skill.canonical_path:
            raise StorageError(f"Canonical skill destination already exists: {canonical_dir}")
        write = self._safe_write_for(draft_skill.scope)
        write_result = write.execute(
            SafeWriteCommand(
                relative_path=canonical_file,
                content=content,
                scope=_audit_scope(draft_skill.scope),
                origin=validated.origin,
                action="publish_skill",
            )
        )
        now = datetime.now(UTC)
        skill = draft_skill.model_copy(
            update={
                "updated_at": now,
                "name": parsed.name,
                "slug": slug,
                "description": parsed.description,
                "status": AgentSkillStatus.active,
                "canonical_path": canonical_file,
                "origin": validated.origin,
                "content_hash": _hash_text(content),
                "metadata": {
                    **draft_skill.metadata,
                    "triggers": parsed.triggers,
                    "creation_flow": "draft_publish",
                    "draft_path": draft_skill.draft_path,
                    "validation": report.to_payload(),
                },
            }
        )
        native_result = None
        if validated.sync:
            native_result = self.native_skill_sync.sync(
                skill=skill,  # type: ignore[arg-type]
                slug=slug,
                canonical_skill_file=canonical_file,
                origin=validated.origin,
                drift_decision="keep",
                canonical_base_path=write.project_root,
                targets=validated.targets,
                allow_unmanaged_overwrite=False,
            )
            skill = skill.model_copy(update={"native_installations": native_result.installations})
        registry_write = self.repository.replace(skill, origin=validated.origin)
        audit_refs = [
            write_result.audit_reference,
            *(native_result.audit_references if native_result is not None else []),
        ]
        snapshot_refs = [
            write_result.snapshot_reference,
            *(native_result.snapshot_references if native_result is not None else []),
        ]
        if registry_write is not None:
            audit_refs.append(registry_write.audit_reference)
            snapshot_refs.append(registry_write.snapshot_reference)
        return PublishSkillResult(
            agent_skill=skill,
            slug=slug,
            skill_dir=canonical_dir,
            skill_file=canonical_file,
            affected_paths=[
                write_result.relative_path,
                *(native_result.affected_paths if native_result is not None else []),
            ],
            audit_reference=", ".join(ref for ref in audit_refs if ref),
            snapshot_reference=", ".join(ref for ref in snapshot_refs if ref),
            validation=report,
            native_installations=native_result.installations if native_result is not None else [],
            warnings=[
                *report.warnings,
                *(native_result.warnings if native_result is not None else []),
            ],
        )

    def _resolve_draft(self, draft_or_path: str) -> tuple[AgentSkill, Path]:
        path = Path(draft_or_path)
        if not path.is_absolute():
            path = self.project_root / path
        if path.exists():
            draft_file = path / "SKILL.md" if path.is_dir() else path
            for skill in self.repository.list(status=AgentSkillStatus.draft):
                if (
                    self.project_root / (skill.draft_path or skill.canonical_path)
                ).resolve() == draft_file.resolve():
                    return skill, draft_file.resolve()
            raise ValidationFailedError(
                "Draft path is not registered. Use skills adopt for existing canonical work."
            )
        for skill in self.repository.list(status=AgentSkillStatus.draft):
            if (
                draft_or_path in {skill.id, skill.slug}
                or skill.name.casefold() == draft_or_path.casefold()
            ):
                return skill, self.project_root / (skill.draft_path or skill.canonical_path)
        raise ValidationFailedError(f"Draft skill not found: {draft_or_path}")

    def _safe_write_for(self, scope: LatentSkillScope) -> SafeWriteUseCase:
        if scope == LatentSkillScope.global_:
            return self.global_safe_write_use_case
        return self.safe_write_use_case

    def _base_for(self, scope: LatentSkillScope) -> Path:
        return self._safe_write_for(scope).project_root


def _draft_markdown(*, name: str, description: str, triggers: list[str]) -> str:
    active_triggers = triggers or [name]
    lines = [
        "---",
        f'name: "{name}"',
        f'description: "{description}"',
        "triggers:",
        *(f'  - "{trigger}"' for trigger in active_triggers),
        "---",
        "",
        f"# {name}",
        "",
        "## When To Use",
        "",
        *[f"- {trigger}" for trigger in active_triggers],
        "",
        "## Operational Instructions",
        "",
        f"- {description}",
        "- Record files and references using project-relative paths.",
        "",
    ]
    return "\n".join(lines)


def _draft_path(scope: LatentSkillScope, slug: str) -> str:
    if scope == LatentSkillScope.global_:
        return f"drafts/skills/{slug}/SKILL.md"
    return f".umem/drafts/skills/{slug}/SKILL.md"


def _canonical_dir(scope: LatentSkillScope, slug: str) -> str:
    if scope == LatentSkillScope.global_:
        return f"skills/{slug}"
    return f".umem/skills/{slug}"


def _audit_scope(scope: LatentSkillScope) -> AuditEventScope:
    return AuditEventScope.global_ if scope == LatentSkillScope.global_ else AuditEventScope.project
