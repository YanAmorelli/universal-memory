from abc import ABC, abstractmethod

from universal_memory.domain.entities import Rule, RuleScope, RuleStatus


class RuleRepository(ABC):
    @abstractmethod
    def read(self, id: str) -> Rule:
        """Read a rule by its ID.

        Args:
            id: The unique identifier of the rule.

        Returns:
            The Rule entity if found.

        Raises:
            UniversalMemoryError: If the rule is not found.
        """
        ...

    @abstractmethod
    def list(self, scope: RuleScope | None = None, status: RuleStatus | None = None) -> list[Rule]:
        """List all rules matching the optional scope and status filters.

        Args:
            scope: Optional scope filter.
            status: Optional status filter.

        Returns:
            A list of matching Rule entities.
        """
        ...

    @abstractmethod
    def write(self, entity: Rule) -> None:
        """Write or update a rule in the repository.

        Args:
            entity: The Rule entity to write.
        """
        ...

    @abstractmethod
    def delete(self, id: str) -> None:
        """Mark a rule as deleted.

        Args:
            id: The unique identifier of the rule to delete.
        """
        ...

    @abstractmethod
    def migrate(self, target_version: int) -> None:
        """Execute structural data migrations to the target schema version.

        Args:
            target_version: The schema version to migrate to.
        """
        ...
