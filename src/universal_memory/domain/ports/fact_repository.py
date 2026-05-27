from __future__ import annotations

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
    def list(self, scope: FactScope | None = None, status: FactStatus | None = None) -> list[Fact]:
        """List all facts matching the optional scope and status filters.

        Args:
            scope: Optional scope filter.
            status: Optional status filter.

        Returns:
            A list of matching Fact entities.
        """
        ...

    @abstractmethod
    def search(self, query: str, include_inactive: bool = False) -> list[Fact]:
        """Search facts by local text matching.

        Args:
            query: Text or regex query to match against fact content.
            include_inactive: Whether archived, stale, or purged facts are included.

        Returns:
            A list of matching Fact entities.
        """
        ...

    @abstractmethod
    def write(self, entity: Fact) -> object | None:
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

    def write_batch(self, entities: list[Fact]) -> object | None:
        """Write a batch of facts to the repository. Default implementation loops sequentially.

        Args:
            entities: The list of Fact entities to write.
        """
        last_res = None
        for entity in entities:
            last_res = self.write(entity)
        return last_res

    def purge_batch(self, ids: list[str]) -> None:
        """Permanently erase a batch of facts from physical storage.

        Default implementation loops sequentially.

        Args:
            ids: The list of unique identifiers of the facts to purge.
        """
        for id in ids:
            self.purge(id)
