"""Real git and process regressions; every filesystem target is temporary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from universal_memory.application.onboarding.setup_project import setup_project
from universal_memory.bootstrap.cli import main
from universal_memory.bootstrap.mcp import build_server
from universal_memory.bootstrap.project_memory import ProjectNotInitializedError
from universal_memory.domain import SnapshotFailedError, StorageError
from universal_memory.domain.entities import FactScope
from universal_memory.infrastructure.config import LocalConfigValidationPort, LocalProjectLayoutPort
from universal_memory.infrastructure.config.project_roots import resolve_project_roots
from universal_memory.infrastructure.security import (
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)
from universal_memory.infrastructure.storage import LocalFactRepository
from universal_memory.interfaces.cli import init_command

# Numeric values below express the timeout contract and parallel process count.
# ruff: noqa: PLR2004

SOURCE = str(Path(__file__).resolve().parents[2] / "src")


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        target = tmp_path / name.lower()
        target.mkdir()
        monkeypatch.setenv(name, str(target))
    monkeypatch.delenv("UMEM_MEMORY_ROOT", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("PYTHONPATH", SOURCE)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.chdir(tmp_path)


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def initialize(root: Path) -> None:
    setup_project(
        root,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "main"
    root.mkdir()
    git(root, "init")
    (root / ".gitignore").write_text(".umem/\n.umem_global_test_home/\nwt/\n")
    git(root, "add", ".gitignore")
    git(root, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "base")
    inside, outside = root / "wt" / "inside", tmp_path / "outside"
    git(root, "worktree", "add", "-b", "inside", str(inside))
    git(root, "worktree", "add", "-b", "outside", str(outside))
    return root, inside, outside


def cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.pop("PYTEST_CURRENT_TEST", None)
    return subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "import sys; from universal_memory.bootstrap.cli import main; sys.exit(main())",
            *args,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=environment,
    )


def test_main_subfolder_and_both_worktrees_share_owner(repository: tuple[Path, Path, Path]) -> None:
    root, inside, outside = repository
    initialize(root)
    for checkout in (root, inside, outside):
        child = checkout / "subfolder"
        child.mkdir()
        for location in (checkout, child):
            roots = resolve_project_roots(location)
            assert roots.project_root == checkout
            assert roots.memory_root == root
            result = cli(location, "bootstrap", "--format", "json")
            assert result.returncode == 0, result.stdout + result.stderr
    assert not (inside / ".umem").exists()
    assert not (outside / ".umem").exists()


@pytest.mark.parametrize("complete", [False, True])
def test_local_memory_is_preserved_and_warned(
    repository: tuple[Path, Path, Path],
    complete: bool,
) -> None:
    root, _, outside = repository
    initialize(root)
    if complete:
        initialize(outside)
    local = outside / ".umem" / "memory" / "facts.jsonl"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text("orphaned data\n")
    roots = resolve_project_roots(outside)
    assert roots.memory_root == root
    assert "orphaned facts" in " ".join(roots.warnings)
    result = cli(outside, "context", "--format", "json")
    assert result.returncode == 0, result.stdout
    assert "orphaned facts" in result.stderr
    assert local.read_text() == "orphaned data\n"


def test_explicit_override_uses_local_checkout(
    repository: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _, outside = repository
    initialize(outside)
    monkeypatch.setenv("UMEM_MEMORY_ROOT", str(outside))
    assert resolve_project_roots(root).memory_root == outside
    result = cli(root, "remember", "override memory", "--scope", "project", "--format", "json")
    assert result.returncode == 0, result.stdout
    assert "override memory" in (outside / ".umem/memory/facts.jsonl").read_text()
    assert not (root / ".umem").exists()


def test_bare_root_and_linked_checkout(tmp_path: Path) -> None:
    bare = tmp_path / "bare.git"
    bare.mkdir()
    git(bare, "init", "--bare")
    checkout = tmp_path / "checkout"
    git(bare, "worktree", "add", "--orphan", "-b", "branch", str(checkout))
    assert resolve_project_roots(bare).memory_root == bare
    assert resolve_project_roots(checkout).memory_root == bare
    initialize(bare)
    result = cli(checkout, "remember", "bare memory", "--scope", "project", "--format", "json")
    assert result.returncode == 0, result.stdout
    assert (bare / ".umem/memory/facts.jsonl").exists()
    assert not (checkout / ".umem").exists()


def test_non_git_project_and_subfolder(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    assert resolve_project_roots(root).memory_root == root
    initialize(root)
    child = root / "child"
    child.mkdir()
    assert resolve_project_roots(child).memory_root == root


def test_separate_git_directory_does_not_become_memory_owner(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    root.mkdir()
    git(root, "init", "--separate-git-dir", str(tmp_path / "metadata"))
    roots = resolve_project_roots(root)
    assert roots.project_root == root
    assert roots.memory_root == root


def test_hook_git_environment_cannot_redirect_project_resolution(
    repository: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _, outside = repository
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    git(unrelated, "init")
    monkeypatch.setenv("GIT_DIR", str(unrelated / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(unrelated))
    monkeypatch.setenv("GIT_INDEX_FILE", str(unrelated / ".git/index"))
    roots = resolve_project_roots(outside)
    assert roots.project_root == outside
    assert roots.memory_root == root


def test_complete_worktree_memory_does_not_implicitly_initialize_main(
    repository: tuple[Path, Path, Path],
) -> None:
    root, _, outside = repository
    initialize(outside)
    before = (outside / ".umem/config.toml").read_bytes()
    result = cli(outside, "remember", "local orphan", "--scope", "project", "--format", "json")
    assert result.returncode == 1
    assert json.loads(result.stdout)["error"]["memory_root"] == str(root)
    assert "orphaned facts" in result.stderr
    assert (outside / ".umem/config.toml").read_bytes() == before
    assert not (root / ".umem").exists()


@pytest.mark.parametrize(
    "args",
    [
        ["remember", "no implicit storage", "--scope", "project"],
        ["context"],
        ["bootstrap"],
        ["facts", "purge", "--scope", "project", "--yes"],
        ["host", "setup", "claude_code", "--yes"],
        ["skills", "create", "--name", "uninitialized", "--description", "A test skill"],
    ],
)
def test_noninteractive_uninitialized_writes_nothing(
    repository: tuple[Path, Path, Path],
    args: list[str],
) -> None:
    root, _, outside = repository
    result = cli(outside, *args, "--format", "json")
    assert result.returncode != 0
    error = json.loads(result.stdout)["error"]
    assert error["code"] == "project_not_initialized", result.stdout
    assert error["memory_root"] == str(root)
    assert "Ask the person" in error["recovery_hint"]
    assert not (root / ".umem").exists()
    assert not (outside / ".umem").exists()


@pytest.mark.parametrize("answer,expected", [(False, 1), (True, 0)])
def test_interactive_initialization_requires_yes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    answer: bool,
    expected: int,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    prompts: list[str] = []

    def confirm(prompt: str, default: bool = False) -> bool:
        assert not default
        prompts.append(prompt)
        return answer

    monkeypatch.setattr(init_command, "_confirm", confirm)
    assert main(["remember", "interactive memory", "--scope", "project"]) == expected
    assert len(prompts) == 1
    assert (tmp_path / ".umem").exists() == answer


def test_global_commands_do_not_initialize_project(tmp_path: Path) -> None:
    for args in (
        ["remember", "global preference", "--scope", "global"],
        ["context", "--scope", "global"],
    ):
        result = cli(tmp_path, *args, "--format", "json")
        assert result.returncode == 0, result.stdout
    assert not (tmp_path / ".umem").exists()
    assert (Path(os.environ["HOME"]) / ".local/share/umem/memory/facts.jsonl").exists()


def test_json_does_not_prompt_even_with_tty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(init_command, "_confirm", lambda *args, **kwargs: pytest.fail("prompted"))
    assert main(["remember", "json memory", "--scope", "project", "--format", "json"]) == 1
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "project_not_initialized"
    assert not (tmp_path / ".umem").exists()


def test_non_tty_initialization_error_is_structured_without_format(tmp_path: Path) -> None:
    result = cli(tmp_path, "remember", "no implicit project", "--scope", "project")
    assert result.returncode == 1
    assert json.loads(result.stdout)["error"]["code"] == "project_not_initialized"
    assert not (tmp_path / ".umem").exists()


def test_all_cli_project_mutators_are_guarded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from universal_memory.bootstrap import cli as cli_bootstrap  # noqa: PLC0415

    handlers = {}

    def capture(**kwargs):
        handlers.update(kwargs)
        return lambda argv: 0

    monkeypatch.setattr(cli_bootstrap, "build_main", capture)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert main([]) == 0
    mutations = (
        "bootstrap",
        "context",
        "remember",
        "facts_purge",
        "facts_hygiene",
        "rollback",
        "host_setup",
        "host_check",
        "host_sync",
        "propose_skill",
        "track_latent_skill",
        "generate_skill",
        "create_skill",
        "create_skill_draft",
        "publish_skill",
        "share_skill",
        "sync_skills",
        "promote_skill_recommendation",
        "import_skill",
        "adopt_skill",
        "update_canonical_skill",
        "rename_skill",
        "cleanup_skill",
        "repair_skills",
        "activate_skill",
        "deactivate_skill",
        "update_skill",
        "update_managed_skills",
        "update_migrate",
        "update_benchmarks",
        "layout_migrate",
    )
    for mutation in mutations:
        with pytest.raises(ProjectNotInitializedError):
            handlers[mutation + "_command"](SimpleNamespace(scope=FactScope.project))
    assert not (tmp_path / ".umem").exists()


def test_all_mcp_project_mutators_are_guarded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from universal_memory.interfaces.mcp import server as mcp_server  # noqa: PLC0415

    captured = []

    def capture(server, use_cases, **kwargs):
        captured.append(use_cases)
        return server

    monkeypatch.setattr(mcp_server, "configure_server", capture)
    # build_server imports the public re-export, so patch it as well.
    monkeypatch.setattr("universal_memory.interfaces.mcp.configure_server", capture)
    build_server(tmp_path)
    mutations = (
        "bootstrap",
        "context",
        "remember",
        "purge_fact",
        "rollback_scope",
        "host_setup",
        "host_check",
        "sync_instructions",
        "propose_skill",
        "track_latent_skill",
        "generate_skill",
        "create_skill",
        "create_skill_draft",
        "publish_skill",
        "share_skill",
        "sync_skills",
        "promote_skill_recommendation",
        "import_skill",
        "adopt_skill",
        "update_canonical_skill",
        "rename_skill",
        "cleanup_skill",
        "repair_skills",
        "activate_skill",
        "deactivate_skill",
        "update_skill",
        "migrate_project_layout",
    )
    for mutation in mutations:
        with pytest.raises(ProjectNotInitializedError):
            getattr(captured[0], mutation)(SimpleNamespace(scope=FactScope.project))
    assert not (tmp_path / ".umem").exists()


def test_host_instructions_follow_worktree(repository: tuple[Path, Path, Path]) -> None:
    root, _, outside = repository
    initialize(root)
    (outside / "CLAUDE.md").write_text("# Existing local instructions\n")
    result = cli(outside, "host", "setup", "claude_code", "--yes", "--format", "json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (outside / "CLAUDE.md").is_file()
    assert not (root / "CLAUDE.md").exists()
    snapshots = cli(outside, "snapshots", "list", "--format", "json")
    assert snapshots.returncode == 0, snapshots.stdout
    assert "CLAUDE.md" in snapshots.stdout
    rollback = cli(outside, "rollback", "--scope", "project", "--yes", "--format", "json")
    assert rollback.returncode == 0, rollback.stdout
    assert (outside / "CLAUDE.md").read_text() == "# Existing local instructions\n"
    result = cli(outside, "host", "sync", "--apply", "--yes", "--format", "json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (root / "CLAUDE.md").exists()
    assert (outside / "CLAUDE.md").is_file()


@pytest.mark.parametrize("kind", ["facts", "audit", "snapshots"])
def test_unknown_legacy_lock_is_not_recovered_by_age(tmp_path: Path, kind: str) -> None:
    paths = {
        "facts": "memory/facts.jsonl.lock",
        "audit": "audit/events.jsonl.lock",
        "snapshots": "snapshots/manifest.json.lock",
    }
    path = tmp_path / ".umem" / paths[kind]
    path.parent.mkdir(parents=True)
    path.write_text("abandoned")
    os.utime(path, (time.time() - 11, time.time() - 11))
    if kind == "facts":
        lock = LocalFactRepository(project_root=tmp_path)._lock(FactScope.project)
    elif kind == "audit":
        lock = LocalAuditLogRepository(project_root=tmp_path, data_root=tmp_path / ".umem")._lock()
    else:
        lock = LocalSnapshotRepository(project_root=tmp_path, data_root=tmp_path / ".umem")._lock()
    with pytest.raises((StorageError, SnapshotFailedError)), lock:
        pytest.fail("unknown legacy lock was evicted")
    assert path.read_text() == "abandoned"


def test_remember_survives_worktree_remove(repository: tuple[Path, Path, Path]) -> None:
    root, _, outside = repository
    initialize(root)
    result = cli(outside, "remember", "durable memory", "--scope", "project", "--format", "json")
    assert result.returncode == 0, result.stdout
    git(root, "worktree", "remove", str(outside))
    result = cli(root, "facts", "list", "--format", "json")
    assert result.returncode == 0
    assert "durable memory" in result.stdout


def test_concurrent_remember_across_worktrees(repository: tuple[Path, Path, Path]) -> None:
    root, inside, outside = repository
    initialize(root)
    processes = [
        subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-c",
                "import sys; from universal_memory.bootstrap.cli import main; sys.exit(main())",
                "remember",
                f"parallel fact {index}",
                "--scope",
                "project",
                "--format",
                "json",
            ],
            cwd=(root, inside, outside)[index % 3],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(12)
    ]
    for process in processes:
        out, err = process.communicate(timeout=30)
        assert process.returncode == 0, out + err
    facts = [
        json.loads(line) for line in (root / ".umem/memory/facts.jsonl").read_text().splitlines()
    ]
    assert len(facts) == 12
    assert len({fact["id"] for fact in facts}) == 12
    events = [
        json.loads(line) for line in (root / ".umem/audit/events.jsonl").read_text().splitlines()
    ]
    assert len([event for event in events if event["action"] == "write_fact"]) == 12
    manifest = json.loads((root / ".umem/snapshots/manifest.json").read_text())
    assert manifest


@pytest.mark.parametrize("kind", ["facts", "audit", "snapshots"])
def test_live_lock_over_ten_seconds_is_not_broken(tmp_path: Path, kind: str) -> None:
    code = """
