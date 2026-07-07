import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from universal_memory.application.diagnostics import DoctorCommand, DoctorUseCase
from universal_memory.application.host import ConfigureHostCommand, ConfigureHostResult
from universal_memory.infrastructure.config.project_layout import (
    ensure_project_layout,
    ensure_shared_project_layout,
)


def prepare_global_paths(tmp_path: Path) -> tuple[Path, Path]:
    xdg_data_home = tmp_path / "xdg-data"
    xdg_config_home = tmp_path / "xdg-config"
    (xdg_data_home / "umem").mkdir(parents=True)
    (xdg_config_home / "umem").mkdir(parents=True)
    return xdg_data_home, xdg_config_home


def test_doctor_reports_success_for_healthy_layout(
    tmp_path: Path,
) -> None:
    ensure_project_layout(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))

    assert result.ok is True
    assert result.summary.to_payload() == {
        "total_checks": 9,
        "passed": 7,
        "warnings": 2,
        "failed": 0,
    }


def test_doctor_reports_partial_layout_without_stopping_other_checks(
    tmp_path: Path,
) -> None:
    ensure_project_layout(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)
    (tmp_path / ".umem" / "audit" / "events.jsonl").unlink()

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    checks = {check.name: check for check in result.checks}

    assert result.ok is False
    assert checks["project_layout"].status == "failed"
    assert checks["project_layout"].error == "Missing path: .umem/audit/events.jsonl"
    assert checks["path_executables"].status == "success"


