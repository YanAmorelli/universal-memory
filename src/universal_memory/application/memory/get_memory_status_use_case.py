from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from universal_memory.domain.entities import (
    FactScope,
    FactStatus,
    LatentSkillStatus,
    RuleStatus,
)
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.domain.ports import (
    FactRepository,
    LatentSkillRepository,
    ProjectLayoutPort,
    RuleRepository,
)


@dataclass(frozen=True, slots=True)
class GetMemoryStatusCommand:
    project_root: Path


@dataclass(frozen=True, slots=True)
class GetMemoryStatusResult:
    initialized: bool
    project_path: str
    fact_counts: dict[str, dict[str, int]]
    active_rules_count: int
    registered_skills_count: int
    approximate_size_bytes: int
    last_health_check: str | None
    host_validation: dict[str, str]
    recommended_action: str | None = None


class GetMemoryStatusUseCase:
    def __init__(  # noqa: PLR0913
        self,
        *,
        fact_repository: FactRepository,
        rule_repository: RuleRepository,
        latent_skill_repository: LatentSkillRepository,
        layout_port: ProjectLayoutPort,
        data_root: Path | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.fact_repository = fact_repository
        self.rule_repository = rule_repository
        self.latent_skill_repository = latent_skill_repository
        self.layout_port = layout_port
        self.data_root = data_root
        self.clock = clock

    def execute(self, command: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        project_root = command.project_root.resolve()
        project_path = _relative_project_path(project_root)
        data_root = self.data_root or (project_root / ".umem")

        if not self.layout_port.is_project_initialized(project_root):
            return GetMemoryStatusResult(
                initialized=False,
                project_path=project_path,
                fact_counts={},
                active_rules_count=0,
                registered_skills_count=0,
                approximate_size_bytes=0,
                last_health_check=None,
                host_validation={},
                recommended_action="Execute 'umem init' a partir do diretorio raiz do projeto.",
            )

        # Diagnóstico de health check: verificar permissão de leitura/escrita
        health_ok = True
        try:
            if not data_root.exists() or not os.access(data_root, os.R_OK | os.W_OK):
                health_ok = False
        except OSError:
            health_ok = False

        facts = self.fact_repository.list()
        fact_counts = _empty_fact_counts()
        for fact in facts:
            fact_counts[fact.scope.value][fact.status.value] += 1

        active_rules = self.rule_repository.list(status=RuleStatus.active)
        active_skills = self.latent_skill_repository.list(status=LatentSkillStatus.active)

        return GetMemoryStatusResult(
            initialized=True,
            project_path=project_path,
            fact_counts=fact_counts,
            active_rules_count=len(active_rules),
            registered_skills_count=len(active_skills),
            approximate_size_bytes=_directory_size(data_root),
            last_health_check=format_utc_iso(self.clock()) if health_ok else None,
            host_validation={
                "claude": _host_status(project_root / "CLAUDE.md"),
                "gemini": _host_status(project_root / "AGENTS.md"),
            },
            recommended_action=None,
        )


def _empty_fact_counts() -> dict[str, dict[str, int]]:
    return {scope.value: {status.value: 0 for status in FactStatus} for scope in FactScope}


def _directory_size(root: Path) -> int:
    if not root.is_dir():
        return 0
    size = 0
    try:
        for path in root.rglob("*"):
            try:
                if path.is_file() and not path.is_symlink():
                    size += path.stat().st_size
            except OSError:
                pass
    except OSError:
        pass
    return size


def _host_status(path: Path) -> str:
    try:
        return "valid" if path.is_file() and path.stat().st_size > 0 else "unconfigured"
    except OSError:
        return "unconfigured"


def _relative_project_path(project_root: Path) -> str:
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        return "."
    if project_root == cwd:
        return "."
    try:
        rel = os.path.relpath(project_root, cwd)
        return rel if rel != "." else "."
    except (ValueError, OSError):
        return "."
