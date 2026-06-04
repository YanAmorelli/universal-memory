from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from universal_memory.application.host import ConfigureHostCommand, ConfigureHostResult
from universal_memory.infrastructure.config.project_layout import (
    DIRECTORY_LAYOUT_PATHS,
    PROJECT_LAYOUT_PATHS,
)
from universal_memory.infrastructure.config.toml_loader import load_config

CheckStatus = str
HostCheckCommand = Callable[[ConfigureHostCommand], ConfigureHostResult]
WhichResolver = Callable[[str], str | None]
CONFIG_LOAD_ERROR_PREFIX = "__config_load_error__:"


@dataclass(frozen=True, slots=True)
class DoctorCommand:
    project_root: Path


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    status: CheckStatus
    detail: str | None = None
    error: str | None = None
    recovery_hint: str | None = None

    def to_payload(self) -> dict[str, str]:
        payload = {"name": self.name, "status": self.status}
        if self.detail is not None:
            payload["detail"] = self.detail
        if self.error is not None:
            payload["error"] = self.error
        if self.recovery_hint is not None:
            payload["recovery_hint"] = self.recovery_hint
        return payload


@dataclass(frozen=True, slots=True)
class DoctorSummary:
    total_checks: int
    passed: int
    failed: int

    def to_payload(self) -> dict[str, int]:
        return {
            "total_checks": self.total_checks,
            "passed": self.passed,
            "failed": self.failed,
        }


@dataclass(frozen=True, slots=True)
class DoctorResult:
    checks: list[DoctorCheck]

    @property
    def ok(self) -> bool:
        return all(check.status == "success" for check in self.checks)

    @property
    def summary(self) -> DoctorSummary:
        passed = sum(1 for check in self.checks if check.status == "success")
        failed = len(self.checks) - passed
        return DoctorSummary(total_checks=len(self.checks), passed=passed, failed=failed)

    def to_payload(self) -> dict[str, object]:
        return {
            "checks": [check.to_payload() for check in self.checks],
            "summary": self.summary.to_payload(),
        }


