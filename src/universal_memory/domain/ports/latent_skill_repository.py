from __future__ import annotations

from abc import ABC, abstractmethod

from universal_memory.domain.entities import (
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    SafeWriteResult,
)


class LatentSkillRepository(ABC):
    @abstractmethod
    def read(self, id: str) -> LatentSkill:
        """Read a latent skill by its ID.

        Args:
            id: The unique identifier of the latent skill.

        Returns:
            The LatentSkill entity if found.

        Raises:
            UniversalMemoryError: If the latent skill is not found.
        """
        ...

    @abstractmethod
    def list(
        self, scope: LatentSkillScope | None = None, status: LatentSkillStatus | None = None
    ) -> list[LatentSkill]:
        """List all latent skills matching the optional scope and status filters.

        Args:
            scope: Optional scope filter.
            status: Optional status filter.

        Returns:
            A list of matching LatentSkill entities.
        """
        ...

    @abstractmethod
    def write(self, entity: LatentSkill) -> SafeWriteResult | None:
        """Write or update a latent skill in the repository.

        Args:
            entity: The LatentSkill entity to write.
        """
        ...

    @abstractmethod
    def delete(self, id: str) -> None:
        """Mark a latent skill as deleted.

        Args:
            id: The unique identifier of the latent skill to delete.
        """
        ...

    @abstractmethod
    def migrate(self, target_version: int) -> None:
        """Execute structural data migrations to the target schema version.

        Args:
            target_version: The schema version to migrate to.
        """
        ...
