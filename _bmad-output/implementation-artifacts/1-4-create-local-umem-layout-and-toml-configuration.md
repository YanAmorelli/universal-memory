# Story 1.4: Create Local `.umem/` Layout and TOML Configuration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user initializing a project,
I want `universal-memory` to create and recognize a human-readable local structure,
so that I can version, inspect, and manually edit the project memory.

## Acceptance Criteria

1. **Given** project initialization tests written first,
   **When** the initialization command/use case runs in a clean directory,
   **Then** the `.umem/` structure is created with `config.toml`, `memory/`, `audit/events.jsonl`, `snapshots/`, `skills/`, and `benchmarks/`;
   **And** the initial files are human-readable and safe for manual editing.

2. **Given** a global configuration and a project configuration,
   **When** the configuration is loaded,
   **Then** TOML is read with `tomllib` and prepared for writing with `tomli-w`;
   **And** global and local paths are resolved offline (without depending on network).

## Tasks / Subtasks

- [x] **Task 1: Write RED tests for local layout and config loading** (AC: 1, 2)
  - [x] Create `tests/application/test_setup_project.py` covering initialization in a clean directory and basic idempotency of the setup workflow without CLI.
  - [x] Create `tests/infrastructure/test_project_layout.py` validating the creation of the canonical `.umem/` tree and human-readable initial files.
  - [x] Create `tests/infrastructure/config/test_toml_loader.py` validating reading with `tomllib`, serialization with `tomli-w`, and merge/resolution between global config and project config.
  - [x] Confirm the RED phase with failures due to the absence of `application/onboarding/` and `infrastructure/config/` implementations.

- [x] **Task 2: Implement the configuration model and the local persistent layout** (AC: 1, 2)
  - [x] Create `src/universal_memory/infrastructure/config/__init__.py`.
  - [x] Create `src/universal_memory/infrastructure/config/project_layout.py` with explicit helpers to materialize and recognize `.umem/`.
  - [x] Create `src/universal_memory/infrastructure/config/toml_loader.py` reading with `tomllib` and writing prepared via `tomli-w`, without network dependency.
  - [x] Define human-readable initial values for:
    - [x] `.umem/config.toml`
    - [x] `.umem/audit/events.jsonl`
    - [x] `.umem/benchmarks/retrieval-results.json`
  - [x] Ensure that the created tree strictly follows the canonical layout of the architecture:
    - [x] `.umem/config.toml`
    - [x] `.umem/memory/`
    - [x] `.umem/audit/events.jsonl`
    - [x] `.umem/snapshots/`
    - [x] `.umem/skills/`
    - [x] `.umem/benchmarks/`

- [x] **Task 3: Implement the onboarding usecase without coupling the CLI** (AC: 1, 2)
  - [x] Create `src/universal_memory/application/__init__.py` if it does not already exist.
  - [x] Create `src/universal_memory/application/onboarding/__init__.py`.
  - [x] Create `src/universal_memory/application/onboarding/setup_project.py` to orchestrate project initialization and return a structured result for future consumption by CLI and MCP.
  - [x] Ensure that the use case remains synchronous and that any filesystem/TOML I/O is encapsulated in `infrastructure/config/`.
  - [x] Do not introduce a CLI adapter in this story; `src/universal_memory/__main__.py` must remain minimal until Story 1.5.

- [x] **Task 4: Validate global + project configuration recognition and resolution** (AC: 2)
  - [x] Cover the global path `~/.config/umem/config.toml` only as a read/resolution input in this story (updated by BUG-002).
  - [x] Ensure that the project configuration resides in `.umem/config.toml`.
  - [x] Ensure that returned project paths are relative when appropriate for output/diagnostics, and absolute only internally when required for I/O.
  - [x] Ensure that invalid TOML scenarios result in `InvalidConfigError`, avoiding the use of `ValueError`/`RuntimeError` for known errors.

- [x] **Task 5: Close in GREEN with suite, typing, and regression checking** (AC: 1, 2)
  - [x] Run `uv run pytest tests/application/test_setup_project.py tests/infrastructure/test_project_layout.py tests/infrastructure/config/test_toml_loader.py`.
  - [x] Run `uv run pytest` to validate the absence of regressions in stories 1.1–1.3.
  - [x] Run `uv run ruff check .` and `uv run pyright`.

## Dev Notes

- **Real goal of this story:**
  - This story bridges the gap between the already existing scaffold and the canonical persistent layout described in the architecture.
  - The focus here is to prepare the local foundation of the product and configuration loading; the human CLI interface is deferred to Story 1.5.

