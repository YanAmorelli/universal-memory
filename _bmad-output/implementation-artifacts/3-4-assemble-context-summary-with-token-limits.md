# Story 3.4: Assemble Context Summary with Token Limits

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an agent starting a new session,  
I want to receive a compact summary of the applicable memory,  
so that the initial context helps me without causing overflow or noise in my prompt.

## Acceptance Criteria

1. **Given** project facts, global preferences, and active rules,  
   **When** the context summary is assembled,  
   **Then** it prioritizes items by scope (project before global), recency (most recent first), status (active only), and relevance (relevance to the scope),  
   **And** clearly separates the sections `project_summary`, `universal_preferences`, and `active_rules`.

2. **Given** a configuration for character or token size limits (e.g., `max_size_chars`),  
   **When** the retrieved content exceeds this limit,  
   **Then** the system gracefully summarizes or removes lower-priority items,  
   **And** preserves the reference (fact IDs) to the original facts used to assemble the summary in the metadata or audit log.

3. **Given** a context read or injection requested by an agent,  
   **When** the operation is executed,  
   **Then** the system exposes evidence of the last read, the summary origin (global or project), and records injection failures via entity status or in the audit log,  
   **And** ensures that no sensitive information/secrets detected by `SecretScannerPort` are exposed in the summary.

## Tasks / Subtasks

- [x] **Task 1: Implement the Local Context Summary Repository (ContextSummaryRepository)** (AC: 1, 3)
  - [x] Create the `LocalContextSummaryRepository` implementation in `src/universal_memory/infrastructure/storage/local_context_summary_repository.py`.
  - [x] Implement reading and writing to a local file `.umem/memory/context_summaries.jsonl` (or similar) following the persistence pattern of `LocalFactRepository`.
  - [x] Support schema migration with the `migrate` method.
  - [x] Create complete unit and integration tests in `tests/infrastructure/storage/test_local_context_summary_repository.py` ensuring write isolation.

- [x] **Task 2: Design and Implement the AssembleContextSummaryUseCase Use Case** (AC: 1, 2, 3)
  - [x] Create the file `src/universal_memory/application/memory/assemble_context_summary_use_case.py`.
  - [x] Define the DTOs `AssembleContextSummaryCommand` and `AssembleContextSummaryResult`. The command must accept `scope`, `max_size_chars`, and optionally an agent or session identification key.
  - [x] Actively retrieve facts using `FactRepository` and active rules using `RuleRepository`.
  - [x] Filter inactive, obsolete, or sensitive-marked facts (secrets) using the `SecretScannerPort` port.
  - [x] Implement the sorting and prioritization algorithm:
    - Prioritize facts from the requested scope (`project` vs `global`).
    - Sort by recency (descending `created_at`) and optionally by recurrence count (`recurrence_count`).
  - [x] Structure the context summary with well-delimited keys:
    - `project_summary`: Summary of project-specific facts.
    - `universal_preferences`: Consolidated universal preferences of the user.
    - `active_rules`: Relevant active behavior rules.
  - [x] Implement size limit controls:
    - If the sum of the sections exceeds `max_size_chars`, prune lower-priority facts.
    - Summarize the text if the character count still exceeds the safety limit.
  - [x] Generate and persist an audit event in the `AuditLogRepository` recording the context read with the list of included fact IDs (evidence of last read, FR16).
  - [x] Save the generated `ContextSummary` via `ContextSummaryRepository` associated with the generated audit.

- [x] **Task 3: Develop the Unit and Integration Test Suite for the Use Case** (AC: 1, 2, 3)
  - [x] Create use case tests in `tests/application/memory/test_assemble_context_summary_use_case.py`.
  - [x] Test scenarios where the size limit is strictly respected (verify graceful removal of lower-priority facts).
  - [x] Test Secret Scanner integration ensuring that facts triggering the scanner are hidden/blocked in the injection summary.
  - [x] Validate the writing of audit events and generation of evidence containing the IDs of consumed facts.
  - [x] Test behavior in case of injection failure or database corruption.

- [x] **Task 4: Static Validation and Quality**
  - [x] Ensure 100% test pass rate by running `uv run pytest`.
  - [x] Run ruff for style checks: `uv run ruff check .`.
  - [x] Run pyright for strict type validation: `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Infinite Growth of Context Summary History — The JSONL repository appends new summaries indefinitely, causing performance degradation. Should we implement a retention strategy (e.g., keep the last 100 items) or allow it to grow without limits?
- [x] [Review][Patch] TOCTOU and Race Condition in Lock File Creation and Check [src/universal_memory/infrastructure/storage/local_context_summary_repository.py:41-78]
- [x] [Review][Patch] Priority Inversion and Blind Exclusion of Active Rules in Size Limit Control [src/universal_memory/application/memory/assemble_context_summary_use_case.py:227-248]
- [x] [Review][Patch] Priority Mixing between Scope and High-Priority Tags [src/universal_memory/application/memory/assemble_context_summary_use_case.py:269-276]
- [x] [Review][Patch] Character Limit Violation under Very Short or Negative Limits [src/universal_memory/application/memory/assemble_context_summary_use_case.py:110-137]
- [x] [Review][Patch] Rules Blocked by Secret Contamination Omitted in Audit [src/universal_memory/application/memory/assemble_context_summary_use_case.py:196-216]
- [x] [Review][Patch] Concurrency Bottleneck due to Exclusive Lock on Reads [src/universal_memory/infrastructure/storage/local_context_summary_repository.py:85-98]
- [x] [Review][Patch] Corrupted Database Exception Masked as Item Not Found [src/universal_memory/infrastructure/storage/local_context_summary_repository.py:79-83]
- [x] [Review][Patch] Missing Test Coverage for Tight Limit and Rule Prioritization Scenarios [tests/application/memory/test_assemble_context_summary_use_case.py:249-274]

## Dev Notes

- **Content Separator:** The context summary injected into the prompt must be structured in clean Markdown, using code blocks or clear markers for:
  - `# MEMORY CONTEXT SUMMARY`
  - `## Project Summary`
  - `## Universal Preferences`
  - `## Active Rules`
