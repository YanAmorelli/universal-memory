"""Resolve code and memory ownership without creating any files.

UMEM_MEMORY_ROOT is an explicit checkout-directory override, not a .umem path.
Bare repositories own memory inside the bare repository directory itself.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectRoots:
    project_root: Path
    memory_root: Path
    warnings: tuple[str, ...] = ()


def _git(cwd: Path, *args: str) -> str | None:
    environment = dict(os.environ)
    # Git hooks export repository-local variables. They must not override the
    # directory being resolved (or redirect a child process into another repo).
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_PREFIX",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE",
    ):
        environment.pop(key, None)
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(cwd), *args],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def resolve_project_roots(
    cwd: Path | None = None,
    *,
    memory_root: Path | None = None,
) -> ProjectRoots:
    start = (cwd or Path.cwd()).resolve()
    top = _git(start, "rev-parse", "--show-toplevel")
    common = _git(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    project = Path(top).resolve() if top else start
    if common:
        common_path = Path(common).resolve()
        # Git reports the main checkout first for linked worktrees, including a
        # bare root. A main checkout's .git may itself reference separate metadata.
        worktrees = _git(start, "worktree", "list", "--porcelain", "-z")
        first = worktrees.split("\0", 1)[0] if worktrees else ""
        entry = project / ".git"
        checkout_git_dir = entry.resolve()
        if entry.is_file():
            content = entry.read_text().strip()
            if content.startswith("gitdir: "):
                checkout_git_dir = (project / content.removeprefix("gitdir: ")).resolve()
        owner = (
            project
            if top and checkout_git_dir == common_path
            else (
                Path(first.removeprefix("worktree ")).resolve()
                if first.startswith("worktree ")
                else common_path.parent
            )
        )
        if not top:
            project = owner
    else:
        # Outside git, an existing project can still be addressed from a subfolder.
        owner = next(
            (path for path in (start, *start.parents) if (path / ".umem").is_dir()),
            start,
        )
        project = owner
    override = memory_root or os.environ.get("UMEM_MEMORY_ROOT")
    if override:
        owner = Path(override).expanduser().resolve()
    warnings: list[str] = []
    ignored_roots = [start]
    if project != start:
        ignored_roots.extend(path for path in start.parents if path.is_relative_to(project))
    for ignored in dict.fromkeys(ignored_roots):
        if ignored == owner:
            continue
        for relative in (".umem/memory", "umem/memory"):
            local = ignored / relative
            if local.is_dir() and any(
                path.is_file() and path.stat().st_size for path in local.rglob("*")
            ):
                warnings.append(
                    f"Local memory at {local} is not used; shared memory root is {owner}. "
                    "Files were preserved. Review orphaned facts or explicitly set "
                    "UMEM_MEMORY_ROOT."
                )
    return ProjectRoots(project, owner, tuple(warnings))