class DoctorUseCase:
    def __init__(  # noqa: PLR0913
        self,
        *,
        host_check_command: HostCheckCommand | None = None,
        which: WhichResolver = shutil.which,
        version_info: tuple[int, int, int] | None = None,
        home: Path | None = None,
        xdg_data_home: Path | None = None,
        xdg_config_home: Path | None = None,
    ) -> None:
        self.host_check_command = host_check_command
        self.which = which
        self.version_info = version_info or (
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        )
        self.home = home or Path.home()
        self.xdg_data_home = xdg_data_home
        self.xdg_config_home = xdg_config_home

    def execute(self, command: DoctorCommand) -> DoctorResult:
        project_root = command.project_root.resolve()
        checks = [
            self._python_version_check(),
            self._path_permissions_check(project_root),
            self._project_layout_check(project_root),
            self._path_executables_check(),
            self._hosts_integration_check(project_root),
        ]
        return DoctorResult(checks=checks)

    def _python_version_check(self) -> DoctorCheck:
        major, minor, micro = self.version_info
        detail = f"Python {major}.{minor}.{micro}"
        if (major, minor) >= (3, 12):
            return DoctorCheck(name="python_version", status="success", detail=detail)
        return DoctorCheck(
            name="python_version",
            status="failed",
            detail=detail,
            error="Python 3.12 or higher is required.",
            recovery_hint="Configure a virtual environment with Python 3.12 or higher.",
        )

    def _path_permissions_check(self, project_root: Path) -> DoctorCheck:
        paths = [
            (self._global_data_root(), "directory"),
            (self._global_config_path(), "file"),
        ]
        if (project_root / ".umem").exists():
            paths.append((project_root / ".umem", "directory"))
        else:
            paths.append((project_root, "directory"))

        failures: list[str] = []
        for path, expected_kind in paths:
            failure = self._permission_failure(path, expected_kind, project_root)
            if failure is not None:
                failures.append(failure)

        if not failures:
            return DoctorCheck(
                name="filesystem_permissions",
                status="success",
                detail="Canonical local and global paths are writable.",
            )
        return DoctorCheck(
            name="filesystem_permissions",
            status="failed",
            error="; ".join(failures),
            recovery_hint="Fix filesystem permissions with chmod -R u+rw <path>.",
        )

    def _project_layout_check(self, project_root: Path) -> DoctorCheck:
        umem_root = project_root / ".umem"
        if not umem_root.exists():
            return DoctorCheck(
                name="project_layout",
                status="failed",
                error="Missing project layout: .umem",
                recovery_hint="Run umem init --yes to create the project layout.",
            )
        if not umem_root.is_dir():
            return DoctorCheck(
                name="project_layout",
                status="failed",
                error="Project layout root .umem is not a directory.",
                recovery_hint="Move the conflicting .umem file and run umem init --yes.",
            )

        failures: list[str] = []
        for relative_path in PROJECT_LAYOUT_PATHS:
            target = project_root / relative_path
            expected = "directory" if relative_path in DIRECTORY_LAYOUT_PATHS else "file"
            if not target.exists():
                failures.append(f"Missing path: {relative_path}")
            elif expected == "directory" and not target.is_dir():
                failures.append(f"Wrong path kind: {relative_path} must be a directory")
            elif expected == "file" and not target.is_file():
                failures.append(f"Wrong path kind: {relative_path} must be a file")

        if not failures:
            return DoctorCheck(
                name="project_layout",
                status="success",
                detail="Project layout is complete.",
            )
        return DoctorCheck(
            name="project_layout",
            status="failed",
            error="; ".join(failures),
            recovery_hint="Run umem init --yes to rebuild missing default paths.",
        )

    def _path_executables_check(self) -> DoctorCheck:
        required = ["umem", "umem-mcp"]
        missing = [name for name in required if self.which(name) is None]
        if not missing:
            return DoctorCheck(
                name="path_executables",
                status="success",
                detail="umem and umem-mcp are available on PATH.",
            )
        return DoctorCheck(
            name="path_executables",
            status="failed",
            error=f"Missing executables on PATH: {', '.join(missing)}",
            recovery_hint="Activate the virtual environment or install with uv sync.",
        )

    def _hosts_integration_check(self, project_root: Path) -> DoctorCheck:
        host_ids = self._configured_host_ids(project_root)
        config_errors = [
            host_id.removeprefix(CONFIG_LOAD_ERROR_PREFIX)
            for host_id in host_ids
            if host_id.startswith(CONFIG_LOAD_ERROR_PREFIX)
        ]
        if config_errors:
            return DoctorCheck(
                name="hosts_integration",
                status="failed",
                error="; ".join(config_errors),
                recovery_hint="Fix .umem/config.toml and re-run umem doctor.",
            )
        if self.host_check_command is None:
            return DoctorCheck(
                name="hosts_integration",
                status="success",
                detail="Host integration check is not configured.",
            )
        if not host_ids:
            return DoctorCheck(
                name="hosts_integration",
                status="success",
                detail="No hosts configured.",
            )

        failures: list[str] = []
        for host_id in host_ids:
            try:
                result = self.host_check_command(
                    ConfigureHostCommand(
                        host_id=host_id,
                        apply=False,
                        check=True,
                        record_audit=False,
                    )
                )
            except Exception as error:
                failures.append(f"{host_id}: {error}")
                continue
            if result.validation_status != "success":
                detail = ", ".join(result.warnings or result.manual_steps)
                suffix = f" ({detail})" if detail else ""
                failures.append(f"{host_id}: {result.validation_status}{suffix}")

        if not failures:
            return DoctorCheck(
                name="hosts_integration",
                status="success",
                detail=f"Validated hosts: {', '.join(host_ids)}.",
            )
        return DoctorCheck(
            name="hosts_integration",
            status="failed",
            error="; ".join(failures),
            recovery_hint="Run umem host setup <host_id> --yes to repair host instructions.",
        )

    def _configured_host_ids(self, project_root: Path) -> list[str]:
        try:
            loaded = load_config(project_root)
        except Exception as error:
            return [f"{CONFIG_LOAD_ERROR_PREFIX}{error}"]

        host_ids: list[str] = []
        for section_name in ("runtimes", "hosts"):
            section = loaded.merged.get(section_name)
            if not isinstance(section, dict):
                continue
            enabled = section.get("enabled")
            if isinstance(enabled, list):
                host_ids.extend(str(item) for item in enabled)
            for key, value in section.items():
                if isinstance(value, dict) and value.get("enabled") is True:
                    host_ids.append(str(key))

        supported = {"codex", "claude_code"}
        deduped: list[str] = []
        for host_id in host_ids:
            if host_id in supported and host_id not in deduped:
                deduped.append(host_id)
        return deduped

    def _global_data_root(self) -> Path:
        configured = self.xdg_data_home or _env_path("XDG_DATA_HOME")
        return (configured if configured is not None else self.home / ".local" / "share") / "umem"

    def _global_config_path(self) -> Path:
        configured = self.xdg_config_home or _env_path("XDG_CONFIG_HOME")
        root = configured if configured is not None else self.home / ".config"
        return root / "umem" / "config.toml"

    @staticmethod
    def _relative_or_user_path(path: Path, project_root: Path) -> str:
        try:
            return path.resolve().relative_to(project_root.resolve()).as_posix()
        except ValueError:
            return path.expanduser().as_posix()

    def _permission_failure(
        self,
        path: Path,
        expected_kind: str,
        project_root: Path,
    ) -> str | None:
        display_path = self._relative_or_user_path(path, project_root)
        if path.exists():
            if expected_kind == "directory":
                if not path.is_dir():
                    return f"{display_path}: path must be a directory"
                if os.access(path, os.R_OK | os.W_OK | os.X_OK):
                    return None
                return f"{display_path}: directory is not readable, writable, and searchable"
            if not path.is_file():
                return f"{display_path}: path must be a file"
            if expected_kind == "file":
                if os.access(path, os.R_OK | os.W_OK):
                    return None
                return f"{display_path}: file is not readable and writable"

        parent = path.parent
        if parent.exists() and parent.is_dir() and os.access(parent, os.R_OK | os.W_OK | os.X_OK):
            return None
        if not parent.exists():
            return f"{display_path}: parent directory is missing"
        return f"{display_path}: parent directory is not readable, writable, and searchable"


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value)
