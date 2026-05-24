from pathlib import Path

from universal_memory.domain import ConfigValidationPort, ProjectLayoutPort, ProjectLayoutResult
from universal_memory.infrastructure.config.project_layout import ensure_project_layout
from universal_memory.infrastructure.config.toml_loader import load_config


class LocalProjectLayoutPort(ProjectLayoutPort):
    def ensure_project_layout(self, project_root: Path) -> ProjectLayoutResult:
        return ensure_project_layout(project_root)


class LocalConfigValidationPort(ConfigValidationPort):
    def validate_project_config(
        self, project_root: Path, global_config_path: Path | None = None
    ) -> None:
        load_config(project_root=project_root, global_config_path=global_config_path)
