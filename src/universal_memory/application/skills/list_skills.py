from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from universal_memory.application.skills.recommend_skills import (
    RecommendSkillsCommand,
    RecommendSkillsUseCase,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
)
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.domain.ports import AgentSkillRepository, LatentSkillRepository

RECOMMENDED_SKILL_ACTION = (
    "Latent skills appear when universal-memory records recurring evidence. "
    "Use `umem skills track --name ... --description ... --evidence-summary ...` "
    "to capture explicit evidence; then run `umem skills recommend`."
)
FRONTMATTER_SPLIT_PARTS = 2


@dataclass(frozen=True, slots=True)
class ListSkillsCommand:
    scope: LatentSkillScope | None = None
    status: LatentSkillStatus | None = None


@dataclass(frozen=True, slots=True)
class SkillListItem:
    name: str
    scope: str
    status: str
    relative_path: str | None
    created_at: str
    updated_at: str
    origin: str
    audit_reference: str
    id: str | None = None
    canonical_path: str | None = None
    targets: list[dict[str, Any]] | None = None
    source_recommendation_id: str | None = None
    recommended_action: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "scope": self.scope,
            "status": self.status,
            "relative_path": self.relative_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "origin": self.origin,
            "audit_reference": self.audit_reference,
        }
        if self.id is not None:
            payload["id"] = self.id
        if self.canonical_path is not None:
            payload["canonical_path"] = self.canonical_path
        if self.targets is not None:
            payload["targets"] = self.targets
        if self.source_recommendation_id is not None:
            payload["source_recommendation_id"] = self.source_recommendation_id
        if self.recommended_action is not None:
            payload["recommended_action"] = self.recommended_action
        return payload


@dataclass(frozen=True, slots=True)
class ListSkillsResult:
    skills: list[SkillListItem]
    recommendations: list[SkillListItem] | None = None
    recommended_action: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"skills": [skill.to_payload() for skill in self.skills]}
        if self.recommendations is not None:
            payload["recommendations"] = [item.to_payload() for item in self.recommendations]
        if self.recommended_action is not None:
            payload["recommended_action"] = self.recommended_action
        return payload


@dataclass(frozen=True, slots=True)
class GetSkillDetailCommand:
    name_or_id: str


@dataclass(frozen=True, slots=True)
class GetSkillDetailResult:
    name: str
    scope: str
    status: str
    relative_path: str | None
    triggers: list[str]
    audit_reference: str
    references_loaded: bool = False
    id: str | None = None
    canonical_path: str | None = None
    targets: list[dict[str, Any]] | None = None
    origin: str | None = None
    content_hash: str | None = None
    source_recommendation_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "scope": self.scope,
            "status": self.status,
            "relative_path": self.relative_path,
            "triggers": self.triggers,
            "audit_reference": self.audit_reference,
            "references_loaded": self.references_loaded,
        }
        if self.id is not None:
            payload["id"] = self.id
        if self.canonical_path is not None:
            payload["canonical_path"] = self.canonical_path
        if self.targets is not None:
            payload["targets"] = self.targets
        if self.origin is not None:
            payload["origin"] = self.origin
        if self.content_hash is not None:
            payload["content_hash"] = self.content_hash
        if self.source_recommendation_id is not None:
            payload["source_recommendation_id"] = self.source_recommendation_id
        return payload


class ListSkillsUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        repository: LatentSkillRepository,
        agent_skill_repository: AgentSkillRepository | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository
        self.agent_skill_repository = agent_skill_repository

    def execute(self, command: ListSkillsCommand) -> ListSkillsResult:
        if self.agent_skill_repository is not None:
            agent_status = _agent_status_filter(command.status)
            if command.status is not None and agent_status is None:
                canonical = []
            else:
                canonical = self.agent_skill_repository.list(
                    scope=command.scope,
                    status=agent_status,
                )
            skills = [self._canonical_item_for(skill) for skill in canonical]
            skills.sort(key=lambda item: item.created_at)
            recommendations = self._recommendation_items_for(command)
            recommendations.sort(key=lambda item: item.created_at)
            if not skills and not recommendations:
                return ListSkillsResult(
                    skills=[], recommendations=[], recommended_action=RECOMMENDED_SKILL_ACTION
                )
            return ListSkillsResult(skills=skills, recommendations=recommendations)

        skills = self.repository.list(scope=command.scope, status=command.status)
        items = [self._item_for(skill) for skill in skills]
        items.sort(key=lambda item: item.created_at)
        if not items:
            return ListSkillsResult(skills=[], recommended_action=RECOMMENDED_SKILL_ACTION)
        return ListSkillsResult(skills=items)

    def _canonical_item_for(self, skill: AgentSkill) -> SkillListItem:
        return SkillListItem(
            id=skill.id,
            name=skill.name,
            scope=skill.scope.value,
            status=skill.status.value,
            relative_path=skill.canonical_path,
            canonical_path=skill.canonical_path,
            created_at=format_utc_iso(skill.created_at),
            updated_at=format_utc_iso(skill.updated_at),
            origin=skill.origin,
            audit_reference=skill.audit_reference,
            targets=_targets_for(skill.native_installations),
            source_recommendation_id=skill.source_recommendation_id,
        )

    def _recommendation_items_for(self, command: ListSkillsCommand) -> list[SkillListItem]:
        if command.status is not None and command.status != LatentSkillStatus.proposed:
            return []
        result = RecommendSkillsUseCase(repository=self.repository).execute(
            RecommendSkillsCommand(scope=command.scope)
        )
        proposed_by_id = {
            skill.id: skill
            for skill in self.repository.list(
                scope=command.scope, status=LatentSkillStatus.proposed
            )
            if not _is_promoted_recommendation(skill)
        }
        return [
            self._item_for(
                proposed_by_id[recommendation.id],
                recommended_action=recommendation.recommended_action,
            )
            for recommendation in result.recommendations
            if recommendation.id in proposed_by_id
        ]

    def _item_for(
        self,
        skill: LatentSkill,
        *,
        recommended_action: str | None = None,
    ) -> SkillListItem:
        is_candidate = skill.status == LatentSkillStatus.proposed
        return SkillListItem(
            id=skill.id if is_candidate else None,
            name=skill.name,
            scope=skill.scope.value,
            status=_status_label(skill.status),
            relative_path=_relative_skill_file(self.project_root, skill),
            created_at=format_utc_iso(skill.created_at),
            updated_at=format_utc_iso(skill.updated_at),
            origin=_metadata_string(skill, "origin", default="unknown"),
            audit_reference=_metadata_string(skill, "audit_reference", default="UNAUDITED"),
            recommended_action=recommended_action
            or (f"umem skills promote {skill.id}" if is_candidate else None),
        )


class GetSkillDetailUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        repository: LatentSkillRepository,
        agent_skill_repository: AgentSkillRepository | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository
        self.agent_skill_repository = agent_skill_repository

    def execute(self, command: GetSkillDetailCommand) -> GetSkillDetailResult:
        if self.agent_skill_repository is not None:
            canonical = self._find_agent_skill(command.name_or_id)
            if canonical is not None:
                return GetSkillDetailResult(
                    id=canonical.id,
                    name=canonical.name,
                    scope=canonical.scope.value,
                    status=canonical.status.value,
                    relative_path=canonical.canonical_path,
                    canonical_path=canonical.canonical_path,
                    triggers=self._canonical_triggers_for(canonical),
                    audit_reference=canonical.audit_reference,
                    references_loaded=False,
                    targets=_targets_for(canonical.native_installations),
                    origin=canonical.origin,
                    content_hash=canonical.content_hash,
                    source_recommendation_id=canonical.source_recommendation_id,
                )
        skill = self._find_skill(command.name_or_id)
        relative_path = _relative_skill_file(self.project_root, skill)
        return GetSkillDetailResult(
            name=skill.name,
            scope=skill.scope.value,
            status=_status_label(skill.status),
            relative_path=relative_path,
            triggers=self._triggers_for(skill, relative_path),
            audit_reference=_metadata_string(skill, "audit_reference", default="UNAUDITED"),
            references_loaded=False,
        )

    def _find_skill(self, name_or_id: str) -> LatentSkill:
        needle = name_or_id.strip()
        if not needle:
            raise ValidationFailedError("Informe o nome ou ID da skill.")
        name_matches: list[LatentSkill] = []
        for skill in self.repository.list():
            if skill.id == needle:
                return skill
            if skill.name.casefold() == needle.casefold():
                name_matches.append(skill)
        if len(name_matches) == 1:
            return name_matches[0]
        if len(name_matches) > 1:
            raise ValidationFailedError(
                f"Mais de uma skill corresponde a '{name_or_id}'. Informe o ID da skill."
            )
        raise ValidationFailedError(f"Skill '{name_or_id}' not found.")

    def _find_agent_skill(self, name_or_id: str) -> AgentSkill | None:
        needle = name_or_id.strip()
        if not needle:
            raise ValidationFailedError("Informe o nome ou ID da skill.")
        name_matches: list[AgentSkill] = []
        for skill in self.agent_skill_repository.list() if self.agent_skill_repository else []:
            if needle in (skill.id, skill.slug):
                return skill
            if skill.name.casefold() == needle.casefold():
                name_matches.append(skill)
        if len(name_matches) == 1:
            return name_matches[0]
        if len(name_matches) > 1:
            raise ValidationFailedError(
                f"Mais de uma skill corresponde a '{name_or_id}'. Informe o ID da skill."
            )
        return None

    def _triggers_for(self, skill: LatentSkill, relative_path: str | None) -> list[str]:
        if relative_path is not None:
            triggers = _read_frontmatter_triggers(self.project_root / relative_path)
            if triggers:
                return triggers
        raw_triggers = (skill.metadata or {}).get("triggers") or (skill.metadata or {}).get("tags")
        return _as_clean_list(raw_triggers) or [skill.name]

    def _canonical_triggers_for(self, skill: AgentSkill) -> list[str]:
        triggers = _read_frontmatter_triggers(self.project_root / skill.canonical_path)
        if triggers:
            return triggers
        return _as_clean_list(skill.metadata.get("triggers")) or [skill.name]


