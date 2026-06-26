# Tasks: Skill Authoring Flow

**Input**: Design documents from `specs/001-skill-authoring-flow/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/cli.md`, `contracts/mcp.md`, `quickstart.md`

**Tests**: Included because the specification and quickstart require pytest, CLI, MCP, parity, and docs validation.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently after the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks.
- **[Story]**: Maps to the user story from `spec.md`.
- Every task includes exact file paths.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare reusable test fixtures and feature scaffolding for the skill lifecycle work.

- [X] T001 [P] Add shared skill lifecycle test builders for safe writes, repositories, runtime registries, and sample AgentSkill objects in `tests/application/skills/conftest.py`
- [X] T002 [P] Add shared CLI/MCP command fixture helpers for skill lifecycle payload assertions in `tests/interfaces/conftest.py`
- [X] T003 [P] Add reusable valid and invalid skill fixture trees under `tests/fixtures/skills/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared validation, storage, export, and bootstrap primitives required by all user stories.

**Critical**: No user story work should begin until this phase is complete.

- [X] T004 Create SkillValidationReport command/result models and check result types in `src/universal_memory/application/skills/validate_skill.py`
- [X] T005 Implement shared skill content validation for frontmatter, triggers, placeholders, relative links, local references, unsafe paths, and risky commands in `src/universal_memory/application/skills/validate_skill.py`
- [X] T006 Add explicit slug and project-relative path validation helpers in `src/universal_memory/application/skills/update_skill.py`
- [X] T007 Extend AgentSkill metadata conventions for draft_path, validation, source path, and cleanup warnings in `src/universal_memory/domain/entities/agent_skill.py`
- [X] T008 Add repository helpers for read-by-slug, list-by-status, replace record, and remove record in `src/universal_memory/domain/ports/agent_skill_repository.py` and `src/universal_memory/infrastructure/storage/local_agent_skill_repository.py`
- [X] T009 Export new skill lifecycle command/result/use-case symbols from `src/universal_memory/application/skills/__init__.py`
- [X] T010 Wire new skill lifecycle dependency slots through `src/universal_memory/bootstrap/cli.py` and `src/universal_memory/bootstrap/mcp.py`

**Checkpoint**: Shared validation and repository capabilities are ready for story implementation.

---

## Phase 3: User Story 1 - Author a Skill Without Runtime Side Effects (Priority: P1) - MVP

**Goal**: Users can create, validate, and publish draft skills without writing native runtime targets until sync is explicit.

**Independent Test**: Create a draft, validate it, publish it without sync, verify canonical registration exists, and verify native runtime target directories are unchanged until sync is requested.

### Tests for User Story 1

- [X] T011 [P] [US1] Add application tests for draft creation without native sync and draft metadata in `tests/application/skills/test_draft_skill.py`
- [X] T012 [US1] Add application tests for draft validation, publish without sync, and publish with explicit sync in `tests/application/skills/test_draft_skill.py`
- [X] T013 [P] [US1] Add CLI behavior and help-text tests for `skills draft create`, `skills draft validate`, and `skills publish` in `tests/interfaces/cli/test_skills_draft.py`
- [X] T014 [P] [US1] Add MCP behavior and tool-description tests for `create_skill_draft`, `validate_skill`, and `publish_skill` in `tests/interfaces/mcp/test_skills_draft.py`
- [X] T015 [US1] Add CLI/MCP parity cases for `skills.draft.create`, `skills.validate`, and `skills.publish` in `tests/interfaces/test_parity.py`

### Implementation for User Story 1

- [X] T016 [US1] Implement CreateSkillDraftCommand, PublishSkillCommand, results, and use cases in `src/universal_memory/application/skills/draft_skill.py`
- [X] T017 [US1] Integrate SkillValidationReport checks into draft validation and publish gating in `src/universal_memory/application/skills/draft_skill.py`
- [X] T018 [US1] Change CreateSkillCommand to accept explicit slug, sync flag behavior, and canonical-only default in `src/universal_memory/application/skills/create_skill.py`
- [X] T019 [US1] Add `skills draft create`, `skills draft validate`, `skills publish`, `skills create --slug`, and `skills create --sync` CLI handling in `src/universal_memory/interfaces/cli/init_command.py`
- [X] T020 [US1] Add MCP tools and payload mapping for draft create, skill validate, and publish in `src/universal_memory/interfaces/mcp/server.py`
- [X] T021 [US1] Wire draft, publish, and validate use cases into CLI and MCP bootstraps in `src/universal_memory/bootstrap/cli.py` and `src/universal_memory/bootstrap/mcp.py`
- [X] T022 [US1] Export draft, publish, and validate commands/results from `src/universal_memory/application/skills/__init__.py`
- [X] T023 [US1] Update draft/create lifecycle guidance, including when-to-use command examples, in `docs/reference/skill-lifecycle.md` and `README.md`
- [X] T024 [US1] Validate quickstart scenarios 1 and 2 against `specs/001-skill-authoring-flow/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and delivers the MVP.

