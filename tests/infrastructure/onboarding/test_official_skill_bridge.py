import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from universal_memory.application.onboarding import (
    ExternalSkillAction,
    RegistrySignalAgentDetector,
)
from universal_memory.domain.entities import AuditEvent, AuditEventScope
from universal_memory.domain.entities.runtime import default_runtime_registry
from universal_memory.domain.ports import AuditLogRepository
from universal_memory.infrastructure.onboarding import (
    ExternalActionAuditPort,
    LocalExternalActionAuditPort,
    LocalOfficialSkillEnvironmentProbe,
    OfficialSkillBridgeMapping,
    OfficialSkillConnectionStatePort,
    OfficialSkillExternalActionExecutor,
    OfficialSkillMappedAgentDetector,
    StaticOfficialSkillMappingPort,
    StoredOfficialSkillConnection,
)

EXPECTED_INSTALL_PROCESS_CALLS = 1
EXPECTED_STAGED_FAILURE_PROCESS_CALLS = 1
EXPECTED_ADD_PROCESS_CALLS = 1
EXPECTED_TIMEOUT_SECONDS = 17
FAILED_EXIT_CODE = 7
PACKAGED_SKILL_ROOT = Path("src/universal_memory/resources/skills/universal-memory")


def _mapping(
    *,
    agent_id: str = "windsurf",
    display_name: str = "Windsurf",
    instruction_target: str = ".windsurf/skills/universal-memory/SKILL.md",
) -> OfficialSkillBridgeMapping:
    return OfficialSkillBridgeMapping(
        agent_id=agent_id,
        external_agent_id=agent_id,
        display_name=display_name,
        detection_paths=(f".{agent_id}",),
        instruction_targets=(instruction_target,) if instruction_target else (),
    )


def _action(
    *,
    agent_id: str = "windsurf",
    instruction_target: str = ".windsurf/skills/universal-memory/SKILL.md",
) -> ExternalSkillAction:
    return ExternalSkillAction(
        agent_id=agent_id,
        external_agent_id=agent_id,
        instruction_targets=(instruction_target,) if instruction_target else (),
        available=True,
        scope="project",
        action="external_action",
        channel="npx_skills",
        argv=(
            "npx",
            "--yes",
            "skills@1.5.20",
            "add",
            "https://github.com/YanAmorelli/universal-memory/tree/v0.5.0/skills/universal-memory",
            "--skill",
            "universal-memory",
            "--agent",
            agent_id,
            "--copy",
            "-y",
        ),
        environment=(("DISABLE_TELEMETRY", "1"),),
    )


def _copy_packaged_skill(
    root: Path,
    relative_target: str = ".windsurf/skills/universal-memory",
) -> Path:
    target = root / relative_target
    shutil.copytree(PACKAGED_SKILL_ROOT, target)
    return target


def _installed_payload(
    root: Path,
    *,
    relative_target: str = ".windsurf/skills/universal-memory",
    reported_agent: str = "Windsurf",
) -> str:
    return json.dumps(
        [
            {
                "name": "universal-memory",
                "path": str(root / relative_target),
                "scope": "project",
                "agents": [reported_agent],
                "source": "YanAmorelli/universal-memory",
                "sourceUrl": "https://github.com/YanAmorelli/universal-memory",
                "sourceType": "github",
            }
        ]
    )


@pytest.mark.parametrize(
    "instruction_targets",
    [(), (".windsurf/skills/universal-memory",), ("one/SKILL.md", "two/SKILL.md")],
)
def test_mapping_requires_one_safe_skill_instruction_target(
    instruction_targets: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="instruction target"):
        OfficialSkillBridgeMapping(
            agent_id="windsurf",
            external_agent_id="windsurf",
            display_name="Windsurf",
            detection_paths=(".windsurf",),
            instruction_targets=instruction_targets,
        )


def test_local_probe_uses_only_injected_local_capabilities(tmp_path: Path) -> None:
    mapping_port = StaticOfficialSkillMappingPort((_mapping(),))
    looked_up: list[str] = []

    def which(name: str) -> str | None:
        looked_up.append(name)
        return f"/tools/{name}"

    probe = LocalOfficialSkillEnvironmentProbe(
        mapping_port=mapping_port,
        which=which,
        network_allowed=lambda: True,
    )

    environment = probe.resolve(agent_id="windsurf")
    generic = probe.resolve(agent_id="zed")
    invalid = probe.resolve(agent_id="../../unknown")

    assert environment.node_available is True
    assert environment.npx_available is True
    assert environment.network_available is True
    assert environment.agent_mapping_available is True
    assert generic.agent_mapping_available is True
    assert invalid.agent_mapping_available is False
    assert looked_up == ["node", "npx", "node", "npx", "node", "npx"]
    assert not list(tmp_path.iterdir())


