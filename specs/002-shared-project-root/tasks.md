# Tasks: Shared Project Root

**Input**: Design documents from `specs/002-shared-project-root/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included because the specification, contracts, and quickstart define independent validation scenarios for layout initialization, migration, operational privacy, doctor diagnostics, CLI behavior, MCP behavior, and parity.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently after the shared layout foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or depends only on completed phases
- **[Story]**: User story label from `spec.md`
- All paths are project-relative

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add empty extension points and test helpers so the layout feature can be implemented without scattering ad hoc fixtures.

- [ ] T001 Create the layout application package exports in `src/universal_memory/application/layout/__init__.py`
- [ ] T002 [P] Add shared layout application test fixtures in `tests/application/layout/conftest.py`
- [ ] T003 [P] Add storage path fixture helpers for legacy, shared, and private layouts in `tests/infrastructure/storage/conftest.py`
- [ ] T004 [P] Extend interface fixture helpers for layout CLI and MCP payload assertions in `tests/interfaces/conftest.py`
- [ ] T005 [P] Add shared root documentation assertions to the docs test helper coverage in `tests/docs/test_mkdocs_content_contracts.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the layout data model, resolver, and storage routing that every user story depends on.

**Critical**: No user story work should begin until this phase is complete.

### Tests for Foundational Layout Behavior

- [ ] T006 [P] Add layout metadata validation tests for `umem/project.toml`, relative paths, precedence, and invalid roots in `tests/infrastructure/test_project_layout.py`
- [ ] T007 [P] Add fact repository path routing tests for legacy, shared, private, and global facts in `tests/infrastructure/storage/test_local_fact_repository.py`
- [ ] T008 [P] Add rule repository path routing tests for legacy, shared, private, and global rules in `tests/infrastructure/storage/test_local_rule_repository.py`
- [ ] T009 [P] Add agent skill repository path routing tests for shared, operational, private, and global project skills in `tests/infrastructure/storage/test_local_agent_skill_repository.py`
- [ ] T010 [P] Add safe write path tests proving shared content uses `umem/` while locks, audit, and snapshots stay under `.umem/` in `tests/application/security/test_safe_write_use_case.py`

### Implementation for Foundational Layout Behavior

