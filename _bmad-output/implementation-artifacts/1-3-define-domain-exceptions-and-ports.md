# Story 1.3: Define Domain Exceptions and Ports

Status: done

## Story

As a developer implementing use cases and adapters,
I want stable domain exceptions and ports,
so that infrastructure, CLI, and MCP can evolve in parallel without undue coupling.

## Acceptance Criteria

1. **Given** import boundary tests and port contracts written first (TDD),
   **When** the domain ports are implemented under `domain/ports/`,
   **Then** there are abstract ports (ABCs) for facts, rules, latent skills, snapshots, audit log, and context summaries.
   **And** attempting to instantiate any of these ports directly results in a type error (`TypeError`).
   **And** each port exposes the abstract signatures for the minimum operations of read, list, write, delete/purge (where applicable), and migration hooks.

2. **Given** expected errors and business exception scenarios in the domain,
   **When** they are simulated in tests or raised by future use cases,
   **Then** the system exposes typed domain exceptions:
     - `SecretDetectedError` (Error detecting secrets/API keys in facts or rules; JSON-RPC code: `-32010`)
     - `SnapshotFailedError` (Snapshot integrity or creation/restoration failure; JSON-RPC code: `-32020`)
     - `ValidationFailedError` (Logical validation failure in the business layer; JSON-RPC code: `-32602`)
     - `FactNotFoundError` (Requested fact ID not found; JSON-RPC code: `-32040`)
     - `InvalidConfigError` (Invalid or missing global or local TOML configuration; JSON-RPC code: `-32050`)
     - `StorageError` (Physical failure or corruption in the `.umem/` persistence layout; JSON-RPC code: `-32060`)
   **And** all exceptions inherit from a common domain base class (`UniversalMemoryError` or similar) and accept detailed error messages.
   **And** no internal business logic or port needs to use generic exceptions like `ValueError` or `RuntimeError` for known scenarios.

## Tasks / Subtasks

- [x] **Task 1: Write Contract Tests and Exceptions First (TDD - RED Phase)** (AC: 1, 2)
  - [x] Create the `tests/domain/test_exceptions.py` test file validating that all required domain exceptions inherit from a base exception and carry the correct properties.
  - [x] Create the `tests/domain/test_ports.py` test file to ensure that abstract ports cannot be instantiated and expose signatures with Pyright-compatible type signatures and type hints.
  - [x] Validate the RED phase by ensuring these tests fail due to the absence of production files.

