from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from importlib import resources
from pathlib import Path, PurePosixPath
from uuid import uuid4

from universal_memory.application.onboarding.agent_connections import (
    AgentDetectorPort,
    DetectedAgent,
    ExternalSkillAction,
    OfficialSkillAgentMapping,
)
from universal_memory.application.onboarding.execute_agent_connections import (
    ExternalActionExecution,
)
from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.application.skills.official_skill_distribution import (
    OfficialSkillAgent,
    OfficialSkillDistributionPlanner,
    OfficialSkillEnvironment,
    SkillInstallMethod,
    SkillInstallScope,
)
from universal_memory.domain.entities import AuditEvent, AuditEventScope
from universal_memory.domain.entities.runtime import RuntimeAdapter
from universal_memory.domain.ports import AuditLogRepository
from universal_memory.infrastructure.onboarding.pinned_skills_catalog import (
    PINNED_SKILLS_AGENTS,
)

_ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(token|password|passwd|secret|api[_-]?key)\s*[:=]\s*([^\s,;]+)"
)
_BEARER_SECRET = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_GITHUB_SECRET = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
_AWS_SECRET = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
_CREDENTIAL_URL = re.compile(r"(?i)(https?://)[^/@\s:]+:[^/@\s]+@")
_MAX_CAPTURE_CHARS = 800
_MAX_TIMEOUT_SECONDS = 600
_INHERITED_ENVIRONMENT_KEYS = frozenset(
    {
        "ALL_PROXY",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NODE_EXTRA_CA_CERTS",
        "NO_PROXY",
        "PATH",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "TEMP",
        "TMP",
        "TMPDIR",
    }
)


@dataclass(frozen=True, slots=True)
class OfficialSkillBridgeMapping:
    """Reviewed capability mapping for one external installer target."""

    agent_id: str
    external_agent_id: str
    display_name: str
    detection_paths: tuple[str, ...]
    instruction_targets: tuple[str, ...]
    installed: bool = False

    def __post_init__(self) -> None:
        if not _safe_agent_id(self.agent_id) or not _safe_agent_id(self.external_agent_id):
            raise ValueError("Official skill agent IDs must be lowercase kebab-case values.")
        if not self.display_name.strip():
            raise ValueError("Official skill display name must not be blank.")
        if not self.detection_paths:
            raise ValueError("Official skill mappings require a detection path.")
        if len(self.instruction_targets) != 1:
            raise ValueError("Official skill mappings require exactly one instruction target.")
        for value in (*self.detection_paths, *self.instruction_targets):
            if not _safe_relative_path(value):
                raise ValueError("Official skill mapping paths must be safe relative paths.")
        if PurePosixPath(self.instruction_targets[0]).name != "SKILL.md":
            raise ValueError("Official skill instruction targets must end in SKILL.md.")


@dataclass(frozen=True, slots=True)
class StoredOfficialSkillConnection:
    agent_id: str
    external_agent_id: str
    relative_target: str
    tree_hash: str


class OfficialSkillConnectionStatePort:
    def get(self, *, agent_id: str) -> StoredOfficialSkillConnection | None:
        return None

    def persist(self, connection: StoredOfficialSkillConnection) -> str | None:
        del connection
        return None


class ExternalActionAuditPort:
    def record(
        self,
        *,
        phase: str,
        action: ExternalSkillAction,
        status: str,
        relative_target: str | None,
        detail: str | None,
    ) -> str | None:
        del phase, action, status, relative_target, detail
        return None