def _agent_status_filter(status: LatentSkillStatus | None) -> AgentSkillStatus | None:
    if status is None:
        return None
    if status == LatentSkillStatus.active:
        return AgentSkillStatus.active
    if status == LatentSkillStatus.ignored:
        return AgentSkillStatus.disabled
    return None


def _targets_for(installations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets = []
    for installation in installations:
        targets.append(
            {
                "runtime": installation.get("runtime"),
                "path": installation.get("path"),
                "status": "synced",
                "drift_detected": bool(installation.get("drift_detected", False)),
            }
        )
    return targets


def _is_promoted_recommendation(skill: LatentSkill) -> bool:
    promotion = (skill.metadata or {}).get("promotion")
    return isinstance(promotion, dict) and bool(promotion.get("promoted_skill_id"))


def _status_label(status: LatentSkillStatus) -> str:
    if status == LatentSkillStatus.proposed:
        return "candidate"
    if status == LatentSkillStatus.ignored:
        return "disabled"
    return status.value


def _relative_skill_file(project_root: Path, skill: LatentSkill) -> str | None:
    if skill.status == LatentSkillStatus.proposed:
        return None
    return _resolve_materialized_skill_file(project_root, skill)


def _metadata_string(skill: LatentSkill, key: str, *, default: str) -> str:
    value = (skill.metadata or {}).get(key)
    if value is None:
        return default
    return str(value)


def _read_frontmatter_triggers(skill_file: Path) -> list[str]:
    try:
        content = skill_file.read_text(encoding="utf-8-sig")
    except OSError:
        return []
    content = content.replace("\r\n", "\n")
    frontmatter = _frontmatter_block(content)
    if frontmatter is None:
        return []

    triggers: list[str] = []
    in_triggers = False
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith("triggers:"):
            inline_value = stripped.removeprefix("triggers:").strip()
            if inline_value:
                return _parse_inline_triggers(inline_value)
            in_triggers = True
            continue
        if in_triggers:
            item = _parse_frontmatter_list_item(line)
            if item is not None:
                triggers.append(item)
                continue
            if stripped and not line[:1].isspace():
                break
    return [trigger for trigger in triggers if trigger]


def _resolve_materialized_skill_file(project_root: Path, skill: LatentSkill) -> str | None:
    scope_dir = _skill_scope_dir(skill.scope)
    expected_relative_path = f"{scope_dir}/{_slug(skill.name)}/SKILL.md"
    expected_file = project_root / expected_relative_path
    if expected_file.is_file():
        return expected_relative_path

    base_dir = project_root / scope_dir
    if not base_dir.is_dir():
        return None

    for skill_file in sorted(base_dir.glob("*/SKILL.md")):
        if _read_frontmatter_name(skill_file).casefold() == skill.name.casefold():
            return skill_file.relative_to(project_root).as_posix()
    return None


def _skill_scope_dir(scope: LatentSkillScope) -> str:
    return "skills" if scope == LatentSkillScope.global_ else ".umem/skills"


def _frontmatter_block(content: str) -> str | None:
    if not content.startswith("---\n"):
        return None
    parts = content.split("\n---\n", 1)
    if len(parts) != FRONTMATTER_SPLIT_PARTS:
        return None
    return parts[0].removeprefix("---\n")


def _read_frontmatter_name(skill_file: Path) -> str:
    try:
        content = skill_file.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    except OSError:
        return ""
    frontmatter = _frontmatter_block(content)
    if frontmatter is None:
        return ""
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith("name:"):
            return _decode_frontmatter_scalar(stripped.removeprefix("name:").strip())
    return ""


def _parse_frontmatter_list_item(line: str) -> str | None:
    stripped = line.lstrip()
    if not stripped.startswith("- "):
        return None
    value = stripped.removeprefix("- ").strip()
    return _decode_frontmatter_scalar(value)


def _parse_inline_triggers(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                return []
            return [
                _decode_frontmatter_scalar(part.strip())
                for part in inner.split(",")
                if part.strip()
            ]
        return [_decode_frontmatter_scalar(value)]
    return _as_clean_list(parsed)


def _decode_frontmatter_scalar(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
        return str(parsed).strip()
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'").strip()
    return value.strip()


def _as_clean_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, tuple | set):
        raw_items = list(value)
    else:
        raw_items = [value]
    return [str(item).strip() for item in raw_items if str(item).strip()]


def _slug(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return slug or "skill"