---

## Phase 4: User Story 2 - Adopt Existing Skill Work Safely (Priority: P1)

**Goal**: Users can detect and adopt existing local skill directories without unwanted suffixed duplicates.

**Independent Test**: Place a valid unregistered skill under `.umem/skills/`, run list and adopt, then verify detail/list output resolves the requested slug and no duplicate slug directory is created.

### Tests for User Story 2

- [X] T025 [P] [US2] Add application tests for adopting an existing `.umem/skills/<slug>/SKILL.md` directory in place in `tests/application/skills/test_adopt_skill.py`
- [X] T026 [US2] Add application tests for unregistered directory listing and slug conflict errors in `tests/application/skills/test_adopt_skill.py`
- [X] T027 [P] [US2] Add CLI behavior and help-text tests for `skills adopt <path>` with slug, sync, and conflict behavior in `tests/interfaces/cli/test_skills_adopt.py`
- [X] T028 [P] [US2] Add MCP behavior and tool-description tests for `adopt_skill` payloads and validation failures in `tests/interfaces/mcp/test_skills_adopt.py`
- [X] T029 [US2] Add CLI/MCP parity cases for `skills.adopt` in `tests/interfaces/test_parity.py`

### Implementation for User Story 2

- [X] T030 [US2] Implement AdoptSkillCommand, AdoptSkillResult, and AdoptSkillUseCase in `src/universal_memory/application/skills/adopt_skill.py`
- [X] T031 [US2] Refactor import behavior to share validation and conflict handling with adoption while preserving import compatibility in `src/universal_memory/application/skills/import_skill.py`
- [X] T032 [US2] Extend skill list/detail discovery to surface valid unregistered skill directories and adoption guidance in `src/universal_memory/application/skills/list_skills.py`
- [X] T033 [US2] Add `skills adopt` CLI parsing, human output, JSON payloads, and conflict errors in `src/universal_memory/interfaces/cli/init_command.py`
- [X] T034 [US2] Add `adopt_skill` MCP tool and payload mapping in `src/universal_memory/interfaces/mcp/server.py`
- [X] T035 [US2] Wire and export adoption use cases in `src/universal_memory/bootstrap/cli.py`, `src/universal_memory/bootstrap/mcp.py`, and `src/universal_memory/application/skills/__init__.py`
- [X] T036 [US2] Update adopt/import documentation with command selection guidance in `docs/reference/skill-lifecycle.md` and `README.md`

**Checkpoint**: User Story 2 is independently functional and testable.

---

## Phase 5: User Story 3 - Maintain Canonical Skills With Explicit Commands (Priority: P2)

**Goal**: Users can update, validate, rename, clean up, and repair canonical skills without manual registry edits.

**Independent Test**: Update canonical content through the supported flow, rename a slug, validate the skill, dry-run cleanup, and verify registry, canonical paths, target manifests, and output stay consistent.

### Tests for User Story 3

- [X] T037 [P] [US3] Add application tests for canonical update validation and optional sync in `tests/application/skills/test_canonical_update_skill.py`
- [X] T038 [P] [US3] Add application tests for slug rename path movement, metadata updates, target manifest updates, and unmanaged destination conflicts in `tests/application/skills/test_rename_skill.py`
- [X] T039 [P] [US3] Add application tests for cleanup and repair dry-run/apply managed-only behavior in `tests/application/skills/test_cleanup_skill.py`
- [X] T040 [P] [US3] Add CLI behavior and help-text tests for `skills canonical update`, `skills rename`, `skills validate`, `skills cleanup`, and `skills repair` in `tests/interfaces/cli/test_skills_maintenance.py`
- [X] T041 [P] [US3] Add MCP behavior and tool-description tests for `update_canonical_skill`, `rename_skill`, `cleanup_skill`, and `repair_skills` in `tests/interfaces/mcp/test_skills_maintenance.py`
- [X] T042 [US3] Add CLI/MCP parity cases for validate, canonical update, rename, cleanup, and repair in `tests/interfaces/test_parity.py`

### Implementation for User Story 3