import sys,time
from pathlib import Path
from universal_memory.infrastructure.security import (
 LocalAuditLogRepository, LocalSnapshotRepository,
)
from universal_memory.infrastructure.storage import LocalFactRepository
from universal_memory.domain.entities import FactScope
root=Path(sys.argv[1]); kind=sys.argv[2]
repo={
 "facts":LocalFactRepository(project_root=root),
 "audit":LocalAuditLogRepository(project_root=root,data_root=root/".umem"),
 "snapshots":LocalSnapshotRepository(project_root=root,data_root=root/".umem"),
}[kind]
lock=repo._lock(FactScope.project) if kind=="facts" else repo._lock()
with lock:
 print("locked",flush=True)
 sys.stdin.readline()
"""
    child = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", code, str(tmp_path), kind],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert child.stdout is not None
    try:
        assert child.stdout.readline().strip() == "locked"
        paths = {
            "facts": "memory/facts.jsonl.lock",
            "audit": "audit/events.jsonl.lock",
            "snapshots": "snapshots/manifest.json.lock",
        }
        lock_path = tmp_path / ".umem" / paths[kind]
        # Aging the lock is equivalent to a slow owner, without a 10s test sleep.
        os.utime(lock_path, (time.time() - 11, time.time() - 11))
        if kind == "facts":
            lock = LocalFactRepository(project_root=tmp_path)._lock(FactScope.project)
        elif kind == "audit":
            lock = LocalAuditLogRepository(
                project_root=tmp_path, data_root=tmp_path / ".umem", lock_acquire_timeout_seconds=2
            )._lock()
        else:
            lock = LocalSnapshotRepository(
                project_root=tmp_path, data_root=tmp_path / ".umem"
            )._lock()
        started = time.monotonic()
        with (
            pytest.raises((StorageError, SnapshotFailedError), match="Failed to acquire lock"),
            lock,
        ):
            pytest.fail("live lock was stolen")
        assert 1.8 <= time.monotonic() - started < 4
        assert lock_path.exists()
    finally:
        child.communicate("release\n", timeout=10)
    assert child.returncode == 0


@pytest.mark.anyio
@pytest.mark.parametrize("location", ["main", "inside", "outside", "subfolder"])
async def test_mcp_cli_parity(repository: tuple[Path, Path, Path], location: str) -> None:
    root, inside, outside = repository
    child = outside / "subfolder"
    child.mkdir()
    selected = {"main": root, "inside": inside, "outside": outside, "subfolder": child}[location]
    server = build_server(selected)
    before = cli(selected, "context", "--format", "json")
    response = await server.call_tool("context", {})
    payload = response.structured_content
    assert payload is not None
    assert (
        payload["error"]["data"]["memory_root"] == json.loads(before.stdout)["error"]["memory_root"]
    )
    assert not (root / ".umem").exists()
    initialize(root)
    response = await server.call_tool(
        "remember_fact", {"content": "MCP shared fact", "scope": "project"}
    )
    assert response.structured_content is not None
    assert response.structured_content["ok"], response.structured_content
    after = cli(root, "facts", "list", "--format", "json")
    assert "MCP shared fact" in after.stdout
    response = await server.call_tool("bootstrap", {})
    assert response.structured_content is not None
    assert response.structured_content["ok"], response.structured_content
    assert not (outside / ".umem").exists()
