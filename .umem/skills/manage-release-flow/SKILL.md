---
name: "manage-release-flow"
description: "Run the Universal Memory release workflow: feature/release branch, PR to dev, PR from dev to main, changelog/version updates, release tag, GitHub Release notes, PyPI publish verification, and explicit release-vs-prerelease confirmation."
triggers:
  - "when preparing a Universal Memory release"
  - "when asked to create release PRs, tags, or GitHub releases"
  - "when moving changes from feature branch to dev and from dev to main"
  - "when publishing Universal Memory to PyPI"
  - "when asked to avoid repeating release process context"
---

# Manage Release Flow

Use this skill for Universal Memory release operations. Keep all paths relative in reports
and generated text.

## Release Modes

Before creating or publishing a GitHub Release, ask the user one explicit question:

```text
Should this be a stable release or a prerelease?
```

Default to no publishing action until the user answers. It is acceptable to prepare PRs,
changelog updates, version bumps, and draft release notes before this answer.

## Versioning Convention

Use SemVer for package versions:

- Package/PyPI version: `MAJOR.MINOR.PATCH`, such as `0.2.1`.
- Git tag: prefix the package version with `v`, such as `v0.2.1`.
- GitHub Release: use the Git tag as the release tag.

Use the SemVer level deliberately:

- `PATCH`: bug fixes, docs/package metadata fixes, README/PyPI rendering fixes, and
  changes that do not alter expected runtime behavior or public APIs.
- `MINOR`: compatible public features, new commands, new supported workflows, or
  meaningful user-visible additions.
- `MAJOR`: incompatible API, CLI, config, storage schema, or migration changes.

While the project is still `0.x`, breaking changes may be released as `MINOR`, but call
them out explicitly in the changelog and GitHub Release notes.

Use PEP 440 prerelease versions for PyPI:

- Alpha: `0.3.0a1`, tag `v0.3.0a1`.
- Beta: `0.3.0b1`, tag `v0.3.0b1`.
- Release candidate: `0.3.0rc1`, tag `v0.3.0rc1`.

Once a version is published to PyPI, treat that version as immutable. If a published
artifact is wrong, publish a new patch/prerelease version instead of reusing the same
version. Repointing an existing tag is acceptable only before a successful PyPI publish,
or when fixing a stale GitHub Release/Actions event that has not produced a published
artifact.

## Standard Flow

1. Inspect repository state.
   - Run `git status --short --branch`.
   - Run `git fetch --prune --tags`.
   - Confirm the intended version, source branch, and target flow.
   - If a release tag already exists, inspect both local and remote tag targets before
     mutating anything.

2. Prepare a feature or release branch.
   - Use the repository branch-prefix convention: `feat/`, `chore/`, `docs/`,
     `config/`, or another established prefix that matches the work.
   - Use a focused branch name such as `chore/release-0.2.2` or
     `docs/pypi-readme-images`.
   - Keep version, changelog, and release-specific fixes in small, reviewable commits.

3. Update release artifacts.
   - Update package version in all version metadata covered by tests.
   - Update or add changelog content before the PR from `dev` to `main`. If no changelog
     file exists, ask whether to create one or include the release note only in the PR and
     GitHub Release.
   - Update tests that assert version metadata.
   - Run the project validation stack used by CI and hooks.

4. Open PR to `dev`.
   - Base: `dev`.
   - Head: the feature/release branch.
   - Include summary, validation, release impact, and whether publishing is expected.
   - Wait for checks or inspect their status.
   - Merge only when the user asks or when the task explicitly includes merging.

5. Open PR from `dev` to `main`.
   - Base: `main`.
   - Head: `dev`.
   - Include release summary, changelog note, validation, and tag/release plan.
   - Verify the PR contains only intended release commits.
   - Wait for checks or inspect their status.
   - Merge only when the user asks or when the task explicitly includes merging.

6. Tag after `main` contains the release commit.
   - Fetch `origin/main`.
   - Confirm `origin/main` is the exact intended target.
   - Create or move `vX.Y.Z` only after confirmation.
   - If moving an existing tag, say that it requires force-pushing the tag and confirm the
     target commit before doing it.

7. Create the GitHub Release.
   - Reuse the release notes from the changelog/PR.
   - Use `--prerelease` only when the user selected prerelease.
   - Target `main`.
   - After creation, verify the release event uses the tag's current commit. If a tag was
     moved after an old release event fired, delete and recreate only the GitHub Release,
     not the tag, to trigger a fresh `release.published` workflow.

8. Verify publishing.
   - Watch the `Publish to PyPI` workflow.
   - If checkout fails with an expected-commit mismatch, treat it as a stale release event
     caused by tag movement; recreate the GitHub Release.
   - Verify the installed package from PyPI, for example:

     ```bash
     uvx --from universal-memory==X.Y.Z umem --version
     ```

## PR Body Template

```markdown
## Summary
- ...

## Release impact
- Version: X.Y.Z
- Release type: stable|prerelease|not publishing yet
- Target package: PyPI `universal-memory`

## Changelog
- ...

## Validation
- `uv run pytest`
- `uv run pyright`
- relevant GitHub checks or pre-push hooks
```

## GitHub Release Notes Template

```markdown
## Universal Memory vX.Y.Z

Short release purpose.

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Versioning
Why this is major, minor, patch, or prerelease.
```

Remove empty sections before publishing.

## Guardrails

- Do not create or move tags before the release PR is merged to `main`.
- Do not assume stable vs prerelease; ask.
- Do not rerun a stale release workflow after moving a tag; recreate the release event.
- Do not overwrite unrelated branches or force-push branches unless explicitly requested.
- Keep branch/PR/release descriptions factual and concise.
- Preserve user changes in the worktree; stage only release-related files.
