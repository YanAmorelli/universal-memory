from abc import ABC, abstractmethod

from universal_memory.domain.entities import ContextSummary, ContextSummaryScope


class ContextSummaryRepository(ABC):
    @abstractmethod
    def read(self, id: str) -> ContextSummary:
        """Read a context summary by its ID.

        Args:
            id: The unique identifier of the context summary.

        Returns:
            The ContextSummary entity if found.

        Raises:
            UniversalMemoryError: If the context summary is not found.
        """
        ...

    @abstractmethod
    def list(self, scope: ContextSummaryScope | None = None) -> list[ContextSummary]:
        """List all context summaries matching the optional scope filter.

        Args:
            scope: Optional scope filter.

        Returns:
            A list of matching ContextSummary entities.
        """
        ...

    @abstractmethod
    def write(self, entity: ContextSummary) -> None:
        """Write or update a context summary in the repository.

        Args:
            entity: The ContextSummary entity to write.
        """
        ...

    @abstractmethod
    def migrate(self, target_version: int) -> None:
        """Execute structural data migrations to the target schema version.

        Args:
            target_version: The schema version to migrate to.
        """
        ...
