from enum import StrEnum
from typing import Any

from pydantic import Field

from universal_memory.domain.entities.base import BaseEntity


class RuleScope(StrEnum):
    global_ = "global"
    project = "project"


class RuleStatus(StrEnum):
    active = "active"
    inactive = "inactive"


class Rule(BaseEntity):
    name: str
    content: str
    scope: RuleScope
    status: RuleStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
