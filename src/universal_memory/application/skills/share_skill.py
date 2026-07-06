from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import tomli_w
from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.application.skills.create_skill import _hash_text
from universal_memory.application.skills.update_skill import _parse_skill_markdown
from universal_memory.application.skills.validate_skill import (
    assert_validation_passes,
    validate_skill_tree,
)
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    AuditEventScope,
    LatentSkillScope,
)
from universal_memory.domain.ports import AgentSkillRepository


@dataclass(frozen=True, slots=True)
class ShareSkillCommand:
    skill_id_or_name: str
    category: str = "user-facing"
    confirm_operational: bool = False
    origin: str = "repository"


@dataclass(frozen=True, slots=True)
class ShareSkillResult:
    agent_skill: AgentSkill
    old_canonical_path: str
    new_canonical_path: str
    affected_paths: list[str]
    audit_reference: str
    snapshot_reference: str
    warnings: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "skill_id": self.agent_skill.id,
            "name": self.agent_skill.name,
            "slug": self.agent_skill.slug,
            "skill_dir": str(Path(self.new_canonical_path).parent).replace("\\", "/"),
            "skill_file": self.new_canonical_path,
            "old_canonical_path": self.old_canonical_path,
            "new_canonical_path": self.new_canonical_path,
            "affected_paths": self.affected_paths,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "recommended_actions": self.recommended_actions,
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


class _ShareSkillSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    skill_id_or_name: str = Field(min_length=1)
    category: str = "user-facing"
    confirm_operational: bool = False
    origin: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class _ResolvedSkill:
    skill: AgentSkill
    registered: bool