class LocalOfficialSkillConnectionStatePort(OfficialSkillConnectionStatePort):
    _RELATIVE_PATH = ".umem/connections/external-skills.json"

    def __init__(self, *, project_root: Path, safe_write_use_case: SafeWriteUseCase) -> None:
        self._project_root = project_root
        self._safe_write_use_case = safe_write_use_case

    def get(self, *, agent_id: str) -> StoredOfficialSkillConnection | None:
        payload = self._load()
        item = payload.get(agent_id)
        if not isinstance(item, dict):
            return None
        try:
            connection = StoredOfficialSkillConnection(
                agent_id=agent_id,
                external_agent_id=str(item["external_agent_id"]),
                relative_target=str(item["relative_target"]),
                tree_hash=str(item["tree_hash"]),
            )
        except (KeyError, TypeError, ValueError):
            return None
        if (
            not _safe_agent_id(connection.agent_id)
            or not _safe_agent_id(connection.external_agent_id)
            or not _safe_relative_path(connection.relative_target)
            or re.fullmatch(r"[0-9a-f]{64}", connection.tree_hash) is None
        ):
            return None
        return connection

    def persist(self, connection: StoredOfficialSkillConnection) -> str | None:
        payload = self._load()
        payload[connection.agent_id] = {
            "external_agent_id": connection.external_agent_id,
            "relative_target": connection.relative_target,
            "tree_hash": connection.tree_hash,
        }
        result = self._safe_write_use_case.execute(
            SafeWriteCommand(
                relative_path=self._RELATIVE_PATH,
                content=json.dumps(payload, sort_keys=True, indent=2) + "\n",
                scope=AuditEventScope.project,
                origin="cli_agent_connection",
                action="persist_external_skill_connection",
            )
        )
        return result.audit_reference

    def _load(self) -> dict[str, object]:
        path = self._project_root / self._RELATIVE_PATH
        if not path.is_file():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}


class LocalExternalActionAuditPort(ExternalActionAuditPort):
    def __init__(self, *, repository: AuditLogRepository) -> None:
        self._repository = repository

    def record(
        self,
        *,
        phase: str,
        action: ExternalSkillAction,
        status: str,
        relative_target: str | None,
        detail: str | None,
    ) -> str:
        now = datetime.now(UTC)
        audit_reference = str(uuid4())
        event = AuditEvent(
            id=audit_reference,
            created_at=now,
            updated_at=now,
            timestamp=now,
            action=f"external_skill_{phase}",
            scope=AuditEventScope.project,
            origin="cli_agent_connection",
            result=status,
            snapshot_reference=str(uuid4()),
            audit_reference=audit_reference,
            status="external_unmanaged",
            details=json.dumps(
                {
                    "agent_id": action.agent_id,
                    "boundary": "external_unmanaged",
                    "cwd": ".",
                    "relative_target": relative_target,
                    "detail": detail,
                    "snapshot_coverage": False,
                    "rollback_coverage": False,
                },
                sort_keys=True,
            ),
        )
        self._repository.write(event)
        return audit_reference


class StaticOfficialSkillMappingPort:
    def __init__(
        self,
        mappings: Sequence[OfficialSkillBridgeMapping],
        *,
        project_root: Path | None = None,
        state_port: OfficialSkillConnectionStatePort | None = None,
    ) -> None:
        self._mappings = tuple(mappings)
        self._project_root = project_root
        self._state_port = state_port or OfficialSkillConnectionStatePort()
        ids = [mapping.agent_id for mapping in self._mappings]
        if len(ids) != len(set(ids)):
            raise ValueError("Official skill mapping IDs must be unique.")

    @property
    def mappings(self) -> tuple[OfficialSkillBridgeMapping, ...]:
        return self._mappings

    def get(self, *, agent_id: str) -> OfficialSkillBridgeMapping | None:
        mapped = next(
            (mapping for mapping in self._mappings if mapping.agent_id == agent_id),
            None,
        )
        stored = self._state_port.get(agent_id=agent_id)
        if stored is not None and self._project_root is not None:
            target = self._project_root / stored.relative_target
            tree_hash = _validate_official_skill_tree(self._project_root, target)
            if tree_hash == stored.tree_hash and stored.external_agent_id == (
                mapped.external_agent_id if mapped else agent_id
            ):
                return OfficialSkillBridgeMapping(
                    agent_id=agent_id,
                    external_agent_id=stored.external_agent_id,
                    display_name=(
                        mapped.display_name
                        if mapped is not None
                        else " ".join(part.capitalize() for part in agent_id.split("-"))
                    ),
                    detection_paths=(
                        mapped.detection_paths if mapped is not None else (f".{agent_id}",)
                    ),
                    instruction_targets=(f"{stored.relative_target}/SKILL.md",),
                    installed=True,
                )
        if mapped is not None:
            return mapped
        if not _safe_agent_id(agent_id):
            return None
        pinned = PINNED_SKILLS_AGENTS.get(agent_id)
        if pinned is None:
            return None
        return OfficialSkillBridgeMapping(
            agent_id=agent_id,
            external_agent_id=agent_id,
            display_name=pinned.display_name,
            detection_paths=(pinned.project_skills_directory,),
            instruction_targets=(pinned.instruction_target,),
        )

    def resolve(self, *, agent_id: str) -> OfficialSkillAgentMapping | None:
        mapping = self.get(agent_id=agent_id)
        if mapping is None:
            return None
        return OfficialSkillAgentMapping(
            external_agent_id=mapping.external_agent_id,
            instruction_targets=mapping.instruction_targets,
            installed=mapping.installed,
        )