- [X] T043 [US3] Implement canonical skill update command/result flow and validation in `src/universal_memory/application/skills/update_skill.py`
- [X] T044 [US3] Implement RenameSkillCommand, RenameSkillResult, and RenameSkillUseCase in `src/universal_memory/application/skills/rename_skill.py`
- [X] T045 [US3] Implement CleanupSkillCommand, RepairSkillsCommand, cleanup plans, and result models in `src/universal_memory/application/skills/cleanup_skill.py`
- [X] T046 [US3] Add safe record move/delete operations for canonical skill maintenance in `src/universal_memory/domain/ports/agent_skill_repository.py` and `src/universal_memory/infrastructure/storage/local_agent_skill_repository.py`
- [X] T047 [US3] Expose managed target ownership and orphan-target planning helpers in `src/universal_memory/application/skills/native_skill_sync.py`
- [X] T048 [US3] Add CLI commands for `skills canonical update`, `skills rename`, `skills validate`, `skills cleanup`, and `skills repair` in `src/universal_memory/interfaces/cli/init_command.py`
- [X] T049 [US3] Add MCP tools for validate, canonical update, rename, cleanup, and repair in `src/universal_memory/interfaces/mcp/server.py`
- [X] T050 [US3] Wire and export maintenance use cases in `src/universal_memory/bootstrap/cli.py`, `src/universal_memory/bootstrap/mcp.py`, and `src/universal_memory/application/skills/__init__.py`
- [X] T051 [US3] Improve unsupported canonical `skills update` error guidance in `src/universal_memory/application/skills/update_skill.py` and `src/universal_memory/interfaces/cli/init_command.py`
- [X] T052 [US3] Update canonical maintenance documentation with safe-flow selection guidance in `docs/reference/skill-lifecycle.md` and `README.md`

**Checkpoint**: User Story 3 is independently functional and testable.

---

## Phase 6: User Story 4 - Operate With Human-Friendly Feedback (Priority: P3)

**Goal**: Users can request concise summary output and receive actionable repository warnings without losing JSON automation detail.

**Independent Test**: Run create, adopt, sync, validate, and cleanup with `--format summary`; verify output stays concise, includes affected paths/warnings/next steps, and JSON output remains complete.

### Tests for User Story 4

- [X] T053 [P] [US4] Add CLI tests for `--format summary` on draft, create, adopt, sync, validate, and cleanup flows in `tests/interfaces/cli/test_skills_summary.py`
- [X] T054 [P] [US4] Add application tests for gitignore and tracked-target warnings during sync planning in `tests/application/skills/test_sync_skills_gitignore.py`
- [X] T055 [P] [US4] Add docs tests for summary output and gitignore warning guidance in `tests/docs/test_mkdocs_content_contracts.py`

### Implementation for User Story 4

- [X] T056 [US4] Extend CLI output format parsing and dispatch to accept `summary` in `src/universal_memory/interfaces/cli/init_command.py`
- [X] T057 [US4] Add concise skill lifecycle summary renderers for create, draft, publish, adopt, sync, validate, rename, cleanup, and repair in `src/universal_memory/interfaces/cli/init_command.py`
- [X] T058 [US4] Add `--check-gitignore` CLI plumbing and repository warning collection in `src/universal_memory/application/skills/sync_skills.py` and `src/universal_memory/application/skills/native_skill_sync.py`
- [X] T059 [US4] Preserve full JSON payload assertions while adding summary-neutral parity coverage in `tests/interfaces/test_parity.py`
- [X] T060 [US4] Extend the existing `Decision Guide For Agents`, `Canonical CLI`, `MCP Equivalents`, and `Official Workflows` sections with draft, adopt, canonical update, summary, cleanup, and repair guidance in `.umem/skills/use-universal-memory/references/skills-lifecycle.md`
- [X] T061 [US4] Add docs tests that verify help text, MCP descriptions, and existing agent-facing lifecycle guidance mention purpose, when to use, safety defaults, and neighboring alternatives in `tests/docs/test_mkdocs_content_contracts.py`

**Checkpoint**: User Story 4 is independently functional and testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, managed-skill guidance, and whole-feature validation.

- [X] T062 [P] Verify `use-universal-memory` routes skill lifecycle work to the existing lifecycle reference without creating a separate new project skill in `.umem/skills/use-universal-memory/SKILL.md`
- [X] T063 [P] Extend the existing CLI/MCP parity table and public lifecycle docs with new tool names in `.umem/skills/use-universal-memory/references/cli-mcp-parity.md`, `docs/reference/skill-lifecycle.md`, and `docs/index.md`
- [X] T064 Validate all quickstart scenarios and update expected outcomes if wording changed in `specs/001-skill-authoring-flow/quickstart.md`
- [X] T065 Run targeted feature tests with `uv run pytest tests/application/skills tests/interfaces/cli tests/interfaces/mcp tests/interfaces/test_parity.py tests/docs`
- [X] T066 Run static checks with `uv run ruff check src tests` and `uv run pyright` using `pyproject.toml`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational. Can run in parallel with User Story 1 after shared validation exists.
- **User Story 3 (Phase 5)**: Depends on Foundational and is easier after User Story 2 clarifies adoption/list semantics.
- **User Story 4 (Phase 6)**: Depends on the commands whose summary output it renders; start after at least User Story 1 and continue incrementally.
- **Polish (Phase 7)**: Depends on selected user stories being complete.