- **Ports to Use:**
  - `FactRepository` to retrieve relevant facts.
  - `RuleRepository` to retrieve active rules.
  - `SecretScannerPort` to intercept and block accidental leaks of API keys/secrets.
  - `AuditLogRepository` to record the injection/read event.
  - `ContextSummaryRepository` to save the history of generated summaries.
- **Prioritization Factors:**
  - Facts with status `active` must be prioritized. Facts with status `stale`, `archived`, or `purged` must be entirely ignored.
  - Facts with high-priority tags (such as `preferences` or `core-behavior`) must come first in their corresponding scope.
- **Reference Preservation:** The `ContextSummary` model contains the `audit_reference` field. This UUID must be exactly the same ID as the audit event generated during the context summary assembly. This way, traceability (FR16) is 100% maintained.

### Project Structure Notes

- The use case class must reside exactly in: `src/universal_memory/application/memory/assemble_context_summary_use_case.py`.
- The concrete repository must reside exactly in: `src/universal_memory/infrastructure/storage/local_context_summary_repository.py`.
- Class and method names must follow exactly the English nomenclature established in the domain ports and entities.

### References

- [PRD: FR16, FR17](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md#L336-L337)
- [Architecture Storage Contract](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L734)
- [Context Summary Entity](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/entities/context_summary.py)
- [Context Summary Port](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/ports/context_summary_repository.py)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- 2026-05-27T19:18:08Z: Task 1 red-green-refactor completed. Initial focused test failed due to the absence of `LocalContextSummaryRepository`; after implementation, `uv run pytest tests/infrastructure/storage/test_local_context_summary_repository.py` passed with 9 tests.
- 2026-05-27T19:18:08Z: Full regression check after Task 1: `uv run pytest` passed with 164 tests.
- 2026-05-27T19:21:27Z: Task 2 red-green-refactor completed. Initial focused test failed due to the absence of DTOs/use case; after implementation, `uv run pytest tests/application/memory/test_assemble_context_summary_use_case.py` passed with 5 tests.
- 2026-05-27T19:21:27Z: Full regression check after Task 2: `uv run pytest` passed with 169 tests.
- 2026-05-27T19:22:07Z: Task 3 validated with `uv run pytest tests/application/memory/test_assemble_context_summary_use_case.py` (5 passed) and full regression `uv run pytest` (169 passed).
- 2026-05-27T19:23:38Z: Task 4 validated with `uv run pytest` (169 passed), `uv run ruff check .` (passed) and `uv run pyright` (0 errors).

### Completion Notes List

- Implemented `LocalContextSummaryRepository` with JSONL persistence in `.umem/memory/context_summaries.jsonl`, local locking, atomic writing, read tolerance to corrupted lines, and write blocking when the file is corrupted.
- Exported the repository in `src/universal_memory/infrastructure/storage/__init__.py` and added a unit/integration test suite with isolation in `tmp_path`.
- Implemented `AssembleContextSummaryUseCase` with DTOs, Markdown assembly, prioritization by scope/tags/recurrence/recency, pruning by `max_size_chars`, filtering via `SecretScannerPort`, persistence of `ContextSummary`, and audit event with included fact IDs.
- Use case suite covers strict limits, pruning of lower-priority facts, blocking of secrets, audit evidence, summary origin, and persistence/corrupted database failure.
- Static validation and full regression check executed successfully for the story.

### File List

- `_bmad-output/implementation-artifacts/3-4-montar-resumo-de-contexto-com-limites-de-tokens.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/infrastructure/storage/__init__.py`
- `src/universal_memory/infrastructure/storage/local_context_summary_repository.py`
- `src/universal_memory/application/memory/__init__.py`
- `src/universal_memory/application/memory/assemble_context_summary_use_case.py`
- `tests/application/memory/test_assemble_context_summary_use_case.py`
- `tests/infrastructure/storage/test_local_context_summary_repository.py`

### Change Log

- 2026-05-27T19:24:25Z: Implemented context summary assembly with local persistence, auditing, limit pruning, secrets filtering, and complete tests.
