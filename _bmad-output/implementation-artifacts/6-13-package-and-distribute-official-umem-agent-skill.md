# Story 6.13: Package And Distribute The Official UMEM Agent Skill

Status: done

## Story

As a user working across different coding agents,
I want an official portable UMEM Agent Skill and low-effort installation guidance,
so that compatible agents can follow the same safe directed-CLI workflow without requiring a native UMEM adapter.

## Acceptance Criteria

1. **Given** the official UMEM Agent Skill source, **When** it is validated, **Then** it follows the open Agent Skills structure under `skills/universal-memory/`, uses a concise `SKILL.md`, and links only through relative paths to optional `references/`, `scripts/`, or `assets/`.
2. **Given** an agent activates the official skill during ordinary repository work, **When** it follows the instructions, **Then** it runs `umem status --format json` and `umem context --scope project --format json` before durable planning, implementation, investigation, or review, reconciles memory with current repository state and user instructions, and does not require the user to say "use UMEM".
3. **Given** the task produces possible durable knowledge, **When** the official skill evaluates recording, **Then** it records only stable, reusable, safe facts; rejects secrets, credentials, raw logs, stack traces, private data, transient progress, and unverified assumptions; respects confirmation boundaries; and reports recorded or proposed durable changes at the end of the task.
4. **Given** a compact `AGENTS.md` bootstrap is needed, **When** the packaged bootstrap asset is inspected, **Then** it remains a short routing instruction that can operate as a minimal Directed CLI fallback and points to the official skill without duplicating the skill's full workflow.
5. **Given** an Agent Skills-compatible target with Node.js, `npx`, network access, and an external agent mapping available, **When** installation assistance is planned, **Then** the application service returns an argument-safe, project-scoped `npx skills` plan for `universal-memory`, disables anonymous telemetry with `DISABLE_TELEMETRY=1`, and does not infer Tier 1 support.
6. **Given** UMEM proposes external installation, **When** the plan is rendered for onboarding, **Then** its primary prompt names the agent and intended outcome without requiring `npx` knowledge, while technical details disclose the exact command, agent, project scope, deterministic copy behavior, network use, disabled telemetry, confirmation requirement, and external mutation boundary.
7. **Given** global installation is explicitly requested, **When** a distribution plan is generated, **Then** the command includes global scope and the plan preserves the requirement for separate explicit confirmation; project scope remains the default.
8. **Given** Node.js, `npx`, network access, or the selected external agent mapping is unavailable, **When** installation assistance is planned, **Then** the application service returns a non-fatal fallback plan using the best available combination of `AGENTS.md`, UMEM-native installation, and manual skill copy, and does not mark the connection ready.
9. **Given** any installation channel completes, **When** readiness is evaluated by the onboarding integration, **Then** the plan requires checks for instruction presence, executable UMEM CLI access, and one successful project context read before success can be reported.
10. **Given** this story is implemented, **When** focused tests and the project quality gates run, **Then** the official assets and application planning contract are covered without adding CLI commands, changing the primary onboarding flow, changing the runtime registry, or invoking an external installer in tests.
11. **Given** onboarding resolves an available project-scoped external installation and the user accepts the combined connection plan, **When** the connection executes, **Then** UMEM invokes the immutable `npx skills` argv with its declared environment and without a shell, records the external mutation boundary, validates instruction presence plus a project context read, and reports success only after validation; declined, unavailable, failed, timed-out, unsafe, and planning-only actions remain non-fatal and action-required.

## Tasks / Subtasks

- [x] **Task 1: Package the official portable skill** (AC: 1, 2, 3, 4)
  - [x] Add `skills/universal-memory/SKILL.md` with valid frontmatter, activation guidance, a compact Directed CLI preflight, and relative reference routing.
  - [x] Add focused references for the directed CLI workflow, memory safety and durable recording, and confirmation/final-reporting behavior.
  - [x] Add a compact `AGENTS.md` bootstrap asset that complements the skill and remains useful when the host cannot load Agent Skills.
  - [x] Use the complete public `universal-memory` tree as the source for project initialization and packaged fallbacks; preserve `use-universal-memory` only as a recognized legacy alias.
