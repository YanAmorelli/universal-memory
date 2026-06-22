from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from universal_memory import __version__
from universal_memory.domain.entities import (
    AgentSkillStatus,
    AuditEventScope,
    FactScope,
    FactStatus,
    LatentSkillStatus,
    RuleStatus,
)
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.domain.ports import (
    AgentSkillRepository,
    AuditLogRepository,
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
    host_validation: dict[str, dict[str, str | None]]
    recommended_action: str | None = None
    installed_version: str = __version__


class GetMemoryStatusUseCase:
    def __init__(  # noqa: PLR0913
        self,
        *,
        fact_repository: FactRepository,
        rule_repository: RuleRepository,
        latent_skill_repository: LatentSkillRepository,
        layout_port: ProjectLayoutPort,
        agent_skill_repository: AgentSkillRepository | None = None,
        audit_log_repository: AuditLogRepository | None = None,
        data_root: Path | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.fact_repository = fact_repository
        self.rule_repository = rule_repository
        self.latent_skill_repository = latent_skill_repository
        self.agent_skill_repository = agent_skill_repository
        self.layout_port = layout_port
        self.audit_log_repository = audit_log_repository
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
                recommended_action="Run 'umem init' from the project root directory.",
            )

        # Health check: verify read/write permissions.
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
        registered_skills_count = self._registered_skills_count()

        return GetMemoryStatusResult(
            initialized=True,
            project_path=project_path,
            fact_counts=fact_counts,
            active_rules_count=len(active_rules),
            registered_skills_count=registered_skills_count,
            approximate_size_bytes=_directory_size(data_root),
            last_health_check=format_utc_iso(self.clock()) if health_ok else None,
            host_validation=self._host_validation(),
            recommended_action=None,
        )

    def _registered_skills_count(self) -> int:
        if self.agent_skill_repository is not None:
            return len(self.agent_skill_repository.list(status=AgentSkillStatus.active))
        return len(self.latent_skill_repository.list(status=LatentSkillStatus.active))

    def _host_validation(self) -> dict[str, dict[str, str | None]]:
        unconfigured = {
            "claude_code": _unconfigured_host_validation(),
            "codex": _unconfigured_host_validation(),
        }
        if self.audit_log_repository is None:
            return unconfigured

        try:
            events = self.audit_log_repository.list(scope=AuditEventScope.project)
        except (OSError, KeyError, ValueError):
            return unconfigured

        latest = {host_id: val.copy() for host_id, val in unconfigured.items()}
        tracked_actions = {
            "host_validation.claude_code": "claude_code",
            "host_validation.codex": "codex",
        }
        for event in events:
            host_id = tracked_actions.get(event.action)
            if host_id is None:
                continue
            current = latest.get(host_id)
            if current and current.get("timestamp") is not None:
                current_timestamp = _parse_iso_utc(current["timestamp"])
                if current_timestamp is not None and current_timestamp > _normalize_datetime(
                    event.timestamp
                ):
                    continue
            latest[host_id] = {
                "status": event.result,
                "timestamp": format_utc_iso(_normalize_datetime(event.timestamp)),
                "method": _host_validation_method(event.details),
                "audit_reference": event.audit_reference,
            }
        return latest


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


def _unconfigured_host_validation() -> dict[str, str | None]:
    return {
        "status": "unconfigured",
        "timestamp": None,
        "method": None,
        "audit_reference": None,
    }


def _host_validation_method(details: str | None) -> str | None:
    if not details:
        return None
    try:
        payload = json.loads(details)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    method = payload.get("method")
    return method if isinstance(method, str) else None


def _parse_iso_utc(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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
