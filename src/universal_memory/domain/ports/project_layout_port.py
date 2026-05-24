from abc import ABC, abstractmethod
from pathlib import Path

from universal_memory.domain.project_layout import ProjectLayoutResult


class ProjectLayoutPort(ABC):
    @abstractmethod
    def ensure_project_layout(self, project_root: Path) -> ProjectLayoutResult:
        """Materialize or validate the canonical `.umem/` layout."""
        ...
