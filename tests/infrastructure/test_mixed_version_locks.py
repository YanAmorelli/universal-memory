"""Real released 0.6.x storage, OS processes and SIGSTOP; no mocked lock algorithms."""

import hashlib
import json
import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from universal_memory.infrastructure.process_lock import (
    LEGACY_LOCK_MTIME_NS,
    LockAcquisitionError,
    legacy_file_lock,
)

WORKER = Path(__file__).parents[1] / "support/mixed_version_worker.py"
SOURCE = Path(__file__).parents[2] / "src"
BLOCKED = 23
LEGACY_STALE_SECONDS = 10.3


def worker(root: Path, version: str, kind: str, label: str, pause: str = "no"):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SOURCE)
    return subprocess.Popen(  # noqa: S603
        [sys.executable, str(WORKER), version, kind, str(root), label, pause],
        cwd=root,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def await_held(process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    assert select.select([process.stdout], [], [], 15)[0], "writer did not acquire lock"
    line = process.stdout.readline().strip()
    assert line == "held", (line, process.communicate(timeout=5))


def records(root: Path, kind: str) -> list[str]:
    if kind == "facts":
        return [
            json.loads(x)["content"]
            for x in (root / ".umem/memory/facts.jsonl").read_text().splitlines()
        ]
    if kind == "audit":
        return [
            json.loads(x)["action"]
            for x in (root / ".umem/audit/events.jsonl").read_text().splitlines()
        ]
    return [
        x["action"]
        for x in json.loads((root / ".umem/snapshots/manifest.json").read_text())["snapshots"]
    ]


def test_frozen_modules_are_exact_released_code() -> None:
    expected = {
        "local_fact_repository": "a91ef7bcf732d1937c67571f0ad5e604da5866cd3fab8e1f5cb0306067a9b326",
        "local_audit_log_repository": (
            "cd44ff132337246ad7b656ec789a60181a95beb43d1b40488663194602c318d4"
        ),
        "local_snapshot_repository": (
            "63aae23fc7e3a7402914b8f0d143aeeb4c9643ac8957e3362977c137c162cb3f"
        ),
    }
    for name, digest in expected.items():
        path = WORKER.parents[1] / "fixtures/legacy_0_6_x" / (name + ".py.txt")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_real_legacy_and_updated_writers_do_not_steal_suspended_locks(tmp_path: Path) -> None:
    held = []
    contenders = []
    try:
        for kind in ("facts", "audit", "snapshots"):
            for first, second in (("new", "old"), ("old", "new")):
                root = tmp_path / (kind + "-" + first)
                root.mkdir()
                process = worker(root, first, kind, "first", "hold")
                held.append((process, root, kind, second))
        for process, *_ in held:
            await_held(process)
            os.kill(process.pid, signal.SIGSTOP)
        # A heartbeat cannot run while stopped. The *real* old expiry test must
        # still see the updated writer's lock as non-stale after ten seconds.
        time.sleep(LEGACY_STALE_SECONDS)
        for _, root, kind, second in held:
            contenders.append(worker(root, second, kind, "second"))
        for contender in contenders:
            out, err = contender.communicate(timeout=15)
            assert contender.returncode == BLOCKED, (out, err)
        for process, *_ in held:
            os.kill(process.pid, signal.SIGCONT)
            out, err = process.communicate("release\n", timeout=15)
            assert process.returncode == 0, (out, err)
        for _, root, kind, second in held:
            retry = worker(root, second, kind, "second")
            out, err = retry.communicate(timeout=15)
            assert retry.returncode == 0, (out, err)
            assert sorted(records(root, kind)) == ["first", "second"]
    finally:
        for process in [item[0] for item in held] + contenders:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)


@pytest.mark.parametrize("kind", ["facts", "audit", "snapshots"])
def test_updated_crash_releases_kernel_owner_and_recovers_known_lock(
    tmp_path: Path, kind: str
) -> None:
    process = worker(tmp_path, "new", kind, "never-committed", "hold")
    try:
        await_held(process)
    finally:
        process.kill()
        process.communicate(timeout=5)
    retry = worker(tmp_path, "new", kind, "recovered")
    out, err = retry.communicate(timeout=10)
    assert retry.returncode == 0, (out, err)
    assert records(tmp_path, kind) == ["recovered"]


def test_unknown_owner_is_not_evicted_by_age_or_pid_guessing(tmp_path: Path) -> None:
    path = tmp_path / "legacy.lock"
    path.write_text("old-uuid-with-no-pid")
    os.utime(path, (1, 1))
    with pytest.raises(LockAcquisitionError), legacy_file_lock(path, timeout=0.05):
        pytest.fail("evicted unknown old owner")
    assert path.read_text() == "old-uuid-with-no-pid"


def test_clock_horizon_fails_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(time, "time", lambda: LEGACY_LOCK_MTIME_NS / 1e9 + 1)
    with pytest.raises(LockAcquisitionError, match="clock"), legacy_file_lock(tmp_path / "lock"):
        pytest.fail("unsafe clock entered protected mutation")


def test_first_legacy_visibility_already_has_nonexpiring_mtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "legacy.lock"
    link = os.link
    seen = []

    def observe(source, destination):
        assert Path(source).stat().st_mtime_ns == LEGACY_LOCK_MTIME_NS
        assert not path.exists()
        seen.append(destination)
        link(source, destination)

    monkeypatch.setattr(os, "link", observe)
    with legacy_file_lock(path):
        assert path.stat().st_mtime_ns == LEGACY_LOCK_MTIME_NS
    assert seen == [path]
    assert not list(tmp_path.glob("*.pending"))
