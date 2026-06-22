# Story 6.7: Agent Skills Canonical Registry and Direct Create

Status: done

<!-- Handover correction: this story was created after implementation started so the work can re-enter the BMAD dev-story/review flow. Do not continue new implementation on this slice until this story is reviewed against the current diff. -->

## Story

As a user or MCP-consuming agent,
I want to create a known Agent Skill directly into the canonical UMEM registry,
so that explicit skill creation does not require the legacy `track -> propose -> generate` latent recommendation path.

## Acceptance Criteria

1. **Given** a direct skill creation request with `name`, `description`, `scope`, optional `triggers`, and optional `raw_markdown`, **When** the request is executed, **Then** the system writes a valid canonical Agent Skill under `.umem/skills/<slug>/SKILL.md` for project scope or the global UMEM skill root for global scope, **And** registers a first-class canonical skill record independent from `latent_skills.jsonl`.

2. **Given** skill metadata contains YAML-sensitive content such as `:`, quotes, brackets, or newlines, **When** the canonical `SKILL.md` is rendered, **Then** frontmatter remains valid YAML and uses safe quoting or escaping.

3. **Given** a canonical skill is created, **When** supported native runtimes are enabled, **Then** native skill targets are synchronized from the canonical source using the existing native sync path, **And** target-level status, affected paths, audit references, and warnings are returned.

4. **Given** canonical skill creation fails after writing the canonical file but before registry registration completes, **When** the failure is raised, **Then** the just-created canonical file is cleaned up to avoid an orphaned UMEM-managed skill folder.

5. **Given** the CLI is used, **When** `umem skills create` runs with human output or `--format json`, **Then** it delegates to the same application use case, returns relative paths and audit/snapshot references, and follows `_bmad-output/planning-artifacts/devex-interaction-spec.md`.

6. **Given** MCP is used, **When** `create_skill(...)` is called, **Then** it delegates to the same application use case with origin `mcp`, returns the same semantic payload as CLI JSON, and maps domain errors through the existing JSON-RPC error policy.

7. **Given** `umem skills list --format json` or `umem skills detail <id-or-name> --format json` runs after direct creation, **Then** canonical skills appear without depending on latent skill records, **And** latent recommendation compatibility remains available for existing `track/propose/generate` flows.

## Tasks / Subtasks

- [x] **Task 1: Add canonical Agent Skill domain and repository contracts** (AC: 1, 7)
  - [x] Create `AgentSkill` and `AgentSkillStatus` in `src/universal_memory/domain/entities/agent_skill.py`.
  - [x] Create `AgentSkillRepository` in `src/universal_memory/domain/ports/agent_skill_repository.py`.
  - [x] Export the new entity and port through existing package `__init__.py` files.

- [x] **Task 2: Implement local canonical registry persistence** (AC: 1, 4)
  - [x] Create `LocalAgentSkillRepository` backed by `.umem/memory/skills.jsonl` for project skills and the global UMEM data root for global skills.
  - [x] Require `SafeWriteUseCase`; do not allow direct production writes that bypass snapshot, audit, or secret scanning.
  - [x] Add corruption handling, lock handling, and project/global path isolation tests.

- [x] **Task 3: Implement direct skill creation use case** (AC: 1, 2, 3, 4)
  - [x] Create `CreateSkillUseCase`, `CreateSkillCommand`, and `CreateSkillResult` in `src/universal_memory/application/skills/create_skill.py`.
  - [x] Validate normalized inputs and reject conflicting `raw_markdown` frontmatter.
  - [x] Render safe Agent Skills frontmatter when `raw_markdown` is absent.
  - [x] Strip absolute project paths from canonical content.
  - [x] Sync native targets using `NativeSkillSync` and pass the correct canonical base path for project and global scopes.
  - [x] Clean up the canonical `SKILL.md` if registry persistence fails after file creation.

- [x] **Task 4: Expose direct creation through CLI and MCP** (AC: 5, 6)
  - [x] Add `umem skills create` to the Typer CLI adapter in `src/universal_memory/interfaces/cli/init_command.py`.
  - [x] Add `create_skill` to `src/universal_memory/interfaces/mcp/server.py`.
  - [x] Wire use cases and repositories in `src/universal_memory/bootstrap/cli.py` and `src/universal_memory/bootstrap/mcp.py`.
  - [x] Add CLI/MCP parity coverage in `tests/interfaces/test_parity.py`.

- [x] **Task 5: Make list/detail reflect canonical registry plus latent compatibility** (AC: 7)
  - [x] Update `ListSkillsUseCase` to load canonical skills from `AgentSkillRepository`.
  - [x] Preserve latent recommendation compatibility in the list/detail payload.
  - [x] Ensure status filters still apply to latent recommendations when canonical records are present.

- [x] **Task 6: BMAD review and full validation gate** (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] Focused tests already run: `uv run pytest tests/application/skills/test_create_skill.py tests/application/skills/test_generate_skill.py tests/application/skills/test_list_skills.py tests/infrastructure/storage/test_local_agent_skill_repository.py tests/interfaces/cli/test_skills_create.py tests/interfaces/cli/test_skills_list.py tests/interfaces/mcp/test_skills.py tests/interfaces/test_parity.py`.
  - [x] Focused Ruff already run on touched files.
  - [x] Run the full test suite: `uv run pytest`.
  - [x] Run full quality checks if feasible: `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright`.
  - [x] Run final code review of the complete diff before moving this story to `done`.