- [ ] T011 Expand layout domain models, enums, visibility values, precedence values, and report dataclasses in `src/universal_memory/domain/project_layout.py`
- [ ] T012 Extend project layout port contracts for inspect, resolve, metadata write, and migration report operations in `src/universal_memory/domain/ports/project_layout_port.py`
- [ ] T013 Implement shared layout metadata loading, validation, and `umem/project.toml` rendering in `src/universal_memory/infrastructure/config/project_layout.py`
- [ ] T014 Extend TOML config loading so committed `umem/project.toml` can influence project layout without replacing `.umem/config.toml` in `src/universal_memory/infrastructure/config/toml_loader.py`
- [ ] T015 Add project fact storage routing, private fact path support, shared-over-legacy precedence, and `.umem/locks` lock placement in `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- [ ] T016 Add project rule storage routing, private rule path support, shared-over-legacy precedence, and `.umem/locks` lock placement in `src/universal_memory/infrastructure/storage/local_rule_repository.py`
- [ ] T017 Add project skill registry routing, shared canonical root support, operational skill root support, and shared-over-legacy precedence in `src/universal_memory/infrastructure/storage/local_agent_skill_repository.py`
- [ ] T018 Add layout resolver dependencies to CLI bootstrap wiring for repositories and layout use cases in `src/universal_memory/bootstrap/cli.py`
- [ ] T019 Add layout resolver dependencies to MCP bootstrap wiring for repositories and layout use cases in `src/universal_memory/bootstrap/mcp.py`
- [ ] T020 Export new layout commands and repository-aware use cases from package initializers in `src/universal_memory/application/__init__.py`

**Checkpoint**: Layout resolution, storage routing, and safe path handling are ready for user stories.

---

## Phase 3: User Story 1 - Share Curated Project Memory (Priority: P1) MVP

**Goal**: New shared-layout projects store curated project facts, project rules, and user-facing project skills under `umem/` while operational state remains under `.umem/`.

**Independent Test**: Initialize a shared-layout project, record a project memory, create a user-facing project skill, and confirm the shared files are visible under `umem/` while operational files remain local under `.umem/`.

### Tests for User Story 1

- [ ] T021 [P] [US1] Add CLI tests for `umem init --layout shared` output and created paths in `tests/interfaces/cli/test_init_command.py`
- [ ] T022 [P] [US1] Add MCP tests for `initialize_project(layout="shared")` output and created paths in `tests/interfaces/mcp/test_compliance.py`
- [ ] T023 [P] [US1] Add project fact visibility tests for shared and private writes in `tests/application/memory/test_memory_use_cases.py`
- [ ] T024 [P] [US1] Add project fact list visibility filter tests for shared, private, all, and legacy labels in `tests/application/memory/test_memory_use_cases.py`
- [ ] T025 [P] [US1] Add user-facing project skill creation tests for shared canonical paths in `tests/application/skills/test_create_skill.py`
- [ ] T026 [P] [US1] Add layout status tests for legacy, shared, partial, and uninitialized projects in `tests/application/layout/test_inspect_project_layout.py`

### Implementation for User Story 1

- [ ] T027 [US1] Add `layout` input and shared layout result fields to setup project models in `src/universal_memory/application/onboarding/setup_project.py`
- [ ] T028 [US1] Update project initialization to create `.umem/` operational storage plus `umem/project.toml`, `umem/memory`, and `umem/skills` for shared layout in `src/universal_memory/application/onboarding/setup_project.py`
- [ ] T029 [US1] Add `--layout legacy|shared` to `umem init` and include layout fields in human, summary, and JSON output in `src/universal_memory/interfaces/cli/init_command.py`
- [ ] T030 [US1] Add `layout` support to MCP `initialize_project` and return shared path fields in `src/universal_memory/interfaces/mcp/server.py`
- [ ] T031 [US1] Implement `InspectProjectLayoutUseCase` for `layout.status` results in `src/universal_memory/application/layout/inspect_project_layout.py`
- [ ] T032 [US1] Add `umem layout status` CLI command, output formatting, and JSON envelope in `src/universal_memory/interfaces/cli/init_command.py`
- [ ] T033 [US1] Add MCP `inspect_project_layout` tool and response envelope in `src/universal_memory/interfaces/mcp/server.py`
- [ ] T034 [US1] Add project fact `visibility` input, `storage_path` output, and global-scope validation to remember fact use case in `src/universal_memory/application/memory/remember_fact_use_case.py`
- [ ] T035 [US1] Add project fact visibility filtering and legacy/shared/private labels to list facts use case in `src/universal_memory/application/memory/list_facts_use_case.py`
- [ ] T036 [US1] Add `umem remember --visibility shared|private`, `umem remember --private`, and `umem facts list --visibility` CLI handling in `src/universal_memory/interfaces/cli/init_command.py`
- [ ] T037 [US1] Add MCP `remember_fact(visibility=...)` and `list_facts(visibility=...)` support in `src/universal_memory/interfaces/mcp/server.py`
- [ ] T038 [US1] Add `visibility`, `category`, and shared canonical path handling to create skill command models in `src/universal_memory/application/skills/create_skill.py`
- [ ] T039 [US1] Add CLI `skills create --visibility shared|private --category user-facing|operational` handling and output fields in `src/universal_memory/interfaces/cli/init_command.py`
- [ ] T040 [US1] Add MCP `create_skill` visibility and category parameters in `src/universal_memory/interfaces/mcp/server.py`
- [ ] T041 [US1] Extend memory status to report active layout, shared root, operational root, and path counts in `src/universal_memory/application/memory/get_memory_status_use_case.py`
- [ ] T042 [US1] Update CLI and MCP status payload serialization for layout fields in `src/universal_memory/interfaces/cli/init_command.py`

**Checkpoint**: User Story 1 is independently testable as the MVP.

---

## Phase 4: User Story 2 - Migrate Without Breaking Existing Projects (Priority: P2)

**Goal**: Existing `.umem` projects can opt into the shared layout with an idempotent migration that preserves legacy compatibility and reports copied, skipped, private, operational, and conflicting content.

**Independent Test**: Start with a legacy project containing project memories and canonical project skills, run dry-run and apply migration twice, and confirm commands still see the same user-facing data without duplicate records.

### Tests for User Story 2

- [ ] T043 [P] [US2] Add migration dry-run, apply, and second-apply idempotency tests in `tests/application/layout/test_migrate_project_layout.py`
- [ ] T044 [P] [US2] Add migration conflict tests for overlapping fact IDs, rule IDs, and skill slugs in `tests/application/layout/test_migrate_project_layout.py`
- [ ] T045 [P] [US2] Add CLI tests for `umem layout migrate --to shared --dry-run` and `--apply` in `tests/interfaces/cli/test_layout_command.py`
- [ ] T046 [P] [US2] Add MCP tests for `migrate_project_layout(target_layout="shared")` in `tests/interfaces/mcp/test_compliance.py`
- [ ] T047 [P] [US2] Add CLI/MCP parity tests for `layout.status` and `layout.migrate` JSON operation keys in `tests/interfaces/test_parity.py`

### Implementation for User Story 2

- [ ] T048 [US2] Implement migration candidate discovery for legacy project facts, project rules, and project canonical skills in `src/universal_memory/application/layout/migrate_project_layout.py`
- [ ] T049 [US2] Implement migration classification for shared, already shared, skipped global, private, operational, and conflicting records in `src/universal_memory/application/layout/migrate_project_layout.py`
- [ ] T050 [US2] Implement idempotent copy/apply behavior and content hash comparison for facts, rules, and skill directories in `src/universal_memory/application/layout/migrate_project_layout.py`
- [ ] T051 [US2] Implement migration report persistence and `umem/project.toml` migration metadata updates in `src/universal_memory/application/layout/migrate_project_layout.py`
- [ ] T052 [US2] Add `umem layout migrate --to shared` CLI options, dry-run default, apply behavior, and output formatting in `src/universal_memory/interfaces/cli/init_command.py`
- [ ] T053 [US2] Add MCP `migrate_project_layout` tool parameters, validation, and response envelope in `src/universal_memory/interfaces/mcp/server.py`
- [ ] T054 [US2] Add overlap labels and active precedence reporting to fact, rule, and skill list behavior in `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- [ ] T055 [US2] Add overlap labels and active precedence reporting to rule list behavior in `src/universal_memory/infrastructure/storage/local_rule_repository.py`
- [ ] T056 [US2] Add overlap labels and active precedence reporting to project skill list/detail behavior in `src/universal_memory/infrastructure/storage/local_agent_skill_repository.py`
- [ ] T057 [US2] Wire layout migration use case into CLI bootstrap in `src/universal_memory/bootstrap/cli.py`
- [ ] T058 [US2] Wire layout migration use case into MCP bootstrap in `src/universal_memory/bootstrap/mcp.py`

