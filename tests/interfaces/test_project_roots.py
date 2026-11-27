"""Real git and process regressions; every filesystem target is temporary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tomllib
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


@pytest.mark.parametrize("linked", [False, True])
def test_complete_nested_init_owns_memory_and_host(
    repository: tuple[Path, Path, Path], linked: bool
) -> None:
    root, _, outside = repository
    initialize(root)
    nested = (outside if linked else root) / "package"
    nested.mkdir()
    initialize(nested)
    child = nested / "src"
    child.mkdir()
    for location in (nested, child):
        roots = resolve_project_roots(location)
        assert roots.memory_root == nested
        assert roots.project_root == nested
        assert not roots.warnings
    result = cli(child, "remember", "nested fact", "--scope", "project", "--format", "json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "nested fact" in (nested / ".umem/memory/facts.jsonl").read_text()
    assert not (root / ".umem/memory/facts.jsonl").exists()


def test_incomplete_nested_init_falls_back_with_warning(
    repository: tuple[Path, Path, Path],
) -> None:
    root, _, outside = repository
    initialize(root)
    nested = outside / "package"
    nested.mkdir()
    initialize(nested)
    (nested / ".umem/benchmarks/retrieval-results.json").unlink()
    roots = resolve_project_roots(nested)
    assert roots.memory_root == root
    assert roots.project_root == outside
    assert "Incomplete nested project" in " ".join(roots.warnings)
    result = cli(nested, "remember", "root fact", "--scope", "project", "--format", "json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Incomplete nested project" in result.stderr
    assert "root fact" in (root / ".umem/memory/facts.jsonl").read_text()


def test_connect_config_and_snapshot_belong_to_memory_owner(
    repository: tuple[Path, Path, Path],
) -> None:
    root, _, outside = repository
    initialize(root)
    (outside / ".codex").mkdir()
    result = cli(outside, "connect", "--agent", "codex", "--format", "json")
    assert result.returncode == 0, result.stdout + result.stderr
    config = tomllib.loads((root / ".umem/config.toml").read_text())
    assert "codex" in config["runtimes"]["enabled"]
    assert not (outside / ".umem/config.toml").exists()
    assert (outside / "AGENTS.md").exists()
    local_manifest = outside / ".umem/snapshots/manifest.json"
    assert ".umem/config.toml" not in local_manifest.read_text()
    assert ".umem/config.toml" in (root / ".umem/snapshots/manifest.json").read_text()


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
        ["update", "--migrate", "--yes"],
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
    # Discover every composed command. New commands default to mutation until
    # explicitly reviewed as read-only; a new unguarded mutator fails this test.
    readers = {
        "audit_list",
        "snapshots_list",
        "rollback_preview",
        "status",
        "doctor",
        "facts_list",
        "validate_skill",
        "recommend_skills",
        "list_skills",
        "get_skill_detail",
        "update_check",
        "agent_connection_plan",
    }
    mutations = {
        name: handler
        for name, handler in handlers.items()
        if name.endswith("_command") and name.removesuffix("_command") not in readers
    }
    assert mutations
    for _name, handler in mutations.items():
        with pytest.raises(ProjectNotInitializedError):
            handler(SimpleNamespace(scope=FactScope.project))
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
    from dataclasses import fields  # noqa: PLC0415

    readers = {
        "status",
        "doctor",
        "list_facts",
        "list_audit_events",
        "list_snapshots",
        "validate_skill",
        "recommend_skills",
        "list_skills",
        "get_skill_detail",
    }
    initialization = {"initialize_project", "execute_agent_connections"}
    mutations = {
        field.name: getattr(captured[0], field.name)
        for field in fields(captured[0])
        if field.name not in readers | initialization
    }
    assert mutations
    for name, handler in mutations.items():
        assert callable(handler), name
        with pytest.raises(ProjectNotInitializedError):
            handler(SimpleNamespace(scope=FactScope.project))
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


@pytest.mark.parametrize("failure", ["missing", "timeout", "dubious"])
def test_git_discovery_failure_is_closed(repository, monkeypatch, failure):
    from universal_memory.infrastructure.config import project_roots  # noqa: PLC0415

    _, _, outside = repository
    original = project_roots.subprocess.run

    def broken(*args, **kwargs):
        if failure == "missing":
            raise FileNotFoundError("git unavailable")
        if failure == "timeout":
            raise subprocess.TimeoutExpired("git", 5)
        return subprocess.CompletedProcess(args[0], 128, "", "dubious ownership")

    monkeypatch.setattr(project_roots.subprocess, "run", broken)
    with pytest.raises(StorageError, match="Git"):
        resolve_project_roots(outside)
    monkeypatch.setattr(project_roots.subprocess, "run", original)
    assert not (outside / ".umem").exists()


def test_portable_git_discovery(repository, monkeypatch):
    from universal_memory.infrastructure.config import project_roots  # noqa: PLC0415

    root, _, outside = repository
    original = project_roots.subprocess.run

    def old_git(args, **kwargs):
        if "-z" in args or "--path-format=absolute" in args:
            return subprocess.CompletedProcess(args, 129, "", "unsupported option")
        return original(args, **kwargs)

    monkeypatch.setattr(project_roots.subprocess, "run", old_git)
    assert resolve_project_roots(outside).memory_root == root


def test_separate_git_linked_checkout_requires_unambiguous_owner(tmp_path, monkeypatch):
    main_root = tmp_path / "separate"
    main_root.mkdir()
    git(main_root, "init", "--separate-git-dir", str(tmp_path / "meta"))
    git(
        main_root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "--allow-empty",
        "-m",
        "base",
    )
    linked = tmp_path / "linked"
    git(main_root, "worktree", "add", "-b", "linked", str(linked))
    with pytest.raises(StorageError, match="UMEM_MEMORY_ROOT"):
        resolve_project_roots(linked)
    monkeypatch.setenv("UMEM_MEMORY_ROOT", str(main_root))
    roots = resolve_project_roots(linked)
    assert roots.memory_root == main_root
    assert roots.project_root == linked


def test_bare_container_preserves_host_root(tmp_path):
    container = tmp_path / "container"
    container.mkdir()
    bare = container / ".bare"
    bare.mkdir()
    git(bare, "init", "--bare")
    (container / ".git").write_text("gitdir: ./.bare\n")
    roots = resolve_project_roots(container)
    assert roots.memory_root == bare
    assert roots.project_root == container


def test_shared_memory_symlink_is_not_orphan(repository):
    root, _, outside = repository
    initialize(root)
    cli(root, "remember", "real memory", "--scope", "project", "--format", "json")
    (outside / ".umem").symlink_to(root / ".umem", target_is_directory=True)
    assert not resolve_project_roots(outside).warnings


@pytest.mark.anyio
@pytest.mark.parametrize("interface", ["cli", "mcp"])
async def test_rollback_does_not_touch_orphan_memory(repository, monkeypatch, interface):
    root, _, outside = repository
    initialize(root)
    for content in ("shared first", "shared second"):
        result = cli(root, "remember", content, "--scope", "project", "--format", "json")
        assert result.returncode == 0, result.stdout
    initialize(outside)
    monkeypatch.setenv("UMEM_MEMORY_ROOT", str(outside))
    for content in ("local first", "local second", "local third"):
        result = cli(outside, "remember", content, "--scope", "project", "--format", "json")
        assert result.returncode == 0, result.stdout
    monkeypatch.delenv("UMEM_MEMORY_ROOT")
    local = outside / ".umem/memory/facts.jsonl"
    before = local.read_bytes()
    if interface == "cli":
        result = cli(outside, "rollback", "--scope", "project", "--yes", "--format", "json")
        assert result.returncode == 0, result.stdout
    else:
        result = await build_server(outside).call_tool(
            "rollback_scope", {"scope": "project", "confirm": True}
        )
        assert result.structured_content is not None
        assert result.structured_content["ok"], result.structured_content
    assert local.read_bytes() == before
    assert len((root / ".umem/memory/facts.jsonl").read_text().splitlines()) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("interface", ["cli", "mcp"])
async def test_doctor_checks_shared_layout(repository, interface):
    root, _, outside = repository
    initialize(root)
    if interface == "cli":
        response = cli(outside, "doctor", "--format", "json")
        payload = json.loads(response.stdout)
    else:
        response = await build_server(outside).call_tool("doctor", {})
        payload = response.structured_content

    def find(value):
        if isinstance(value, dict):
            if value.get("name") == "project_layout":
                return value
            for item in value.values():
                found = find(item)
                if found:
                    return found
        if isinstance(value, list):
            for item in value:
                found = find(item)
                if found:
                    return found
        return None

    check = find(payload)
    assert check is not None, payload
    assert check["status"] == "success", check


def test_existing_project_without_new_optional_layout_can_write(repository):
    root, _, outside = repository
    initialize(root)
    (root / ".umem/benchmarks/retrieval-results.json").unlink()
    (root / ".umem/benchmarks").rmdir()
    result = cli(
        outside, "remember", "old initialized project", "--scope", "project", "--format", "json"
    )
    assert result.returncode == 0, result.stdout
    assert not (outside / ".umem").exists()


@pytest.mark.anyio
@pytest.mark.parametrize("interface", ["cli", "mcp"])
@pytest.mark.parametrize("bare", [False, True])
async def test_native_skill_sync_uses_active_worktree(repository, tmp_path, interface, bare):
    root, _, outside = repository
    if bare:
        root = tmp_path / "bare.git"
        root.mkdir()
        git(root, "init", "--bare")
        outside = tmp_path / "bare-checkout"
        git(root, "worktree", "add", "--orphan", "-b", "bare-branch", str(outside))
    initialize(root)
    created = cli(
        root,
        "skills",
        "create",
        "--name",
        "worktree skill",
        "--description",
        "A useful worktree skill",
        "--format",
        "json",
    )
    assert created.returncode == 0, created.stdout
    if interface == "cli":
        synced = cli(outside, "skills", "sync", "--target", "claude_code", "--format", "json")
        assert synced.returncode == 0, synced.stdout
    else:
        synced = await build_server(outside).call_tool("sync_skills", {"targets": ["claude_code"]})
        assert synced.structured_content is not None
        assert synced.structured_content["ok"], synced.structured_content
    assert list((outside / ".claude/skills").rglob("SKILL.md"))
    assert not (root / ".claude").exists()


@pytest.mark.anyio
@pytest.mark.parametrize("interface", ["cli", "mcp"])
async def test_unknown_lock_error_is_actionable(repository, interface):
    root, _, outside = repository
    initialize(root)
    lock = root / ".umem/memory/facts.jsonl.lock"
    lock.write_text("unknown-owner")
    os.utime(lock, (time.time() - 60, time.time() - 60))
    if interface == "cli":
        response = cli(outside, "remember", "blocked", "--scope", "project", "--format", "json")
        error = json.loads(response.stdout)["error"]
    else:
        response = await build_server(outside).call_tool(
            "remember_fact", {"content": "blocked", "scope": "project"}
        )
        assert response.structured_content is not None
        error = response.structured_content["error"]["data"]
    assert error["lock_path"] == str(lock)
    assert error["lock_age_seconds"] >= 60
    assert "Stop all" in error["recovery_hint"]
    assert ".guard" in error["recovery_hint"]
    assert lock.read_text() == "unknown-owner"


def test_lock_filesystem_failure_is_typed(tmp_path, monkeypatch):
    from universal_memory.infrastructure import process_lock as locks  # noqa: PLC0415

    def denied(*args, **kwargs):
        raise PermissionError("no hard links")

    monkeypatch.setattr(locks.os, "link", denied)
    with pytest.raises(StorageError, match="Failed to acquire lock"):
        with locks.legacy_file_lock(tmp_path / "test.lock"):
            pytest.fail("lock acquired")
    assert not (tmp_path / "test.lock").exists()


def test_environment_isolated_before_collection(tmp_path):
    import shutil  # noqa: PLC0415

    collection = tmp_path / "collection"
    collection.mkdir()
    shutil.copyfile(Path(SOURCE).parent / "tests/conftest.py", collection / "conftest.py")
    (collection / "test_probe.py").write_text(
        "import os\n"
        "assert not os.environ.get('GIT_DIR')\n"
        "assert not os.environ.get('GIT_CONFIG_PARAMETERS')\n"
        "assert 'collection-user-' in os.environ['HOME']\n"
        "def test_probe(): pass\n"
    )
    environment = dict(os.environ, GIT_DIR="/missing/repository", GIT_CONFIG_PARAMETERS="bad")
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(collection)],
        cwd=collection,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_submodule_linked_checkout_uses_submodule_main(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init")
    git(
        source,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "--allow-empty",
        "-m",
        "base",
    )
    parent = tmp_path / "super"
    parent.mkdir()
    git(parent, "init")
    git(parent, "-c", "protocol.file.allow=always", "submodule", "add", str(source), "sub")
    main_root = parent / "sub"
    linked = tmp_path / "sub-linked"
    git(main_root, "worktree", "add", "-b", "sub-linked", str(linked))
    roots = resolve_project_roots(linked)
    assert roots.project_root == linked
    assert roots.memory_root == main_root


@pytest.mark.anyio
async def test_mcp_old_initialized_layout_without_benchmarks(repository):
    root, _, outside = repository
    (root / ".umem/memory").mkdir(parents=True)
    (root / ".umem/config.toml").write_text("[hosts]\nenabled = []\n")
    result = await build_server(outside).call_tool(
        "remember_fact", {"content": "old initialized project", "scope": "project"}
    )
    assert result.structured_content is not None
    assert result.structured_content["ok"], result.structured_content
    assert not (outside / ".umem").exists()


@pytest.mark.parametrize("config", ["", "[unrelated]\nvalue = 1\n", "invalid toml!"])
def test_partial_configuration_does_not_initialize_project(repository, config):
    root, _, outside = repository
    (root / ".umem/memory").mkdir(parents=True)
    (root / ".umem/config.toml").write_text(config)
    before = {
        p.relative_to(root): p.read_bytes() for p in (root / ".umem").rglob("*") if p.is_file()
    }
    result = cli(outside, "remember", "must not write", "--scope", "project", "--format", "json")
    assert result.returncode != 0
    assert json.loads(result.stdout)["error"]["code"] == "project_not_initialized"
    after = {
        p.relative_to(root): p.read_bytes() for p in (root / ".umem").rglob("*") if p.is_file()
    }
    assert before == after


def test_worktree_rollback_does_not_restore_main_host_files(repository):
    root, _, outside = repository
    initialize(root)
    for content in ("shared first", "shared second"):
        result = cli(root, "remember", content, "--scope", "project", "--format", "json")
        assert result.returncode == 0, result.stdout
    (root / "CLAUDE.md").write_text("# Original main instructions\n")
    setup = cli(root, "host", "setup", "claude_code", "--yes", "--format", "json")
    assert setup.returncode == 0, setup.stdout
    main_host = (root / "CLAUDE.md").read_bytes()
    result = cli(outside, "rollback", "--scope", "project", "--yes", "--format", "json")
    assert result.returncode == 0, result.stdout
    assert (root / "CLAUDE.md").read_bytes() == main_host
    assert len((root / ".umem/memory/facts.jsonl").read_text().splitlines()) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("interface", ["cli", "mcp"])
async def test_doctor_host_check_uses_local_host_configuration(repository, interface):
    root, _, outside = repository
    initialize(root)
    (root / ".umem/config.toml").write_text(
        '[project]\nname = "test"\n[hosts]\nenabled = []\n[runtimes]\nenabled = []\n'
    )
    (outside / ".umem").mkdir()
    (outside / ".umem/config.toml").write_text('[hosts]\nenabled = ["claude_code"]\n')
    if interface == "cli":
        result = cli(outside, "doctor", "--format", "json")
        payload = json.loads(result.stdout)
    else:
        result = await build_server(outside).call_tool("doctor", {})
        payload = result.structured_content
    assert payload is not None
    check = next(item for item in payload["data"]["checks"] if item["name"] == "hosts_integration")
    assert check["status"] == "failed", check
    assert "claude_code" in check["error"]


def test_cli_git_failure_returns_structured_error_without_writing(repository, monkeypatch):
    root, _, outside = repository
    initialize(outside)
    before = {p.relative_to(outside): p.read_bytes() for p in outside.rglob("*") if p.is_file()}
    monkeypatch.setenv("PATH", "")
    result = cli(outside, "remember", "no fallback", "--scope", "project", "--format", "json")
    assert result.returncode == 1
    assert json.loads(result.stdout)["error"]["code"] == "storage_error"
    assert "Git" in json.loads(result.stdout)["error"]["detail"]
    with pytest.raises(StorageError, match="Git"):
        build_server(outside)
    after = {p.relative_to(outside): p.read_bytes() for p in outside.rglob("*") if p.is_file()}
    assert before == after
    assert not (root / ".umem").exists()


def test_git_paths_keep_quotes_and_trailing_whitespace(repository, tmp_path):
    root, _, _ = repository
    linked = tmp_path / 'quoted "worktree" '
    git(root, "worktree", "add", "-b", "quoted", str(linked))
    roots = resolve_project_roots(linked)
    assert roots.project_root == linked
    assert roots.memory_root == root
