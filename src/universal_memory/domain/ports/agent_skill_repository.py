from __future__ import annotations

from abc import ABC, abstractmethod

from universal_memory.domain.entities import AgentSkill, AgentSkillStatus, LatentSkillScope
from universal_memory.domain.entities.safe_write_result import SafeWriteResult


class AgentSkillRepository(ABC):
    @abstractmethod
    def read(self, id: str) -> AgentSkill:
        """Read a canonical Agent Skill by ID."""
        ...

    @abstractmethod
    def list(
        self, scope: LatentSkillScope | None = None, status: AgentSkillStatus | None = None
    ) -> list[AgentSkill]:
        """List canonical Agent Skills matching optional filters."""
        ...

    @abstractmethod
    def write(self, entity: AgentSkill, *, origin: str = "repository") -> SafeWriteResult | None:
        """Write or update a canonical Agent Skill registry record."""
        ...
