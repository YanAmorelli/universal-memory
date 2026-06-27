from __future__ import annotations

from abc import ABC, abstractmethod

from universal_memory.domain.entities import AgentSkill, AgentSkillStatus, LatentSkillScope
from universal_memory.domain.entities.safe_write_result import SafeWriteResult


class AgentSkillRepository(ABC):
    @abstractmethod
    def read(self, id: str) -> AgentSkill:
        """Read a canonical Agent Skill by ID."""
        ...

    def read_by_slug(
        self,
        slug: str,
        *,
        scope: LatentSkillScope | None = None,
        status: AgentSkillStatus | None = None,
    ) -> AgentSkill:
        """Read an Agent Skill by slug."""
        for skill in self.list(scope=scope, status=status):
            if skill.slug == slug:
                return skill
        raise KeyError(slug)

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

    def replace(self, entity: AgentSkill, *, origin: str = "repository") -> SafeWriteResult | None:
        """Replace an existing Agent Skill registry record."""
        return self.write(entity, origin=origin)

    def remove(
        self,
        id: str,
        *,
        scope: LatentSkillScope,
        origin: str = "repository",
    ) -> SafeWriteResult | None:
        """Remove an Agent Skill registry record."""
        raise NotImplementedError