- [x] **Task 2: Add an application-level distribution planning contract** (AC: 5, 6, 7, 8, 9)
  - [x] Add immutable agent, environment, fallback, action, and plan result types under `src/universal_memory/application/skills/`.
  - [x] Generate an argv-safe `npx --yes skills add` command for the official Git source, selected skill, and selected agent.
  - [x] Default to deterministic project-scoped copy installation; add `--global` only for an explicit global request and reject false symlink semantics unsupported by the pinned installer.
  - [x] Set `DISABLE_TELEMETRY=1` as process environment metadata rather than relying on shell interpolation.
  - [x] Return progressive-disclosure copy, exact technical details, explicit external-mutation boundaries, and required post-install readiness checks.
  - [x] Return ordered, non-fatal fallback options and a machine-readable unavailability reason when optional prerequisites are missing.
- [x] **Task 3: Implement with focused TDD coverage** (AC: 1-10)
  - [x] First add failing tests for Agent Skills validation, relative links, concise bootstrap behavior, required Tier 2 guidance, default project planning, explicit copy/global planning, input validation, and each prerequisite fallback.
  - [x] Keep tests hermetic: do not require Node.js, network access, `npx`, or writes to real agent directories.
  - [x] Prove the planner never claims readiness or Tier 1 support and always returns the three post-install readiness checks.
