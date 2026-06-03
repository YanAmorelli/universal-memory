from abc import ABC, abstractmethod

from universal_memory.domain.entities import AuditEvent, AuditEventScope


class AuditLogRepository(ABC):
    @abstractmethod
    def read(self, id: str) -> AuditEvent:
        """Read an audit event by its ID.

        Args:
            id: The unique identifier of the audit event.

        Returns:
            The AuditEvent entity if found.

        Raises:
            UniversalMemoryError: If the audit event is not found.
        """
        ...

    @abstractmethod
    def list(self, scope: AuditEventScope | None = None) -> list[AuditEvent]:
        """List all audit events matching the optional scope filter.

        Args:
            scope: Optional scope filter.

        Returns:
            A list of matching AuditEvent entities.
        """
        ...

    @abstractmethod
    def write(self, entity: AuditEvent) -> None:
        """Write or update an audit event in the repository.

        Args:
            entity: The AuditEvent entity to write.
        """
        ...

    @abstractmethod
    def migrate(self, target_version: int) -> None:
        """Execute structural data migrations to the target schema version.

        Args:
            target_version: The schema version to migrate to.
        """
        ...