def test_mapped_detector_adds_only_reviewed_workspace_capabilities(tmp_path: Path) -> None:
    (tmp_path / ".windsurf").mkdir()
    detector = OfficialSkillMappedAgentDetector(
        delegate=RegistrySignalAgentDetector(which=lambda _name: None, home=tmp_path / "home"),
        mapping_port=StaticOfficialSkillMappingPort((_mapping(),)),
    )

    detected = detector.detect(tmp_path, tuple(default_runtime_registry().runtimes))

    assert [(item.agent_id, item.detected_by) for item in detected] == [
        ("windsurf", (".windsurf",))
    ]


def test_executor_binds_npx_and_runs_exact_argv_without_shell(tmp_path: Path) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        root = Path(kwargs["cwd"])
        if "ls" in argv:
            target = root / ".windsurf/skills/universal-memory/SKILL.md"
            return subprocess.CompletedProcess(
                argv,
                0,
                _installed_payload(root) if target.exists() else "[]",
                "",
            )
        _copy_packaged_skill(root)
        return subprocess.CompletedProcess(argv, 0, "installed\n", "")

    executor = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort((_mapping(),)),
        runner=runner,
        which=lambda name: "/tools/npx" if name == "npx" else None,
        base_environment={"PATH": "/tools", "SECRET_TOKEN": "must-not-appear"},
        timeout_seconds=EXPECTED_TIMEOUT_SECONDS,
    )

    result = executor.execute(_action())

    assert result.status == "executed"
    assert result.instruction_present is True
    assert result.mutation_boundary == "external_unmanaged"
    add_calls = [call for call in calls if "add" in call[0]]
    assert len(calls) == EXPECTED_INSTALL_PROCESS_CALLS
    assert len(add_calls) == EXPECTED_ADD_PROCESS_CALLS
    argv, kwargs = next(call for call in add_calls if call[1]["cwd"] == tmp_path)
    environment = cast(dict[str, str], kwargs["env"])
    assert argv == _action().argv
    assert kwargs["executable"] == "/tools/npx"
    assert kwargs["cwd"] == tmp_path
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == EXPECTED_TIMEOUT_SECONDS
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert environment["PATH"] == "/tools"
    assert environment["DISABLE_TELEMETRY"] == "1"
    assert environment["NPM_CONFIG_CACHE"].endswith("/.npm-cache")
    assert environment["NPM_CONFIG_REGISTRY"] == "https://registry.npmjs.org"
    assert environment["NPM_CONFIG_USERCONFIG"] == "/dev/null"
    assert Path(environment["HOME"]).is_absolute()
    assert "SECRET_TOKEN" not in environment


def test_executor_is_idempotent_when_valid_skill_is_already_present(tmp_path: Path) -> None:
    _copy_packaged_skill(tmp_path)
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def inspect_existing(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, _installed_payload(tmp_path), "")

    executor = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort((_mapping(),)),
        runner=inspect_existing,
        which=lambda _name: "/tools/npx",
    )

    first = executor.execute(_action())
    second = executor.execute(_action())

    assert first.status == second.status == "already_present"
    assert first.instruction_present is second.instruction_present is True
    assert calls == []


def test_executor_rejects_conflict_malicious_plan_and_symlink_escape(tmp_path: Path) -> None:
    mapping_port = StaticOfficialSkillMappingPort((_mapping(),))
    calls: list[object] = []

    def unexpected_runner(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("unsafe or conflicting plans must not invoke subprocesses")

    executor = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=mapping_port,
        runner=unexpected_runner,
        which=lambda _name: "/tools/npx",
    )
    target = tmp_path / ".windsurf/skills/universal-memory/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("not the official skill", encoding="utf-8")

    conflict = executor.execute(_action())
    malicious = executor.execute(replace(_action(), argv=(*_action().argv, "--global")))

    assert conflict.status == "conflict"
    assert malicious.status == "unsafe"
    assert calls == []


