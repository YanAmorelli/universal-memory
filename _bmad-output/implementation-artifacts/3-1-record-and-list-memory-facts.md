# Story 3.1: Record and List Memory Facts

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user or agent working on a project,  
I want to record and list memory facts by scope,  
so that relevant context is available for future sessions without re-explanation.

## Acceptance Criteria

1. **Given** the repositories and domain models from Epic 1,  
   **When** a valid fact is recorded by use case,  
   **Then** it is persisted with `schema_version`, `id`, `created_at`, `updated_at`, `scope`, `status`, `source`, `tags`, and `metadata`.

2. **Given** the secure mutation pipeline from Epic 2,  
   **When** the recording is executed,  
   **Then** the write passes through `SafeWriteUseCase` to ensure the content passes through the secrets scanner, takes a pre-mutation snapshot, and records a complete audit of success or block.

3. **Given** persisted facts in the `project` and `global` scopes,  
   **When** the user lists facts,  
   **Then** the system returns only the facts compatible with the requested filter (scope and/or status),  
   **And** preserves the logical separation between Short Term Memory (STM) and Universal Memory (LTM).

4. **Given** that no facts exist in the requested scope or status,  
   **When** listing is executed,  
   **Then** the system returns an explicit empty list,  
   **And** does not treat the absence of facts as an error.

## Tasks / Subtasks

- [x] **Task 1: Write RED tests for the infrastructure repository `LocalFactRepository`** (AC: 1, 3, 4)
  - [x] Create test file `tests/infrastructure/storage/test_local_fact_repository.py`.
  - [x] Cover initialization of `LocalFactRepository` receiving paths to local storage files.
  - [x] Cover `list()` method filtering facts by `scope` and `status`.
  - [x] Cover `read()` method searching for fact by ID and raising `FactNotFoundError` if it does not exist.
  - [x] Cover `write()` method adding or updating a fact directly (for direct support in infrastructure).
  - [x] Cover `delete()` method marking a fact with soft delete (`FactStatus.archived` or `FactStatus.stale`).
  - [x] Cover `purge()` method permanently removing the fact physically/structurally.
  - [x] Cover explicit empty listing behavior when the file does not exist or is empty.

- [x] **Task 2: Implement `LocalFactRepository` in the infrastructure layer** (AC: 1, 3, 4)
  - [x] Create directory `src/universal_memory/infrastructure/storage/` if it does not exist.
  - [x] Create `src/universal_memory/infrastructure/storage/__init__.py`.
  - [x] Create `src/universal_memory/infrastructure/storage/local_fact_repository.py` inheriting from the `FactRepository` interface.
  - [x] Implement reading and writing in `.umem/memory/facts.jsonl` synchronously and resiliently.
  - [x] Handle line corruption during parsing using Pydantic validation for each line individually.
  - [x] Ensure that the repository raises business-specific exceptions (`FactNotFoundError`, `StorageError`) instead of raw operating system errors.

- [x] **Task 3: Write RED tests for application Use Cases (`RememberFactUseCase` and `ListFactsUseCase`)** (AC: 1, 2, 3, 4)
  - [x] Create test file `tests/application/memory/test_memory_use_cases.py`.
  - [x] Cover `RememberFactUseCase` validating that the recording orchestrates with `SafeWriteUseCase` to persist modifications through the secure mutation pipeline.
  - [x] Test blocking of facts containing secrets (AWS credentials, GitHub PAT, etc.), ensuring the scanner triggers `SecretDetectedError` and prevents persistence, while generating a secure audit log of "blocked".
  - [x] Cover `ListFactsUseCase` validating correct loading through `FactRepository` and applying filters appropriately.

- [x] **Task 4: Implement Memory Use Cases in the application layer** (AC: 1, 2, 3, 4)
  - [x] Create directory `src/universal_memory/application/memory/`.
  - [x] Create `src/universal_memory/application/memory/__init__.py`.
  - [x] Create `src/universal_memory/application/memory/remember_fact_use_case.py` with structured command and secure mutation workflow.
  - [x] Create `src/universal_memory/application/memory/list_facts_use_case.py` exposing listing and secure filters.
  - [x] Ensure correct coupling with `SafeWriteUseCase` injected via constructor (Dependency Injection).

- [x] **Task 5: Integrate the new Use Cases into the system Bootstrap**
  - [x] Update `src/universal_memory/bootstrap/cli.py` if necessary to map and prepare the injection of the local repository and new use cases in the future CLI.

- [x] **Task 6: Close in GREEN with quality and regression verification**
  - [x] Run `uv run pytest` and validate that 100% of tests pass without errors.
  - [x] Run `uv run ruff check .` for style and rule validation.
  - [x] Run `uv run pyright` for strict static type checking validation.

### Review Findings

