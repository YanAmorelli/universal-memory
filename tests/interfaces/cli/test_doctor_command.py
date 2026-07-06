from __future__ import annotations

import json
from pathlib import Path

import pytest

from universal_memory.application.diagnostics import DoctorCheck, DoctorCommand, DoctorResult
from universal_memory.interfaces.cli import main as cli_main


def doctor_result(*, ok: bool = True) -> DoctorResult:
    checks = [
        DoctorCheck(
            name="python_version",
            status="success",
            detail="Python 3.12.13",
        )
    ]
    if not ok:
        checks.append(
            DoctorCheck(
                name="project_layout",
                status="failed",
                error="Missing path: .umem/audit/events.jsonl",
                recovery_hint="Run umem init --yes to rebuild missing default paths.",
            )
        )
    return DoctorResult(checks=checks)


def doctor_warning_result() -> DoctorResult:
    return DoctorResult(
        checks=[
            DoctorCheck(
                name="project_layout_mode",
                status="success",
                detail="Shared project layout is active.",
            ),
            DoctorCheck(
                name="shared_root_visibility",
                status="warning",
                error="Shared paths are ignored: umem/",
                recovery_hint="Update ignore rules so umem/ shared content is reviewable.",
            ),
            DoctorCheck(
                name="operational_root_privacy",
                status="warning",
                error="Operational paths are tracked: .umem/audit/events.jsonl",
                recovery_hint="Remove operational .umem paths from Git tracking.",
            ),
            DoctorCheck(
                name="layout_overlaps",
                status="warning",
                error="Legacy/shared overlaps detected: fact:fact-1",
                recovery_hint=(
                    "Shared content takes precedence; remove or migrate shadowed legacy records."
                ),
            ),
        ]
    )


def test_doctor_json_outputs_environment_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    received: list[DoctorCommand] = []

    def command(cmd: DoctorCommand) -> DoctorResult:
        received.append(cmd)
        return doctor_result()

    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(["doctor", "--format", "json"], doctor_command=command)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert received == [DoctorCommand(project_root=tmp_path)]
    assert payload == {
        "ok": True,
        "operation": "doctor",
        "scope": "environment",
        "warnings": [],
        "data": {
            "checks": [
                {
                    "name": "python_version",
                    "status": "success",
                    "detail": "Python 3.12.13",
                }
            ],
            "summary": {"total_checks": 1, "passed": 1, "warnings": 0, "failed": 0},
        },
    }


def test_doctor_json_exits_nonzero_when_any_check_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["doctor", "--format", "json"],
        doctor_command=lambda _cmd: doctor_result(ok=False),
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["data"]["summary"] == {
        "total_checks": 2,
        "passed": 1,
        "warnings": 0,
        "failed": 1,
    }
    assert payload["data"]["checks"][1]["recovery_hint"] == (
        "Run umem init --yes to rebuild missing default paths."
    )


def test_doctor_human_output_summarizes_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(["doctor"], doctor_command=lambda _cmd: doctor_result(ok=False))

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "universal-memory Doctor - Health Report" in captured.out
    assert "[OK] Python Version - Python 3.12.13" in captured.out
    assert "[FAIL] Project Layout" in captured.out
    assert "Final status: 1 failure(s), 0 warning(s) found." in captured.out


def test_doctor_json_outputs_layout_warning_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(
        ["doctor", "--format", "json"],
        doctor_command=lambda _cmd: doctor_warning_result(),
    )

    payload = json.loads(capsys.readouterr().out)
    checks = {check["name"]: check for check in payload["data"]["checks"]}
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["summary"] == {
        "total_checks": 4,
        "passed": 1,
        "warnings": 3,
        "failed": 0,
    }
    assert checks["project_layout_mode"]["status"] == "success"
    assert checks["shared_root_visibility"]["status"] == "warning"
    assert checks["operational_root_privacy"]["status"] == "warning"
    assert checks["layout_overlaps"]["status"] == "warning"


def test_doctor_human_output_renders_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main(["doctor"], doctor_command=lambda _cmd: doctor_warning_result())

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[OK] Project Layout Mode - Shared project layout is active." in captured.out
    assert "[WARN] Shared Root Visibility" in captured.out
    assert "Shared paths are ignored: umem/" in captured.out
    assert "[WARN] Operational Root Privacy" in captured.out
    assert "[WARN] Layout Overlaps" in captured.out
    assert "Final status: 3 warning(s), no failure(s) found." in captured.out