**Checkpoint**: Existing legacy projects can migrate safely and re-run migration without duplicates.

---

## Phase 5: User Story 3 - Keep Operational Skills Private By Default (Priority: P3)

**Goal**: Operational skills such as `use-universal-memory` remain private by default, while maintainers can explicitly publish an operational skill and record that decision in `umem/project.toml`.

**Independent Test**: Initialize a shared-layout project, confirm default UMEM bootstrap guidance remains under `.umem/skills`, then explicitly share an operational skill and verify `umem/project.toml` records the allowlist decision.

### Tests for User Story 3

- [ ] T059 [P] [US3] Add shared init tests proving `use-universal-memory` remains operational under `.umem/skills` by default in `tests/application/test_setup_project.py`
- [ ] T060 [P] [US3] Add `skills share` use case tests for user-facing skills, operational confirmation, and allowlist updates in `tests/application/skills/test_share_skill.py`
- [ ] T061 [P] [US3] Add visibility and category tests for `skills import`, `skills adopt`, and `skills publish` in `tests/application/skills/test_import_skill.py`
- [ ] T062 [P] [US3] Add CLI tests for `umem skills share <skill> --category operational --yes` in `tests/interfaces/cli/test_skills_share.py`
- [ ] T063 [P] [US3] Add MCP tests for `share_skill(confirm_operational=true)` in `tests/interfaces/mcp/test_skills.py`

