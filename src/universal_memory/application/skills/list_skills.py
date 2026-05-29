from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.domain.ports import LatentSkillRepository

RECOMMENDED_SKILL_ACTION = (
    "Latent skills aparecem quando o universal-memory registra padroes recorrentes. "
    "Continue usando `umem remember \"...\"` para registrar memoria; quando uma "
    "candidata aparecer, rode `umem skills list` novamente para acompanhar as skills."
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

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "scope": self.scope,
            "status": self.status,
            "relative_path": self.relative_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "origin": self.origin,
            "audit_reference": self.audit_reference,
        }


@dataclass(frozen=True, slots=True)
class ListSkillsResult:
    skills: list[SkillListItem]
    recommended_action: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"skills": [skill.to_payload() for skill in self.skills]}
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

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "scope": self.scope,
            "status": self.status,
            "relative_path": self.relative_path,
            "triggers": self.triggers,
            "audit_reference": self.audit_reference,
            "references_loaded": self.references_loaded,
        }


class ListSkillsUseCase:
    def __init__(self, *, project_root: Path, repository: LatentSkillRepository) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository

    def execute(self, command: ListSkillsCommand) -> ListSkillsResult:
        skills = self.repository.list(scope=command.scope, status=command.status)
        items = [self._item_for(skill) for skill in skills]
        items.sort(key=lambda item: item.created_at)
        if not items:
            return ListSkillsResult(skills=[], recommended_action=RECOMMENDED_SKILL_ACTION)
        return ListSkillsResult(skills=items)

    def _item_for(self, skill: LatentSkill) -> SkillListItem:
        return SkillListItem(
            name=skill.name,
            scope=skill.scope.value,
            status=_status_label(skill.status),
            relative_path=_relative_skill_file(self.project_root, skill),
            created_at=format_utc_iso(skill.created_at),
            updated_at=format_utc_iso(skill.updated_at),
            origin=_metadata_string(skill, "origin", default="unknown"),
            audit_reference=_metadata_string(skill, "audit_reference", default="UNAUDITED"),
        )


class GetSkillDetailUseCase:
    def __init__(self, *, project_root: Path, repository: LatentSkillRepository) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository

    def execute(self, command: GetSkillDetailCommand) -> GetSkillDetailResult:
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
        raise ValidationFailedError(f"Skill '{name_or_id}' nao encontrada.")

    def _triggers_for(self, skill: LatentSkill, relative_path: str | None) -> list[str]:
        if relative_path is not None:
            triggers = _read_frontmatter_triggers(self.project_root / relative_path)
            if triggers:
                return triggers
        raw_triggers = (skill.metadata or {}).get("triggers") or (skill.metadata or {}).get("tags")
        return _as_clean_list(raw_triggers) or [skill.name]


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
