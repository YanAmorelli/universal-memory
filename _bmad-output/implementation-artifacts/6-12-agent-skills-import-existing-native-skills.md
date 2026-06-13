# Story 6.12: Agent Skills Import Existing Native Skills

Status: done

## Story

As a user who already has native Agent Skill directories outside UMEM,
I want to import an existing skill directory into the canonical `.umem/skills` registry,
so that UMEM can manage the skill as a first-class canonical Agent Skill without requiring recommendation, promotion, or manual recreation.

## Acceptance Criteria

1. **Given** an existing native or local skill directory containing a valid `SKILL.md`, **When** `umem skills import <path> --scope project --format json` runs, **Then** the system validates the source skill, copies the complete source directory into `.umem/skills/<slug>/`, registers an `AgentSkill` record in `.umem/memory/skills.jsonl`, and returns the canonical path, affected paths, audit reference, snapshot reference, and warnings.
2. **Given** the import source path points to a `SKILL.md` file instead of a directory, **When** import runs, **Then** the parent directory is treated as the import source, the copied canonical skill still lands under `.umem/skills/<slug>/`, and response paths remain relative to the project root when possible.
3. **Given** imported `SKILL.md` frontmatter is missing required Agent Skills metadata, has invalid YAML/frontmatter shape, or contains empty `name`/`description`, **When** import runs, **Then** it fails before writing canonical files, native targets, or registry records, and maps the error through the existing `ValidationFailedError` CLI/MCP policy.
4. **Given** imported skill content contains secrets or unsafe content detected by the existing scanner, **When** import runs, **Then** the mutation is blocked before persistence and no canonical or native target files are created.
5. **Given** a skill with the same slug already exists in `.umem/skills/` or the canonical registry, **When** import runs without an explicit overwrite/adopt option, **Then** UMEM does not overwrite the existing canonical skill and returns an actionable validation error explaining the conflict.
6. **Given** import succeeds, **When** `umem skills list --format json` or `umem skills detail <id-or-name> --format json` runs, **Then** the imported skill appears as a canonical skill with `origin` set to `cli` or `mcp`, `metadata.creation_flow` set to `import`, `metadata.recommendation_flow` set to `false`, and no dependency on `latent_skills.jsonl`.
7. **Given** supported native runtimes are enabled, **When** import runs with default target behavior, **Then** UMEM may register the source native location as a managed installation only when it corresponds to a supported runtime target and content matches the imported canonical copy; it must not overwrite unrelated native targets by default.
8. **Given** the caller passes `--replace-native` in CLI or `replace_native=true` in MCP for a supported native source target, **When** import succeeds, **Then** UMEM rewrites that source target from the canonical copy through the existing safe-write pipeline and records target status, audit references, and snapshots.
9. **Given** MCP calls `import_skill(path, scope="project", replace_native=false)`, **When** the import succeeds or fails, **Then** it delegates to the same application use case as CLI, returns the same semantic payload as CLI JSON, and maps domain errors through the existing JSON-RPC error policy.
10. **Given** this story is implemented, **When** the public interface parity tests run, **Then** CLI `skills import` and MCP `import_skill` are represented in parity coverage without introducing `skills recommend`, `skills promote`, or `skills sync` capabilities.

## Tasks / Subtasks

