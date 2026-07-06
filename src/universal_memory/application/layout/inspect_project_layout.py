from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from universal_memory.domain.ports import ProjectLayoutPort
from universal_memory.domain.project_layout import ProjectLayoutInspection


class InspectProjectLayoutUseCase:
    def __init__(self, *, project_root: Path, layout_port: ProjectLayoutPort) -> None:
        self.project_root = project_root
        self.layout_port = layout_port

    def execute(self) -> dict[str, Any]:
        report = self.layout_port.inspect_project_layout(self.project_root)
        report = inspect_repository_layout_health(self.project_root, report)
        return {
            "operation": report.operation,
            "scope": "project",
            "data": asdict(report),
        }


def inspect_repository_layout_health(
    project_root: Path,
    report: ProjectLayoutInspection,
) -> ProjectLayoutInspection:
    normalized_root = project_root.resolve()
    ignored_shared_paths: list[str] = []
    tracked_operational_paths: list[str] = []
    warnings = list(report.warnings)
    recommended_actions = list(report.recommended_actions)
    git_status_available = _is_git_work_tree(normalized_root)

    if not git_status_available:
        warnings.append("Git metadata is unavailable; repository visibility was not verified.")
        recommended_actions.append("Run umem doctor inside a Git repository to verify UMEM paths.")
    else:
        ignored_shared_paths = _ignored_shared_paths(
            normalized_root,
            report.shared_root,
            report.layout,
        )
        tracked_operational_paths = _tracked_operational_paths(
            normalized_root,
            report.operational_root,
        )
        if ignored_shared_paths:
            warnings.append("Shared UMEM content is hidden by repository ignore rules.")
            recommended_actions.append("Review .gitignore so umem/ remains commit-reviewable.")
        if tracked_operational_paths:
            warnings.append("Operational UMEM state is tracked by the repository.")
            recommended_actions.append(
                "Keep .umem operational state private unless explicitly approved."
            )

    overlaps = _layout_overlaps(normalized_root, report.shared_root, report.operational_root)
    if overlaps:
        warnings.append("Legacy and shared UMEM content overlap.")
        recommended_actions.append(
            "Resolve duplicate IDs or slugs; shared content takes precedence over legacy content."
        )

    return ProjectLayoutInspection(
        operation=report.operation,
        layout=report.layout,
        shared_root=report.shared_root,
        operational_root=report.operational_root,
        precedence=report.precedence,
        warnings=_dedupe(warnings),
        recommended_actions=_dedupe(recommended_actions),
        git_status_available=git_status_available,
        ignored_shared_paths=ignored_shared_paths,
        tracked_operational_paths=tracked_operational_paths,
        overlaps=overlaps,
    )


def _is_git_work_tree(project_root: Path) -> bool:
    result = _run_git(project_root, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


def _ignored_shared_paths(project_root: Path, shared_root: str, layout: str) -> list[str]:
    if layout not in {"shared", "partial"}:
        return []

    normalized_shared_root = shared_root.rstrip("/")
    shared_root_display = _directory_display(normalized_shared_root)
    if _is_ignored(project_root, shared_root_display):
        return [shared_root_display]

    candidates = [
        f"{normalized_shared_root}/project.toml",
        f"{normalized_shared_root}/memory",
        f"{normalized_shared_root}/memory/facts.jsonl",
        f"{normalized_shared_root}/memory/rules.jsonl",
        f"{normalized_shared_root}/skills",
        f"{normalized_shared_root}/skills/skills.jsonl",
    ]
    ignored: list[str] = []
    for candidate in candidates:
        if _is_ignored(project_root, _directory_display(candidate)):
            ignored.append(_directory_display(candidate))
    return _collapse_child_paths(_dedupe(ignored))


def _is_ignored(project_root: Path, relative_path: str) -> bool:
    return _run_git(project_root, "check-ignore", "-q", "--", relative_path).returncode == 0


def _tracked_operational_paths(project_root: Path, operational_root: str) -> list[str]:
    result = _run_git(project_root, "ls-files", operational_root)
    if result.returncode != 0:
        return []
    tracked: list[str] = []
    for line in result.stdout.splitlines():
        path = line.strip()
        if _is_operational_path(path, operational_root):
            tracked.append(path)
    return _dedupe(tracked)


def _is_operational_path(path: str, operational_root: str) -> bool:
    private_paths = (
        f"{operational_root}/audit/",
        f"{operational_root}/snapshots/",
        f"{operational_root}/locks/",
        f"{operational_root}/memory/private_facts.jsonl",
        f"{operational_root}/memory/private_rules.jsonl",
        f"{operational_root}/skills/",
    )
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in private_paths)


def _layout_overlaps(
    project_root: Path,
    shared_root: str,
    operational_root: str,
) -> list[dict[str, str]]:
    overlaps: list[dict[str, str]] = []
    overlaps.extend(
        _jsonl_overlaps(
            category="fact",
            key="id",
            active_path=project_root / shared_root / "memory" / "facts.jsonl",
            shadowed_path=project_root / operational_root / "memory" / "facts.jsonl",
            project_root=project_root,
        )
    )
    overlaps.extend(
        _jsonl_overlaps(
            category="rule",
            key="id",
            active_path=project_root / shared_root / "memory" / "rules.jsonl",
            shadowed_path=project_root / operational_root / "memory" / "rules.jsonl",
            project_root=project_root,
        )
    )
    overlaps.extend(
        _jsonl_overlaps(
            category="skill",
            key="slug",
            active_path=project_root / shared_root / "skills" / "skills.jsonl",
            shadowed_path=project_root / operational_root / "memory" / "skills.jsonl",
            project_root=project_root,
        )
    )
    return overlaps


def _jsonl_overlaps(
    *,
    category: str,
    key: str,
    active_path: Path,
    shadowed_path: Path,
    project_root: Path,
) -> list[dict[str, str]]:
    active_values = _jsonl_values(active_path, key)
    shadowed_values = _jsonl_values(shadowed_path, key)
    common = sorted(set(active_values) & set(shadowed_values))
    return [
        {
            "category": category,
            "id": value,
            "active_path": _relative_path(active_path, project_root),
            "shadowed_path": _relative_path(shadowed_path, project_root),
            "active_precedence": "shared_over_legacy",
        }
        for value in common
    ]


def _jsonl_values(path: Path, key: str) -> list[str]:
    if not path.exists():
        return []
    values: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line).get(key)
        except json.JSONDecodeError:
            continue
        if isinstance(value, str):
            values.append(value)
    return values


def _run_git(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git = shutil.which("git") or "git"
    try:
        return subprocess.run(  # noqa: S603
            [git, "-C", project_root.as_posix(), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return subprocess.CompletedProcess(args=["git", *args], returncode=1, stdout="", stderr="")


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _directory_display(path: str) -> str:
    return path if path.endswith("/") or "." in Path(path).name else f"{path}/"


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _collapse_child_paths(paths: list[str]) -> list[str]:
    collapsed: list[str] = []
    for path in paths:
        if any(path.startswith(parent) for parent in collapsed if parent.endswith("/")):
            continue
        collapsed.append(path)
    return collapsed