- [x] **Task 4: Validate and prepare BMAD review** (AC: 1-10)
  - [x] Run focused tests for the official assets and distribution planner.
  - [x] Run `uv run pytest` if feasible.
  - [x] Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright`.
  - [x] Complete the Dev Agent Record and move only this story artifact to `review` after validation succeeds.
- [x] **Task 5: Resolve independent code-review findings** (AC: 1, 5, 8, 10)
  - [x] Remove proprietary `triggers` frontmatter and validate the official source against the open Agent Skills field set.
  - [x] Mirror the public source into package resources, prove byte-for-byte parity, and inspect the built wheel for every fallback asset.
  - [x] Pin the external `skills` package and official skill source to reviewed release versions.
  - [x] Reject non-boolean capability probes and terminal control characters before rendering a plan.
  - [x] Test every CLI surface taught by the official skill through the real Typer command tree.
- [x] **Task 6: Make the official distribution release-safe** (AC: 1, 5, 8, 10)
  - [x] Advance the feature release to `0.5.0` because `0.4.0` is already published and repository convention uses minor releases for new capabilities.
  - [x] Default published distribution plans to the matching `v0.5.0` tag while allowing development and tests to inject an immutable full commit SHA.
  - [x] Validate that the release tag equals `v<project version>`, the checkout is exactly the tag commit, and public, packaged, and wheel skill assets are byte-identical.
  - [x] Check out the explicit release tag only in the validation job and make manual dispatch validation-only, never a PyPI publication path.
  - [x] Keep wheel-build caches inside each test's temporary directory.
- [x] **Task 7: Publish only the validated release artifact** (AC: 1, 5, 8, 10)
  - [x] Build exactly one wheel under `dist/` at the validated tag commit and reject any additional release artifact.
  - [x] Prove the tag commit is contained by the fetched protected `origin/main` ref with `git merge-base --is-ancestor`.
  - [x] Record the validated checkout commit, wheel filename, and SHA-256 as workflow outputs.
  - [x] Upload the validated wheel, download that same artifact in the PyPI job, verify its SHA-256, and publish that exact relative wheel path.
  - [x] Remove the second checkout, second build, and `target_commitish` metadata trust from the publication job.
- [x] **Task 8: Execute the optional bridge through onboarding** (AC: 5, 6, 9, 11)
  - [x] Probe Node.js, `npx`, network policy, and agent mapping behind explicit ports and select the official planner in the real zero-flag and `connect` flows.
  - [x] Add an infrastructure executor that invokes immutable argv with an explicit merged environment, `shell=False`, project working directory, bounded timeout, and captured output.
  - [x] Execute only after the combined confirmation; never run for decline, planning-only JSON, unsafe/global plans, unavailable prerequisites, or fallback-only plans.
  - [x] Validate the installed instruction surface and project context read before reporting ready; expose external execution status in JSON and concise outcome-only human output.
  - [x] Add hermetic TDD coverage with injected probes and runners; tests must never invoke the real network or `npx`.
- [x] **Task 9: Consolidate the canonical skill and one-shot installer** (AC: 1-6, 8-11)
  - [x] Replace the separate embedded onboarding templates with the complete packaged canonical skill tree.
  - [x] Generate and verify package resources from `skills/universal-memory/` so the public tree remains the only authored source.
  - [x] Add a reviewed project-target catalog pinned atomically to `skills@1.5.20`; unknown agent IDs fall back without executing `npx`.
  - [x] Replace staged `add` plus `skills ls` plus project `add` with one project `add` and byte-exact post-install validation.
  - [x] Keep the Windsurf mapping frozen and preserve legacy `use-universal-memory` projects without silent duplication.

## Dev Notes

- **Spec source:** `_bmad-output/implementation-artifacts/spec-agent-support-evolution-tiers-and-mcp-fallback.md`, especially the Tier 2 portable contract, two-layer instruction model, `npx skills` boundary, R5-R11, R23-R24, and the matching acceptance criteria.
- **Execution addendum:** Packaging, planning, and release provenance remain isolated from adapters. The reopened execution task may wire the existing onboarding application port into `umem init` and `umem connect`, but must not change the runtime registry or add a new public command.
- **One canonical skill:** `skills/universal-memory/` is the complete authored source. Package resources are a generated byte-identical mirror, and new projects materialize that same tree under `.umem/skills/universal-memory/`. Existing `.umem/skills/use-universal-memory/` trees remain a non-destructive compatibility alias until an explicit migration is available.
- **External installer boundary:** `npx skills` remains optional implementation plumbing. The planner stays pure; onboarding owns capability probing, one combined user confirmation, execution, validation, and outcome rendering through injected ports.
- **Command safety:** Store executable arguments as an immutable tuple and telemetry controls as environment metadata. A display command may be derived with shell-safe quoting, but consumers should execute argv directly without a shell.
- **Version policy:** Pin the external installer package to a reviewed exact version and resolve the published official Git source through the tag matching the installed UMEM version. Because `0.4.0` is already published without this skill and cannot be republished safely, this feature advances the project to `0.5.0`; release automation must validate and publish `v0.5.0` with the same official skill assets before distribution is offered. Development and tests may inject a full immutable commit SHA instead of a release tag.
- **Release artifact identity:** The validation job owns the only source checkout and wheel build. It must fetch `origin/main`, prove the tagged commit is an ancestor, validate exactly one wheel under `dist/`, and export its SHA-256. The PyPI job may only download, re-hash, and publish that artifact; it must not check out or rebuild source.
- **Packaged fallback source:** Keep `skills/universal-memory/` as the public Git-discoverable source and an exact mirror under `src/universal_memory/resources/skills/universal-memory/` for installed-tool fallbacks. Fallback payload paths are relative to the `universal_memory` package resource root, never the caller's working directory.
- **Scope and method:** Project-scoped copy is the deterministic default. The pinned `skills@1.5.20` CLI has no `--symlink` flag and forces copy for the single selected target even when `--copy` is omitted, so UMEM passes `--copy` explicitly and rejects symlink claims. Global scope remains an explicit input. The plan must state that writes performed by the external installer are outside UMEM snapshot, audit, and rollback guarantees unless a future integration can inspect and protect the complete mutation plan.
- **Fallback contract:** Missing optional prerequisites are not initialization failures. Fallback plans identify what is unavailable, offer only channels declared available by the caller, and remain pending until instruction, CLI, and real context-read validation succeeds.
- **Tier boundary:** External catalog presence and skill installation never promote a host to Tier 1. The planner exposes `support_tier = "tier_2_directed_cli"` as the portable contract it can prepare, not a claim that setup is ready.
- **Path discipline:** All paths in this artifact, skill assets, tests, payloads, and logs must remain relative.

## References

- `_bmad-output/implementation-artifacts/spec-agent-support-evolution-tiers-and-mcp-fallback.md`
- `_bmad-output/implementation-artifacts/6-7-agent-skills-canonical-registry-and-direct-create.md`
- `_bmad-output/implementation-artifacts/6-8-agent-instruction-loop-for-latent-skills.md`
- `_bmad-output/implementation-artifacts/6-9-agent-skills-recommend-latent-candidates.md`
- `_bmad-output/implementation-artifacts/6-10-agent-skills-promote-approved-candidates.md`
- `_bmad-output/implementation-artifacts/6-11-agent-skills-sync-canonical-to-native-targets.md`
- `_bmad-output/implementation-artifacts/6-12-agent-skills-import-existing-native-skills.md`
- `_bmad-output/planning-artifacts/epics.md` (Story 6.13)
- `skills/universal-memory/SKILL.md`
- `src/universal_memory/application/skills/validate_skill.py`
- `src/universal_memory/application/onboarding/setup_project.py`
- `tests/application/test_setup_project.py`

## Dev Agent Record

### Agent Model Used

gpt-5.5

### Debug Log References

- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest tests/application/skills/test_official_skill_distribution.py -q` - RED confirmed with missing application module; final run passed with 19 tests.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff check src/universal_memory/application/skills/official_skill_distribution.py tests/application/skills/test_official_skill_distribution.py` - passed.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff format --check src/universal_memory/application/skills/official_skill_distribution.py tests/application/skills/test_official_skill_distribution.py` - passed after formatting.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pyright src/universal_memory/application/skills/official_skill_distribution.py tests/application/skills/test_official_skill_distribution.py` - passed with 0 errors.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest` - 759 passed and 7 failed in concurrent Story 5.9/5.10 onboarding/CLI work; failures were limited to `tests/interfaces/cli/test_init_command.py` and init CLI/MCP parity, outside the 6.13 file set.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff check .` - 6.13 files passed; the full check reported 10 issues in concurrent `src/universal_memory/application/onboarding/agent_connections.py` and `src/universal_memory/interfaces/cli/init_command.py` changes.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff format --check .` - 6.13 files passed; the full check reported 5 concurrent Story 5.8/5.9/5.10 files requiring formatting.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pyright` - 6.13 files passed; the full check reported one missing return in concurrent `src/universal_memory/interfaces/cli/init_command.py` work.
- `git diff --check` - passed.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest tests/application/skills/test_official_skill_distribution.py -q` - review remediation RED first failed at collection for the missing pin contract, then exposed strict-frontmatter and packaged-asset failures; final run passed with 30 tests.
- Skill-creator `quick_validate.py` against `skills/universal-memory` - passed with `Skill is valid!`.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest tests/application/skills -q` - 160 passed.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest` - 795 passed.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff check .` - passed.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff format --check src/universal_memory/application/skills/official_skill_distribution.py src/universal_memory/application/skills/validate_skill.py tests/application/skills/test_official_skill_distribution.py` - all 6.13 Python files formatted.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff format --check .` - reported nine concurrent Story 5.8/5.9/5.10 files requiring formatting; no 6.13 file was listed.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pyright` - passed with 0 errors.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest tests/packaging/test_official_skill_release.py tests/packaging/test_version_metadata.py tests/application/skills/test_official_skill_distribution.py -q` - final release-remediation focus passed with 41 tests.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff check <6.13 release files>` - passed for all release-remediation files.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff format --check <6.13 release files>` - passed with all six release-remediation Python files already formatted.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pyright <6.13 release files>` - passed with 0 errors.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv lock --check` - passed with 103 packages resolved.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest` - 818 passed and one failed in concurrent MCP initialization wiring: the MCP adapter did not receive the host setup dependency used by Story 5.10 connection execution.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff check .` - 6.13 files passed; the only global issue was import order in concurrent `src/universal_memory/infrastructure/config/__init__.py` work.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff format --check .` - 6.13 files passed; the only files listed were concurrent `src/universal_memory/domain/entities/runtime.py` and `tests/interfaces/cli/test_agent_connect_command.py` work.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pyright` - passed with 0 errors after release remediation.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest tests/packaging/test_official_skill_release.py -q` - second review remediation started RED with eight contract failures for the missing one-build artifact flow and protected-main ancestry gate.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest tests/packaging/test_official_skill_release.py tests/packaging/test_version_metadata.py tests/application/skills/test_official_skill_distribution.py -q` - final second-review focus passed with 44 tests.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff check src/universal_memory/application/skills/official_skill_release.py scripts/validate_official_skill_release.py tests/packaging/test_official_skill_release.py` - passed.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pyright src/universal_memory/application/skills/official_skill_release.py scripts/validate_official_skill_release.py tests/packaging/test_official_skill_release.py` - passed with 0 errors.
- YAML safe-load of `.github/workflows/publish.yml` - passed and confirmed the SHA-256 job output contract is present.
- Local `uv build --help` and `uv publish --help` checks confirmed the exact wheel-build flags and explicit file publication contract used by the workflow.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pytest` - final shared-worktree gate passed with 823 tests.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff check .` - final shared-worktree gate passed.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff format --check .` - final shared-worktree gate passed with 212 files already formatted.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run pyright` - final shared-worktree gate passed with 0 errors.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv lock --check` - final shared-worktree gate passed with 103 packages resolved.
- `git diff --check` - final second-review gate passed.
- `uv run pytest tests/application/onboarding tests/application/skills/test_official_skill_distribution.py tests/infrastructure/onboarding tests/interfaces/cli/test_agent_connect_command.py -q` - Task 8 focused gate passed with 74 tests and no real `npx` or network execution.
- `uv run pytest` - Task 8 integrated gate passed with 839 tests.
- `uv run ruff check .` - Task 8 global lint gate passed.
- `uv run ruff format --check .` - Task 8 global format gate passed with 215 files already formatted.
- `uv run pyright` - Task 8 global type gate passed with 0 errors.
- `git diff --check` - Task 8 final whitespace gate passed.
- `uv run pytest tests/application/onboarding tests/application/skills/test_official_skill_distribution.py tests/infrastructure/onboarding tests/interfaces/cli/test_agent_connect_command.py -q` - final Task 8 review-remediation gate passed with 91 hermetic tests.
- `uv run pytest` - final integrated gate passed with 856 tests after aligning the public zero-flag onboarding documentation contract.
- `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright` - final global gates passed with 0 errors and 215 files formatted.
- `uv lock --check` and `git diff --check` - final lock and whitespace gates passed.
- `uv run pytest` - canonical-skill, one-shot-installer, failure-propagation, and RC
  provenance gate passed with 874 tests.
