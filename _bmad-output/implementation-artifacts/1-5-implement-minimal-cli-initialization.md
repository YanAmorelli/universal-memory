# Story 1.5: Implement Minimal CLI Initialization

Status: done

## Story

As a user of universal-memory,  
I want to run an initial project command,  
so that I can enable local memory in a new repository with clear feedback.

## Acceptance Criteria

1. **Given** CLI tests written before implementation, **When** the user runs `umem init` in a directory without `.umem/`, **Then** the command creates the local project structure, **And** returns a human-friendly message with the created paths, **And** with `--format json` returns pure JSON containing `project_path`, `config_path`, `memory_path`, `audit_path`, `snapshots_path`, `created`, `already_initialized`, and `audit_reference`, **And** follows `devex-interaction-spec.md`.
2. **Given** a directory already initialized with `.umem/`, **When** the user runs `umem init` again, **Then** the command is idempotent and does not corrupt existing files, **And** informs that the memory was already initialized, **And** with `--format json` returns `already_initialized: true`, `created: []` and the same resolved paths.
3. **Given** an offline environment, **When** `umem init` is executed, **Then** the initialization works without external connectivity.

## Tasks / Subtasks

- [x] **Task 1: Write RED tests for minimal CLI** (AC: 1, 2, 3)
  - [x] Create `tests/interfaces/cli/test_init_command.py` covering:
    - [x] Execution of `init` in a clean directory with human-friendly output containing status and next steps.
    - [x] Execution of `init --format json` with pure parseable JSON and required keys.
    - [x] Idempotent re-execution (`already_initialized: true`, `created: []`, without corruption).
    - [x] Offline execution (without any network dependencies; fails if there is any external access attempt).
    - [x] Expected errors with consistent envelope/semantics for the CLI.
  - [x] Confirm RED phase before implementing CLI adapter.

- [x] **Task 2: Implement minimal CLI adapter for `umem init`** (AC: 1, 2, 3)
  - [x] Evolve `src/universal_memory/__main__.py` to expose the `init` command with a minimal argument parser.
  - [x] Support `--format json` with pure JSON in stdout, without additional text.
  - [x] Integrate with existing `setup_project` via already implemented config/layout adapters.
  - [x] Include `audit_reference` in the response payload with a stable and explicit placeholder (`"not-implemented-yet"`), maintaining the contract without inventing premature auditing.
  - [x] Ensure exit code `0` on success and non-zero on expected error.

- [x] **Task 3: Standardize output and error handling for DevEx contract** (AC: 1, 2)
  - [x] Human-friendly output: indicate if `.umem/` was created or reused, list relative paths, suggest next command.
  - [x] JSON output: maintain deterministic format and mandatory fields from the spec.
  - [x] Map domain exceptions (`InvalidConfigError`, `StorageError`, `ValidationFailedError`) to actionable CLI messages.
  - [x] Do not mix business logic in the adapter; perform only I/O orchestration and formatting.

