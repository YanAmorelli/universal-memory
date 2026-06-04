# Story 1.2: Define Domain Models for Memory

Status: done

## Story

As an agent or adapter that uses the memory,
I want validated domain models for facts, rules, latent skills, snapshots, audits, and context summaries,
so that all components share consistent data contracts.

## Acceptance Criteria

1. **Given** that domain tests are written first (TDD),
   **When** Pydantic v2 models are implemented,
   **Then** each persistable entity must contain the attributes `schema_version` (integer), `id` (UUID v4 as string), `created_at` (ISO 8601 UTC timestamp), `updated_at` (ISO 8601 UTC timestamp), `scope` (enum), and `status` (enum or string).
   **And** all JSON-serialized fields follow the `snake_case` convention, enum keys use `lowercase_snake`, and booleans are represented natively in JSON (`true`/`false`).

2. **Given** invalid inputs for the domain entities (such as IDs that are not valid UUIDs, corrupted timestamps, or incompatible types),
   **When** Pydantic model validation is executed,
   **Then** the invalid data is summarily rejected with typed and testable validation errors (`pydantic.ValidationError`).

3. **Given** the Short Term Memory (STM) lifecycle,
   **When** the status of a Fact is evaluated,
   **Then** the system explicitly supports the states: `active`, `stale`, `archived`, and `purged`.

4. **Given** the need for consistency in audit data, snapshots, and context summaries,
   **When** the corresponding entities are instantiated,
   **Then** the Audit model (`AuditEvent`) contains `timestamp`, `action`, `scope`, `origin`, `result`, `snapshot_reference`, and `audit_reference`.
   **And** the Snapshot model contains `timestamp`, `scope`, `action` (responsible), `relative_path`, and `hash` (SHA-256 of the previous file).
   **And** the Context Summary model (`ContextSummary`) clearly differentiates between `project_summary`, `universal_preferences`, and `active_rules`, in addition to containing the corresponding `audit_reference`.

## Tasks / Subtasks

- [x] **Task 1: Write Domain Tests First (TDD)** (AC: 1, 2, 3, 4)
  - [x] Create the file `tests/domain/test_entities.py`.
  - [x] Implement positive validation test cases (perfect inputs) for all entities: `Fact`, `Rule`, `LatentSkill`, `Snapshot`, `AuditEvent`, and `ContextSummary`.
  - [x] Implement negative validation test cases (wrong types, corrupted UUID formats, invalid scopes, etc.) ensuring that `pydantic.ValidationError` is raised.
  - [x] Implement specific test cases for the fact state lifecycle (`active`, `stale`, `archived`, `purged`).

- [x] **Task 2: Define Domain Enums and Structured Typing** (AC: 1, 3)
  - [x] Create the file `src/universal_memory/domain/entities/__init__.py` to facilitate clean exports.
  - [x] Define the `FactScope` enum (`global` or `project`) in `src/universal_memory/domain/entities/fact.py`.
  - [x] Define the `FactStatus` enum (`active`, `stale`, `archived`, `purged`) in `src/universal_memory/domain/entities/fact.py`.
  - [x] Define other enums required for audit control, snapshot status, and rule scopes.

- [x] **Task 3: Implement Domain Pydantic v2 Entities** (AC: 1, 2, 3, 4)
  - [x] Implement `Fact` with robust validations (UUIDv4 for `id`, ISO 8601 UTC for `created_at` / `updated_at`, `recurrence_count` initialized to 0 by default, `tags` as a list of strings, `metadata` as a generic dictionary).
  - [x] Implement `Rule` to represent consolidated prompt rules and active behavioral rules.
  - [x] Implement `LatentSkill` to track the recurrence of user methodologies.
  - [x] Implement `Snapshot` (with manifest metadata: timestamp, scope, action, relative path, SHA-256 hash).
  - [x] Implement `AuditEvent` for append-only structured logs (JSONL).
  - [x] Implement `ContextSummary` segregating `project_summary`, `universal_preferences`, and `active_rules`.
  - [x] Configure all models with `model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)` or ensure that native serialization strictly uses `snake_case` and configure aliases appropriately if necessary (although persistence requires native `snake_case` directly on disk).

- [x] **Task 4: Export Entities at the Root of the Domain Module** (AC: 1)
  - [x] Update `src/universal_memory/domain/__init__.py` to cleanly expose all created entities and associated exceptions (if any).

