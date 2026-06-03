from abc import ABC, abstractmethod
from pathlib import Path


class ConfigValidationPort(ABC):
    @abstractmethod
    def validate_project_config(
        self, project_root: Path, global_config_path: Path | None = None
    ) -> None:
        """Validate and load the effective project configuration."""
        ...
