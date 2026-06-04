# Story 3.5: Show Memory Status

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user checking the health of the local memory,
I want to query the status, size, and activity of the base,
so that I know if the project is configured and which data is active.

## Acceptance Criteria

1. **Given** an initialized `.umem/` base  
   **When** the status is queried by use case or CLI  
   **Then** the system shows the count of facts by scope and status, active rules, registered skills, approximate size of the base, and last known health check  
   **And** the human-readable output is clear for reading in the terminal  
   **And** with `--format json`, it returns pure JSON with `initialized`, `project_path`, `fact_counts`, `active_rules_count`, `registered_skills_count`, `approximate_size_bytes`, `last_health_check`, and `host_validation`  
   **And** the output follows the guidelines of `_bmad-output/planning-artifacts/devex-interaction-spec.md`.

2. **Given** the current directory does not have a `.umem/` folder  
   **When** the status is queried  
   **Then** the system returns an actionable message indicating that the project was not initialized  
   **And** it does not automatically create files during a read-only query  
   **And** with `--format json`, it returns `initialized: false`, `project_path`, and `recommended_action`  

3. **Given** the environment is offline  
   **When** the status is queried  
   **Then** the operation works solely with local data  
   **And** does not depend on external hosts or network calls.

## Tasks / Subtasks

- [x] **Task 1: Implement the GetMemoryStatusUseCase use case** (AC: 1, 2, 3)
  - [x] Create the file `src/universal_memory/application/memory/get_memory_status_use_case.py`.
  - [x] Define the DTOs `GetMemoryStatusCommand` and `GetMemoryStatusResult`.
  - [x] The use case constructor must receive:
    - `fact_repository: FactRepository`
    - `rule_repository: RuleRepository`
    - `latent_skill_repository: LatentSkillRepository`
    - `layout_port: ProjectLayoutPort`
  - [x] Validate the project initialization using `layout_port` (e.g., invoking `is_project_initialized`).
  - [x] If not initialized, return `initialized=False` and `recommended_action="Run umem init from the project root."`.
  - [x] If initialized:
    - Retrieve all facts via `fact_repository.list()` and group them by `scope` and `status` (counting each combination).
    - Filter and count rules with status `RuleStatus.active` via `rule_repository.list(status=RuleStatus.active)`.
    - Filter and count skills with status `LatentSkillStatus.active` via `latent_skill_repository.list(status=LatentSkillStatus.active)`.
    - Compute the approximate size in bytes of the `.umem/` base by recursively summing the size of all files.
    - Validate hosts by checking if the agent instruction files exist in the project root:
      - `claude`: `"valid"` if `CLAUDE.md` exists, otherwise `"unconfigured"`.
      - `gemini`: `"valid"` if `AGENTS.md` exists, otherwise `"unconfigured"`.
    - Run a local diagnostic health check (e.g., verify read/write permission) and record the current ISO 8601 UTC timestamp as `last_health_check`.

- [x] **Task 2: Export the use case and register DTOs** (AC: 1)
  - [x] Update `src/universal_memory/application/memory/__init__.py` to export `GetMemoryStatusUseCase`, `GetMemoryStatusCommand`, and `GetMemoryStatusResult`.

- [x] **Task 3: Develop the status command CLI integration** (AC: 1, 2)
  - [x] Update `src/universal_memory/interfaces/cli/init_command.py`:
    - Add the `status` command parser with the `--format` option (`human` or `json`).
    - Create the `_run_status` handler that executes the use case and formats the output according to `devex-interaction-spec.md`.
    - In `json` format, return the standard success envelope:
      ```json
      {
        "ok": true,
        "operation": "status",
        "scope": "project",
        "data": {
          "initialized": true,
          "project_path": ".",
          "fact_counts": {
            "global": {
              "active": 0,
              "stale": 0,
              "archived": 0,
              "purged": 0
            },
            "project": {
              "active": 0,
              "stale": 0,
              "archived": 0,
              "purged": 0
            }
          },
          "active_rules_count": 0,
          "registered_skills_count": 0,
          "approximate_size_bytes": 0,
          "last_health_check": "2026-05-27T20:00:00Z",
          "host_validation": {
            "claude": "unconfigured",
            "gemini": "unconfigured"
          }
        },
        "warnings": []
      }
      ```
    - In case of an uninitialized base and `--format json`, return `initialized: false`, `project_path`, and `recommended_action` inside the `data` key.
    - In `human` format, display an elegant CLI rendering using formatted text or tables clearly indicating the health, size, hosts, and counts.

- [x] **Task 4: Connect and Adapt Pending Repositories in Bootstrap** (AC: 1)
  - [x] Modify `src/universal_memory/bootstrap/cli.py` to inject the new use case into `build_main`.
  - [x] Since `RuleRepository` and `LatentSkillRepository` do not yet have concrete production implementations (they are backlog), create lightweight local stubs that simply inherit from the abstract interfaces (or create robust mock production classes that return empty lists by default) to keep the CLI fully testable and operational.

