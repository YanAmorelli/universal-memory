# Story 3.2: Query Local Context with Text Search

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an external agent that needs context before acting,  
I want to query relevant facts via local search,  
so that I can retrieve useful memory without depending on network or external services.

## Acceptance Criteria

1. **Given** a local base with active facts,  
   **When** a text query is executed,  
   **Then** the system returns relevant facts using local search by substring, normalization, or regex as defined by the architecture,  
   **And** the results include identifier, scope, snippet or match reason, and relevant timestamp.

2. **Given** archived, stale, or purged facts,  
   **When** the default query is executed,  
   **Then** the system excludes these facts from the active results,  
   **And** allows including non-active states only via an explicit diagnostic option.

3. **Given** the environment is offline,  
   **When** the context query is executed,  
   **Then** it works without external connectivity,  
   **And** does not attempt to access remote services.

## Tasks / Subtasks

- [x] **Task 1: Define Port/Interface in the Domain for Text Search** (AC: 1, 2, 3)
  - [x] Analyze `src/universal_memory/domain/ports/fact_repository.py`.
  - [x] Add the abstract method `search(self, query: str, include_inactive: bool = False) -> list[Fact]` to the `FactRepository` interface.
  - [x] Ensure that the design of the `search` signature allows offline and case-insensitive filtering by default.

- [x] **Task 2: Write RED tests for search in the infrastructure repository `LocalFactRepository`** (AC: 1, 2, 3)
  - [x] Add tests in `tests/infrastructure/storage/test_local_fact_repository.py`.
  - [x] Cover basic text search (case-insensitive by substring).
  - [x] Cover search that ignores accents (basic normalization).
  - [x] Cover search by basic regex (if supported by the default engine).
  - [x] Test that inactive facts (`FactStatus.archived`, `FactStatus.stale`, `FactStatus.purged`) are filtered and excluded by default in the search.
  - [x] Test that inactive facts are returned when `include_inactive=True`.
  - [x] Test the default sorting of results based on descending creation date or direct relevance.
  - [x] Ensure total offline isolation of tests (no external API calls).

- [x] **Task 3: Implement search support in `LocalFactRepository`** (AC: 1, 2, 3)
  - [x] Implement the `search` method in `src/universal_memory/infrastructure/storage/local_fact_repository.py`.
  - [x] Add logic to normalize texts (remove accents or convert to lowercase for case-insensitive search).
  - [x] Apply simple substring matching and, if applicable, native Python regex (`re`).
  - [x] Filter in-memory facts (loaded from the JSONL) according to the fact's current status and the `include_inactive` parameter.
  - [x] Ensure that specific storage exceptions are raised in case of corruption or physical I/O errors.

- [x] **Task 4: Write RED tests for the `SearchFactsUseCase` application Use Case** (AC: 1, 2, 3)
  - [x] Create test file `tests/application/memory/test_search_facts_use_case.py` (or add to `tests/application/memory/test_memory_use_cases.py`).
  - [x] Cover `SearchFactsUseCase` receiving `SearchFactsCommand` with `query` and `include_inactive` attributes.
  - [x] Validate that the Use Case delegates the correct filters to the `FactRepository` and returns `SearchFactsResult`.
  - [x] Test behavior with empty query (should return an empty list or all facts according to the rule).

- [x] **Task 5: Implement the `SearchFactsUseCase` application Use Case** (AC: 1, 2, 3)
  - [x] Create the file `src/universal_memory/application/memory/search_facts_use_case.py`.
  - [x] Define the `SearchFactsCommand` and `SearchFactsResult` DTOs.
  - [x] Implement `SearchFactsUseCase` with dependency injection of the `FactRepository`.
  - [x] Register and expose the new objects in the file `src/universal_memory/application/memory/__init__.py`.

- [x] **Task 6: Ensure GREEN status, linting, and typing**
  - [x] Run `uv run pytest` and achieve 100% success.
  - [x] Run `uv run ruff check .` for linting and formatting validation.
  - [x] Run `uv run pyright` to ensure static typing and strict type compliance.

## Dev Notes

- **Scope of this story:** Exclusive focus on the domain, infrastructure, and application layers for offline text search. Final CLI and MCP commands will belong to the stories of Epic 4.
- **Offline-First:** Do not use libraries that depend on external connectivity. Substring processing and normalization must be 100% native (e.g., `re` module or string manipulation with `unicodedata`).
- **Resilience:** Maintain the resilient handling of JSONL line corruption introduced in Story 3.1.
- **Normalization:** Use `unicodedata.normalize('NFKD', texto)` to remove accents and facilitate exact matching.

### Project Structure Notes

