from abc import ABC, abstractmethod

from universal_memory.domain.entities import Fact, FactScope, FactStatus


class FactRepository(ABC):
    @abstractmethod
    def read(self, id: str) -> Fact:
        """Read a fact by its ID.

        Args:
            id: The unique identifier of the fact.

        Returns:
            The Fact entity if found.

        Raises:
            FactNotFoundError: If no fact with the given ID exists.
        """
        ...

    @abstractmethod
    def list(
        self, scope: FactScope | None = None, status: FactStatus | None = None
    ) -> list[Fact]:
        """List all facts matching the optional scope and status filters.

        Args:
            scope: Optional scope filter.
            status: Optional status filter.

        Returns:
            A list of matching Fact entities.
        """
        ...

    @abstractmethod
    def write(self, entity: Fact) -> None:
        """Write or update a fact in the repository.

        Args:
            entity: The Fact entity to write.
        """
        ...

    @abstractmethod
    def delete(self, id: str) -> None:
        """Mark a fact as deleted (logical/soft delete).

        Args:
            id: The unique identifier of the fact to delete.
        """
        ...

    @abstractmethod
    def purge(self, id: str) -> None:
        """Permanently erase a fact from physical storage (hard delete/purge).

        Args:
            id: The unique identifier of the fact to purge.
        """
        ...

    @abstractmethod
    def migrate(self, target_version: int) -> None:
        """Execute structural data migrations to the target schema version.

        Args:
            target_version: The schema version to migrate to.
        """
        ...