- `UV_CACHE_DIR=/tmp/umem-uv-cache uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright` - final consolidation gates passed with 0 errors and 219 files formatted.
- `uv run python scripts/sync_official_skill_resources.py --check` and skill-creator `quick_validate.py skills/universal-memory` - generated package-resource parity and open Agent Skills validation passed.
- `UV_CACHE_DIR=/tmp/umem-build-cache uv build --wheel --out-dir /tmp/umem-build-output --clear --no-create-gitignore` plus release-focused tests - wheel build passed and all 44 release/distribution tests passed.
- Podman E2E with Pi `0.73.1`, Codex `0.146.0`, Claude Code `2.1.220`, and
  `skills@1.5.20` - main `0.4.0` to worktree `0.5.0` evolution passed for all three
  projects; local one-shot installation and byte-exact trees passed for all three targets.
- Podman production-source E2E - correctly exposed the absent `v0.5.0` remote tag and
  reproduced an incorrect CLI exit `0`; regression coverage now requires exit `1` and
  `ok: false` for authorized external installation failures.
- `uv build --wheel --out-dir /tmp/umem-rc-build --clear --no-create-gitignore` - built
  `universal_memory-0.5.0rc1-py3-none-any.whl` successfully.

### Completion Notes List

- Added the official repository-discoverable `universal-memory` Agent Skill with strict open Agent Skills frontmatter, concise activation/preflight guidance, and relative progressive-disclosure references for Directed CLI operation, memory safety, confirmations, and reporting.
- Added a compact `AGENTS.md` bootstrap asset that remains under 100 words and provides the minimum instruction-plus-CLI fallback without duplicating the full skill.
- Added pure `OfficialSkillDistributionPlanner.plan(agent, environment, ...)` application API returning `external_action`, `managed_fallback`, or `pending` without probing the system, writing files, invoking subprocesses, or coupling to CLI/onboarding.
- External plans default to deterministic project-scoped copy installation, expose immutable argv and environment separately, disable anonymous telemetry, require confirmation, and disclose network use plus the external snapshot/audit/rollback boundary.
- Explicit global and copy inputs add only their corresponding external installer flags.
- Missing Node.js, `npx`, network, or agent mapping yields ordered declared fallbacks and never blocks core initialization or claims readiness.
- Every plan remains `ready=false` and requires instruction presence, UMEM CLI availability, and a successful project context read before the integrating onboarding story may report success.
- Kept Tier 1 classification, registry behavior, existing project onboarding/templates, CLI/MCP adapters, and external execution out of scope.
- Packaged an exact mirror of the public skill under `universal_memory` resources and added a real wheel-content test so no-Node, no-`npx`, and no-network fallbacks remain available after tool installation.
- Pinned the reviewed external installer version and the official skill source tag to the installed UMEM release, preserving deterministic CLI/skill compatibility.
- Hardened application inputs against non-boolean probe values and terminal control characters while retaining immutable argv and environment metadata.
- Added regression coverage against proprietary Agent Skills fields and against every real CLI command/option taught by the portable workflow.
- Advanced the prerelease feature line to `0.5.0rc1` so the exact remote installer can be
  exercised against `v0.5.0rc1` before promotion to the final `v0.5.0` tag.
