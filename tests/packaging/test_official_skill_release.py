from __future__ import annotations

import hashlib
import subprocess
import zipfile
from pathlib import Path

import pytest

from universal_memory.application.skills.official_skill_release import (
    PACKAGED_SKILL_RELATIVE_PATH,
    ReleaseValidationError,
    _git_is_ancestor,
    _protected_release_ref,
    validate_release_bundle,
)


def _release_tree(
    root: Path,
    *,
    version: str = "0.6.1",
    public_content: bytes = b"official skill\n",
    packaged_content: bytes | None = None,
    wheel_content: bytes | None = None,
) -> Path:
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "universal-memory"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    public_file = root / "skills" / "universal-memory" / "SKILL.md"
    packaged_file = root / PACKAGED_SKILL_RELATIVE_PATH / "SKILL.md"
    public_file.parent.mkdir(parents=True)
    packaged_file.parent.mkdir(parents=True)
    public_file.write_bytes(public_content)
    packaged_file.write_bytes(packaged_content or public_content)

    wheel = root / "dist" / "universal_memory-test.whl"
    wheel.parent.mkdir()
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "universal_memory/resources/skills/universal-memory/SKILL.md",
            wheel_content or public_content,
        )
    return wheel


def test_release_bundle_requires_matching_version_tag_checkout_and_assets(tmp_path: Path) -> None:
    wheel = _release_tree(tmp_path)

    result = validate_release_bundle(
        project_root=tmp_path,
        release_tag="v0.6.1",
        checkout_commit="a" * 40,
        tagged_commit="a" * 40,
        tag_on_protected_ref=True,
    )

    assert result.version == "0.6.1"
    assert result.release_tag == "v0.6.1"
    assert result.protected_ref == "origin/main"
    assert result.asset_count == 1
    assert result.wheel_name == wheel.name
    assert result.wheel_sha256 == hashlib.sha256(wheel.read_bytes()).hexdigest()


def test_release_bundle_rejects_tag_from_an_older_package_version(tmp_path: Path) -> None:
    _release_tree(tmp_path)

    with pytest.raises(ReleaseValidationError, match="must match package version"):
        validate_release_bundle(
            project_root=tmp_path,
            release_tag="v0.4.0",
            checkout_commit="a" * 40,
            tagged_commit="a" * 40,
            tag_on_protected_ref=True,
        )


def test_release_bundle_rejects_checkout_that_is_not_the_tag_commit(tmp_path: Path) -> None:
    _release_tree(tmp_path)

    with pytest.raises(ReleaseValidationError, match="checkout commit"):
        validate_release_bundle(
            project_root=tmp_path,
            release_tag="v0.6.1",
            checkout_commit="b" * 40,
            tagged_commit="a" * 40,
            tag_on_protected_ref=True,
        )


def test_release_bundle_rejects_tag_commit_outside_protected_ref(tmp_path: Path) -> None:
    _release_tree(tmp_path)

    with pytest.raises(ReleaseValidationError, match="origin/main"):
        validate_release_bundle(
            project_root=tmp_path,
            release_tag="v0.6.1",
            checkout_commit="a" * 40,
            tagged_commit="a" * 40,
            tag_on_protected_ref=False,
        )


def test_prerelease_bundle_uses_dev_as_its_protected_ref(tmp_path: Path) -> None:
    _release_tree(tmp_path, version="0.5.0rc1")

    result = validate_release_bundle(
        project_root=tmp_path,
        release_tag="v0.5.0rc1",
        checkout_commit="a" * 40,
        tagged_commit="a" * 40,
        tag_on_protected_ref=True,
    )

    assert result.protected_ref == "origin/dev"
    assert _protected_release_ref("0.6.1") == "origin/main"


def test_main_ancestry_check_uses_git_merge_base_is_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def run_git(command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert options["cwd"] == tmp_path
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(
        "universal_memory.application.skills.official_skill_release.shutil.which",
        lambda executable: executable,
    )
    monkeypatch.setattr(
        "universal_memory.application.skills.official_skill_release.subprocess.run",
        run_git,
    )

    assert _git_is_ancestor(tmp_path, "a" * 40, "origin/main") is True
    assert commands == [["git", "merge-base", "--is-ancestor", "a" * 40, "origin/main"]]


def test_release_bundle_rejects_divergent_public_and_packaged_assets(tmp_path: Path) -> None:
    _release_tree(tmp_path, packaged_content=b"stale package resource\n")

    with pytest.raises(ReleaseValidationError, match="package resources differ"):
        validate_release_bundle(
            project_root=tmp_path,
            release_tag="v0.6.1",
            checkout_commit="a" * 40,
            tagged_commit="a" * 40,
            tag_on_protected_ref=True,
        )


def test_release_bundle_rejects_wheel_assets_that_differ_from_tag_source(tmp_path: Path) -> None:
    _release_tree(tmp_path, wheel_content=b"stale wheel resource\n")

    with pytest.raises(ReleaseValidationError, match="wheel resources differ"):
        validate_release_bundle(
            project_root=tmp_path,
            release_tag="v0.6.1",
            checkout_commit="a" * 40,
            tagged_commit="a" * 40,
            tag_on_protected_ref=True,
        )


def test_release_bundle_rejects_more_than_one_wheel_in_dist(tmp_path: Path) -> None:
    _release_tree(tmp_path)
    (tmp_path / "dist" / "second.whl").write_bytes(b"not the validated wheel")

    with pytest.raises(ReleaseValidationError, match="exactly one wheel"):
        validate_release_bundle(
            project_root=tmp_path,
            release_tag="v0.6.1",
            checkout_commit="a" * 40,
            tagged_commit="a" * 40,
            tag_on_protected_ref=True,
        )


def test_publish_workflow_builds_validates_and_publishes_one_identical_wheel() -> None:
    workflow = Path(".github/workflows/publish.yml").read_text(encoding="utf-8")
    publish_job = workflow.split("  pypi-publish:", maxsplit=1)[1]

    assert "release_tag:" in workflow
    assert "required: true" in workflow
    assert "github.event.release.tag_name || inputs.release_tag" in workflow
    assert "git fetch --no-tags origin" in workflow
    assert "refs/remotes/origin/main" in workflow
    assert "refs/remotes/origin/dev" in workflow
    assert "--main-ref" not in workflow
    assert "scripts/validate_official_skill_release.py" in workflow
    assert '--tag "$RELEASE_TAG"' in workflow
    assert "github.event_name == 'release'" in workflow
    assert workflow.count("uv build") == 1
    assert "uv build --wheel --out-dir dist --clear --no-create-gitignore" in workflow
    assert "uses: actions/upload-artifact@v7" in workflow
    assert "path: dist/*.whl" in workflow
    assert "if-no-files-found: error" in workflow
    assert "wheel_sha256:" in workflow
    assert "checkout_commit:" in workflow
    assert "uses: actions/download-artifact@v8" in publish_job
    assert "EXPECTED_WHEEL_SHA256" in publish_job
    assert "sha256sum --check --strict" in publish_job
    assert 'uv publish "dist/$WHEEL_NAME"' in publish_job
    assert "actions/checkout" not in publish_job
    assert "uv build" not in publish_job
    assert "target_commitish" not in workflow
