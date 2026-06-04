# Story 3.3: Implement Retrieval Benchmark

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer of universal-memory,  
I want to compare local text search with a local semantic candidate or stub,  
so that the default retrieval strategy is justified by latency, quality, and simplicity data.

## Acceptance Criteria

1. **Given** the `benchmarks/retrieval.py` script,  
   **When** the benchmark is executed,  
   **Then** it creates or uses a base of at least 1,000 test facts,  
   **And** it runs at least 30 representative queries derived from PRD journeys and requirements.

2. **Given** two comparable strategies (local text search and local semantic candidate/stub),  
   **When** the benchmark finishes,  
   **Then** it records p95 latency, quality score 1-5, offline compatibility, and operational complexity,  
   **And** it saves the result to `.umem/benchmarks/retrieval-results.json`.

3. **Given** the benchmark results,  
   **When** the default strategy is selected,  
   **Then** the justification is recorded along with the results,  
   **And** the choice does not contradict the 150ms p95 limits for local queries.

## Tasks / Subtasks

- [x] **Task 1: Model Data and Prepare Test Dataset (1,000 facts)** (AC: 1)
  - [x] Design the DTO structure to represent data and execution parameters in the benchmark.
  - [x] Implement a dynamic synthetic generator in `benchmarks/retrieval.py` that creates at least 1,000 representative `Fact` instances.
  - [x] Include variability of scope (`global` and `project`), tags, and diverse text content (including accents, case variations, and common terms from the software development domain).
  - [x] Ensure generation is idempotent or writes to an isolated temporary file to avoid affecting actual production data.

- [x] **Task 2: Structure the 30 Representative Queries** (AC: 1)
  - [x] Map and write at least 30 queries based on the PRD user stories (e.g., queries about secrets, local rules, global scope, specific architectural terms, etc.).
  - [x] Add an answer key or relevance expectation (which facts should be retrieved) for each query to calculate the quality score.

- [x] **Task 3: Implement the Local Text Search Strategy** (AC: 2, 3)
  - [x] Load the database of 1,000 facts into a test instance of `LocalFactRepository` or simulate the identical offline substring/regex search and normalization algorithm.
  - [x] Execute the 30 queries sequentially using text search.
  - [x] Accurately measure (`time.perf_counter()`) the latency of each query, calculating the average and the 95th percentile (p95).

- [x] **Task 4: Implement the Local Semantic Candidate/Stub** (AC: 2, 3)
  - [x] Design a local semantic retrieval stub (or a simulated cosine search/lightweight heuristic mapping) for comparison purposes.
  - [x] Document in code the operational assumptions of the real semantic search (local embeddings loading, model overhead, memory footprint, etc.).
  - [x] Time search executions to simulate/measure latency and collect comparative performance data.

- [x] **Task 5: Calculate Comparison Metrics and Generate Justification** (AC: 2, 3)
  - [x] Evaluate the quality of both strategies on a 1 to 5 scale, based on the precision and recall of the ideal facts.
  - [x] Define offline compatibility (100% offline for native text search vs limitations/requirements of semantic stubs).
  - [x] Quantify operational complexity (e.g., 1 for native text search without additional dependencies, 4 for local semantic that requires PyTorch/SentenceTransformers and 500MB+ model downloads).
  - [x] Select the default strategy based on latency constraints (p95 < 150ms) and simplicity, writing a formal technical justification.

- [x] **Task 6: Save Results Report and Create Validation Tests** (AC: 2, 3)
  - [x] Ensure the script creates and saves results in `.umem/benchmarks/retrieval-results.json` in the expected JSON format.
  - [x] Write contract or integration tests in `tests/infrastructure/test_retrieval_benchmark.py` (or under the appropriate directory) to validate benchmark execution and the JSON output format.
  - [x] Ensure 100% network isolation and absence of side effects on the actual persisted memory.

