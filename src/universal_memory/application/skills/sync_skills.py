from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.application.skills.native_skill_sync import (
    NativeDriftDecision,
    NativeSkillSync,
)
from universal_memory.application.skills.update_skill import _parse_skill_markdown
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    LatentSkill,
    LatentSkillStatus,
    RuntimeId,
    RuntimeRegistry,
)
from universal_memory.domain.ports import AgentSkillRepository


@dataclass(frozen=True, slots=True)
class SyncSkillsCommand:
    skill_id_or_name: str | None = None
    targets: list[str] | None = None
    drift_decision: NativeDriftDecision = "keep"
    origin: str = "sync_skills"


@dataclass(frozen=True, slots=True)
class SyncSkillResult:
    skill_id: str
    name: str
    scope: str
    status: str
    canonical_path: str
    affected_paths: list[str] = field(default_factory=list)
    removed_paths: list[str] = field(default_factory=list)
    targets: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    audit_reference: str = ""
    snapshot_reference: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "scope": self.scope,
            "status": self.status,
            "canonical_path": self.canonical_path,
            "affected_paths": self.affected_paths,
            "removed_paths": self.removed_paths,
            "targets": self.targets,
            "warnings": self.warnings,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
        }


@dataclass(frozen=True, slots=True)
class SyncSkillsResult:
    skills: list[SyncSkillResult]
    warnings: list[str] = field(default_factory=list)
    affected_paths: list[str] = field(default_factory=list)
    removed_paths: list[str] = field(default_factory=list)
    audit_reference: str = ""
    snapshot_reference: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "skills": [skill.to_payload() for skill in self.skills],
            "affected_paths": self.affected_paths,
            "removed_paths": self.removed_paths,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
        }


class _SyncSkillsCommandSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    skill_id_or_name: str | None = None
    targets: list[str] | None = None
    drift_decision: NativeDriftDecision = "keep"
    origin: str = Field(min_length=1)