def test_executor_rejects_unknown_agent_without_invoking_npx(tmp_path: Path) -> None:
    calls: list[object] = []

    def unexpected_runner(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("unknown agents must not invoke subprocesses")

    result = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort(()),
        runner=unexpected_runner,
        which=lambda _name: "/tools/npx",
    ).execute(_action(agent_id="made-up-agent", instruction_target=""))

    assert result.status == "unsafe"
    assert calls == []


def test_executor_rejects_instruction_target_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    agent_root = tmp_path / ".windsurf"
    agent_root.symlink_to(outside, target_is_directory=True)
    calls: list[object] = []

    def unexpected_runner(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("escaping targets must not invoke subprocesses")

    executor = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort((_mapping(),)),
        runner=unexpected_runner,
        which=lambda _name: "/tools/npx",
    )

    result = executor.execute(_action())

    assert result.status == "conflict"
    assert calls == []


def test_executor_rejects_internal_ancestor_symlink_before_npx(tmp_path: Path) -> None:
    internal = tmp_path / "internal-agent-root"
    internal.mkdir()
    (tmp_path / ".windsurf").symlink_to(internal, target_is_directory=True)
    calls: list[object] = []

    def unexpected_runner(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("ancestor symlinks must not invoke subprocesses")

    result = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort((_mapping(),)),
        runner=unexpected_runner,
        which=lambda _name: "/tools/npx",
    ).execute(_action())

    assert result.status == "conflict"
    assert calls == []
    assert not (internal / "skills").exists()


def test_executor_reports_timeout_nonzero_and_sanitized_output_nonfatally(
    tmp_path: Path,
) -> None:
    mapping_port = StaticOfficialSkillMappingPort((_mapping(),))

    def timed_out(argv, **kwargs):
        del kwargs
        timeout_capture = f"token={'a' * 3}\x1b[31m"
        raise subprocess.TimeoutExpired(argv, 2, output=timeout_capture, stderr="boom")

    timeout_executor = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=mapping_port,
        runner=timed_out,
        which=lambda _name: "/tools/npx",
        timeout_seconds=2,
    )
    timeout = timeout_executor.execute(_action())

    assert timeout.status == "timeout"
    assert timeout.relative_target == ".windsurf/skills/universal-memory"
    assert "Partial external mutation may require review" in (timeout.detail or "")
    assert "abc" not in (timeout.detail or "")
    assert "\x1b" not in (timeout.detail or "")

    password_value = "".join(("hunter", "2"))
    github_token = f"ghp_{'a' * 30}"
    aws_key = f"AKIA{'A' * 16}"
    url_username = "alice"
    url_password = "".join(("pri", "vate"))
    credential_url = f"https://{url_username}:{url_password}@example.invalid/path"
    failed_executor = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=mapping_port,
        runner=lambda argv, **kwargs: subprocess.CompletedProcess(
            argv,
            FAILED_EXIT_CODE,
            "",
            (
                f"failed at {tmp_path} password={password_value} "
                "Bearer header.payload.signature "
                f"{github_token} "
                f"{aws_key} "
                f"{credential_url}"
            ),
        ),
        which=lambda _name: "/tools/npx",
    )
    failed = failed_executor.execute(_action())

    assert failed.status == "failed"
    assert failed.relative_target == ".windsurf/skills/universal-memory"
    assert "Partial external mutation may require review" in (failed.detail or "")
    assert failed.exit_code == FAILED_EXIT_CODE
    assert str(tmp_path) not in (failed.detail or "")
    assert password_value not in (failed.detail or "")
    assert "header.payload.signature" not in (failed.detail or "")
    assert github_token not in (failed.detail or "")
    assert aws_key not in (failed.detail or "")
    assert f"{url_username}:{url_password}" not in (failed.detail or "")


def test_executor_never_trusts_exit_zero_without_expected_instruction(tmp_path: Path) -> None:
    invocations = 0

    def runner(argv, **kwargs):
        nonlocal invocations
        del kwargs
        invocations += 1
        return subprocess.CompletedProcess(argv, 0, "[]" if "ls" in argv else "ok", "")

    executor = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort((_mapping(),)),
        runner=runner,
        which=lambda _name: "/tools/npx",
    )

    result = executor.execute(_action())

    assert result.status == "validation_failed"
    assert result.instruction_present is False
    assert invocations == EXPECTED_STAGED_FAILURE_PROCESS_CALLS


