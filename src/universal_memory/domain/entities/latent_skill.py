from enum import StrEnum
from typing import Any

from pydantic import Field

from universal_memory.domain.entities.base import BaseEntity


class LatentSkillScope(StrEnum):
    global_ = "global"
    project = "project"


class LatentSkillStatus(StrEnum):
    proposed = "proposed"
    active = "active"
    ignored = "ignored"


class LatentSkill(BaseEntity):
    name: str
    description: str
    scope: LatentSkillScope
    status: LatentSkillStatus
    recurrence_count: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