### Implementation for User Story 3

- [ ] T064 [US3] Add skill visibility and category convenience properties to `src/universal_memory/domain/entities/agent_skill.py`
- [ ] T065 [US3] Implement `ShareSkillUseCase` with operational confirmation, allowlist updates, and shared canonical copy behavior in `src/universal_memory/application/skills/share_skill.py`
- [ ] T066 [US3] Extend `skills import` visibility and category command handling in `src/universal_memory/application/skills/import_skill.py`
- [ ] T067 [US3] Extend `skills adopt` visibility and category command handling in `src/universal_memory/application/skills/adopt_skill.py`
- [ ] T068 [US3] Extend `skills publish` visibility and category command handling in `src/universal_memory/application/skills/draft_skill.py`
- [ ] T069 [US3] Add `umem skills share` CLI command and output formatting in `src/universal_memory/interfaces/cli/init_command.py`
- [ ] T070 [US3] Add MCP `share_skill` tool and response envelope in `src/universal_memory/interfaces/mcp/server.py`
- [ ] T071 [US3] Export and wire `ShareSkillUseCase` in `src/universal_memory/application/skills/__init__.py`
- [ ] T072 [US3] Wire `ShareSkillUseCase` into CLI bootstrap dependencies in `src/universal_memory/bootstrap/cli.py`
- [ ] T073 [US3] Wire `ShareSkillUseCase` into MCP bootstrap dependencies in `src/universal_memory/bootstrap/mcp.py`

**Checkpoint**: Operational skills stay local by default and explicit publication is reviewable.

---

## Phase 6: User Story 4 - Verify Layout Health With Doctor (Priority: P4)

**Goal**: `umem doctor` detects layout mode, hidden shared content, tracked operational state, and legacy/shared overlaps with actionable next steps.

**Independent Test**: Run doctor against healthy, legacy, partially migrated, ignored-shared-root, tracked-operational-state, and overlapping-content projects and verify pass, warning, or failure status with recovery hints.

### Tests for User Story 4

- [X] T074 [P] [US4] Add doctor use case tests for layout mode, healthy shared layout, partial layout, and missing shared metadata in `tests/application/diagnostics/test_doctor_use_case.py`
- [X] T075 [P] [US4] Add doctor use case tests for ignored `umem/`, tracked `.umem` operational paths, and non-Git warning behavior in `tests/application/diagnostics/test_doctor_use_case.py`
- [X] T076 [P] [US4] Add CLI doctor output tests for shared layout checks and warning rendering in `tests/interfaces/cli/test_doctor_command.py`
- [X] T077 [P] [US4] Add MCP doctor payload tests for `project_layout_mode`, `shared_root_visibility`, `operational_root_privacy`, and `layout_overlaps` in `tests/interfaces/mcp/test_compliance.py`

### Implementation for User Story 4

