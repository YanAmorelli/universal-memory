from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from universal_memory.domain.ports import ProjectLayoutPort


class InspectProjectLayoutUseCase:
    def __init__(self, *, project_root: Path, layout_port: ProjectLayoutPort) -> None:
        self.project_root = project_root
        self.layout_port = layout_port

    def execute(self) -> dict[str, Any]:
        report = self.layout_port.inspect_project_layout(self.project_root)
        return {
            "operation": report.operation,
            "scope": "project",
            "data": asdict(report),
        }
