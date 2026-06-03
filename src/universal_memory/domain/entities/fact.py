from enum import StrEnum
from typing import Any

from pydantic import Field

from universal_memory.domain.entities.base import BaseEntity


class FactScope(StrEnum):
    global_ = "global"
    project = "project"


class FactStatus(StrEnum):
    active = "active"
    stale = "stale"
    archived = "archived"
    purged = "purged"


class Fact(BaseEntity):
    content: str
    scope: FactScope
    source: str
    status: FactStatus
    recurrence_count: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