- [X] T078 [US4] Implement repository visibility inspection for ignored shared paths and tracked operational paths in `src/universal_memory/application/layout/inspect_project_layout.py`
- [X] T079 [US4] Implement overlap detection for legacy/shared facts, rules, and skills in `src/universal_memory/application/layout/inspect_project_layout.py`
- [X] T080 [US4] Extend doctor checks with layout mode, shared root visibility, operational root privacy, and layout overlaps in `src/universal_memory/application/diagnostics/doctor_use_case.py`
- [X] T081 [US4] Update CLI doctor human, summary, and JSON output to render warning status and layout recovery hints in `src/universal_memory/interfaces/cli/init_command.py`
- [X] T082 [US4] Update MCP doctor serialization for added layout checks in `src/universal_memory/interfaces/mcp/server.py`

**Checkpoint**: Doctor can validate shared layout health repeatedly after migration or repository changes.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Update user-facing guidance, parity documentation, and quickstart validation after the stories work.

- [X] T083 [P] Update user CLI documentation for shared layout commands, visibility flags, and migration examples in `docs/users/cli.md`
- [X] T084 [P] Update agent operating guidance for shared root usage, operational privacy, and when to ask before publishing context in `docs/agents/operating-protocol.md`
- [X] T085 [P] Update instruction file guidance for `AGENTS.md`, `.umem/`, and `umem/` responsibilities in `docs/agents/instruction-files.md`
- [X] T086 [P] Update skill lifecycle documentation for shared, private, and operational project skill paths in `docs/reference/skill-lifecycle.md`
- [X] T087 [P] Update CLI/MCP parity reference with `layout.status`, `layout.migrate`, visibility fields, and `share_skill` in `docs/reference/cli-mcp-parity.md`
- [X] T088 [P] Update UMEM skill memory guidance for shared root and private operational state in `.umem/skills/use-universal-memory/references/memory-facts.md`
- [X] T089 [P] Update UMEM skill lifecycle guidance for shared and operational skill decisions in `.umem/skills/use-universal-memory/references/skills-lifecycle.md`
- [X] T090 [P] Update CLI/MCP parity guidance inside the UMEM skill reference in `.umem/skills/use-universal-memory/references/cli-mcp-parity.md`
- [X] T091 Run the quickstart static check command and update validation notes if needed in `specs/002-shared-project-root/quickstart.md`
- [X] T092 Run formatting and targeted test suites, then document any deferred follow-up in `specs/002-shared-project-root/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1 MVP**: Depends on Phase 2.
- **Phase 4 US2 Migration**: Depends on Phase 2 and benefits from US1 storage behavior.
- **Phase 5 US3 Operational Privacy**: Depends on Phase 2 and can proceed after US1 skill visibility contracts are stable.
- **Phase 6 US4 Doctor**: Depends on Phase 2 and should run after enough US1/US2 behavior exists to inspect real states.
- **Phase 7 Polish**: Depends on the user stories being implemented.

### User Story Dependencies

- **US1 (P1)**: Starts after foundational layout routing. This is the MVP.
- **US2 (P2)**: Starts after foundational layout routing; migration should preserve US1 semantics.
- **US3 (P3)**: Starts after foundational layout routing and US1 skill visibility contracts.
- **US4 (P4)**: Starts after foundational layout routing; full validation is strongest after US1 and US2.

### Within Each User Story

- Add tests before implementation tasks in the same story.
- Implement application use cases before CLI/MCP surfaces.
- Wire bootstrap dependencies after application use cases exist.
- Update parity tests after CLI/MCP envelopes are defined.
- Validate each story independently at its checkpoint.

---

## Parallel Opportunities

- Setup tasks T002, T003, T004, and T005 can run in parallel after T001.
- Foundational tests T006 through T010 can run in parallel.
- Storage implementation tasks T015, T016, and T017 can run in parallel after T011 through T014.
- US1 tests T021 through T026 can run in parallel.
- US2 tests T043 through T047 can run in parallel.
- US3 tests T059 through T063 can run in parallel.
- US4 tests T074 through T077 can run in parallel.
- Documentation tasks T083 through T090 can run in parallel after implementation behavior stabilizes.

---

## Parallel Example: User Story 1

```bash
Task: "T021 [P] [US1] Add CLI tests for umem init --layout shared output and created paths in tests/interfaces/cli/test_init_command.py"
Task: "T022 [P] [US1] Add MCP tests for initialize_project(layout=\"shared\") output and created paths in tests/interfaces/mcp/test_compliance.py"
Task: "T023 [P] [US1] Add project fact visibility tests for shared and private writes in tests/application/memory/test_memory_use_cases.py"
Task: "T025 [P] [US1] Add user-facing project skill creation tests for shared canonical paths in tests/application/skills/test_create_skill.py"
```

## Parallel Example: User Story 2

```bash
Task: "T043 [P] [US2] Add migration dry-run, apply, and second-apply idempotency tests in tests/application/layout/test_migrate_project_layout.py"
Task: "T045 [P] [US2] Add CLI tests for umem layout migrate --to shared --dry-run and --apply in tests/interfaces/cli/test_layout_command.py"
Task: "T046 [P] [US2] Add MCP tests for migrate_project_layout(target_layout=\"shared\") in tests/interfaces/mcp/test_compliance.py"
Task: "T047 [P] [US2] Add CLI/MCP parity tests for layout.status and layout.migrate JSON operation keys in tests/interfaces/test_parity.py"
```

## Parallel Example: User Story 3

```bash
Task: "T060 [P] [US3] Add skills share use case tests for user-facing skills, operational confirmation, and allowlist updates in tests/application/skills/test_share_skill.py"
Task: "T061 [P] [US3] Add visibility and category tests for skills import, skills adopt, and skills publish in tests/application/skills/test_import_skill.py"
Task: "T062 [P] [US3] Add CLI tests for umem skills share <skill> --category operational --yes in tests/interfaces/cli/test_skills_share.py"
Task: "T063 [P] [US3] Add MCP tests for share_skill(confirm_operational=true) in tests/interfaces/mcp/test_skills.py"
```

## Parallel Example: User Story 4

```bash
Task: "T074 [P] [US4] Add doctor use case tests for layout mode, healthy shared layout, partial layout, and missing shared metadata in tests/application/diagnostics/test_doctor_use_case.py"
Task: "T075 [P] [US4] Add doctor use case tests for ignored umem/, tracked .umem operational paths, and non-Git warning behavior in tests/application/diagnostics/test_doctor_use_case.py"
Task: "T076 [P] [US4] Add CLI doctor output tests for shared layout checks and warning rendering in tests/interfaces/cli/test_doctor_command.py"
Task: "T077 [P] [US4] Add MCP doctor payload tests for project_layout_mode, shared_root_visibility, operational_root_privacy, and layout_overlaps in tests/interfaces/mcp/test_compliance.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational layout resolver and storage routing.
3. Complete Phase 3 for shared initialization, shared project facts, shared project skills, and layout status.
4. Stop and validate Scenario 1, Scenario 2, Scenario 3, and Scenario 7 subsets from `quickstart.md`.

### Incremental Delivery

1. Deliver US1 as the minimum useful shared-root workflow.
2. Add US2 to migrate legacy repositories without duplicate data.
3. Add US3 to enforce operational skill privacy and explicit sharing.
4. Add US4 to make layout health diagnosable before commits.
5. Finish docs and quickstart validation.

### Parallel Team Strategy

1. One engineer owns foundational domain and resolver tasks.
2. One engineer owns repository routing tasks after the resolver contracts are stable.
3. After Phase 2, split by user story: US1 storage and CLI/MCP, US2 migration, US3 skill privacy, US4 doctor.
4. Rejoin for parity, docs, and quickstart validation.

## Notes

- `umem/` is the commit-friendly shared root.
- `.umem/` remains the operational and private project root.
- `use-universal-memory` is operational and private by default.
- Global memory and global skills stay outside project shared-root migration.
- Paths in output and docs must remain project-relative.