def test_executor_reports_possible_partial_mutation_without_cleaning_it(
    tmp_path: Path,
) -> None:
    def partially_failing_install(argv, **kwargs):
        target = Path(kwargs["cwd"]) / ".windsurf/skills/universal-memory"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("partial\n", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 1, "", "installation failed")

    result = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort((_mapping(),)),
        runner=partially_failing_install,
        which=lambda _name: "/tools/npx",
    ).execute(_action())

    assert result.status == "failed"
    assert result.relative_target == ".windsurf/skills/universal-memory"
    assert "Partial external mutation may require review" in (result.detail or "")
    assert (tmp_path / result.relative_target / "SKILL.md").read_text() == "partial\n"


@pytest.mark.parametrize(
    ("agent_id", "reported_agent", "relative_target"),
    [
        ("claude-code", "Claude Code", ".claude/skills/universal-memory"),
        ("github-copilot", "GitHub Copilot", ".agents/skills/universal-memory"),
        ("autohand-code", "Autohand Code CLI", ".autohand/skills/universal-memory"),
        ("bob", "IBM Bob", ".bob/skills/universal-memory"),
        ("cortex", "Cortex Code", ".cortex/skills/universal-memory"),
        ("devin", "Devin for Terminal", ".devin/skills/universal-memory"),
        ("grok", "Grok Build", ".grok/skills/universal-memory"),
        ("kilo", "Kilo Code", ".kilocode/skills/universal-memory"),
        ("roo", "Roo Code", ".roo/skills/universal-memory"),
    ],
)
def test_executor_accepts_pinned_cli_display_names(
    tmp_path: Path,
    agent_id: str,
    reported_agent: str,
    relative_target: str,
) -> None:
    mapping = _mapping(
        agent_id=agent_id,
        display_name=reported_agent,
        instruction_target=f"{relative_target}/SKILL.md",
    )

    def runner(argv, **kwargs):
        root = Path(kwargs["cwd"])
        if "ls" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                _installed_payload(
                    root,
                    relative_target=relative_target,
                    reported_agent=reported_agent,
                ),
                "",
            )
        _copy_packaged_skill(root, relative_target)
        return subprocess.CompletedProcess(argv, 0, "installed", "")

    result = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort((mapping,)),
        runner=runner,
        which=lambda _name: "/tools/npx",
    ).execute(
        _action(
            agent_id=agent_id,
            instruction_target=f"{relative_target}/SKILL.md",
        )
    )

    assert result.status == "executed"
    assert result.relative_target == relative_target


@pytest.mark.parametrize("mutation", ["missing_reference", "tampered_asset"])
def test_executor_rejects_incomplete_or_tampered_official_tree_before_npx(
    tmp_path: Path,
    mutation: str,
) -> None:
    target = _copy_packaged_skill(tmp_path)
    if mutation == "missing_reference":
        (target / "references/startup-and-context.md").unlink()
    else:
        (target / "assets/agents-md-bootstrap.md").write_text(
            "tampered",
            encoding="utf-8",
        )
    calls: list[object] = []

    def unexpected_runner(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("invalid trees must not invoke subprocesses")

    result = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort((_mapping(),)),
        runner=unexpected_runner,
        which=lambda _name: "/tools/npx",
    ).execute(_action())

    assert result.status == "conflict"
    assert calls == []


def test_pinned_target_is_checked_before_an_occupied_project_path_is_rejected(
    tmp_path: Path,
) -> None:
    relative_target = ".agents/skills/universal-memory"
    occupied = tmp_path / relative_target
    occupied.mkdir(parents=True)
    (occupied / "SKILL.md").write_text("user content", encoding="utf-8")
    calls: list[Path] = []

    def runner(argv, **kwargs):
        root = Path(kwargs["cwd"])
        calls.append(root)
        if "ls" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                _installed_payload(
                    root,
                    relative_target=relative_target,
                    reported_agent="Zed",
                ),
                "",
            )
        _copy_packaged_skill(root, relative_target)
        return subprocess.CompletedProcess(argv, 0, "installed", "")

    result = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort(()),
        runner=runner,
        which=lambda _name: "/tools/npx",
    ).execute(
        _action(
            agent_id="zed",
            instruction_target=f"{relative_target}/SKILL.md",
        )
    )

    assert result.status == "conflict"
    assert calls == []
    assert (occupied / "SKILL.md").read_text(encoding="utf-8") == "user content"


