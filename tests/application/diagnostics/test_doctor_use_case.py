from pathlib import Path

from universal_memory.application.diagnostics import DoctorCommand, DoctorUseCase
from universal_memory.application.host import ConfigureHostCommand, ConfigureHostResult
from universal_memory.infrastructure.config.project_layout import ensure_project_layout


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
    assert result.summary.to_payload() == {"total_checks": 5, "passed": 5, "failed": 0}


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
