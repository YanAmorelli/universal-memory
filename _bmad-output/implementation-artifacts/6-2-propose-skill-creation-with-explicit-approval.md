# Story 6.2: Propose Skill Creation with Explicit Approval

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user controlling the evolution of the system,
I want to approve or reject the creation of a skill when a recurrence is detected,
so that the system learns without automating sensitive behavioral decisions.

## Acceptance Criteria

1. **Given** a latent skill reaches the configured recurrence trigger, **When** the proposal is presented to the user, **Then** the system offers explicit options `Yes`, `Always`, and `No`, **And** explains the suggested name, purpose, scope, and summarized evidence of the recurrence, **And** the confirmation follows the decision and safety pattern of [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md).
2. **Given** the user chooses `Yes`, **When** the proposal is accepted, **Then** the system creates a skill generation request for that occurrence, **And** keeps future occurrences subject to a new confirmation.
3. **Given** the user chooses `Always`, **When** the proposal is accepted, **Then** the system registers a preference to automatically approve equivalent proposals within the configured scope, **And** the decision is auditable and reversible.
4. **Given** the user chooses `No`, **When** the proposal is rejected, **Then** the system marks the latent skill as rejected/ignored or reduces its priority (`ignored`), **And** does not create skill files.

## Tasks / Subtasks

- [x] **Task 1: Write RED tests for the Skill Proposal use case and preferences** (AC: 1, 2, 3, 4)
  - [x] Create `tests/application/skills/test_propose_skill.py`.
  - [x] Cover proposal flow presented to the user, offering explicit options `Yes`, `Always`, and `No`.
  - [x] Test scenario with choice `Yes`: the proposal is accepted, changes the status of `LatentSkill` from `proposed` to `active` (or schedules generation), keeping future occurrences subject to a new confirmation.
  - [x] Test scenario with choice `Always`: the proposal is accepted and the system registers an auto-approval preference in the local configuration file `.umem/config.toml` (for equivalent proposals with the same name/pattern in scope).
  - [x] Test scenario with choice `No`: the proposal is rejected, marking the latent skill with status `ignored` persistently, without creating skill files.
  - [x] Test auditability and rollback of decisions, including preference registration (reversible).
  - [x] Validate compliance with the mandatory mutation pipeline (snapshot verification, atomic write, and audit).

- [x] **Task 2: Implement the `ProposeSkillUseCase` usecase and decision logic** (AC: 1, 2, 3, 4)
  - [x] Create `src/universal_memory/application/skills/propose_skill.py` containing `ProposeSkillUseCase` and its input/output commands (`ProposeSkillCommand`, `ProposeSkillResult`).
  - [x] Implement the business logic for `LatentSkill` status transitions based on the user's choice (`Yes/Always/No`).
  - [x] Implement the persistence of auto-approval preferences in the local configuration `.umem/config.toml` using the secure logic of `toml_loader.py` and `update_project_config(...)` in the case of `Always`.
  - [x] Integrate the complete secure pipeline:
    1. Validate the transition using the domain Pydantic model (`LatentSkill`).
    2. Create a snapshot with `SnapshotRepository` (aborting on error with `SnapshotFailedError`).
    3. Write to the `LatentSkillRepository` repository atomically.
    4. Register an audit in `AuditLogRepository` (originating from CLI or MCP) indicating the action, decision, and references.
    5. Return the audit reference and operation status.
  - [x] Export `ProposeSkillUseCase` in `src/universal_memory/application/skills/__init__.py`.

- [x] **Task 3: Write RED tests for the Skill Proposal CLI (`umem skills propose`)** (AC: 1, 2, 3, 4)
  - [x] Create tests in `tests/interfaces/cli/test_skills_propose.py`.
  - [x] Test Rich rendering in the terminal showing the suggested name, purpose, scope, and summarized evidence of recurrence in a clean way.
  - [x] Test prompt interactivity accepting `Yes` (or `y`), `Always` (or `a` / `always`), `No` (or `n`).
  - [x] Test behavior with `--yes` (for automations or bypass) and strict compatibility with `--format json` (returning pure JSON without Rich markups).
  - [x] Test error handling and compliance with the default success/error envelope.