- [x] **Task 5: Implement Automated Test Suite** (AC: 1, 2, 3)
  - [x] Create unit and integration tests for the use case in `tests/application/memory/test_get_memory_status_use_case.py`.
  - [x] Cover scenarios of initialized base, uninitialized base, correct count, and host detection.
  - [x] Create CLI integration unit tests in `tests/interfaces/cli/test_status_command.py` ensuring support for both human and json outputs and the standard response envelope.

- [x] **Task 6: Style Validation, Types, and Full Regression**
  - [x] Run the test suite with `uv run pytest` and ensure 100% success.
  - [x] Run the ruff linter and formatter: `uv run ruff check .`.
  - [x] Validate the pyright strict type checking: `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Missing actual local health check/diagnostics (and misleading current time field) [src/universal_memory/application/memory/get_memory_status_use_case.py:85-86]
- [x] [Review][Patch] Vulnerabilities and unhandled OSError in directory size recursive calculation [src/universal_memory/application/memory/get_memory_status_use_case.py:156-159]
- [x] [Review][Patch] Flawed relative project path resolution and unhandled OSError when CWD is deleted/restricted [src/universal_memory/application/memory/get_memory_status_use_case.py:166-172]
- [x] [Review][Patch] Fragile scope mapping and potential KeyError for unexpected FactScope or FactStatus [src/universal_memory/application/memory/get_memory_status_use_case.py:126-129]
- [x] [Review][Patch] Hardcoded data directory path in approximate_size_bytes calculation [src/universal_memory/application/memory/get_memory_status_use_case.py]
- [x] [Review][Patch] Inconsistent language between CLI outputs and recommended action [src/universal_memory/application/memory/get_memory_status_use_case.py:122]
- [x] [Review][Patch] Naive "Host Validation" checks hardcoded to Claude and Gemini [src/universal_memory/application/memory/get_memory_status_use_case.py]
- [x] [Review][Patch] Hard dependency on system clock for last_health_check [src/universal_memory/application/memory/get_memory_status_use_case.py:84]
- [x] [Review][Patch] CLI status parser lacks catch-all error handling for unexpected exceptions [src/universal_memory/interfaces/cli/init_command.py:258-274]
- [x] [Review][Defer] Inefficient full-database scan to count facts [src/universal_memory/application/memory/get_memory_status_use_case.py] — deferred, pre-existing

## Dev Notes

- **UX/CLI Compliance:** The structured output must strictly comply with the contracts detailed in `devex-interaction-spec.md`. No Rich tags or extra prose text should be output when `--format json` is active.
- **Ports to Use:**
  - `FactRepository` to list and group the count of facts.
  - `RuleRepository` to query active rules.
  - `LatentSkillRepository` to count registered skills.
  - `ProjectLayoutPort` for robust checking of the `.umem/` structure.
- **Stub Strategy:** Use simple stub implementations in the backlog repositories to avoid injection failures in the production CLI until the respective cycle stories are implemented.

### Project Structure Notes

- The use case must reside exactly in: `src/universal_memory/application/memory/get_memory_status_use_case.py`.
- The use case test must reside exactly in: `tests/application/memory/test_get_memory_status_use_case.py`.
- The CLI command test must reside in: `tests/interfaces/cli/test_status_command.py`.

### References

- [PRD: FR10, FR16](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md#L326)
- [DevEx Interaction Spec: umem status Command](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md#L133-L148)
- [Project Layout Domain](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/project_layout.py)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest tests/application/memory/test_get_memory_status_use_case.py tests/interfaces/cli/test_status_command.py` initially failed due to missing imports of `GetMemoryStatusCommand`, confirming RED.
- `uv run pytest tests/application/memory/test_get_memory_status_use_case.py tests/interfaces/cli/test_status_command.py tests/domain/test_ports.py` passed with 26 tests.
- `uv run pytest` passed with 179 tests.
- `uv run ruff check .` passed.
- `uv run pyright` passed.

### Completion Notes List

- Implemented `GetMemoryStatusUseCase` with DTOs for initialized and uninitialized status, fact count by scope/status, active rules and skills count, approximate size of `.umem/`, local health check with UTC timestamp, and host validation for `CLAUDE.md`/`AGENTS.md`.
- Exposed `is_project_initialized` in `ProjectLayoutPort` and in the local adapter to allow read-only queries without creating `.umem/`.
- Added `status` CLI command with human-readable output and pure JSON in the standard envelope, including a reduced and actionable payload when the base is not initialized.
- Connected the status in bootstrap with `LocalFactRepository` and empty stubs for `RuleRepository` and `LatentSkillRepository` while the production repositories are in the backlog.
- Added unit and integration tests covering initialized base, uninitialized base, counts, host detection, JSON envelope, human-readable output, bootstrap composition, and network absence.

### File List

- `_bmad-output/implementation-artifacts/3-5-exibir-status-da-mem-ria.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/memory/__init__.py`
- `src/universal_memory/application/memory/get_memory_status_use_case.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/domain/ports/project_layout_port.py`
- `src/universal_memory/infrastructure/config/adapters.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/memory/test_get_memory_status_use_case.py`
- `tests/domain/test_ports.py`
- `tests/interfaces/cli/test_status_command.py`

### Change Log

- 2026-05-27: Implemented local memory status command/use case and moved the story to review.