- [x] **Task 4: Quality and regression check** (AC: 1, 2, 3)
  - [x] Run `uv run pytest tests/interfaces/cli/test_init_command.py`.
  - [x] Run full `uv run pytest` for regressions on stories 1.1-1.4.
  - [x] Run `uv run ruff check .` and `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Remove direct CLI access to infrastructure [`src/universal_memory/__main__.py:13`]
- [x] [Review][Patch] Success JSON does not follow DevEx envelope [`src/universal_memory/__main__.py:59`]
- [x] [Review][Patch] Filesystem errors outside of domain exceptions can leak traceback [`src/universal_memory/__main__.py:49`]
- [x] [Review][Patch] Tests do not exercise real execution of installed CLI or as process [`tests/interfaces/cli/test_init_command.py:7`]

## Dev Notes

- **Scope of this story:** Minimal initialization CLI (`umem init`) on top of the already existing onboarding use case, without anticipating the complete CLI adapter of Epic 4.
- **Architectural goal:** Keep `application` without dependency on `infrastructure`/`interfaces`; CLI as a thin adapter.
- **Core functional contract:** Initialize local `.umem/` and deliver human-friendly feedback + parseable JSON response for agents.

### Technical Requirements

- Python `>=3.12`; offline operation is mandatory.
- Reuse `setup_project(...)` from `application/onboarding/setup_project.py`.
- Reuse `LocalProjectLayoutPort` and `LocalConfigValidationPort` from `infrastructure/config/adapters.py`.
- Do not create new domain models for this story; only compose CLI response.
- `--format json` must print **only valid JSON**.

### Architecture Compliance

- Dependency rule: `interfaces -> application -> domain <- infrastructure`.
- Do not move business logic to `__main__.py`; use `setup_project` for initialization orchestration.
- Preserve the already existing idempotent behavior in the layout/config of Story 1.4.
- Do not introduce MCP, secrets scanner, snapshot pipeline, or rollback in this story.

### Library / Framework Requirements

- Implement minimal CLI with the standard library (`argparse`) in this story for lower risk surface.
- Maintain compatibility with the already declared project stack (`typer`, `fastmcp`, `pydantic`, `tomli-w`) without premature coupling.
- Recent information already recorded in Story 1.4 (date: 2026-05-24): `typer 0.25.1`, `rich 15.0.0`, `pydantic 2.13.4`, `tomli-w 1.2.0`, `fastmcp 3.3.1`.
- Inference: Story 1.5 should not force dependency upgrades; focus is on the CLI initialization contract.

### File Structure Requirements

- **Mandatory UPDATE files:**
  - `src/universal_memory/__main__.py`
- **Expected NEW files:**
  - `tests/interfaces/cli/test_init_command.py`
- **Files that can be modified if strictly necessary:**
  - `src/universal_memory/__init__.py` (only metadata/version, if required by tests)
  - `pyproject.toml` (only if entrypoint/execution requires minimal adjustment)

### Testing Requirements

- TDD Strategy: RED -> GREEN -> REFACTOR.
- Cover success (new project), idempotency (already initialized project), JSON format, and offline-first.
- Validate JSON parseability with `json.loads` in the test.
- Validate that returned paths are relative in the payload/human-friendly output (`.`, `.umem/...`) for DevEx compliance.
- Ensure absence of regressions in existing domain/application/infra suites.

### Previous Story Intelligence (1.4)

- `setup_project` already returns `created`, `already_initialized`, `created_paths`, and `existing_paths`; leverage directly.
- `.umem/` layout and TOML validation have already been hardened; CLI must not reimplement filesystem/config logic.
- Previous review fixed layer boundary violations; avoid direct coupling of `application` with `infrastructure` again.
- Current quality standard: run `pytest`, `ruff`, `pyright` before closing.

### Git Intelligence Summary

- Most recent commit: `feat: harden project init layout and config loading` reinforces setup robustness and idempotency.
- Recent history consolidated domain base and contracts (`exceptions`, `ports`) for use by interfaces.
- The current story must preserve incrementality: add minimal CLI surface without broad refactoring.

### Project Structure Notes

- Current structure already contains `application/onboarding` and `infrastructure/config`; only functional CLI entry is missing.
- `src/universal_memory/__main__.py` currently prints a fixed string; this file is the natural evolutionary point for `umem init`.
- Do not create full `interfaces/cli/` in this story; that belongs to Epic 4.

### References

- `_bmad-output/planning-artifacts/epics.md` (Story 1.5 / ACs)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (`umem init`, pure JSON, required keys)
- `_bmad-output/planning-artifacts/architecture.md` (Clean Architecture, CLI/MCP patterns, dependencies)
- `_bmad-output/planning-artifacts/prd.md` (FR9 and offline-first contract)
- `_bmad-output/implementation-artifacts/1-4-criar-layout-local-umem-e-configura-o-toml.md` (learnings and guardrails)
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/infrastructure/config/adapters.py`
- `src/universal_memory/__main__.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-24: automatic discovery of the next story in backlog via `sprint-status.yaml`.
- 2026-05-24: analysis of `epics.md`, `architecture.md`, `prd.md`, `devex-interaction-spec.md` and learnings from story 1.4.
- 2026-05-24: review of current code state (`__main__.py`, `setup_project.py`, config/layout adapters).
- 2026-05-24: RED phase confirmed with `uv run pytest tests/interfaces/cli/test_init_command.py` failing with `TypeError: main() takes 0 positional arguments but 1 was given`.
- 2026-05-24: GREEN phase of CLI suite confirmed with `uv run pytest tests/interfaces/cli/test_init_command.py` (5 passed).
- 2026-05-24: entrypoint `umem` validated in a temporary directory with the local project as source.
- 2026-05-24: output and error contract revalidated with `uv run pytest tests/interfaces/cli/test_init_command.py` (5 passed).
- 2026-05-24: full regression validated with `uv run pytest` (60 passed).
- 2026-05-24: quality validated with `uv run ruff check .` and `uv run pyright` (no errors).

### Completion Notes List

- Story contextualized with TDD tasks and architecture guardrails for safe implementation.
- Human-friendly and JSON output criteria defined for DevEx contract compliance.
- Scope bounded to avoid premature inclusion of Epic 4's full CLI adapter.
- CLI RED/GREEN tests added covering clean initialization, pure JSON, idempotency, offline-first, and expected error envelope.
- Minimal CLI adapter implemented with `argparse`, `init` command, `umem` alias, composition via `setup_project`, and stable audit placeholder.
- Human-friendly and JSON outputs standardized to relative paths and expected errors mapped to an actionable CLI envelope.
- Final regression and quality verification completed with 60 passing tests, clean `ruff`, and `pyright` with no errors.

### File List

- `_bmad-output/implementation-artifacts/1-5-implementar-inicializa-o-cli-m-nima.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `pyproject.toml`
- `src/universal_memory/__main__.py`
- `tests/interfaces/cli/test_init_command.py`

### Change Log

- 2026-05-24: Implemented minimal `umem init` with human-friendly output, pure JSON, idempotency, and expected error envelope.
- 2026-05-24: Added TDD CLI suite for initialization, idempotency, offline-first, and expected errors.
- 2026-05-24: Story moved to `review` after complete validation (`pytest`, `ruff`, `pyright`).