- **Context already established by previous stories:**
  - Story 1.1 has already created the Python scaffold, `pyproject.toml`, `uv.lock`, `src/`, `tests/`, and `benchmarks/`.
  - Story 1.2 has already consolidated the Pydantic domain models with `schema_version`, UUID v4, UTC timestamps, and scope/status enums.
  - Story 1.3 has already consolidated `InvalidConfigError`, `StorageError`, and domain storage ports, so this story should reuse these components instead of creating new ad hoc errors.

- **Architecture guardrails that the dev must follow:**
  - Respect the `src/` layout and Clean Architecture boundaries in `_bmad-output/planning-artifacts/architecture.md`.
  - `application/` depends only on `domain/`; logic of filesystem and TOML must reside in `infrastructure/config/`.
  - The use case must be synchronous.
  - No part of this story should depend on the network (must work offline).
  - Do not implement the Typer/Rich CLI or the FastMCP server prematurely in this delivery.

- **Mandatory canonical layout for this story:**
  - `.umem/config.toml`
  - `.umem/memory/`
  - `.umem/audit/events.jsonl`
  - `.umem/snapshots/`
  - `.umem/skills/`
  - `.umem/benchmarks/`
  - The architecture details future files inside `memory/` and `benchmarks/`, but this story needs to at least leave the structure recognizable and stable for the following stories.

- **Configuration format and behavior:**
  - Read TOML with `tomllib` and write/prepare TOML with `tomli-w`.
  - Global configuration: `~/.config/umem/config.toml` (updated by BUG-002).
  - Project configuration: `.umem/config.toml`.
  - The flow must resolve both locally, offline, and handle invalid config with `InvalidConfigError`.

- **Current code state that matters for implementation:**
  - `src/universal_memory/__main__.py` still prints only a fixed string; do not use this story to turn it into a complete CLI.
  - `src/universal_memory/domain/entities/` and `src/universal_memory/domain/ports/` already exist and must remain the typed foundation for the next layers.
  - `src/universal_memory/application/` and `src/universal_memory/infrastructure/config/` do not exist yet; this story is the right point to introduce them.
  - `pyproject.toml` already contains `pydantic`, `tomli-w`, `typer`, and `fastmcp`, but with looser constraints than the architectural baselines. If any adjustment to this file is strictly necessary for the story, preserve the minimum scope and do not mix in a broad dependency refactoring.

- **Useful learnings from previous stories:**
  - The project already uses explicit TDD and RED/GREEN validation on completed stories.
  - Existing tests already run with `uv run pytest`, `ruff`, and `pyright`; maintain the same standard.
  - Existing artifacts favor predictable file names and small responsibilities per module.

- **Current technical information verified externally on 2026-05-24:**
  - `fastmcp` 3.3.1 is published on PyPI and remains compatible with Python 3.12+, aligned with the architectural decision to use the 3.x line.
  - `pydantic` 2.13.4 is published on PyPI and confirms the v2 line assumed by the architecture.
  - `typer` 0.25.1, `rich` 15.0.0, and `tomli-w` 1.2.0 are published on PyPI; this reinforces the minimum versions defined in the planning artifacts.
  - Inference: this story does not need to update dependencies on its own, but the developer must not introduce APIs incompatible with these target versions.

### Project Structure Notes

- New modules expected in this story:
  - `src/universal_memory/application/__init__.py`
  - `src/universal_memory/application/onboarding/__init__.py`
  - `src/universal_memory/application/onboarding/setup_project.py`
  - `src/universal_memory/infrastructure/__init__.py`
  - `src/universal_memory/infrastructure/config/__init__.py`
  - `src/universal_memory/infrastructure/config/project_layout.py`
  - `src/universal_memory/infrastructure/config/toml_loader.py`
- New tests expected in this story:
  - `tests/application/test_setup_project.py`
  - `tests/infrastructure/test_project_layout.py`
  - `tests/infrastructure/config/test_toml_loader.py`
- Existing files that can be modified only if necessary:
  - `pyproject.toml`
  - `src/universal_memory/domain/__init__.py`
  - `src/universal_memory/__main__.py`
- Preserve incremental evolution: do not create `interfaces/cli/` or `interfaces/mcp/` yet.

### References

