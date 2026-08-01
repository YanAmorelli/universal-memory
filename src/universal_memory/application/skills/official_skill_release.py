from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import tomllib
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

PUBLIC_SKILL_RELATIVE_PATH = Path("skills/universal-memory")
PACKAGED_SKILL_RELATIVE_PATH = Path("src/universal_memory/resources/skills/universal-memory")
WHEEL_SKILL_PREFIX = "universal_memory/resources/skills/universal-memory/"
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_PRERELEASE_VERSION_PATTERN = re.compile(r"(?:a|b|rc)\d+(?:\.dev\d+)?$|\.dev\d+$")


class ReleaseValidationError(RuntimeError):
    """Raised when a release cannot safely distribute the official skill."""


@dataclass(frozen=True, slots=True)
class OfficialSkillReleaseValidation:
    version: str
    release_tag: str
    protected_ref: str
    checkout_commit: str
    asset_count: int
    wheel_name: str
    wheel_sha256: str


def validate_release_bundle(
    *,
    project_root: Path,
    release_tag: str,
    checkout_commit: str,
    tagged_commit: str,
    tag_on_protected_ref: bool,
) -> OfficialSkillReleaseValidation:
    version = _project_version(project_root / "pyproject.toml")
    protected_ref = _protected_release_ref(version)
    expected_tag = f"v{version}"
    if release_tag != expected_tag:
        raise ReleaseValidationError(
            f"Release tag {release_tag!r} must match package version tag {expected_tag!r}."
        )
    if not _COMMIT_PATTERN.fullmatch(checkout_commit) or checkout_commit != tagged_commit:
        raise ReleaseValidationError(
            "Release checkout commit must be the commit referenced by the release tag."
        )
    if not tag_on_protected_ref:
        raise ReleaseValidationError(
            f"Release tag commit must be an ancestor of the protected {protected_ref} branch."
        )

    wheel_path = _release_wheel(project_root / "dist")
    public_assets = _asset_tree(project_root / PUBLIC_SKILL_RELATIVE_PATH)
    packaged_assets = _asset_tree(project_root / PACKAGED_SKILL_RELATIVE_PATH)
    if packaged_assets != public_assets:
        raise ReleaseValidationError(
            "Official skill package resources differ from the public tagged source."
        )

    wheel_assets = _wheel_assets(wheel_path)
    if wheel_assets != public_assets:
        raise ReleaseValidationError(
            "Official skill wheel resources differ from the public tagged source."
        )
    return OfficialSkillReleaseValidation(
        version=version,
        release_tag=release_tag,
        protected_ref=protected_ref,
        checkout_commit=checkout_commit,
        asset_count=len(public_assets),
        wheel_name=wheel_path.name,
        wheel_sha256=_sha256(wheel_path),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate official skill release provenance.")
    parser.add_argument("--tag", required=True, help="Release tag to validate.")
    parser.add_argument(
        "--github-output",
        type=Path,
        help="Optional GitHub Actions output file receiving validated provenance.",
    )
    args = parser.parse_args(argv)
    project_root = Path.cwd()
    version = _project_version(project_root / "pyproject.toml")
    protected_ref = _protected_release_ref(version)
    checkout_commit = _git_output(project_root, "rev-parse", "HEAD")
    tagged_commit = _git_output(project_root, "rev-parse", f"{args.tag}^{{commit}}")
    tag_on_protected_ref = _git_is_ancestor(project_root, tagged_commit, protected_ref)
    result = validate_release_bundle(
        project_root=project_root,
        release_tag=args.tag,
        checkout_commit=checkout_commit,
        tagged_commit=tagged_commit,
        tag_on_protected_ref=tag_on_protected_ref,
    )
    if args.github_output is not None:
        _write_github_output(args.github_output, result)
    print(
        f"Validated {result.release_tag} at {result.checkout_commit} "
        f"with {result.asset_count} official skill assets; "
        f"{result.wheel_name} sha256={result.wheel_sha256}."
    )
    return 0


def _project_version(path: Path) -> str:
    project = tomllib.loads(path.read_text(encoding="utf-8"))
    version = project.get("project", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        raise ReleaseValidationError("pyproject.toml has no valid project version.")
    return version.strip()


def _protected_release_ref(version: str) -> str:
    return "origin/dev" if _PRERELEASE_VERSION_PATTERN.search(version) else "origin/main"


def _asset_tree(root: Path) -> dict[str, bytes]:
    if not root.is_dir():
        raise ReleaseValidationError(f"Official skill asset directory is missing: {root.name}")
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _wheel_assets(path: Path) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path) as archive:
            return {
                name.removeprefix(WHEEL_SKILL_PREFIX): archive.read(name)
                for name in sorted(archive.namelist())
                if name.startswith(WHEEL_SKILL_PREFIX) and not name.endswith("/")
            }
    except (OSError, zipfile.BadZipFile) as exc:
        raise ReleaseValidationError("Built wheel could not be inspected.") from exc


def _release_wheel(dist_directory: Path) -> Path:
    if not dist_directory.is_dir():
        raise ReleaseValidationError("Release validation requires the relative dist/ directory.")
    artifacts = sorted(path for path in dist_directory.iterdir() if path.is_file())
    if len(artifacts) != 1 or artifacts[0].suffix != ".whl":
        raise ReleaseValidationError("Release dist/ must contain exactly one wheel artifact.")
    return artifacts[0]


def _sha256(path: Path) -> str:
    with path.open("rb") as wheel_file:
        return hashlib.file_digest(wheel_file, "sha256").hexdigest()


def _git_output(project_root: Path, *arguments: str) -> str:
    git_path = shutil.which("git")
    if git_path is None:
        raise ReleaseValidationError("git is required for release provenance validation.")
    completed = subprocess.run(  # noqa: S603
        [git_path, *arguments],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ReleaseValidationError("Release tag or checkout commit could not be resolved.")
    return completed.stdout.strip()


def _git_is_ancestor(project_root: Path, ancestor: str, descendant: str) -> bool:
    git_path = shutil.which("git")
    if git_path is None:
        raise ReleaseValidationError("git is required for release provenance validation.")
    completed = subprocess.run(  # noqa: S603
        [git_path, "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise ReleaseValidationError("Protected main ref could not be resolved for validation.")


def _write_github_output(
    output_path: Path,
    result: OfficialSkillReleaseValidation,
) -> None:
    fields = {
        "release_tag": result.release_tag,
        "protected_ref": result.protected_ref,
        "checkout_commit": result.checkout_commit,
        "wheel_name": result.wheel_name,
        "wheel_sha256": result.wheel_sha256,
    }
    with output_path.open("a", encoding="utf-8") as output:
        for name, value in fields.items():
            output.write(f"{name}={value}\n")