- [x] **Task 7: Execute Static Validation and Overall Quality**
  - [x] Run the entire suite via `uv run pytest` ensuring all tests pass.
  - [x] Validate adherence to formatting and linting standards using `uv run ruff check .`.
  - [x] Validate strict typing with `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Artificial bias in Quality Score calculation in Benchmark — The `local_text` strategy returns the 10 most recent items (sorted by `created_at` descending), excluding the expected ideal fact (which is the oldest). On the other hand, the `semantic_stub` strategy sorts by ascending `id` as a tie-breaker, which keeps the ideal fact at the top and artificially inflates its score. We need to decide how to balance this comparison.
- [x] [Review][Patch] Variable leakage in search use case loop [src/universal_memory/application/memory/search_facts_use_case.py:67]
- [x] [Review][Patch] Inadequate regex query normalization corrupting patterns [src/universal_memory/infrastructure/storage/local_fact_repository.py:152]
- [x] [Review][Patch] Lack of OSError handling when writing benchmark report [benchmarks/retrieval.py:326]
- [x] [Review][Patch] Absence of regex search support in the benchmark's mock text search [benchmarks/retrieval.py:159]
- [x] [Review][Patch] Risk of IndexError in p95 percentile calculation with an empty list [benchmarks/retrieval.py:183]
- [x] [Review][Patch] Risk of StatisticsError in quality score calculation with an empty list [benchmarks/retrieval.py:189]
- [x] [Review][Patch] Risk of TypeError in benchmark text normalization with null content [benchmarks/retrieval.py:64]
- [x] [Review][Defer] Duplication of the MIN_REGEX_QUERY_LENGTH constant [multiple files] — deferred, pre-existing
- [x] [Review][Defer] Duplication of text normalization logic [multiple files] — deferred, pre-existing
- [x] [Review][Defer] Silencing re.error exceptions in the fact repository [src/universal_memory/infrastructure/storage/local_fact_repository.py:165] — deferred, pre-existing
- [x] [Review][Defer] Potential ReDoS vulnerability in regex searches [src/universal_memory/infrastructure/storage/local_fact_repository.py] — deferred, pre-existing

## Dev Notes

- **Results Location:** The final results file must be saved exactly in `.umem/benchmarks/retrieval-results.json`. Create the `benchmarks` folder inside the local data directory if it does not exist.
- **Selected Default Strategy:** Since native text search operates in local memory reading JSONL extremely efficiently (< 5ms), the justification should document that it easily satisfies the 150ms p95 limit, eliminating complex dependencies (SentenceTransformers, PyTorch) that would violate the "boring technology" principle and simplicity of CLI installation.
- **Quality Metrics (1-5):**
  - 5: Excellent (returns all expected results with zero noise).
  - 3: Acceptable (returns expected results but with partial matches or some noise).
  - 1: Poor (matching errors or loss of crucial facts).

### Project Structure Notes

- The `benchmarks/retrieval.py` file must be an executable script that can be called directly via command line (e.g., `python benchmarks/retrieval.py` or via `uv run`).
- Ensure that any sub-module imports (`universal_memory.*`) use absolute imports based on the package root.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR3, Retrieval Latency, Retrieval Benchmark)
- `_bmad-output/planning-artifacts/architecture.md` (Retrieval Benchmark Protocol, Performance, Structure Mapping)
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- `uv run pytest tests/infrastructure/test_retrieval_benchmark.py` - initial RED failed due to missing `benchmarks.retrieval` module; GREEN passed after implementation.
- `uv run python benchmarks/retrieval.py` - generated `.umem/benchmarks/retrieval-results.json` with 1,000 facts and 30 queries.
- `uv run pytest` - 155 passed.
- `uv run ruff check .` - passed.
- `uv run pyright` - 0 errors, 0 warnings.

### Completion Notes List

- Implemented `benchmarks/retrieval.py` with query DTOs, metrics, and strategy configuration.
- Synthetic generator creates 1,000 `Fact` facts in memory, with `global`/`project` scopes, tags, accents, case variations, and domain terms.
- Added 30 representative queries with expected IDs for quality calculation.
- Implemented `local_text` and `semantic_stub` strategies, with measurement via `time.perf_counter()`, mean, p95, 1-5 score, offline compatibility, and operational complexity.
- Result saved in `.umem/benchmarks/retrieval-results.json`; default strategy registered is `local_text`, justified by p95 under 150ms and lower complexity.
- Added benchmark contract tests and minor lint adjustments in the existing text search to allow global `ruff check .`.

### File List

- `.umem/benchmarks/retrieval-results.json`
- `_bmad-output/implementation-artifacts/3-3-implementar-benchmark-de-recupera-o.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `benchmarks/retrieval.py`
- `src/universal_memory/application/memory/search_facts_use_case.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `tests/application/memory/test_memory_use_cases.py`
- `tests/infrastructure/storage/test_local_fact_repository.py`
- `tests/infrastructure/test_retrieval_benchmark.py`

### Change Log

- 2026-05-27: Implemented local retrieval benchmark with JSON report, contract tests, and full validations.