- Added an injectable immutable source ref for development while keeping the published plan tied to the installed version's release tag.
- Added a release provenance gate that proves tag/version/commit identity and byte-for-byte parity across public source, packaged resources, and built wheel contents.
- Hardened the PyPI workflow so only the validation job checks out the explicit release tag and `workflow_dispatch` can validate an existing tag but cannot publish it.
- Isolated wheel-test `uv` caches under `tmp_path` so packaging coverage never writes to a user cache.
- Replaced the rebuild-based publication path with one wheel built at the validated tag commit, uploaded under a commit-bound artifact name, downloaded without another source checkout, SHA-256 verified, and passed explicitly to `uv publish`.
- Added protected-ref provenance using `git merge-base --is-ancestor`: prereleases must
  belong to freshly fetched `origin/dev`, while final releases must belong to
  `origin/main`, rather than trusting mutable release metadata.
- Wired the official environment probe and planner into real CLI `init` and `connect` composition, with reviewed zero-flag detection plus safe explicit external agent IDs without copying the external catalog into UMEM support tiers.
- Added fail-closed external execution authority: JSON, non-interactive, and non-prompted explicit-selection plans remain planning-only unless `--yes` grants explicit authority; the existing interactive combined confirmation grants authority once.
- Added a pinned subprocess executor with exact official argv provenance, resolved `npx`, project working directory, `shell=False`, bounded timeout, UTF-8 replacement decoding, allowlisted inherited environment, disabled telemetry, sanitized captures, and non-fatal failure outcomes.
- Added a package-pinned local target catalog, preflight conflict/idempotency checks, one consent-gated project installation, and byte-exact validation of the complete packaged skill tree before a fresh context read can report readiness.
- Corrected pinned `skills@1.5.20` behavior to deterministic project-scoped `--copy`; unsupported symlink semantics are rejected instead of being falsely disclosed.
- Persisted validated generic agent targets and complete-tree hashes for no-prompt reuse, isolated npm home/cache/config and registry provenance, and recorded sanitized attempt/outcome audit events with the explicit external unmanaged boundary and no snapshot/rollback coverage.
- Updated the public README and user documentation to lead with `uv tool install universal-memory`, zero-flag `umem init`, one combined confirmation, and `umem connect` for later additions; explicit runtime selection remains an advanced automation path.
- Consolidated public distribution, packaged fallback, project seed, and native consumption around the complete `universal-memory` skill; package resources are generated and parity-checked rather than separately authored.
- Replaced the three-process staged installer with one `npx skills add` at the catalog-pinned target, preserving an isolated npm home/cache and full post-install verification.
- Propagated authorized external installer failures through `init` and `connect` as a
  non-zero process exit and `ok: false` while retaining structured diagnostics.