- [x] **Task 1: Add import use case and result contract** (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [x] Create `ImportSkillCommand`, `ImportSkillResult`, and `ImportSkillUseCase` under `src/universal_memory/application/skills/import_skill.py`.
  - [x] Accept source `path`, `scope`, `origin`, and `replace_native` inputs; keep the first implementation to project/global canonical import only.
  - [x] Reuse existing frontmatter parsing/validation behavior from `update_skill._parse_skill_markdown` or extract a small shared validator if necessary.
  - [x] Normalize source file vs directory input and reject missing paths, regular files other than `SKILL.md`, and directories without `SKILL.md`.
  - [x] Derive the canonical slug from frontmatter `name` using the same slug rules as direct create; do not silently create `-2` variants for import conflicts.
- [x] **Task 2: Copy source directory into canonical `.umem/skills` safely** (AC: 1, 2, 3, 4, 5)
  - [x] Copy all regular files from the source skill directory, preserving relative structure such as `scripts/` and `references/`.
  - [x] Reject absolute path traversal, symlink traversal, and files outside the source directory.
  - [x] Persist each copied file through `SafeWriteUseCase`; do not use direct writes for production mutations.
  - [x] Scan all imported file contents before persistence using the existing safe-write/secret-scanner pipeline.
  - [x] If any write or registry operation fails after partial canonical copy, clean up files created by this import attempt.
- [x] **Task 3: Register canonical AgentSkill metadata** (AC: 1, 5, 6)
  - [x] Write an `AgentSkill` record through `AgentSkillRepository` with `status=active`, `canonical_path`, `content_hash`, `audit_reference`, and `native_installations`.
  - [x] Store `metadata.triggers` from frontmatter when present.
  - [x] Store `metadata.creation_flow = "import"`, `metadata.recommendation_flow = false`, and a safe relative `metadata.import_source` when the source is under the project root.
  - [x] Ensure import does not create or modify `latent_skills.jsonl`.
  - [x] Ensure existing list/detail use cases surface the imported canonical skill without special adapter logic.
- [x] **Task 4: Handle native source adoption/replacement conservatively** (AC: 7, 8)
  - [x] Detect whether the source directory matches a configured `RuntimeRegistry.native_skill_targets` path for a supported runtime.
  - [x] On default import, report the matching native source as an installation only if its hash matches the canonical copy; otherwise return a warning and leave it unmanaged.
  - [x] When `replace_native` is true and the source is a supported native target, rewrite the source target from canonical content through `NativeSkillSync` or equivalent safe-write logic.
  - [x] Keep unrelated native targets untouched; do not implement broad `skills sync` in this story.
- [x] **Task 5: Expose import through CLI and MCP** (AC: 1, 2, 9, 10)
  - [x] Add `umem skills import <path>` to `src/universal_memory/interfaces/cli/init_command.py` with `--scope`, `--replace-native`, and `--format json` support.
  - [x] Add `import_skill` MCP tool to `src/universal_memory/interfaces/mcp/server.py` with semantic parity to CLI JSON.
  - [x] Wire the import use case in `src/universal_memory/bootstrap/cli.py` and `src/universal_memory/bootstrap/mcp.py`.
  - [x] Export import command/use case types from `src/universal_memory/application/skills/__init__.py`.
  - [x] Update interface parity tests so public CLI/MCP import support is required.
- [x] **Task 6: Add focused tests before/with implementation** (AC: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
  - [x] Add application tests for directory import, `SKILL.md` file input, invalid frontmatter rejection, duplicate slug rejection, scanner rejection, and cleanup on registry failure.
  - [x] Add repository/list/detail integration coverage proving imported skills are canonical records and latent records are untouched.
  - [x] Add CLI tests for human and JSON output, including `--replace-native` argument mapping.
  - [x] Add MCP tests for `import_skill` command mapping, success envelope, validation error mapping, and parity inventory.
  - [x] Add native-source tests for default conservative adoption and explicit replacement behavior.
- [x] **Task 7: Validate and prepare for review** (AC: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
  - [x] Run focused tests: `uv run pytest tests/application/skills/test_import_skill.py tests/interfaces/cli/test_skills_import.py tests/interfaces/mcp/test_skills.py tests/interfaces/test_parity.py`.
  - [x] Run regression tests: `uv run pytest tests/application/skills/test_create_skill.py tests/application/skills/test_list_skills.py tests/infrastructure/storage/test_local_agent_skill_repository.py`.
  - [x] Run full quality checks if feasible: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright`.
  - [x] Move this story to `review` only after implementation and validation are complete.

## Dev Notes

- **Spec source:** `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`, Phase 3 and acceptance criteria around canonical registry/import. This story intentionally implements only Phase 3 import.
- **Strict scope boundary:** Do not implement `skills recommend`, `recommend_skills`, `skills promote`, `promote_skill_recommendation`, or broad `skills sync` in this story. Do not change latent recommendation thresholds, promotion behavior, or host instruction guidance.
- **Existing foundation:** Story 6.7 added `AgentSkill`, `AgentSkillRepository`, `LocalAgentSkillRepository`, `CreateSkillUseCase`, CLI `skills create`, MCP `create_skill`, canonical list/detail support, and native sync behavior. Reuse those patterns rather than creating a separate registry model.
- **Recent instruction loop:** Story 6.8 completed agent-facing latent skill guidance. This import story should not alter `.umem/skills/use-universal-memory/SKILL.md`, `AGENTS.md`, or `CLAUDE.md` unless a test fixture absolutely requires generated output updates.
- **Architecture constraints:** Follow Clean Architecture: `domain` defines entities/ports, `application` owns import logic, `infrastructure` owns storage, and CLI/MCP remain thin adapters. No adapter may copy files, write repositories, or bypass `SafeWriteUseCase`.
- **Canonical source of truth:** After import, `.umem/skills/<slug>/` is authoritative for the imported skill. Native host directories remain materialized targets or optional adopted installations, not the long-term source.
- **Validation source:** Current `_parse_skill_markdown` lives in `src/universal_memory/application/skills/update_skill.py` and validates frontmatter fields used by update/create. If sharing it avoids duplication, extract carefully without weakening existing tests.
- **Direct create reference:** `CreateSkillUseCase` currently renders/validates direct skill creation, writes canonical `SKILL.md`, calls `NativeSkillSync`, registers through `AgentSkillRepository`, and cleans up canonical/native files on registry failure. Import should mirror the cleanup discipline for multi-file directory copies.
- **Repository contract:** `LocalAgentSkillRepository` persists canonical records to `.umem/memory/skills.jsonl` for project scope and the global UMEM memory root for global scope. Do not overload `.umem/memory/latent_skills.jsonl`.
- **Native target guardrail:** `NativeSkillSync` already preserves unmanaged native targets by default and warns instead of overwriting. Import must preserve that safety posture. Replacement of the source native folder is explicit and narrow; broad sync/repair remains a later story.
- **Path handling:** Payloads should use relative paths when under the project root or global UMEM root. Avoid leaking absolute project paths in persisted metadata or JSON output unless the source path is necessarily external and no safe relative form exists.
- **Expected public command shape:** `umem skills import <path> --scope project --replace-native --format json`. Default scope should match direct create behavior (`project`) if the existing CLI conventions allow it.
- **Expected MCP shape:** `import_skill(path, scope="project", replace_native=false)`. Keep output semantically aligned with CLI JSON and existing `_skill_create_success_envelope` style where possible.

## References

- `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`
- `_bmad-output/implementation-artifacts/6-7-agent-skills-canonical-registry-and-direct-create.md`
- `_bmad-output/implementation-artifacts/6-8-agent-instruction-loop-for-latent-skills.md`
- `_bmad-output/planning-artifacts/epics.md` (Epic 6, FR20-FR21, FR31-FR32)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md`
- `src/universal_memory/application/skills/create_skill.py`
- `src/universal_memory/application/skills/update_skill.py`
- `src/universal_memory/application/skills/native_skill_sync.py`
- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/domain/entities/agent_skill.py`
- `src/universal_memory/domain/ports/agent_skill_repository.py`
- `src/universal_memory/infrastructure/storage/local_agent_skill_repository.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`

## Dev Agent Record

### Agent Model Used

gpt-5.5

### Debug Log References

- `uv run pytest tests/application/skills/test_import_skill.py tests/interfaces/cli/test_skills_import.py tests/interfaces/mcp/test_skills.py tests/interfaces/test_parity.py`
- `uv run pytest tests/application/skills/test_create_skill.py tests/application/skills/test_list_skills.py tests/infrastructure/storage/test_local_agent_skill_repository.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pyright`
- `uv run pytest tests/application/skills/test_import_skill.py tests/interfaces/test_parity.py`

### Completion Notes List

- Implemented canonical import use case for existing `SKILL.md` directories/files.
- Added safe multi-file canonical copy, duplicate slug rejection, scanner blocking, registry cleanup, and conservative native-source adoption/replacement.
- Exposed `umem skills import <path>` and MCP `import_skill` using the same application use case.
- Added focused application, CLI, MCP, parity, and compliance coverage for import.
- Warden follow-up fixes: `replace_native=True` now restores the pre-existing native source tree if registry write fails after native replacement, and root source directory symlinks are rejected before resolving the import input.
- Added import-specific parity coverage that only wires `import_skill` CLI/MCP dependencies; broader parity inventory also contains adjacent phase capabilities from other active worktree changes, but Story 6.12 validation no longer depends on those capabilities.
- Warden re-review found no open issues; final validation is green: full pytest, ruff check, ruff format check, and pyright pass.

### File List

- `_bmad-output/implementation-artifacts/6-12-agent-skills-import-existing-native-skills.md`
- `src/universal_memory/application/skills/import_skill.py`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/skills/test_import_skill.py`
- `tests/interfaces/cli/test_skills_import.py`
- `tests/interfaces/mcp/test_skills.py`
- `tests/interfaces/test_parity.py`
- `tests/interfaces/mcp/test_compliance.py`

### Change Log

- 2026-06-12: Created BMAD story for import phase with status `ready-for-dev` and strict scope excluding recommend, promote, and broad sync.
- 2026-06-12: Implemented import flow and moved story to review.
- 2026-06-13: Addressed Warden review fixes for native rollback, symlink rejection, import-specific parity coverage, and completed Dev Agent Record.
- 2026-06-13: Warden re-review found no open issues; moved story to done after final validation passed.