class ShareSkillUseCase:
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

    def execute(self, command: ShareSkillCommand) -> ShareSkillResult:  # noqa: PLR0912, PLR0915
        validated = _ShareSkillSchema.model_validate(command)
        requested_category = _normalize_category(validated.category)
        resolved = self._resolve_project_skill(validated.skill_id_or_name.strip())
        skill = resolved.skill
        category = self._effective_category(skill, requested_category)
        if category == "operational" and not validated.confirm_operational:
            raise ValidationFailedError(
                "Sharing operational skills requires explicit confirmation."
            )
        if skill.scope != LatentSkillScope.project:
            raise ValidationFailedError("Only project skills can be shared.")
        _validate_slug(skill.slug)
        _validate_skill_file_path(skill.canonical_path)
        source_dir = (self.project_root / Path(skill.canonical_path).parent).resolve()
        try:
            source_dir.relative_to(self.project_root)
        except ValueError as exc:
            raise ValidationFailedError("canonical_path must stay within the project.") from exc
        source_file = source_dir / "SKILL.md"
        if not source_file.is_file():
            raise StorageError(f"Canonical skill file not found: {skill.canonical_path}")
        target_dir = Path("umem") / "skills" / skill.slug
        target_file = f"{target_dir.as_posix()}/SKILL.md"
        if source_dir == (self.project_root / target_dir).resolve():
            existing = skill.model_copy(
                update={
                    "metadata": {
                        **skill.metadata,
                        "visibility": "shared",
                        "category": category,
                        "shared_allowed": category == "operational",
                    }
                }
            )
            metadata_result = None
            if category == "operational":
                metadata_result = self._allow_operational_skill(
                    skill.slug,
                    origin=validated.origin,
                )
            registry_write = self.repository.write(existing, origin=validated.origin)
            audit_refs = []
            snapshot_refs = []
            affected_paths = []
            if metadata_result is not None:
                audit_refs.append(metadata_result.audit_reference)
                snapshot_refs.append(metadata_result.snapshot_reference)
                affected_paths.append(metadata_result.relative_path)
            if registry_write is not None:
                audit_refs.append(registry_write.audit_reference)
                snapshot_refs.append(registry_write.snapshot_reference)
                affected_paths.append(registry_write.relative_path)
            return ShareSkillResult(
                agent_skill=existing,
                old_canonical_path=skill.canonical_path,
                new_canonical_path=target_file,
                affected_paths=affected_paths,
                audit_reference=", ".join(ref for ref in audit_refs if ref),
                snapshot_reference=", ".join(ref for ref in snapshot_refs if ref),
                recommended_actions=["Review umem/project.toml and commit the shared skill."],
            )

        files = self._source_files(source_dir)
        write_results = []
        try:
            for relative_file, content in files:
                write_results.append(
                    self.safe_write_use_case.execute(
                        SafeWriteCommand(
                            relative_path=f"{target_dir.as_posix()}/{relative_file}",
                            content=content,
                            scope=AuditEventScope.project,
                            origin=validated.origin,
                            action="share_skill",
                        )
                    )
                )
            metadata_result = None
            if category == "operational":
                metadata_result = self._allow_operational_skill(
                    skill.slug,
                    origin=validated.origin,
                )
            report = validate_skill_tree(
                self.project_root / target_file,
                project_root=self.project_root,
                subject=skill.slug,
            )
            assert_validation_passes(report)
            updated = skill.model_copy(
                update={
                    "canonical_path": target_file,
                    "origin": validated.origin,
                    "content_hash": _hash_text(
                        (self.project_root / target_file).read_text(encoding="utf-8")
                    ),
                    "metadata": {
                        **skill.metadata,
                        "visibility": "shared",
                        "category": category,
                        "shared_allowed": category == "operational",
                        "shared_from": skill.canonical_path,
                        "validation": report.to_payload(),
                    },
                }
            )
            remove_write = None
            if resolved.registered:
                remove_write = self.repository.remove(
                    skill.id,
                    scope=LatentSkillScope.project,
                    origin=validated.origin,
                )
            registry_write = self.repository.write(updated, origin=validated.origin)
        except Exception:
            for result in write_results:
                _cleanup_created_path(self.project_root / result.relative_path)
            raise

        audit_refs = [result.audit_reference for result in write_results]
        snapshot_refs = [result.snapshot_reference for result in write_results]
        if metadata_result is not None:
            audit_refs.append(metadata_result.audit_reference)
            snapshot_refs.append(metadata_result.snapshot_reference)
        if remove_write is not None:
            audit_refs.append(remove_write.audit_reference)
            snapshot_refs.append(remove_write.snapshot_reference)
        if registry_write is not None:
            audit_refs.append(registry_write.audit_reference)
            snapshot_refs.append(registry_write.snapshot_reference)
        affected_paths = [result.relative_path for result in write_results]
        if metadata_result is not None:
            affected_paths.append(metadata_result.relative_path)
        return ShareSkillResult(
            agent_skill=updated,
            old_canonical_path=skill.canonical_path,
            new_canonical_path=target_file,
            affected_paths=affected_paths,
            audit_reference=", ".join(ref for ref in audit_refs if ref),
            snapshot_reference=", ".join(ref for ref in snapshot_refs if ref),
            warnings=report.warnings,
            recommended_actions=["Review umem/project.toml and commit the shared skill."],
        )

    def _resolve_project_skill(self, skill_id_or_name: str) -> _ResolvedSkill:
        for skill in self.repository.list(scope=LatentSkillScope.project):
            if (
                skill_id_or_name in {skill.id, skill.slug}
                or skill.name.casefold() == skill_id_or_name.casefold()
            ):
                return _ResolvedSkill(skill=skill, registered=True)
        unregistered = self._unregistered_operational_skill(skill_id_or_name)
        if unregistered is not None:
            return _ResolvedSkill(skill=unregistered, registered=False)
        raise StorageError(f"Agent skill not found: {skill_id_or_name}")

    def _unregistered_operational_skill(self, skill_id_or_name: str) -> AgentSkill | None:
        slug = skill_id_or_name
        if slug != "use-universal-memory" or not _is_safe_slug(slug):
            return None
        skill_file = self.project_root / ".umem" / "skills" / slug / "SKILL.md"
        if not skill_file.is_file():
            return None
        report = validate_skill_tree(skill_file, project_root=self.project_root, subject=slug)
        assert_validation_passes(report)
        parsed = _parse_skill_markdown(skill_file.read_text(encoding="utf-8"))
        if (
            skill_id_or_name not in {slug, parsed.name}
            and parsed.name.casefold() != skill_id_or_name.casefold()
        ):
            return None
        now = datetime.now(UTC)
        return AgentSkill(
            id=str(uuid4()),
            created_at=now,
            updated_at=now,
            name=parsed.name,
            slug=slug,
            description=parsed.description,
            scope=LatentSkillScope.project,
            status=AgentSkillStatus.active,
            canonical_path=f".umem/skills/{slug}/SKILL.md",
            origin="local",
            audit_reference="UNREGISTERED",
            content_hash=_hash_text(skill_file.read_text(encoding="utf-8")),
            metadata={
                "triggers": parsed.triggers,
                "visibility": "private",
                "category": "operational" if slug == "use-universal-memory" else "user-facing",
                "creation_flow": "unregistered_share",
                "validation": report.to_payload(),
            },
        )

    @staticmethod
    def _effective_category(skill: AgentSkill, requested_category: str) -> str:
        stored_category = skill.category
        if stored_category is not None:
            normalized = _normalize_category(stored_category)
            if normalized == "operational":
                return "operational"
        if skill.slug == "use-universal-memory":
            return "operational"
        return requested_category

    def _source_files(self, source_dir: Path) -> list[tuple[str, str]]:
        files: list[tuple[str, str]] = []
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative_path = path.relative_to(source_dir).as_posix()
            files.append((relative_path, path.read_text(encoding="utf-8")))
        return files

    def _allow_operational_skill(self, slug: str, *, origin: str):
        policy_path = self.project_root / "umem" / "project.toml"
        if not policy_path.is_file():
            raise StorageError("Shared layout metadata umem/project.toml is missing")
        data = tomllib.loads(policy_path.read_text(encoding="utf-8"))
        allowlist = data.get("shared_operational_skills", [])
        if not isinstance(allowlist, list):
            raise StorageError("shared_operational_skills must be a list of skill slugs")
        if slug not in allowlist:
            allowlist = [*allowlist, slug]
        data["shared_operational_skills"] = sorted(str(item) for item in allowlist)
        return self.safe_write_use_case.execute(
            SafeWriteCommand(
                relative_path="umem/project.toml",
                content=tomli_w.dumps(data),
                scope=AuditEventScope.project,
                origin=origin,
                action="share_operational_skill",
            )
        )


def _normalize_category(category: str) -> str:
    normalized = category.strip().lower().replace("_", "-")
    if normalized not in {"user-facing", "operational"}:
        raise ValidationFailedError("category must be user-facing or operational.")
    return normalized


def _is_safe_slug(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug))


def _validate_slug(slug: str) -> None:
    if not _is_safe_slug(slug):
        raise ValidationFailedError("Skill slug must use lowercase letters, numbers, and hyphens.")


def _validate_relative_path(value: str) -> None:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValidationFailedError("canonical_path must be project-relative and safe.")


def _validate_skill_file_path(value: str) -> None:
    _validate_relative_path(value)
    if Path(value).name != "SKILL.md":
        raise ValidationFailedError("canonical_path must point to SKILL.md.")


def _cleanup_created_path(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink(missing_ok=True)
        parent = path.parent
        while parent.name and parent != parent.parent and not any(parent.iterdir()):
            parent.rmdir()
            if parent.as_posix().endswith("umem/skills"):
                break
            parent = parent.parent
    except OSError:
        pass
