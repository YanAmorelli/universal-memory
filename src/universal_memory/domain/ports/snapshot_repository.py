from abc import ABC, abstractmethod

from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus


class SnapshotRepository(ABC):
    @abstractmethod
    def read(self, id: str) -> Snapshot:
        """Read a snapshot by its ID.

        Args:
            id: The unique identifier of the snapshot.

        Returns:
            The Snapshot entity if found.

        Raises:
            UniversalMemoryError: If the snapshot is not found.
        """
        ...

    @abstractmethod
    def list(
        self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None
    ) -> list[Snapshot]:
        """List all snapshots matching the optional scope and status filters.

        Args:
            scope: Optional scope filter.
            status: Optional status filter.

        Returns:
            A list of matching Snapshot entities.
        """
        ...

    @abstractmethod
    def write(self, entity: Snapshot) -> None:
        """Write or update a snapshot in the repository.

        Args:
            entity: The Snapshot entity to write.
        """
        ...

    @abstractmethod
    def migrate(self, target_version: int) -> None:
        """Execute structural data migrations to the target schema version.

        Args:
            target_version: The schema version to migrate to.
        """
        ...