class LocalOfficialSkillEnvironmentProbe:
    """Resolve local executable/policy capabilities without network or subprocess probes."""

    def __init__(
        self,
        *,
        mapping_port: StaticOfficialSkillMappingPort,
        which: Callable[[str], str | None] = shutil.which,
        network_allowed: Callable[[], bool] | None = None,
    ) -> None:
        self._mapping_port = mapping_port
        self._which = which
        self._network_allowed = network_allowed or _environment_allows_network

    def resolve(self, *, agent_id: str) -> OfficialSkillEnvironment:
        return OfficialSkillEnvironment(
            node_available=self._which("node") is not None,
            npx_available=self._which("npx") is not None,
            network_available=bool(self._network_allowed()),
            agent_mapping_available=self._mapping_port.get(agent_id=agent_id) is not None,
            agents_md_available=True,
            umem_native_available=True,
            manual_copy_available=True,
        )


class OfficialSkillMappedAgentDetector:
    """Add narrowly mapped portable agents to registry-owned detection."""

    def __init__(
        self,
        *,
        delegate: AgentDetectorPort,
        mapping_port: StaticOfficialSkillMappingPort,
    ) -> None:
        self._delegate = delegate
        self._mapping_port = mapping_port

    def detect(
        self,
        project_root: Path,
        runtimes: tuple[RuntimeAdapter, ...],
    ) -> list[DetectedAgent]:
        detected = self._delegate.detect(project_root, runtimes)
        seen = {agent.agent_id for agent in detected}
        for mapping in self._mapping_port.mappings:
            matches = tuple(
                path
                for path in mapping.detection_paths
                if _safe_project_candidate(project_root, path).exists()
            )
            if matches and mapping.agent_id not in seen:
                detected.append(
                    DetectedAgent(
                        agent_id=mapping.agent_id,
                        display_name=mapping.display_name,
                        detected_by=matches,
                    )
                )
        return detected


SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


