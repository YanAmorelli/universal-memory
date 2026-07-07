from pathlib import Path

from universal_memory.domain import ConfigValidationPort, ProjectLayoutPort, ProjectLayoutResult
from universal_memory.domain.project_layout import (
    ProjectLayoutInspection,
    ProjectLayoutPolicy,
    ResolvedProjectLayout,
)
from universal_memory.infrastructure.config.project_layout import (
    ensure_project_layout,
    inspect_project_layout,
    is_project_initialized,
    resolve_project_layout,
    write_project_layout_metadata,
)
from universal_memory.infrastructure.config.toml_loader import load_config


class LocalProjectLayoutPort(ProjectLayoutPort):
    def ensure_project_layout(self, project_root: Path) -> ProjectLayoutResult:
        return ensure_project_layout(project_root)

    def is_project_initialized(self, project_root: Path) -> bool:
        return is_project_initialized(project_root)

    def inspect_project_layout(self, project_root: Path) -> ProjectLayoutInspection:
        return inspect_project_layout(project_root)

    def resolve_project_layout(self, project_root: Path) -> ResolvedProjectLayout:
        return resolve_project_layout(project_root)

    def write_project_layout_metadata(
        self,
        project_root: Path,
        *,
        layout: str = "shared",
    ) -> ProjectLayoutPolicy:
        return write_project_layout_metadata(project_root, layout=layout)


class LocalConfigValidationPort(ConfigValidationPort):
    def validate_project_config(
        self, project_root: Path, global_config_path: Path | None = None
    ) -> None:
        load_config(project_root=project_root, global_config_path=global_config_path)
