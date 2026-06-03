---
title: 'Publish to PyPI via GitHub Actions with Trusted Publishers'
type: 'feature'
created: '2026-06-03'
status: 'done'
baseline_commit: ''
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** We want to automate building and publishing the `universal-memory` package to PyPI on new GitHub Releases securely, without using static API keys/tokens.

**Approach:** Implement a GitHub Actions workflow `.github/workflows/publish.yml` that triggers on `release: published`, builds the project using `uv build`, and publishes it to PyPI using `uv publish`. Authenticate securely via OpenID Connect (OIDC) Trusted Publishers.

## Boundaries & Constraints

**Always:** 
- Keep workflow secrets out of source control.
- Ensure the job uses PyPI environment-level permissions and Trusted Publisher OIDC configuration (`id-token: write`).
- Use the target environment `pypi` for the job context.

**Ask First:** 
- None.

**Never:** 
- Do not store long-lived tokens/secrets in the repository.

## I/O & Edge-Case Matrix

| Scenario | Trigger / Inputs | Expected Output / Behavior | Error Handling |
|----------|------------------|---------------------------|----------------|
| HAPPY_PATH (Release) | GitHub Release published | Workflow executes: checks out, installs `uv`, runs `uv build`, publishes to PyPI via OIDC. | PyPI rejects package if version is already published. |
| DRY-RUN (Local testing) | Run `uv build` locally | Generates source distribution (`.tar.gz`) and wheel (`.whl`) files in `dist/`. | Verification of packages fails if build-backend is broken. |

</frozen-after-approval>

## Code Map

- `.github/workflows/publish.yml` -- The workflow definition file.
- `pyproject.toml` -- Checked to verify package metadata and build-system.

## Tasks & Acceptance

**Execution:**
- [x] Create `.github/workflows/publish.yml` with OIDC and `uv` setup.
- [x] Test the build step locally using `uv build` to verify package packaging.

**Acceptance Criteria:**
- Workflow file `.github/workflows/publish.yml` exists under `.github/workflows/`.
- The job in `publish.yml` targets the `pypi` environment, specifies `id-token: write` permissions, and executes `uv build` followed by `uv publish`.
- Run `uv build` locally creates valid package artifacts in `dist/`.

### Review Findings
- [x] [Review][Patch] Target environment pypi not configured in pypi-publish job [.github/workflows/publish.yml:41-49]
- [x] [Review][Patch] Missing job-level contents: read permission in pypi-publish job [.github/workflows/publish.yml:47-48]
- [x] [Review][Patch] Portuguese comment in workflow file [.github/workflows/publish.yml:49]
- [x] [Review][Patch] Missing workflow_dispatch trigger [.github/workflows/publish.yml:3-5]
- [x] [Review][Patch] Missing build verification in checks job [.github/workflows/publish.yml:10-38]
- [x] [Review][Patch] Dependencies sync lacks --locked enforcement [.github/workflows/publish.yml:29]

## Verification

**Commands:**
- `uv build` -- expected: SUCCESS
- Workflow schema is valid and linted.