### File List

- `_bmad-output/implementation-artifacts/6-13-package-and-distribute-official-umem-agent-skill.md`
- `.github/workflows/publish.yml`
- `CHANGELOG.md`
- `README.md`
- `docs/index.md`
- `docs/overrides/main.html`
- `docs/users/cli.md`
- `docs/users/getting-started.md`
- `pyproject.toml`
- `scripts/sync_official_skill_resources.py`
- `scripts/validate_official_skill_release.py`
- `src/universal_memory/__init__.py`
- `skills/universal-memory/SKILL.md`
- `skills/universal-memory/assets/agents-md-bootstrap.md`
- `skills/universal-memory/references/cli-mcp-parity.md`
- `skills/universal-memory/references/guardrails-and-recording.md`
- `skills/universal-memory/references/host-instructions-sync.md`
- `skills/universal-memory/references/memory-facts.md`
- `skills/universal-memory/references/skills-lifecycle.md`
- `skills/universal-memory/references/startup-and-context.md`
- `src/universal_memory/application/skills/official_skill_assets.py`
- `src/universal_memory/application/skills/official_skill_distribution.py`
- `src/universal_memory/application/skills/official_skill_release.py`
- `src/universal_memory/application/skills/validate_skill.py`
- `src/universal_memory/application/onboarding/__init__.py`
- `src/universal_memory/application/onboarding/agent_connections.py`
- `src/universal_memory/application/onboarding/execute_agent_connections.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/infrastructure/onboarding/__init__.py`
- `src/universal_memory/infrastructure/onboarding/official_skill_bridge.py`
- `src/universal_memory/infrastructure/onboarding/pinned_skills_catalog.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/resources/skills/universal-memory/SKILL.md`
- `src/universal_memory/resources/skills/universal-memory/assets/agents-md-bootstrap.md`
- `src/universal_memory/resources/skills/universal-memory/references/cli-mcp-parity.md`
- `src/universal_memory/resources/skills/universal-memory/references/guardrails-and-recording.md`
- `src/universal_memory/resources/skills/universal-memory/references/host-instructions-sync.md`
- `src/universal_memory/resources/skills/universal-memory/references/memory-facts.md`
- `src/universal_memory/resources/skills/universal-memory/references/skills-lifecycle.md`
- `src/universal_memory/resources/skills/universal-memory/references/startup-and-context.md`
- `tests/application/skills/test_official_skill_distribution.py`
- `tests/application/onboarding/test_agent_connections.py`
- `tests/application/onboarding/test_execute_agent_connections.py`
- `tests/infrastructure/onboarding/test_official_skill_bridge.py`
- `tests/infrastructure/onboarding/test_pinned_skills_catalog.py`
- `tests/docs/test_mkdocs_content_contracts.py`
- `tests/interfaces/cli/test_agent_connect_command.py`
- `tests/packaging/test_official_skill_release.py`
- `tests/packaging/test_version_metadata.py`
- `uv.lock`