- The change in the `FactRepository` interface requires any test stubs (such as `RecordingFactRepository` in `test_memory_use_cases.py`) to also implement the `search` method to avoid breaking the existing test suite.
- The folder structure strictly follows the established Clean Architecture patterns.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR3, FR16, NFR3)
- `_bmad-output/planning-artifacts/architecture.md` (Data Architecture, Core Memory Management)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (Output Contract, Error Contract)
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/domain/entities/fact.py`
- `src/universal_memory/application/memory/list_facts_use_case.py`

## Dev Agent Record

### Agent Model Used

Codex GPT-5

### Debug Log References

- `uv run pytest tests/domain/test_ports.py -q` failed initially until `FactRepository.search` was added.
- `uv run pytest tests/infrastructure/storage/test_local_fact_repository.py -q` failed initially until `LocalFactRepository.search` was implemented and the sorting test with inactive facts became deterministic.
- `uv run pytest tests/application/memory/test_memory_use_cases.py -q` failed initially until `SearchFactsUseCase` was created and exported.
- `uv run pytest` passed with 151 tests.
- `uv run ruff check .` passed.
- `uv run pyright` passed with 0 errors.

### Completion Notes List

- Added `FactRepository.search(query, include_inactive=False)` as an abstract contract for offline text search.
- Implemented `LocalFactRepository.search` with normalization via `unicodedata.normalize("NFKD", ...)`, case-insensitive search, fallback to native Python regex, filtering of active facts by default, and descending sorting by `created_at`.
- Added `SearchFactsUseCase`, `SearchFactsCommand`, and `SearchFactsResult`, with blank query returning an empty list without calling the repository.
- Updated stubs/tests to cover substring, accents, regex, inactive filters, diagnostic inclusion of inactive facts, sorting, and use case delegation.
- Adjusted the return contract of `FactRepository.write` to `object | None`, preserving the optional return used by the safe write pipeline and keeping `pyright` green.

### File List

- `_bmad-output/implementation-artifacts/3-2-consultar-contexto-local-com-busca-textual.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/memory/__init__.py`
- `src/universal_memory/application/memory/remember_fact_use_case.py`
- `src/universal_memory/application/memory/search_facts_use_case.py`
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `tests/application/memory/test_memory_use_cases.py`
- `tests/domain/test_ports.py`
- `tests/infrastructure/storage/test_local_fact_repository.py`

### Change Log

- 2026-05-27: Implemented offline local text search for facts, application use case, domain/application/infrastructure tests, and `pytest`, `ruff`, and `pyright` validations.

### Review Findings

- [x] [Review][Decision] Unescaped Regex Search & ReDoS Vulnerability in LocalFactRepository — The search implementation falls back to `re.search` using raw, unescaped user query. This can cause accidental regex matches (e.g. 'C+' matching 'C') and exposes a Regular Expression Denial of Service (ReDoS) vulnerability. Accent stripping before regex compilation also corrupts regex syntax.
- [x] [Review][Decision] Acceptance Criteria Violation: Lack of Match Snippet or Motive in Search Results — Acceptance Criterion 1 requires results to include 'identificador, escopo, trecho ou motivo de correspondência e timestamp relevante'. However, SearchFactsResult only returns a list of Fact entities directly, with no snippet or motive metadata.
- [x] [Review][Patch] Fragile Hardcoded Path.home() as Fallback in RememberFactUseCase [src/universal_memory/application/memory/remember_fact_use_case.py:44]
- [x] [Review][Patch] Dead Code and Fragile Unused References in RememberFactUseCase [src/universal_memory/application/memory/remember_fact_use_case.py:73]
- [x] [Review][Patch] Inconsistent Sorting Semantics Between List, Search, and Mock Repository [src/universal_memory/infrastructure/storage/local_fact_repository.py:145]
- [x] [Review][Patch] LSP Violation: Mock RecordingFactRepository.search Lacks Normalization and Regex Support [tests/application/memory/test_memory_use_cases.py:98]
- [x] [Review][Patch] Inefficient Full-Scan and Suboptimal Filtering in LocalFactRepository.search [src/universal_memory/infrastructure/storage/local_fact_repository.py:138]
- [x] [Review][Patch] Robustness Gaps: Potential AttributeErrors and TypeErrors on None/Malformed inputs in Repository Search [src/universal_memory/application/memory/search_facts_use_case.py:23]
- [x] [Review][Defer] Weak Domain Port Typing for write() and Abundant cast(Any, ...) Workarounds [src/universal_memory/domain/ports/fact_repository.py:50] — deferred, pre-existing
- [x] [Review][Defer] Clean Architecture Violation: Dynamic Runtime State and Injection on Repository Port [src/universal_memory/application/memory/remember_fact_use_case.py:40] — deferred, pre-existing
- [x] [Review][Defer] Agent Skills to explain UMEM capabilities to the model — deferred, new requirement
