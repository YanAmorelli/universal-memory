from enum import StrEnum
from typing import Any

from pydantic import Field

from universal_memory.domain.entities.base import BaseEntity
from universal_memory.domain.entities.latent_skill import LatentSkillScope


class AgentSkillStatus(StrEnum):
    active = "active"
    disabled = "disabled"
    draft = "draft"


class AgentSkill(BaseEntity):
    name: str
    slug: str
    description: str
    scope: LatentSkillScope
    status: AgentSkillStatus
    canonical_path: str
    origin: str
    audit_reference: str
    content_hash: str
    native_installations: list[dict[str, Any]] = Field(default_factory=list)
    source_recommendation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def draft_path(self) -> str | None:
        value = self.metadata.get("draft_path")
        return str(value) if value else None

    @property
    def validation(self) -> dict[str, Any] | None:
        value = self.metadata.get("validation")
        return value if isinstance(value, dict) else None