- [x] **Task 5: Validate the Complete Local Test Suite** (AC: 1, 2, 4)
  - [x] Run `uv run pytest tests/domain/` and verify complete coverage (100% green in entity tests).
  - [x] Run `uv run ruff check .` and `uv run pyright` to ensure strict compliance with quality and static typing rules.

### Review Findings

- [x] [Review][Patch] Validate timestamps as UTC in all persistable entities [`src/universal_memory/domain/entities/base.py`:8]
- [x] [Review][Patch] Require canonical `schema_version` equal to 1 [`src/universal_memory/domain/entities/base.py`:6]
- [x] [Review][Patch] Validate `Snapshot.relative_path` as a safe relative path [`src/universal_memory/domain/entities/snapshot.py`:18]
- [x] [Review][Patch] Validate `Snapshot.hash` as a SHA-256 digest [`src/universal_memory/domain/entities/snapshot.py`:19]
- [x] [Review][Patch] Validate snapshot/audit references instead of accepting free placeholders [`src/universal_memory/domain/entities/audit_event.py`:15]
- [x] [Review][Patch] Prevent negative `recurrence_count` in facts and latent skills [`src/universal_memory/domain/entities/fact.py`:21]
- [x] [Review][Patch] Export all public scope enums in the `domain` and `domain.entities` modules [`src/universal_memory/domain/entities/__init__.py`:3]
- [x] [Review][Patch] Fix failures reported in `ruff check` and `pyright` [`tests/domain/test_entities.py`:104]

## Dev Notes

- **Clean Architecture Pattern (Boundaries):**
  - Domain entities reside in the innermost layer (`domain/entities/`). They CANNOT import anything from `application/`, `infrastructure/`, or `interfaces/`.
  - Use native Pydantic v2 without dependencies on additional frameworks.
- **JSON Persistence Patterns:**
  - In compliance with the architecture described in `architecture.md`, the persistable entities on disk (Facts, Rules, Snapshots, AuditEvents, LatentSkills) must always carry canonical metadata: `"schema_version": 1`.
  - Ensure timestamps use absolute UTC (e.g., `datetime.now(timezone.utc)` or serialization with `Z` suffix).
- **Prevention of Type Hallucinations:**
  - Ensure strict typing with Pyright. Use type-hints completos (e.g., `str`, `int`, `list[str]`, `dict[str, Any]`, `datetime`).
  - In Pydantic v2, prefer using `pydantic.Field` to specify default values (`default_factory=uuid4` or `default_factory=lambda: datetime.now(timezone.utc)`).

### Project Structure Notes

- Entities must be created within the `src/universal_memory/domain/entities/` layout.
- Expected file structure:
  - `src/universal_memory/domain/entities/__init__.py`
  - `src/universal_memory/domain/entities/fact.py`
  - `src/universal_memory/domain/entities/rule.py`
  - `src/universal_memory/domain/entities/latent_skill.py`
  - `src/universal_memory/domain/entities/snapshot.py`
  - `src/universal_memory/domain/entities/audit_event.py`
  - `src/universal_memory/domain/entities/context_summary.py`

### References

- **Architecture - Persistent Data Layout:** [architecture.md#L652-L679](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L652-L679)
- **Architecture - Naming Patterns:** [architecture.md#L245-L268](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L245-L268)
- **PRD - Functional Requirements:** [prd.md#L312-L318](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md#L312-L318)

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 3.5 Pro / Advanced Agentic Coding)

### Debug Log References

### Completion Notes List

- All domain models (Fact, Rule, LatentSkill, Snapshot, AuditEvent, ContextSummary) were implemented using Pydantic v2 with strong validations for UUID v4 and timezone.
- The unit test suite written beforehand (tests/domain/test_entities.py) was kept intact and is fully compatible with the created classes.
- Complete isolation of the domain layer was strictly maintained (Clean Architecture).

### File List

- `src/universal_memory/domain/entities/base.py`
- `src/universal_memory/domain/entities/fact.py`
- `src/universal_memory/domain/entities/rule.py`
- `src/universal_memory/domain/entities/latent_skill.py`
- `src/universal_memory/domain/entities/snapshot.py`
- `src/universal_memory/domain/entities/audit_event.py`
- `src/universal_memory/domain/entities/context_summary.py`
- `src/universal_memory/domain/entities/__init__.py`
- `src/universal_memory/domain/__init__.py`

### Change Log

- 2026-05-22: Story successfully initialized and designed; ready for TDD development.
- 2026-05-22: Implementation of domain entities completed and TDD compliance guaranteed.
