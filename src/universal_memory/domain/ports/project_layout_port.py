from abc import ABC, abstractmethod
from pathlib import Path

from universal_memory.domain.project_layout import (
    ProjectLayoutInspection,
    ProjectLayoutPolicy,
    ProjectLayoutResult,
    ResolvedProjectLayout,
)


class ProjectLayoutPort(ABC):
    @abstractmethod
    def ensure_project_layout(self, project_root: Path) -> ProjectLayoutResult:
        """Materialize or validate the canonical `.umem/` layout."""
        ...

    @abstractmethod
    def is_project_initialized(self, project_root: Path) -> bool:
        """Return whether the canonical `.umem/` layout already exists."""
        ...

    @abstractmethod
    def inspect_project_layout(self, project_root: Path) -> ProjectLayoutInspection:
        """Return the active layout mode and non-mutating guidance."""
        ...

    @abstractmethod
    def resolve_project_layout(self, project_root: Path) -> ResolvedProjectLayout:
        """Resolve effective shared and operational storage paths."""
        ...

    @abstractmethod
    def write_project_layout_metadata(
        self,
        project_root: Path,
        *,
        layout: str = "shared",
    ) -> ProjectLayoutPolicy:
        """Write `umem/project.toml` metadata for the selected layout."""
        ...