- Structure and boundaries: `_bmad-output/planning-artifacts/architecture.md` (Project Structure & Boundaries)
- Canonical persistent layout and mutation contract: `_bmad-output/planning-artifacts/architecture.md` (Project data root / Canonical structure / Mutation Pipeline)
- Functional requirements and MVP NFRs: `_bmad-output/planning-artifacts/prd.md`
- Story source and dependencies between stories: `_bmad-output/planning-artifacts/epics.md`
- DevEx contract for relative paths and parseable outputs: `_bmad-output/planning-artifacts/devex-interaction-spec.md`
- Previous learnings:
  - `_bmad-output/implementation-artifacts/1-1-inicializar-scaffold-python-do-produto.md`
  - `_bmad-output/implementation-artifacts/1-2-definir-modelos-de-dom-nio-para-mem-ria.md`
  - `_bmad-output/implementation-artifacts/1-3-definir-exce-es-e-ports-de-dom-nio.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-24: Story created based on `epics.md`, `architecture.md`, `prd.md`, `devex-interaction-spec.md` and learnings from stories 1.1–1.3.
- 2026-05-24: External verification of target versions on PyPI for `fastmcp`, `pydantic`, `typer`, `rich`, and `tomli-w`.
- 2026-05-24: RED phase confirmed with `ModuleNotFoundError` for `universal_memory.application` and `universal_memory.infrastructure` when running the target suite prior to implementation.
- 2026-05-24: GREEN validations completed with `uv run pytest`, `uv run ruff check .`, and `uv run pyright`.

### Completion Notes List

- Story contextualized for TDD implementation of the local `.umem/` layout and offline TOML loading.
- Guardrails added to prevent premature coupling with CLI/MCP and to preserve architecture boundaries.
- Implemented `ensure_project_layout` with the canonical `.umem/` tree, human-readable initial files, and idempotent project recognition.
- Implemented `load_config` with offline reading via `tomllib`, serialization via `tomli-w`, global + project deep merge, and the typed error `InvalidConfigError`.
- Implemented `setup_project` as a synchronous use case with a structured return for future CLI and MCP integration.
- Added application and infrastructure tests covering RED/GREEN, idempotency, configuration merging, and invalid TOML.

### File List

- `_bmad-output/implementation-artifacts/1-4-criar-layout-local-umem-e-configura-o-toml.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/__init__.py`
- `src/universal_memory/application/onboarding/__init__.py`
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/infrastructure/__init__.py`
- `src/universal_memory/infrastructure/config/__init__.py`
- `src/universal_memory/infrastructure/config/project_layout.py`
- `src/universal_memory/infrastructure/config/toml_loader.py`
- `tests/application/test_setup_project.py`
- `tests/infrastructure/config/test_toml_loader.py`
- `tests/infrastructure/test_project_layout.py`

### Change Log

- 2026-05-24: Story created and enriched with architectural context, story dependencies, TDD tasks, and implementation guardrails.
- 2026-05-24: Local `.umem/` layout, offline TOML loader, and onboarding usecase implemented with test coverage and complete validations.

### Review Findings

- [x] [Review][Patch] Violation of the application layer boundary [`src/universal_memory/application/onboarding/setup_project.py:4`] — resolved via domain ports and local adapters, removing direct coupling of `application/` with `infrastructure/`.
- [x] [Review][Patch] Partial or corrupted state of `.umem/` must fail explicitly [`src/universal_memory/infrastructure/config/project_layout.py:47`] — resolved with explicit validation and a deterministic error for partial/corrupted tree.
- [x] [Review][Patch] File-directory collision is accepted as a valid layout [`src/universal_memory/infrastructure/config/project_layout.py:47`] — resolved with expected type checking for each canonical path.
- [x] [Review][Patch] TOML read lets real filesystem errors escape without normalization [`src/universal_memory/infrastructure/config/toml_loader.py:55`] — resolved with normalization to `StorageError`/`InvalidConfigError`.
- [x] [Review][Patch] The loader does not resolve configured paths, it only merges strings [`src/universal_memory/infrastructure/config/toml_loader.py:27`] — resolved with `resolved_paths` returning absolute paths calculated offline.
- [x] [Review][Patch] `merged` shares mutable references with `global_data` and `project_data` [`src/universal_memory/infrastructure/config/toml_loader.py:70`] — resolved with deep copy merging.
- [x] [Review][Patch] Layout tracking does not fully represent the canonical structure of `benchmarks/` [`src/universal_memory/infrastructure/config/project_layout.py:4`] — resolved by including `benchmarks/` in the canonical layout and returned tracking.
- [x] [Review][Defer] Resilient self-repair strategy for specific `.umem/` states [`src/universal_memory/infrastructure/config/project_layout.py:47`] — deferred, future desirable evolution after defining explicit rules for which partial corruptions can be safely repaired.