def test_persisted_generic_target_is_reused_without_external_execution(tmp_path: Path) -> None:
    relative_target = ".agents/skills/universal-memory"

    class MemoryState(OfficialSkillConnectionStatePort):
        connection: StoredOfficialSkillConnection | None = None

        def get(self, *, agent_id: str) -> StoredOfficialSkillConnection | None:
            if self.connection is not None and self.connection.agent_id == agent_id:
                return self.connection
            return None

        def persist(self, connection: StoredOfficialSkillConnection) -> str:
            self.connection = connection
            return "state-audit"

    state = MemoryState()
    first_mapping_port = StaticOfficialSkillMappingPort(
        (),
        project_root=tmp_path,
        state_port=state,
    )

    def install(argv, **kwargs):
        root = Path(kwargs["cwd"])
        if "ls" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                _installed_payload(
                    root,
                    relative_target=relative_target,
                    reported_agent="Zed",
                ),
                "",
            )
        _copy_packaged_skill(root, relative_target)
        return subprocess.CompletedProcess(argv, 0, "installed", "")

    first = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=first_mapping_port,
        runner=install,
        which=lambda _name: "/tools/npx",
        state_port=state,
    ).execute(
        _action(
            agent_id="zed",
            instruction_target=f"{relative_target}/SKILL.md",
        )
    )

    unexpected_calls: list[object] = []
    persisted_mapping_port = StaticOfficialSkillMappingPort(
        (),
        project_root=tmp_path,
        state_port=state,
    )

    def unexpected_runner(*_args, **_kwargs):
        unexpected_calls.append((_args, _kwargs))
        raise AssertionError("a persisted valid target must not invoke subprocesses")

    second = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=persisted_mapping_port,
        runner=unexpected_runner,
        which=lambda _name: "/tools/npx",
        state_port=state,
    ).execute(
        _action(
            agent_id="zed",
            instruction_target=f"{relative_target}/SKILL.md",
        )
    )

    assert first.status == "executed"
    assert second.status == "already_present"
    assert second.relative_target == relative_target
    assert unexpected_calls == []


def test_executor_audits_attempt_and_external_boundary_outcome(tmp_path: Path) -> None:
    _copy_packaged_skill(tmp_path)

    class RecordingAudit(ExternalActionAuditPort):
        def __init__(self) -> None:
            self.records: list[dict[str, object]] = []

        def record(
            self,
            *,
            phase: str,
            action: ExternalSkillAction,
            status: str,
            relative_target: str | None,
            detail: str | None,
        ) -> str:
            values = {
                "phase": phase,
                "action": action,
                "status": status,
                "relative_target": relative_target,
                "detail": detail,
            }
            self.records.append(values)
            return f"audit-{phase}"

    audit = RecordingAudit()
    result = OfficialSkillExternalActionExecutor(
        project_root=tmp_path,
        mapping_port=StaticOfficialSkillMappingPort((_mapping(),)),
        runner=lambda *_args, **_kwargs: pytest.fail("npx must not run"),
        which=lambda _name: "/tools/npx",
        audit_port=audit,
    ).execute(_action())

    assert result.audit_reference == "audit-outcome"
    assert [record["phase"] for record in audit.records] == ["attempt", "outcome"]
    assert audit.records[1]["status"] == "already_present"
    assert audit.records[1]["relative_target"] == ".windsurf/skills/universal-memory"


def test_production_audit_adapter_persists_valid_external_boundary_event() -> None:
    class RecordingRepository(AuditLogRepository):
        def __init__(self) -> None:
            self.events: list[AuditEvent] = []

        def read(self, id: str) -> AuditEvent:
            raise KeyError(id)

        def list(self, scope: AuditEventScope | None = None) -> list[AuditEvent]:
            if scope is None:
                return self.events
            return [event for event in self.events if event.scope == scope]

        def write(self, entity: AuditEvent) -> None:
            self.events.append(entity)

        def migrate(self, target_version: int) -> None:
            del target_version

    repository = RecordingRepository()
    audit_reference = LocalExternalActionAuditPort(repository=repository).record(
        phase="outcome",
        action=_action(),
        status="executed",
        relative_target=".windsurf/skills/universal-memory",
        detail="installed",
    )

    assert len(repository.events) == 1
    event = repository.events[0]
    assert event.audit_reference == audit_reference
    assert event.snapshot_reference != audit_reference
    assert event.status == "external_unmanaged"
    assert '"snapshot_coverage": false' in (event.details or "")
    assert '"rollback_coverage": false' in (event.details or "")
