"""Resolve checkout and memory ownership without guessing or writing files."""

from __future__ import annotations

import ast
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from universal_memory.domain import StorageError
from universal_memory.infrastructure.config.project_layout import (
    has_project_identity,
    is_project_initialized,
    resolve_project_layout,
)


class ProjectRootResolutionError(StorageError):
    """Git ownership could not be established safely."""


@dataclass(frozen=True)
class ProjectRoots:
    project_root: Path
    memory_root: Path
    warnings: tuple[str, ...] = ()


def _git(cwd: Path, *args: str, optional: bool = False) -> str | None:
    # Hooks and config injection must not redirect discovery to another repository.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(cwd), *args],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ProjectRootResolutionError(
            "Git discovery failed. Hint: restore Git access and retry; no files were written."
        ) from error
    if result.returncode:
        if optional and result.returncode == 1:
            return None
        raise ProjectRootResolutionError(
            "Git discovery failed. Hint: check repository access and ownership, then retry; "
            "no project files were written."
        )
    return result.stdout.removesuffix("\n")


def _marker(start: Path) -> Path | None:
    return next(
        (
            path
            for path in (start, *start.parents)
            if os.path.lexists(path / ".git")
            or all((path / name).exists() for name in ("HEAD", "objects", "config"))
        ),
        None,
    )


def _checkout_git_dir(checkout: Path) -> Path:
    entry = checkout / ".git"
    if entry.is_file():
        content = entry.read_text().removesuffix("\n")
        if content.startswith("gitdir: "):
            return (checkout / content.removeprefix("gitdir: ")).resolve()
    return entry.resolve()


def _main_checkout(start: Path, common: Path) -> Path | None:
    # Plain porcelain predates -z and --path-format. Decode Git's quoted paths.
    listing = _git(start, "-c", "core.quotePath=false", "worktree", "list", "--porcelain")
    block = (listing or "").split("\n\n", 1)[0].splitlines()
    if not block or not block[0].startswith("worktree "):
        return None
    value = block[0].removeprefix("worktree ")
    if value.startswith('"'):
        value = ast.literal_eval(value)
    candidate = Path(value).resolve()
    if "bare" in block or _checkout_git_dir(candidate) == common:
        return candidate
    # Submodules normally record core.worktree relative to their common git dir.
    configured = _git(
        start,
        "config",
        "--file",
        str(common / "config"),
        "--path",
        "--get",
        "core.worktree",
        optional=True,
    )
    if configured:
        candidate = (common / configured).resolve()
        if _checkout_git_dir(candidate) == common:
            return candidate
    # --separate-git-dir need not retain a backlink to its checkout. Guessing
    # common.parent or scanning siblings would silently split memory again.
    return None


def _nested_project(start: Path, checkout: Path) -> tuple[Path | None, list[Path]]:
    incomplete: list[Path] = []
    for candidate in (start, *start.parents):
        if candidate == checkout or not candidate.is_relative_to(checkout):
            break
        if is_project_initialized(candidate) and has_project_identity(candidate):
            return candidate, incomplete
        if (candidate / ".umem").exists():
            incomplete.append(candidate)
    return None, incomplete


def _has_tracked_facts(project: Path) -> bool:
    layout = resolve_project_layout(project)
    facts = layout.shared_facts_path if layout.is_shared else layout.legacy_facts_path
    return (
        _git(
            project,
            "--literal-pathspecs",
            "ls-files",
            "--error-unmatch",
            "--",
            str(facts.relative_to(project)),
            optional=True,
        )
        is not None
    )


def resolve_project_roots(  # noqa: PLR0912
    cwd: Path | None = None,
    *,
    memory_root: Path | None = None,
) -> ProjectRoots:
    start = (cwd or Path.cwd()).resolve()
    warnings: list[str] = []
    override = memory_root or os.environ.get("UMEM_MEMORY_ROOT")
    marker = _marker(start)
    if marker is None:
        owner = next((path for path in (start, *start.parents) if (path / ".umem").is_dir()), start)
        project = owner
    else:
        common = _git(start, "rev-parse", "--git-common-dir")
        common_path = (start / (common or "")).resolve()
        if not common or not common_path.is_dir():
            raise ProjectRootResolutionError("Git returned an invalid common directory.")
        bare = _git(start, "rev-parse", "--is-bare-repository") == "true"
        top = None if bare else _git(start, "rev-parse", "--show-toplevel")
        project = Path(top).resolve() if top else marker
        # A nested project must have completed init; mere host/audit remnants
        # must not steal ownership from the checkout. Linked checkout roots
        # themselves still share the main checkout's memory.
        nested, incomplete = _nested_project(start, project)
        if nested is not None:
            project = owner = nested
        elif top and not override and _has_tracked_facts(project):
            # Use this worktree's index, never the main checkout's index/HEAD.
            # Versioned memory follows the branch even if the main is uninitialized.
            owner = project
        else:
            owner = (
                project
                if top and _checkout_git_dir(project) == common_path
                else _main_checkout(start, common_path)
            )
        if owner is None and not override:
            raise ProjectRootResolutionError(
                "Git does not identify the main checkout. "
                "Hint: explicitly set UMEM_MEMORY_ROOT to the main checkout directory."
            )
        warnings.extend(
            f"Incomplete nested project at {candidate}; using checkout memory root "
            f"{owner}. Complete umem init with UMEM_MEMORY_ROOT set to that "
            "subdirectory to give it its own memory. Files were preserved."
            for candidate in incomplete
        )
    if override:
        owner = Path(override).expanduser().resolve()
    if owner is None:  # Defensive: discovery must never silently fall back.
        raise ProjectRootResolutionError("Git memory ownership is unresolved.")
    ignored_roots = [start]
    if project != start:
        ignored_roots.extend(path for path in start.parents if path.is_relative_to(project))
    for ignored in dict.fromkeys(ignored_roots):
        if ignored == owner:
            continue
        for relative in (".umem/memory", "umem/memory"):
            local = ignored / relative
            if local.resolve() == (owner / relative).resolve():
                continue
            if local.is_dir() and any(
                path.is_file() and path.stat().st_size for path in local.rglob("*")
            ):
                warnings.append(
                    f"Local memory at {local} is not used; shared memory root is {owner}. "
                    "Files were preserved. Review orphaned facts or explicitly set "
                    "UMEM_MEMORY_ROOT."
                )
    return ProjectRoots(project, owner, tuple(warnings))