- [x] [Review][Decision] Separation of Universal Memory (LTM) Global Storage Path — Resolved: Global scope facts saved in `~/.umem/memory/facts.jsonl` (user's home) and local project facts in `.umem/memory/facts.jsonl` (local directory).
- [x] [Review][Patch] Race Condition in RememberFactUseCase (Read-Modify-Write unprotected) [src/universal_memory/application/memory/remember_fact_use_case.py:47-70]
- [x] [Review][Patch] TOCTOU and Lock Stealing in Lock Mechanism [src/universal_memory/infrastructure/storage/local_fact_repository.py:40-73]
- [x] [Review][Patch] Direct Repository Modifying Methods Bypass SafeWriteUseCase [src/universal_memory/infrastructure/storage/local_fact_repository.py:87]
- [x] [Review][Patch] Concurrent Soft Delete Race Condition [src/universal_memory/infrastructure/storage/local_fact_repository.py:98-103]
- [x] [Review][Patch] Silent Permanent Data Loss on JSONL Line Corruption [src/universal_memory/infrastructure/storage/local_fact_repository.py:129-137]
- [x] [Review][Patch] Indiscriminate DateTime Suffix Normalization Corrupts User Content [src/universal_memory/application/memory/remember_fact_use_case.py:81-89]
- [x] [Review][Patch] Leaky Abstractions and Hardcoded Storage Paths in Use Cases [src/universal_memory/application/memory/remember_fact_use_case.py:78]
- [x] [Review][Patch] Duplicated Serializer and Normalizer Rules [src/universal_memory/application/memory/remember_fact_use_case.py:78]

## Dev Notes

- **Scope of this story:** Exclusive focus on the domain layer, infrastructure, and application use cases for recording and listing memory facts. The end-user interface (Typer CLI commands like `umem remember` or `umem facts list` and equivalent FastMCP tools) will belong to Epic 4 stories.
- **Epic 2 Secure Pipeline:** The safe write pipeline `SafeWriteUseCase` is already implemented and must be used. It already handles:
  - Offline secrets scanning via `SecretScannerPort` (raises `SecretDetectedError`).
  - Automatic rollback snapshots via `SnapshotRepository`.
  - Atomic writing to files with atomic temporary file replacement.
  - Local auditable log via `AuditLogRepository`.
- **Fact File Format:** Facts must be written to `.umem/memory/facts.jsonl` in JSON Lines format (one valid JSON per line) representing each serialized `Fact` instance.

### Project Structure Notes

- The creation of the `infrastructure/storage/` directory and the `local_fact_repository.py` file follows the clean architecture guidelines agreed upon in `architecture.md`.
- The Use Cases must live in `application/memory/` and respect the dependency barrier (without importing anything from `infrastructure` or `interfaces`).

### References

- `_bmad-output/planning-artifacts/prd.md` (FR1, FR2, FR22, FR23, FR25)
- `_bmad-output/planning-artifacts/architecture.md` (Core Memory Management, Clean Architecture, Structure Mapping, Mutation Pipeline)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (remember fact, list facts, error mappings)
- `src/universal_memory/application/security/safe_write_use_case.py`
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/domain/entities/fact.py`

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash

### Debug Log References

- 2026-05-26: Initialized Story 3.1 creation with in-depth analysis of epics, architecture, and interaction specifications.
- 2026-05-26: Identified active Epic 2 patterns for local audits and secure local snapshots.
- 2026-05-26: Structured task modeling with TDD and strict isolation of layers.
- 2026-05-26: Created RED tests for `LocalFactRepository`; initial failure confirmed absence of the `infrastructure.storage` package.
- 2026-05-26: Implemented `LocalFactRepository` with JSONL, filters, soft delete, purge, resilient skipping of invalid lines, and typed errors.
- 2026-05-26: Created RED tests for `RememberFactUseCase` and `ListFactsUseCase`; initial failure confirmed absence of the `application.memory` package.
- 2026-05-26: Implemented memory use cases with DI of `FactRepository` and `SafeWriteUseCase`, keeping final CLI commands out of scope for this story.
- 2026-05-26: Final validations executed: `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

### Completion Notes List

- Story context created for offline local fact storage.
- SafeWriteUseCase integrated as a mandatory dependency for the fact modification flow to satisfy security auditing requirements.
- JSON Lines formats and exceptions mapped securely.
- Implemented `LocalFactRepository` for `.umem/memory/facts.jsonl`, with explicit empty read/listing, filters by `scope` and `status`, `read`, `write`, logical `delete` via `archived`, physical `purge`, and line corruption handling.
- Implemented `RememberFactUseCase` and `ListFactsUseCase`; recording facts creates a complete `Fact` and persists the content via `SafeWriteUseCase`, ensuring scanner, snapshot, and success/block auditing.
- CLI bootstrap was not modified because the story limits the delivery to domain/infra/application layers; `umem remember` and `umem facts list` commands are explicitly reserved for Epic 4.
- Added/updated tests cover infrastructure, use cases, block by secret, filters, and empty listing.
- Final checks passed: `uv run pytest` (143 passed), `uv run ruff check .`, `uv run pyright`.

### File List

- `_bmad-output/implementation-artifacts/3-1-gravar-e-listar-fatos-de-mem-ria.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/memory/__init__.py`
- `src/universal_memory/application/memory/list_facts_use_case.py`
- `src/universal_memory/application/memory/remember_fact_use_case.py`
- `src/universal_memory/infrastructure/storage/__init__.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `tests/application/memory/test_memory_use_cases.py`
- `tests/infrastructure/storage/test_local_fact_repository.py`

### Change Log

- 2026-05-26: Implemented Story 3.1 with local fact repository, memory use cases, and complete automated coverage.