class OfficialSkillExternalActionExecutor:
    """Execute a validated official bridge action and independently verify its result."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        project_root: Path,
        mapping_port: StaticOfficialSkillMappingPort,
        runner: SubprocessRunner | None = None,
        which: Callable[[str], str | None] = shutil.which,
        base_environment: Mapping[str, str] | None = None,
        timeout_seconds: int = 120,
        state_port: OfficialSkillConnectionStatePort | None = None,
        audit_port: ExternalActionAuditPort | None = None,
    ) -> None:
        if timeout_seconds < 1 or timeout_seconds > _MAX_TIMEOUT_SECONDS:
            raise ValueError("External installer timeout must be between 1 and 600 seconds.")
        self._project_root = project_root
        self._mapping_port = mapping_port
        self._runner = runner or subprocess.run
        self._which = which
        inherited = base_environment if base_environment is not None else os.environ
        self._sensitive_paths = tuple(
            value for key, value in inherited.items() if key in {"HOME", "USERPROFILE"} and value
        )
        self._base_environment = {
            key: value for key, value in inherited.items() if key in _INHERITED_ENVIRONMENT_KEYS
        }
        self._timeout_seconds = timeout_seconds
        self._state_port = state_port or OfficialSkillConnectionStatePort()
        self._audit_port = audit_port or ExternalActionAuditPort()

    def execute(self, action: ExternalSkillAction) -> ExternalActionExecution:
        self._record_audit(
            phase="attempt",
            action=action,
            status="started",
            relative_target=None,
            detail=None,
        )
        result = self._execute(action)
        audit_reference = self._record_audit(
            phase="outcome",
            action=action,
            status=result.status,
            relative_target=result.relative_target,
            detail=result.detail,
        )
        return replace(result, audit_reference=audit_reference or result.audit_reference)

    def _execute(  # noqa: PLR0911
        self, action: ExternalSkillAction
    ) -> ExternalActionExecution:
        mapping = self._mapping_port.get(agent_id=action.agent_id)
        unsafe_reason = self._unsafe_reason(action, mapping)
        if unsafe_reason is not None:
            return _external_result("unsafe", detail=unsafe_reason)
        if mapping is None:
            return _external_result("unsafe", detail="The external mapping is unavailable.")

        preflight_result = self._preflight_known_destination(action, mapping)
        if preflight_result is not None:
            return preflight_result

        resolved_npx = self._which("npx")
        if resolved_npx is None or not Path(resolved_npx).is_absolute():
            return _external_result("unavailable", detail="The npx executable is unavailable.")

        instruction_target = PurePosixPath(mapping.instruction_targets[0])
        relative_target = instruction_target.parent.as_posix()
        with tempfile.TemporaryDirectory(prefix="umem-npx-skills-") as isolated_home_name:
            isolated_home = Path(isolated_home_name)
            process_environment = self._process_environment(
                action,
                isolated_home=isolated_home,
            )
            completed, error = self._invoke(
                action.argv,
                cwd=self._project_root,
                resolved_npx=resolved_npx,
                process_environment=process_environment,
            )
            if error is not None:
                detail = "Partial external mutation may require review."
                if error.detail:
                    detail = f"{error.detail}\n{detail}"
                return replace(error, detail=detail, relative_target=relative_target)
            if completed is None:
                return _external_result("failed", detail="Installation returned no result.")
            if (
                _validate_official_skill_tree(
                    self._project_root,
                    self._project_root / relative_target,
                )
                is None
            ):
                return _external_result(
                    "validation_failed",
                    detail=(
                        "The installer completed but the pinned target did not contain the "
                        "complete official skill. Partial external mutation may require review."
                    ),
                    relative_target=relative_target,
                )
            return self._persist_validated_connection(
                action,
                mapping,
                relative_target=relative_target,
                status="executed",
                detail=self._captured_detail(completed.stdout, completed.stderr),
            )

    def _preflight_known_destination(
        self,
        action: ExternalSkillAction,
        mapping: OfficialSkillBridgeMapping,
    ) -> ExternalActionExecution | None:
        instruction_target = PurePosixPath(mapping.instruction_targets[0])
        relative_target = (
            instruction_target.parent.as_posix()
            if instruction_target.name == "SKILL.md"
            else instruction_target.as_posix()
        )
        state = _official_skill_tree_state(
            self._project_root,
            self._project_root / relative_target,
        )
        if state == "absent":
            return None
        if state == "conflict":
            return _external_result(
                "conflict",
                detail="The selected agent has an occupied or invalid skill target.",
                relative_target=relative_target,
            )
        return self._persist_validated_connection(
            action,
            mapping,
            relative_target=relative_target,
            status="already_present",
        )

    def _invoke(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        resolved_npx: str,
        process_environment: Mapping[str, str],
    ) -> tuple[subprocess.CompletedProcess[str] | None, ExternalActionExecution | None]:
        try:
            completed = self._runner(
                argv,
                executable=resolved_npx,
                cwd=cwd,
                env=dict(process_environment),
                shell=False,
                timeout=self._timeout_seconds,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            return None, _external_result(
                "timeout",
                detail=self._captured_detail(error.output, error.stderr),
            )
        except OSError as error:
            return None, _external_result("failed", detail=self._captured_detail("", str(error)))
        if completed.returncode != 0:
            return None, _external_result(
                "failed",
                detail=self._captured_detail(completed.stdout, completed.stderr),
                exit_code=completed.returncode,
            )
        return completed, None

    def _process_environment(
        self,
        action: ExternalSkillAction,
        *,
        isolated_home: Path,
    ) -> dict[str, str]:
        environment = dict(self._base_environment)
        environment.update(
            {
                "HOME": str(isolated_home),
                "NPM_CONFIG_CACHE": str(isolated_home / ".npm-cache"),
                "NPM_CONFIG_REGISTRY": "https://registry.npmjs.org",
                "NPM_CONFIG_USERCONFIG": os.devnull,
            }
        )
        environment.update(dict(action.environment))
        return environment

    def _persist_validated_connection(
        self,
        action: ExternalSkillAction,
        mapping: OfficialSkillBridgeMapping,
        *,
        relative_target: str,
        status: str,
        detail: str | None = None,
    ) -> ExternalActionExecution:
        tree_hash = _validate_official_skill_tree(
            self._project_root,
            self._project_root / relative_target,
        )
        if tree_hash is None:
            return _external_result("validation_failed", relative_target=relative_target)
        try:
            self._state_port.persist(
                StoredOfficialSkillConnection(
                    agent_id=action.agent_id,
                    external_agent_id=mapping.external_agent_id,
                    relative_target=relative_target,
                    tree_hash=tree_hash,
                )
            )
        except Exception as error:
            return _external_result(
                "persistence_failed",
                detail=self._captured_detail("", str(error)),
                relative_target=relative_target,
            )
        return _external_result(
            status,
            instruction_present=True,
            detail=detail,
            exit_code=0,
            relative_target=relative_target,
        )

    def _record_audit(
        self,
        *,
        phase: str,
        action: ExternalSkillAction,
        status: str,
        relative_target: str | None,
        detail: str | None,
    ) -> str | None:
        try:
            return self._audit_port.record(
                phase=phase,
                action=action,
                status=status,
                relative_target=relative_target,
                detail=self._captured_detail("", detail),
            )
        except Exception:
            return None

    def _unsafe_reason(
        self,
        action: ExternalSkillAction,
        mapping: OfficialSkillBridgeMapping | None,
    ) -> str | None:
        if mapping is None:
            return "No reviewed external mapping exists for the selected agent."
        expected = OfficialSkillDistributionPlanner.for_published_distribution().plan(
            OfficialSkillAgent(
                agent_id=mapping.external_agent_id,
                display_name=mapping.display_name,
            ),
            OfficialSkillEnvironment(
                node_available=True,
                npx_available=True,
                network_available=True,
                agent_mapping_available=True,
                agents_md_available=True,
                umem_native_available=True,
                manual_copy_available=True,
            ),
            scope=SkillInstallScope.project,
            install_method=SkillInstallMethod.copy,
        )
        checks = (
            action.available is True,
            action.action == "external_action",
            action.channel == "npx_skills",
            action.scope == "project",
            action.network_required is True,
            action.telemetry_disabled is True,
            action.mutation_owner == "external",
            action.external_agent_id == mapping.external_agent_id,
            action.instruction_targets == mapping.instruction_targets,
            type(action.argv) is tuple,
            action.argv == expected.argv,
            action.environment == (("DISABLE_TELEMETRY", "1"),),
        )
        if not all(checks):
            return "The external action does not match the pinned official project plan."
        return None

    def _captured_detail(self, stdout: object, stderr: object) -> str | None:
        rendered = "\n".join(
            value for value in (_sanitize_capture(stdout), _sanitize_capture(stderr)) if value
        )
        if not rendered:
            return None
        rendered = rendered.replace(str(self._project_root.resolve()), ".")
        for sensitive_path in self._sensitive_paths:
            rendered = rendered.replace(sensitive_path, "<home>")
        return rendered[:_MAX_CAPTURE_CHARS]


def _external_result(
    status: str,
    *,
    instruction_present: bool = False,
    detail: str | None = None,
    exit_code: int | None = None,
    relative_target: str | None = None,
) -> ExternalActionExecution:
    return ExternalActionExecution(
        status=status,
        instruction_present=instruction_present,
        detail=detail,
        mutation_boundary="external_unmanaged",
        exit_code=exit_code,
        relative_target=relative_target,
    )


def _safe_agent_id(value: str) -> bool:
    return re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is not None


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(
        value
        and "\\" not in value
        and not path.is_absolute()
        and path != PurePosixPath(".")
        and ".." not in path.parts
    )


def _safe_project_candidate(project_root: Path, relative_path: str) -> Path:
    if not _safe_relative_path(relative_path):
        raise ValueError("Expected a safe relative project path.")
    return project_root / relative_path


def _candidate_stays_in_project(project_root: Path, candidate: Path) -> bool:
    root = project_root.resolve()
    try:
        relative = candidate.relative_to(project_root)
        candidate.resolve(strict=False).relative_to(root)
    except (OSError, ValueError):
        return False
    current = project_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return False
    ancestor = candidate.parent
    while not ancestor.exists() and ancestor != project_root:
        ancestor = ancestor.parent
    try:
        ancestor.resolve(strict=False).relative_to(root)
    except (OSError, ValueError):
        return False
    return True


def _official_skill_tree_state(project_root: Path, candidate: Path) -> str:
    if not candidate.exists() and not candidate.is_symlink():
        if _candidate_stays_in_project(project_root, candidate):
            return "absent"
        return "conflict"
    return "valid" if _validate_official_skill_tree(project_root, candidate) else "conflict"


def _validate_official_skill_tree(  # noqa: PLR0911
    project_root: Path,
    candidate: Path,
) -> str | None:
    if not _candidate_stays_in_project(project_root, candidate):
        return None
    try:
        relative = candidate.relative_to(project_root)
    except ValueError:
        return None
    current = project_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return None
    if not candidate.is_dir() or candidate.is_symlink():
        return None
    packaged_root = Path(
        str(resources.files("universal_memory").joinpath("resources/skills/universal-memory"))
    )
    packaged_files = {
        path.relative_to(packaged_root).as_posix(): path.read_bytes()
        for path in packaged_root.rglob("*")
        if path.is_file()
    }
    installed_files: dict[str, bytes] = {}
    try:
        for path in candidate.rglob("*"):
            if path.is_symlink():
                return None
            if path.is_file():
                installed_files[path.relative_to(candidate).as_posix()] = path.read_bytes()
    except OSError:
        return None
    if installed_files != packaged_files:
        return None
    digest = sha256()
    for relative_path, content in sorted(installed_files.items()):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def _environment_allows_network() -> bool:
    value = os.environ.get("UMEM_OFFLINE", "").strip().lower()
    return value not in {"1", "true", "yes", "on"}


def _sanitize_capture(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        rendered = value.decode("utf-8", errors="replace")
    else:
        rendered = str(value)
    rendered = _ANSI_ESCAPE.sub("", rendered)
    rendered = "".join(
        character
        for character in rendered
        if character in "\n\t" or (character.isprintable() and character not in "\r")
    )
    rendered = _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", rendered)
    rendered = _BEARER_SECRET.sub("Bearer [REDACTED]", rendered)
    rendered = _GITHUB_SECRET.sub("[REDACTED]", rendered)
    rendered = _AWS_SECRET.sub("[REDACTED]", rendered)
    rendered = _CREDENTIAL_URL.sub(r"\1[REDACTED]@", rendered)
    return rendered.strip()


# Deliberately narrow: this is an executable capability mapping, not a Tier 1 support catalog.
DEFAULT_OFFICIAL_SKILL_MAPPINGS = (
    OfficialSkillBridgeMapping(
        agent_id="windsurf",
        external_agent_id="windsurf",
        display_name="Windsurf",
        detection_paths=(".windsurf",),
        instruction_targets=(".windsurf/skills/universal-memory/SKILL.md",),
    ),
)