### Review Findings

- [x] [Review][Patch] Direct create could overwrite unmanaged native targets with the same slug because drift detection only considered previously registered installations. Fixed by treating existing untracked native targets as unmanaged drift under `keep` and preserving them with a warning.
- [x] [Review][Patch] Registry write failure after native sync could leave newly written native target files orphaned. Fixed by cleaning native affected paths during create failure cleanup.
- [x] [Review][Patch] MCP direct create did not implement the spec's `targets` parameter or `targets=[]` native-sync disable behavior. Fixed by adding `targets` to `CreateSkillCommand`, MCP `create_skill`, and `NativeSkillSync` filtering.

## Dev Notes

- **Corrective BMAD context:** This story formalizes work that already exists in the current `chore/agent-skills-spec` worktree. Treat status `review` as intentional: the implementation must now be reviewed and validated against this story before completion.

- **Spec source:** `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`, especially Phase 1, FR1-FR5, and acceptance criteria 1-3, 9, 11.

- **Architecture constraints:** Follow Clean Architecture: `domain` defines entities/ports, `application` owns use-case logic, `infrastructure` implements storage, and CLI/MCP remain thin adapters. No adapter may write files or repositories directly.

- **Persistence contract:** Canonical Agent Skills must not overload `.umem/memory/latent_skills.jsonl`. Use `.umem/memory/skills.jsonl` or the equivalent global UMEM memory root.

- **Compatibility guardrail:** Existing `track -> propose -> generate` behavior is compatibility, not the primary path for explicit skill creation. Do not break existing latent skill tests or commands.

- **Native target guardrail:** Native host directories are materialized targets, not authoritative sources. Direct create should sync from canonical content and use `keep` as the safe drift default in non-interactive paths.

- **Known handover fixes already applied:** `NativeSkillSync.sync` accepts `canonical_base_path`; `GenerateSkillUseCase` and `CreateSkillUseCase` pass correct project/global roots; `CreateSkillUseCase` cleans up canonical `SKILL.md` on registry failure; `ListSkillsUseCase` applies status filters to latent recommendations in canonical list mode.

## References

- `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`
- `_bmad-output/planning-artifacts/prd.md` (FR18-FR21, FR31-FR32)
- `_bmad-output/planning-artifacts/architecture.md` (Clean Architecture, Mutation Pipeline, Canonical Skills vs Native Targets)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (CLI/MCP parity and JSON envelopes)
- `src/universal_memory/application/skills/create_skill.py`
- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/application/skills/native_skill_sync.py`
- `src/universal_memory/domain/entities/agent_skill.py`
- `src/universal_memory/domain/ports/agent_skill_repository.py`
- `src/universal_memory/infrastructure/storage/local_agent_skill_repository.py`

## Dev Agent Record

### Agent Model Used

OpenCode / Maestri delegated implementation prior to BMAD handover.

### Debug Log References

- Handover note `handover-agent-skills-canon` recorded that Forge implemented Phase 1 and Sentry reviewed early issues.
- Focused validation reported in the handover: 64 tests passed for create/generate/list/repository/CLI/MCP/parity slices.
- Focused `ruff check` on touched files passed per handover.

### Completion Notes List

- Canonical Agent Skill domain entity and repository port added.
- Local canonical skill registry added under `.umem/memory/skills.jsonl` with global scope support.
- Direct creation use case added with safe YAML rendering, canonical file creation, registry write, native sync, and rollback cleanup on registry failure.
- CLI `umem skills create` and MCP `create_skill` added with parity tests.
- `skills list/detail` now surface canonical records while preserving latent compatibility.
- BMAD review gate completed with full suite, full quality checks, and final review fixes.

### File List

- `_bmad-output/implementation-artifacts/6-7-agent-skills-canonical-registry-and-direct-create.md`
- `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/application/skills/create_skill.py`
- `src/universal_memory/application/skills/generate_skill.py`
- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/application/skills/native_skill_sync.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/domain/entities/__init__.py`
- `src/universal_memory/domain/entities/agent_skill.py`
- `src/universal_memory/domain/ports/__init__.py`
- `src/universal_memory/domain/ports/agent_skill_repository.py`
- `src/universal_memory/infrastructure/storage/__init__.py`
- `src/universal_memory/infrastructure/storage/local_agent_skill_repository.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/skills/test_create_skill.py`
- `tests/application/skills/test_list_skills.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/infrastructure/storage/test_local_agent_skill_repository.py`
- `tests/interfaces/cli/test_skills_create.py`
- `tests/interfaces/cli/test_skills_list.py`
- `tests/interfaces/mcp/test_skills.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-06-11: Created corrective BMAD story for already-started Agent Skills canonical registry/direct create implementation and moved it into review gate.
- 2026-06-11: Completed BMAD review gate, fixed native target overwrite/orphan cleanup/targets support findings, and validated full suite plus quality checks.