class SyncSkillsUseCase:
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

    def execute(self, command: SyncSkillsCommand) -> SyncSkillsResult:
        validated = _SyncSkillsCommandSchema.model_validate(command)
        _validate_targets(validated.targets)
        skills = self._resolve_skills(validated.skill_id_or_name)
        for skill in skills:
            self._validate_canonical_skill(skill)

        results: list[SyncSkillResult] = []
        warnings: list[str] = []
        affected_paths: list[str] = []
        removed_paths: list[str] = []
        audit_refs: list[str] = []
        snapshot_refs: list[str] = []
        for skill in skills:
            base_path = self._canonical_base_path_for(skill)
            native_result = self.native_skill_sync.sync(
                skill=self._latent_view_for(skill),
                slug=skill.slug,
                canonical_skill_file=skill.canonical_path,
                origin=validated.origin,
                drift_decision=validated.drift_decision,
                canonical_base_path=base_path,
                targets=validated.targets,
                allow_unmanaged_overwrite=False,
            )
            audit_ref_candidates = [
                ref for ref in [skill.audit_reference, *native_result.audit_references] if ref
            ]
            managed_installations = _merge_managed_installations(
                skill.native_installations,
                native_result.installations,
            )
            updated = skill.model_copy(
                update={
                    "updated_at": datetime.now(UTC),
                    "content_hash": _hash_text(self._canonical_text_for(skill)),
                    "native_installations": managed_installations,
                    "audit_reference": ", ".join(audit_ref_candidates),
                }
            )
            registry_write = self.repository.write(updated, origin=validated.origin)
            skill_audit_refs = [*native_result.audit_references]
            skill_snapshot_refs = [*native_result.snapshot_references]
            if registry_write is not None:
                skill_audit_refs.append(registry_write.audit_reference)
                skill_snapshot_refs.append(registry_write.snapshot_reference)

            skill_result = SyncSkillResult(
                skill_id=updated.id,
                name=updated.name,
                scope=updated.scope.value,
                status=updated.status.value,
                canonical_path=updated.canonical_path,
                affected_paths=native_result.affected_paths,
                removed_paths=native_result.removed_paths,
                targets=[_target_payload(target) for target in native_result.installations],
                warnings=native_result.warnings,
                audit_reference=", ".join(ref for ref in skill_audit_refs if ref),
                snapshot_reference=", ".join(ref for ref in skill_snapshot_refs if ref),
            )
            results.append(skill_result)
            warnings.extend(native_result.warnings)
            affected_paths.extend(native_result.affected_paths)
            removed_paths.extend(native_result.removed_paths)
            audit_refs.extend(skill_audit_refs)
            snapshot_refs.extend(skill_snapshot_refs)

        return SyncSkillsResult(
            skills=results,
            warnings=warnings,
            affected_paths=affected_paths,
            removed_paths=removed_paths,
            audit_reference=", ".join(ref for ref in audit_refs if ref),
            snapshot_reference=", ".join(ref for ref in snapshot_refs if ref),
        )

    def _resolve_skills(self, selector: str | None) -> list[AgentSkill]:
        active_skills = self.repository.list(status=AgentSkillStatus.active)
        if selector is None:
            return active_skills
        normalized = selector.strip().casefold()
        if not normalized:
            raise ValidationFailedError("Skill selector must not be empty.")
        id_matches = [skill for skill in active_skills if skill.id == selector]
        if id_matches:
            return id_matches
        name_matches = [skill for skill in active_skills if skill.name.casefold() == normalized]
        if len(name_matches) > 1:
            raise ValidationFailedError(f"Ambiguous skill selector: {selector}")
        if name_matches:
            return name_matches
        raise ValidationFailedError(f"Canonical skill not found: {selector}")

    def _validate_canonical_skill(self, skill: AgentSkill) -> None:
        relative_path = _safe_relative_path(skill.canonical_path)
        path = self._canonical_base_path_for(skill) / relative_path
        if not path.is_file():
            raise ValidationFailedError(
                f"Canonical SKILL.md missing for skill {skill.id}: {skill.canonical_path}"
            )
        try:
            _parse_skill_markdown(path.read_text(encoding="utf-8"))
        except ValidationFailedError as exc:
            raise ValidationFailedError(
                f"Canonical SKILL.md invalid for skill {skill.id}: {skill.canonical_path}"
            ) from exc

    def _canonical_text_for(self, skill: AgentSkill) -> str:
        relative_path = _safe_relative_path(skill.canonical_path)
        return (self._canonical_base_path_for(skill) / relative_path).read_text(encoding="utf-8")

    def _canonical_base_path_for(self, skill: AgentSkill) -> Path:
        if skill.scope.value == "global":
            return self.global_safe_write_use_case.project_root
        return self.project_root

    @staticmethod
    def _latent_view_for(skill: AgentSkill) -> LatentSkill:
        return LatentSkill(
            id=skill.id,
            created_at=skill.created_at,
            updated_at=skill.updated_at,
            name=skill.name,
            description=skill.description,
            scope=skill.scope,
            status=LatentSkillStatus.active,
            recurrence_count=1,
            metadata={**skill.metadata, "native_installations": skill.native_installations},
        )


def _validate_targets(targets: list[str] | None) -> None:
    if targets is None:
        return
    supported = {item.value for item in RuntimeId}
    unsupported = [target for target in targets if target not in supported]
    if unsupported:
        raise ValidationFailedError(f"Unsupported runtimes: {', '.join(unsupported)}")


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValidationFailedError(f"Invalid canonical skill path: {value}")
    return path


def _target_payload(installation: dict[str, Any]) -> dict[str, Any]:
    drift = bool(installation.get("drift_detected", False))
    status = installation.get("status")
    if drift and status not in {"unmanaged_native", "overwritten"}:
        status = "drift_kept"
    if status is None:
        status = "drift_kept" if drift and not installation.get("audit_reference") else "synced"
    return {
        "runtime": installation.get("runtime", ""),
        "path": installation.get("path", ""),
        "status": status,
        "drift_detected": drift,
        "canonical_hash": installation.get("canonical_hash", ""),
        "target_hash": installation.get("target_hash", ""),
        "audit_reference": installation.get("audit_reference", ""),
        "snapshot_reference": installation.get("snapshot_reference", ""),
        "affected_paths": list(installation.get("manifest", [])),
        "removed_paths": list(installation.get("removed_paths", [])),
    }


def _merge_managed_installations(
    existing: list[dict[str, Any]],
    sync_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = {
        str(installation.get("path")): dict(installation)
        for installation in existing
        if installation.get("path")
    }
    for installation in sync_results:
        path = str(installation.get("path", ""))
        if not path or installation.get("status") == "unmanaged_native":
            continue
        merged[path] = dict(installation)
    return list(merged.values())


def _hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