### User Story Dependencies

- **US1**: No dependency on other stories after Foundational. Delivers MVP.
- **US2**: No hard dependency on US1 after Foundational; shares validation and repository helpers.
- **US3**: Depends on shared validation and repository helpers; can be built after US1 or US2.
- **US4**: Depends on command result shapes from US1-US3 for complete summary coverage.

### Within Each User Story

- Write story-specific tests before implementation.
- Implement application use case behavior before CLI and MCP wiring.
- Wire CLI and MCP after application use cases are stable.
- Update docs after behavior and output shape are stable.
- Validate each story independently before moving to lower-priority stories.

---

## Parallel Opportunities

- Setup tasks T001-T003 can run in parallel.
- Story test files marked [P] can be created in parallel before implementation.
- Application use case modules for draft, adopt, rename, cleanup, and summary warnings can be implemented in parallel after Foundational.
- CLI and MCP tests can be authored in parallel because they use separate files.
- Documentation updates in Phase 7 can run in parallel with final validation prep.

## Parallel Example: User Story 1

```text
Task: "T011 [P] [US1] Add application tests for draft creation without native sync and draft metadata in tests/application/skills/test_draft_skill.py"
Task: "T013 [P] [US1] Add CLI tests for skills draft create, skills draft validate, and skills publish in tests/interfaces/cli/test_skills_draft.py"
Task: "T014 [P] [US1] Add MCP tests for create_skill_draft, validate_skill, and publish_skill in tests/interfaces/mcp/test_skills_draft.py"
```

## Parallel Example: User Story 2

```text
Task: "T025 [P] [US2] Add application tests for adopting an existing .umem/skills/<slug>/SKILL.md directory in place in tests/application/skills/test_adopt_skill.py"
Task: "T027 [P] [US2] Add CLI tests for skills adopt <path> with slug, sync, and conflict behavior in tests/interfaces/cli/test_skills_adopt.py"
Task: "T028 [P] [US2] Add MCP tests for adopt_skill payloads and validation failures in tests/interfaces/mcp/test_skills_adopt.py"
```

## Parallel Example: User Story 3

```text
Task: "T037 [P] [US3] Add application tests for canonical update validation and optional sync in tests/application/skills/test_canonical_update_skill.py"
Task: "T038 [P] [US3] Add application tests for slug rename path movement, metadata updates, target manifest updates, and unmanaged destination conflicts in tests/application/skills/test_rename_skill.py"
Task: "T039 [P] [US3] Add application tests for cleanup and repair dry-run/apply managed-only behavior in tests/application/skills/test_cleanup_skill.py"
```

## Parallel Example: User Story 4

```text
Task: "T053 [P] [US4] Add CLI tests for --format summary on draft, create, adopt, sync, validate, and cleanup flows in tests/interfaces/cli/test_skills_summary.py"
Task: "T054 [P] [US4] Add application tests for gitignore and tracked-target warnings during sync planning in tests/application/skills/test_sync_skills_gitignore.py"
Task: "T055 [P] [US4] Add docs tests for summary output and gitignore warning guidance in tests/docs/test_mkdocs_content_contracts.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 for draft create, validate, publish, and explicit sync.
3. Validate User Story 1 with `tests/application/skills/test_draft_skill.py`, `tests/interfaces/cli/test_skills_draft.py`, `tests/interfaces/mcp/test_skills_draft.py`, and the related parity cases.
4. Stop and review before adoption and maintenance commands.

### Incremental Delivery

1. Deliver US1 to make draft authoring safe.
2. Deliver US2 to recover existing manual skill work.
3. Deliver US3 to make canonical maintenance safe.
4. Deliver US4 to improve interactive operation and warnings.
5. Run Phase 7 validation before release.

### Parallel Team Strategy

After Foundational completes:

- Developer A: US1 draft and create-default behavior.
- Developer B: US2 adopt/list/import behavior.
- Developer C: US3 maintenance use cases.
- Developer D: US4 summary output and gitignore warnings after command payloads stabilize.

## Notes

- Keep all user-facing paths project-relative.
- Preserve existing JSON envelopes and add new keys compatibly.
- Do not delete unmanaged files during cleanup or repair.
- Native runtime sync must remain explicit outside dedicated sync commands.