- [x] **Task 2: Implement Domain Exceptions** (AC: 2)
  - [x] Create `src/universal_memory/domain/exceptions.py`.
  - [x] Define the `UniversalMemoryError` base exception inheriting from `Exception`.
  - [x] Implement `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, and `StorageError` inheriting from `UniversalMemoryError`.

- [x] **Task 3: Implement Storage and Persistence Ports** (AC: 1)
  - [x] Create the `src/universal_memory/domain/ports/` directory.
  - [x] Create the `src/universal_memory/domain/ports/__init__.py` file to cleanly export all abstract interfaces.
  - [x] Implement the following abstract ports using `abc.ABC` and `abc.abstractmethod`:
    - [x] `FactRepository` in `fact_repository.py` with methods: `read`, `list`, `write`, `delete`, `purge`, and `migrate`.
    - [x] `RuleRepository` in `rule_repository.py` with methods: `read`, `list`, `write`, `delete`, and `migrate`.
    - [x] `LatentSkillRepository` in `latent_skill_repository.py` with methods: `read`, `list`, `write`, `delete`, and `migrate`.
    - [x] `SnapshotRepository` in `snapshot_repository.py` with methods: `read`, `list`, `write`, and `migrate`.
    - [x] `AuditLogRepository` in `audit_log_repository.py` with methods: `read`, `list`, `write`, and `migrate`.
    - [x] `ContextSummaryRepository` in `context_summary_repository.py` with methods: `read`, `list`, `write`, and `migrate`.

- [x] **Task 4: Export Exceptions and Ports at the Domain Module Root** (AC: 1, 2)
  - [x] Update `src/universal_memory/domain/__init__.py` to export all defined exceptions and ports, facilitating access for external layers (`application` and `infrastructure`).

- [x] **Task 5: Validate the Complete Test Suite and Static Typing (GREEN Phase)** (AC: 1, 2)
  - [x] Run the domain unit tests and ensure 100% green coverage.
  - [x] Run the `ruff check .` linter and `pyright` analyzer ensuring flawless static typing free of warnings.

### Review Findings

- [x] [Review][Decision] Protocol Leak (JSON-RPC) in Domain Layer — Custom domain exceptions directly define `json_rpc_code` as a class attribute. Although this is mapped in the references for Story 1.3, defining transport protocol codes directly in the domain violates the separation of concerns of Clean Architecture. Ideally, the external MCP layer should perform this translation, keeping the exceptions pure.
- [x] [Review][Patch] Generic `str` instead of Specific Domain Enums in Ports [src/universal_memory/domain/ports/]
- [x] [Review][Patch] Inappropriate `status` Parameter in AuditLog and ContextSummary [src/universal_memory/domain/ports/audit_log_repository.py]
- [x] [Review][Patch] Redundant Use of `raise NotImplementedError` in Abstract Methods [src/universal_memory/domain/ports/]
- [x] [Review][Patch] Lack of Documentation in `read` Methods (Handling Not Found) [src/universal_memory/domain/ports/]
- [x] [Review][Patch] Missing Docstrings Explaining `delete` and `purge` [src/universal_memory/domain/ports/fact_repository.py]
- [x] [Review][Patch] Fragility and Robustness Errors in Signature Tests (`test_ports.py`) [tests/domain/test_ports.py]
- [x] [Review][Patch] Language Inconsistency in Exception Tests [tests/domain/test_exceptions.py]
- [x] [Review][Defer] Specific Structured Data in Domain Exceptions [src/universal_memory/domain/exceptions.py] — deferred, pre-existing

## Dev Notes

- **Clean Architecture Compliance:**
  - Ports represent the boundaries of our system. They define contracts and signatures that the infrastructure layer (`infrastructure/`) will implement.
  - The domain layer does not directly depend on databases, TOML files, JSON serializers, or FastMCP. Its ports must contain only native types and the domain entities defined in Story 1.2.
- **Strict Typing with ABCs:**
  - Use `abc.ABC` and the `abc.abstractmethod` decorator for all port methods.
  - Use full type hints in all signatures (e.g. `Optional`, `list`, `Union` from `typing`, or native types if running on Python 3.12+).
- **Suggested signatures for repository methods:**
  - `read(id: str) -> Entity`: Returns the corresponding entity or raises `FactNotFoundError` (or related not found exception).
  - `list(...) -> list[Entity]`: Returns a list of entities found that match the provided filters (e.g. `scope`, `status`).
  - `write(entity: Entity) -> None`: Writes or updates the entity atomically in physical storage.
  - `delete(id: str) -> None`: Logically deletes or marks as unavailable/inactive (where applicable).
  - `purge(id: str) -> None` (specific to facts): Permanently and irrecoverably removes from physical storage.
  - `migrate(target_version: int) -> None`: Hook responsible for performing structural data migrations when the `schema_version` changes.

### Project Structure Notes

- The expected file tree for the domain layer after this story should be:
  ```
  src/universal_memory/domain/
  ├── __init__.py
  ├── entities/
  │   ├── __init__.py
  │   ├── base.py
  │   ├── fact.py
  │   ├── rule.py
  │   ├── latent_skill.py
  │   ├── snapshot.py
  │   ├── audit_event.py
  │   └── context_summary.py
  ├── exceptions.py
  └── ports/
      ├── __init__.py
      ├── fact_repository.py
      ├── rule_repository.py
      ├── latent_skill_repository.py
      ├── snapshot_repository.py
      ├── audit_log_repository.py
      └── context_summary_repository.py
  ```

### References

- **Persistent Data Layout & Storage Contract:** [architecture.md#L725-L737](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L725-L737)
- **MCP Error Mapping Spec:** [architecture.md#L738-L752](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L738-L752)
- **Quality & Boundaries:** [architecture.md#L400-L415](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L400-L415)

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 3.5 Pro / Advanced Agentic Coding)

### Debug Log References

- 2026-05-22: RED confirmed with `uv run pytest tests/domain/test_exceptions.py tests/domain/test_ports.py`, failing due to the absence of `universal_memory.domain.exceptions` and `universal_memory.domain.ports`.
- 2026-05-22: GREEN confirmed with `uv run pytest`.
- 2026-05-22: Quality confirmed with `uv run ruff check .` and `uv run pyright`.

### Completion Notes List

- Implemented typed domain exceptions with `UniversalMemoryError` as a common base, detailed message, and JSON-RPC codes for each known scenario.
- Implemented abstract ports for facts, rules, latent skills, snapshots, audit log, and context summaries with `abc.ABC`, abstract methods, and typed signatures.
- Exported exceptions and port interfaces in `universal_memory.domain` for consumption by external layers.

### File List

- `_bmad-output/implementation-artifacts/1-3-definir-exce-es-e-ports-de-dom-nio.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/domain/__init__.py`
- `src/universal_memory/domain/exceptions.py`
- `src/universal_memory/domain/ports/__init__.py`
- `src/universal_memory/domain/ports/audit_log_repository.py`
- `src/universal_memory/domain/ports/context_summary_repository.py`
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/domain/ports/latent_skill_repository.py`
- `src/universal_memory/domain/ports/rule_repository.py`
- `src/universal_memory/domain/ports/snapshot_repository.py`
- `tests/domain/test_exceptions.py`
- `tests/domain/test_ports.py`

### Change Log

- 2026-05-22: Story successfully initialized and detailed. Ready for TDD development (RED/GREEN).
- 2026-05-22: Implemented domain exceptions and ports with contract tests, complete suite, Ruff and Pyright green.