- [x] **Task 4: Implement the CLI command `umem skills propose`** (AC: 1, 2, 3, 4)
  - [x] Add the new CLI subgroup/command for skills in `src/universal_memory/interfaces/cli/init_command.py` or create a dedicated module.
  - [x] Format the Rich standard output in strict compliance with `devex-interaction-spec.md` (operation, scope, affected relative paths, audit references, and safe confirmation questions with no exposed secrets).
  - [x] Handle `--format json` to return pure JSON in compliance with the standard success/error envelope.
  - [x] Bind correctly in the bootstrapper `src/universal_memory/bootstrap/cli.py` injecting the use case into `build_main`.

- [x] **Task 5: Implement the corresponding MCP Adapter `propose_skill`** (AC: 1, 2, 3, 4)
  - [x] Add the MCP tool `propose_skill` in `src/universal_memory/interfaces/mcp/server.py`.
  - [x] Handle the non-interactive nature of MCP: accept an optional `decision` parameter ("sim", "sempre", "nao") or, if omitted, return the proposal and evidence in a standardized format requesting the subsequent call with the decision.
  - [x] Ensure full semantic parity of JSON-RPC return and errors with the CLI in compliance with `devex-interaction-spec.md`.

- [x] **Task 6: Quality and compliance verification** (AC: 1, 2, 3, 4)
  - [x] Run the complete test suite: `uv run pytest`.
  - [x] Run the linter and formatter: `uv run ruff check .` and `uv run ruff format --check .`.
  - [x] Run static type checking: `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Auto-Approval Rollback does not revert preferences in the project TOML [src/universal_memory/application/skills/propose_skill.py:128]
- [x] [Review][Patch] Interactive confirmation prompt violates the specification's Confirmation Contract [src/universal_memory/interfaces/cli/init_command.py:651]
- [x] [Review][Patch] Lack of parity and inconsistent duplication in decision conversion [src/universal_memory/interfaces/cli/init_command.py:678]
- [x] [Review][Patch] CLI exits successfully in a non-TTY environment without a decision provided [src/universal_memory/interfaces/cli/init_command.py:1299]
- [x] [Review][Patch] CLI generates a stack trace and crashes when receiving Ctrl+C or Ctrl+D at the prompt [src/universal_memory/interfaces/cli/init_command.py:1318]
- [x] [Review][Patch] CLI accepts invalid decisions and exits silently with success status [src/universal_memory/interfaces/cli/init_command.py:1320]
- [x] [Review][Patch] Lack of transactional atomicity and automatic rollback handling on failure [src/universal_memory/application/skills/propose_skill.py:121]
- [x] [Review][Patch] Failure to catch KeyError in the CLI when the latent skill ID does not exist [src/universal_memory/interfaces/cli/init_command.py:1308]
- [x] [Review][Patch] Entity modification uses model_copy, ignoring Pydantic validations [src/universal_memory/application/skills/propose_skill.py:160]
- [x] [Review][Patch] CLI error tests missing from the test suite file [tests/interfaces/cli/test_skills_propose.py:1]
- [x] [Review][Patch] Risk of slug collision for non-Latin or special skill names [src/universal_memory/application/skills/propose_skill.py:212]
- [x] [Review][Patch] AttributeError crash when loading null (None) metadata [src/universal_memory/application/skills/propose_skill.py:154]
- [x] [Review][Patch] Missing imports of ValidationError and sys in CLI [src/universal_memory/interfaces/cli/init_command.py:49]
- [x] [Review][Patch] Writing auto-approval rules violates global scope isolation [src/universal_memory/application/skills/propose_skill.py:168]
- [x] [Review][Patch] Config path is hardcoded in update_project_config [src/universal_memory/infrastructure/config/toml_loader.py:65]
- [x] [Review][Patch] Architectural workaround in domain tests couples domain to application [tests/domain/test_ports.py:1031]
- [x] [Review][Patch] Lack of latent skill state transition validation in the use case [src/universal_memory/application/skills/propose_skill.py:111]
- [x] [Review][Patch] Race conditions in concurrent simultaneous writing to config.toml [src/universal_memory/infrastructure/config/toml_loader.py:65]

## Dev Notes

- **Scope of this story:** Create the skill proposal and decision use case, persisting explicit approval and auto-approval rules in the local configuration in a secure and auditable way. Integrate this into the CLI under `umem skills propose` and MCP under `propose_skill`. Do not implement the physical generation of folder structures or the writing of `SKILL.md` files in this story (that belongs to story 6.3).
- **CLI/MCP Parity:** According to `devex-interaction-spec.md`, each command must have a corresponding CLI and MCP adapter, running the same use case under the same validations.
- **Secure Mutation Pipeline:** All writes and modifications to the local configuration `.umem/config.toml` or the latent skill status must create snapshots via `SnapshotRepository` and register detailed, auditable tracks via `AuditLogRepository`.

### Project Structure Notes

- The new use case must reside under `src/universal_memory/application/skills/propose_skill.py`.
- The CLI and MCP binding must be done in `src/universal_memory/bootstrap/cli.py` and `src/universal_memory/interfaces/mcp/server.py`.
- The auto-approval registration must extend the configuration schema of the project's `config.toml` using the existing TOML adapter.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR19, FR24, FR25, FR26, FR28) - [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)
- `_bmad-output/planning-artifacts/architecture.md` (Mutation Pipeline, Clean Architecture, Storage Contract) - [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (CLI output, JSON CLI output, Confirmation contract, skills command contracts) - [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- `src/universal_memory/domain/entities/latent_skill.py` - [latent_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/entities/latent_skill.py)
- `src/universal_memory/application/skills/track_latent_skill.py` - [track_latent_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/skills/track_latent_skill.py)

## Dev Agent Record

### Agent Model Used

Gemini 1.5 Pro (via Antigravity)

### Debug Log References

- 2026-05-29: Created story from the bmad create-story flow for epic-6 story-2.
- 2026-05-29: Analyzed persistence dependencies in config, logic of the secure mutation pipeline, and compliance with `devex-interaction-spec.md`.
- 2026-05-29: Implemented `ProposeSkillUseCase` with RED/GREEN tests for preview, `Yes`, `Always`, and `No` decisions, reversible preference in `.umem/config.toml`, snapshot, and audit.
- 2026-05-29: Implemented CLI adapters `umem skills propose` and MCP adapter `propose_skill`, including semantic parity and MCP compliance inventory.
- 2026-05-29: Final validation run with `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright`.

### Completion Notes List

- Context and architecture analysis completed - comprehensive implementation guide created.
- Story configured as ready for development with detailed scope and tasks.
- Mandatory integration of the secure mutation pipeline detailed in the use case task.
- Interactive `Yes/Always/No` pattern and its CLI/MCP parity detailed in operational tasks.
- `ProposeSkillUseCase` created and exported, with persistent transitions to `active`/`ignored` and approval registration in metadata.
- `Always` decision writes auto-approval preference to `.umem/config.toml` via secure write with snapshot and audit.
- CLI `umem skills propose` supports preview, interactive prompt, `--decision`, `--yes`, and `--format json` with default envelope.
- MCP `propose_skill` supports preview without decision and explicit non-interactive decision with the same semantic contract as the CLI.
- Complete suite and quality checks passed: 318 tests, ruff check, ruff format check, and pyright.

### File List

- `_bmad-output/implementation-artifacts/6-2-propor-cria-o-de-skill-com-aprova-o-expl-cita.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/application/skills/propose_skill.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/infrastructure/config/toml_loader.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/skills/test_propose_skill.py`
- `tests/domain/test_ports.py`
- `tests/infrastructure/storage/test_local_latent_skill_repository.py`
- `tests/interfaces/cli/test_skills_propose.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_server.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-05-29: Implemented skill creation proposal with explicit approval, `Always` preference, CLI/MCP, and full validations.