def test_doctor_reports_missing_executables(
    tmp_path: Path,
) -> None:
    ensure_project_layout(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)

    use_case = DoctorUseCase(
        which=lambda name: "/bin/umem" if name == "umem" else None,
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    executable_check = {check.name: check for check in result.checks}["path_executables"]

    assert result.ok is False
    assert executable_check.status == "failed"
    assert executable_check.error == "Missing executables on PATH: umem-mcp"


def test_doctor_reports_host_integration_failure(
    tmp_path: Path,
) -> None:
    ensure_project_layout(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)
    (tmp_path / ".umem" / "config.toml").write_text(
        '[runtimes]\nenabled = ["codex"]\n',
        encoding="utf-8",
    )
    received: list[ConfigureHostCommand] = []

    def host_check(command: ConfigureHostCommand) -> ConfigureHostResult:
        received.append(command)
        return ConfigureHostResult(
            host_id=command.host_id,
            instruction_targets=["AGENTS.md"],
            planned_changes=[],
            manual_steps=[],
            validation_status="failure",
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
            timestamp="2026-06-04T00:00:00Z",
            warnings=["AGENTS.md has corrupted UMEM managed block"],
        )

    use_case = DoctorUseCase(
        host_check_command=host_check,
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    host_check_result = {check.name: check for check in result.checks}["hosts_integration"]

    assert result.ok is False
    assert host_check_result.status == "failed"
    assert "codex: failure" in (host_check_result.error or "")
    assert received == [
        ConfigureHostCommand(
            host_id="codex",
            apply=False,
            check=True,
            record_audit=False,
        )
    ]


def test_doctor_reports_uninitialized_project_without_mutating_global_paths(
    tmp_path: Path,
) -> None:
    xdg_data_home = tmp_path / "xdg-data"
    xdg_config_home = tmp_path / "xdg-config"

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    checks = {check.name: check for check in result.checks}

    assert result.ok is False
    assert checks["filesystem_permissions"].status == "failed"
    assert "parent directory is missing" in (checks["filesystem_permissions"].error or "")
    assert checks["project_layout"].status == "failed"
    assert checks["project_layout"].error == "Missing project layout: .umem"
    assert not xdg_data_home.exists()
    assert not xdg_config_home.exists()


def test_doctor_reports_invalid_config_as_host_integration_failure(
    tmp_path: Path,
) -> None:
    ensure_project_layout(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)
    (tmp_path / ".umem" / "config.toml").write_text("[runtimes\n", encoding="utf-8")

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    host_check_result = {check.name: check for check in result.checks}["hosts_integration"]

    assert result.ok is False
    assert host_check_result.status == "failed"
    assert "Invalid TOML in config.toml" in (host_check_result.error or "")


def test_doctor_validates_global_config_path_kind(
    tmp_path: Path,
) -> None:
    ensure_project_layout(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)
    (xdg_config_home / "umem" / "config.toml").mkdir()

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    permission_check = {check.name: check for check in result.checks}["filesystem_permissions"]

    assert result.ok is False
    assert permission_check.status == "failed"
    assert "config.toml: path must be a file" in (permission_check.error or "")


def test_doctor_reports_healthy_shared_layout_checks(tmp_path: Path) -> None:
    ensure_shared_project_layout(tmp_path)
    _git_init(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    checks = {check.name: check for check in result.checks}

    assert result.ok is True
    assert checks["project_layout_mode"].status == "success"
    assert checks["project_layout_mode"].detail == "Shared project layout is active."
    assert checks["shared_root_visibility"].status == "success"
    assert checks["operational_root_privacy"].status == "success"
    assert checks["layout_overlaps"].status == "success"


def test_doctor_warns_for_partial_layout_and_missing_shared_metadata(tmp_path: Path) -> None:
    ensure_project_layout(tmp_path)
    (tmp_path / "umem" / "memory").mkdir(parents=True)
    (tmp_path / "umem" / "skills").mkdir()
    _git_init(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    layout_mode = {check.name: check for check in result.checks}["project_layout_mode"]

    assert result.ok is True
    assert layout_mode.status == "warning"
    assert "without complete shared metadata" in (layout_mode.error or "")


def test_doctor_warns_for_ignored_shared_root(tmp_path: Path) -> None:
    ensure_shared_project_layout(tmp_path)
    (tmp_path / ".gitignore").write_text("umem/\n", encoding="utf-8")
    _git_init(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    visibility = {check.name: check for check in result.checks}["shared_root_visibility"]

    assert result.ok is True
    assert visibility.status == "warning"
    assert visibility.error == "Shared paths are ignored: umem/"


def test_doctor_warns_for_ignored_shared_memory_path(tmp_path: Path) -> None:
    ensure_shared_project_layout(tmp_path)
    (tmp_path / ".gitignore").write_text("umem/memory/\n", encoding="utf-8")
    _git_init(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    visibility = {check.name: check for check in result.checks}["shared_root_visibility"]

    assert result.ok is True
    assert visibility.status == "warning"
    assert visibility.error == "Shared paths are ignored: umem/memory/"


def test_doctor_warns_for_tracked_operational_paths(tmp_path: Path) -> None:
    ensure_shared_project_layout(tmp_path)
    _git_init(tmp_path)
    _git(tmp_path, "add", ".umem/audit/events.jsonl")
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    privacy = {check.name: check for check in result.checks}["operational_root_privacy"]

    assert result.ok is True
    assert privacy.status == "warning"
    assert privacy.error == "Operational paths are tracked: .umem/audit/events.jsonl"


def test_doctor_warns_when_git_metadata_is_unavailable(tmp_path: Path) -> None:
    ensure_shared_project_layout(tmp_path)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    checks = {check.name: check for check in result.checks}

    assert result.ok is True
    assert checks["shared_root_visibility"].status == "warning"
    assert checks["operational_root_privacy"].status == "warning"


def test_doctor_ignores_inherited_git_hook_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ambient_repo = tmp_path / "ambient"
    ambient_repo.mkdir()
    _git(ambient_repo, "init")
    (ambient_repo / ".umem" / "audit").mkdir(parents=True)
    (ambient_repo / ".umem" / "audit" / "events.jsonl").write_text("", encoding="utf-8")
    _git(ambient_repo, "add", ".umem/audit/events.jsonl")
    target_project = tmp_path / "target"
    ensure_shared_project_layout(target_project)
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)
    monkeypatch.setenv("GIT_DIR", (ambient_repo / ".git").as_posix())
    monkeypatch.setenv("GIT_WORK_TREE", ambient_repo.as_posix())
    monkeypatch.setenv("GIT_INDEX_FILE", (ambient_repo / ".git" / "index").as_posix())

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=target_project))
    checks = {check.name: check for check in result.checks}

    assert result.ok is True
    assert checks["shared_root_visibility"].status == "warning"
    assert checks["operational_root_privacy"].status == "warning"
    assert checks["operational_root_privacy"].error is None


def test_doctor_warns_for_legacy_shared_overlaps(tmp_path: Path) -> None:
    ensure_shared_project_layout(tmp_path)
    _git_init(tmp_path)
    _append_jsonl(tmp_path / "umem/memory/facts.jsonl", {"id": "fact-1"})
    _append_jsonl(tmp_path / ".umem/memory/facts.jsonl", {"id": "fact-1"})
    _append_jsonl(tmp_path / "umem/memory/rules.jsonl", {"id": "rule-1"})
    _append_jsonl(tmp_path / ".umem/memory/rules.jsonl", {"id": "rule-1"})
    _append_jsonl(tmp_path / "umem/skills/skills.jsonl", {"slug": "review-helper"})
    _append_jsonl(tmp_path / ".umem/memory/skills.jsonl", {"slug": "review-helper"})
    xdg_data_home, xdg_config_home = prepare_global_paths(tmp_path)

    use_case = DoctorUseCase(
        which=lambda _name: "/bin/tool",
        home=tmp_path / "home",
        xdg_data_home=xdg_data_home,
        xdg_config_home=xdg_config_home,
    )

    result = use_case.execute(DoctorCommand(project_root=tmp_path))
    overlap = {check.name: check for check in result.checks}["layout_overlaps"]

    assert result.ok is True
    assert overlap.status == "warning"
    assert overlap.error == (
        "Legacy/shared overlaps detected: fact:fact-1, rule:rule-1, skill:review-helper"
    )
    assert "Shared content takes precedence" in (overlap.recovery_hint or "")


def _git_init(project_root: Path) -> None:
    _git(project_root, "init")


def _git(project_root: Path, *args: str) -> None:
    git = shutil.which("git") or "git"
    subprocess.run(  # noqa: S603
        [git, "-C", project_root.as_posix(), *args],
        check=True,
        capture_output=True,
        env=_sanitized_git_env(),
    )


def _append_jsonl(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _sanitized_git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG",
        "GIT_CONFIG_COUNT",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PREFIX",
        "GIT_WORK_TREE",
    ):
        env.pop(key, None)
    return env
