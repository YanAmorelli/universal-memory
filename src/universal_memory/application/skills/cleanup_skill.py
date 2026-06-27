from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.skills.native_skill_sync import (
    managed_native_target_paths,
    orphan_native_target_paths,
    planned_managed_target_cleanup,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import AgentSkill, AgentSkillStatus
from universal_memory.domain.ports import AgentSkillRepository


@dataclass(frozen=True, slots=True)
class CleanupSkillCommand:
    skill_id_or_name: str
    origin: str
    targets: bool = True
    dry_run: bool = True


@dataclass(frozen=True, slots=True)
class RepairSkillsCommand:
    origin: str
    remove_orphan_targets: bool = False
    dry_run: bool = True


@dataclass(frozen=True, slots=True)
class CleanupPlan:
    skill: str
    mode: str
    dry_run: bool
    removable_paths: list[str] = field(default_factory=list)
    blocked_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "skill": self.skill,
            "mode": self.mode,
            "dry_run": self.dry_run,
            "removable_paths": self.removable_paths,
            "blocked_paths": self.blocked_paths,
            "warnings": self.warnings,
        }


@dataclass(frozen=True, slots=True)
class CleanupSkillResult:
    plan: CleanupPlan
    removed_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_payload(),
            "removed_paths": self.removed_paths,
            "warnings": self.warnings,
        }


@dataclass(frozen=True, slots=True)
class RepairSkillsResult:
    plans: list[CleanupPlan]
    removed_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "plans": [plan.to_payload() for plan in self.plans],
            "removed_paths": self.removed_paths,
            "warnings": self.warnings,
        }


class _CleanupSkillSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    skill_id_or_name: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    targets: bool = True
    dry_run: bool = True


class _RepairSkillsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    origin: str = Field(min_length=1)
    remove_orphan_targets: bool = False
    dry_run: bool = True


class CleanupSkillUseCase:
    def __init__(self, *, project_root: Path, repository: AgentSkillRepository) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository

    def execute(self, command: CleanupSkillCommand) -> CleanupSkillResult:
        validated = _CleanupSkillSchema.model_validate(command)
        skill = _resolve_skill(self.repository, validated.skill_id_or_name)
        plan = _plan_for_skill(skill, project_root=self.project_root, dry_run=validated.dry_run)
        removed = (
            [] if validated.dry_run else _remove_paths(self.project_root, plan.removable_paths)
        )
        return CleanupSkillResult(plan=plan, removed_paths=removed, warnings=plan.warnings)


class RepairSkillsUseCase:
    def __init__(self, *, project_root: Path, repository: AgentSkillRepository) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository

    def execute(self, command: RepairSkillsCommand) -> RepairSkillsResult:
        validated = _RepairSkillsSchema.model_validate(command)
        if not validated.remove_orphan_targets:
            return RepairSkillsResult(
                plans=[],
                warnings=[
                    "No repair action selected. Use remove_orphan_targets for target cleanup."
                ],
            )
        active_skills = self.repository.list(status=AgentSkillStatus.active)
        managed_installations = [
            installation for skill in active_skills for installation in skill.native_installations
        ]
        orphan_roots = orphan_native_target_paths(
            project_root=self.project_root,
            managed_installations=managed_installations,
        )
        plan = CleanupPlan(
            skill="all",
            mode="orphan-targets",
            dry_run=validated.dry_run,
            removable_paths=orphan_roots,
        )
        removed = [] if validated.dry_run else _remove_paths(self.project_root, orphan_roots)
        return RepairSkillsResult(plans=[plan], removed_paths=removed, warnings=plan.warnings)


def _plan_for_skill(skill: AgentSkill, *, project_root: Path, dry_run: bool) -> CleanupPlan:
    existing_managed = set(
        planned_managed_target_cleanup(
            project_root=project_root,
            installations=skill.native_installations,
        )
    )
    removable: list[str] = []
    managed = set(managed_native_target_paths(skill.native_installations))
    blocked: list[str] = []
    for installation in skill.native_installations:
        root = str(installation.get("path") or "")
        manifest = installation.get("manifest")
        if not root:
            continue
        if root in managed and root in existing_managed and isinstance(manifest, list) and manifest:
            removable.append(root)
        else:
            blocked.append(root)
    warnings = []
    if blocked:
        warnings.append("Some target paths lack managed manifests and were blocked.")
    return CleanupPlan(
        skill=skill.slug,
        mode="targets",
        dry_run=dry_run,
        removable_paths=sorted(set(removable)),
        blocked_paths=sorted(set(blocked)),
        warnings=warnings,
    )


def _resolve_skill(repository: AgentSkillRepository, selector: str) -> AgentSkill:
    normalized = selector.strip().casefold()
    matches: list[AgentSkill] = []
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


def _remove_paths(project_root: Path, paths: list[str]) -> list[str]:
    removed: list[str] = []
    for relative in paths:
        target = (project_root / relative).resolve()
        try:
            target.relative_to(project_root)
        except ValueError as exc:
            raise ValidationFailedError("Cleanup target resolves outside the project.") from exc
        if target.is_dir():
            shutil.rmtree(target)
            removed.append(relative)
        elif target.is_file():
            target.unlink()
            removed.append(relative)
    return removed