### Change Log

- 2026-07-31: Created the BMAD dev-story artifact and moved it to `in-progress` before implementation.
- 2026-07-31: Implemented the official portable skill assets and pure distribution planner through TDD, recorded validation results, and moved the story to `review`.
- 2026-07-31: Resolved independent review findings for open-standard frontmatter, wheel packaging, deterministic version pins, strict input validation, and external contract tests; returned the story to `review`.
- 2026-07-31: Resolved the residual release-safety review with the `0.5.0` feature bump, immutable source refs, tag/commit/asset provenance gates, validation-only manual dispatch, and isolated wheel caches; returned the story to `review`.
- 2026-07-31: Resolved the final artifact-identity review by building once, validating protected-main ancestry, propagating commit and wheel SHA-256, and publishing only the downloaded validated bytes; returned the story to `review`.
- 2026-07-31: Independent final review approved the release-safe distribution with no remaining findings; 823 integrated tests and all quality gates passed.
- 2026-07-31: Reopened Task 8, implemented the consent-gated optional bridge through real CLI onboarding with independent post-install validation, corrected pinned copy semantics, passed 839 integrated tests and all quality gates, and returned the story to `review`.
- 2026-07-31: Resolved the adversarial Task 8 review with safe generic-target staging, full-tree verification, pinned display-name aliases, persisted validated connections, isolated npm execution, production audit coverage, complete pre-confirmation disclosure, and zero-flag public onboarding docs; independent re-review approved the result and the story moved to `done` after 856 integrated tests and all quality gates passed.
- 2026-08-01: Consolidated the complete canonical skill across public, packaged, and initialized flows; added the package-pinned target catalog; changed external installation to one `npx skills add`; preserved the frozen Windsurf adapter and legacy `use-universal-memory` alias.
