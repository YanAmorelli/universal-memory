# Story 1.1: Initialize Product Python Scaffold

Status: done


<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a universal-memory developer,
I want to initialize the Python package with defined structure, dependencies, and tooling,
so that the project has a reproducible base for TDD development and parallel work.

## Acceptance Criteria

1. **Given** a repository without a complete Python scaffold,
   **When** the project is initialized with `uv`,
   **Then** `pyproject.toml`, `uv.lock`, `.python-version`, `src/universal_memory/`, `tests/`, `tests/contracts/`, and `benchmarks/` exist;
   **And** the runtime is Python 3.12+ and versioned runtime/dev dependencies are configured.

2. **Given** the initial scaffold,
   **When** verification commands are executed,
   **Then** `ruff`, `pyright`, and `pytest` run without failures against the minimal base;
   **And** there is at least one initial test that would fail if the package were not importable.

3. **Given** the initial scaffold versioned in the repository,
   **When** a change is pushed or a pull request is created,
   **Then** a CI workflow in `.github/workflows/ci.yml` runs `ruff`, `pyright`, and `pytest`;
   **And** the workflow fails when lint, type check, or automated tests fail.

## Tasks / Subtasks

- [x] **Task 1: Configure Environment and UV Scaffold** (AC: 1)
  - [x] Create or configure the `.python-version` file with `3.12` or higher.
  - [x] Configure the basic scaffold with `uv init --package` in the project root directory.
  - [x] Organize and create the package root in `src/universal_memory/`.
- [x] **Task 2: Configure Dependencies and Tools in pyproject.toml** (AC: 1, 2)
  - [x] Add recommended runtime dependencies: `pydantic>=2.0`, `typer>=0.9.0` (optional in this step, but recommended), `tomli-w>=1.0.0` (for offline TOML writing), and `fastmcp>=0.1.0` (for MCP server).
  - [x] Add development dependencies: `pytest>=8.0.0`, `ruff>=0.3.0`, `pyright>=1.1.350`.
  - [x] Configure the `[tool.ruff]` section with strict rules (e.g., `select = ["E", "F", "I", "N", "UP", "PL", "RUF"]`).
  - [x] Configure the `[tool.pyright]` section defining the type check layout (e.g., `include = ["src", "tests"]` and `typeCheckingMode = "standard"` or `"strict"`).
  - [x] Run `uv sync` to lock the dependencies in `uv.lock`.
- [x] **Task 3: Structure the Classic Directory Tree** (AC: 1)
  - [x] Create the initial package files:
    - [x] `src/universal_memory/__init__.py` (exposing the product version and ensuring importability)
    - [x] `src/universal_memory/__main__.py` (minimal entry point that can be run via `python -m universal_memory`)
  - [x] Create the complete test subdirectories structure:
    - [x] `tests/conftest.py` (global fixtures and minimal setup mocks)
    - [x] `tests/contracts/` (for compliance tests with port contracts)
    - [x] `tests/domain/` (for pure domain entity and exception tests)
    - [x] `tests/application/` (for Use Case tests)
    - [x] `tests/infrastructure/` (for I/O adapter, storage, and security tests)
    - [x] `tests/interfaces/` (for CLI and MCP server tests)
  - [x] Create the `benchmarks/` directory and add a placeholder/initial structure file (e.g., `benchmarks/__init__.py`).
- [x] **Task 4: Implement Importability (Smoke) Test** (AC: 2)
  - [x] Create `tests/test_smoke.py` with at least one initial test that verifies that the `universal_memory` package can be imported correctly and exposes its version.
- [x] **Task 5: Configure GitHub Actions Workflow (CI)** (AC: 3)
  - [x] Create `.github/workflows/ci.yml` configured to run on every push and pull request targeting the main branch (`main` or `dev`).
  - [x] Ensure the pipeline installs `uv`, configures the dependency cache, runs `ruff check`, `ruff format --check`, `pyright` for static typing, and finally runs `pytest` for unit tests.
- [x] **Task 6: Local Validation of the Full Tooling** (AC: 2)
  - [x] Ensure that `uv run ruff check .` and `uv run ruff format --check .` run without failures.
  - [x] Ensure that `uv run pyright` passes without warnings or errors.
  - [x] Ensure that `uv run pytest` runs successfully and all initial tests pass.

## Dev Notes

- **Unified Directory Structure and Boundaries:**
  - The structural layout described in the architecture in [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L335-L398) must be strictly followed.
  - Importing dependencies from `infrastructure/` or `interfaces/` inside `domain/` or `application/` is prohibited.
  - The interfaces (`cli` and `mcp`) and infrastructure (`storage`, `security`) must be decoupled from the core business logic using ports in `domain/ports/`.
- **Dependency Management with `uv`:**
  - Avoid using any tool other than `uv`. Resolution speed and local execution are crucial for local DevEx cycle performance.
  - Remember to run `uv sync` whenever the `pyproject.toml` file is modified to ensure that `uv.lock` remains consistently updated.
- **Typing and Style Guidelines:**
  - The `ruff` linter and `pyright` type checker are not optional; they act as guardians of repository health and code readability. CI must reject any code that fails these steps.

### Project Structure Notes

- The project must be configured using the classic Python `src/` layout to avoid issues with uninstalled local package imports during CLI and MCP execution.
- The `benchmarks/` directory must be kept at the same level as `src/` and `tests/` to facilitate isolated runs without coupling to the main package runtime.

### References

- **Software Architecture**: [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L335-L398)
- **DevEx Interaction Specification**: [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- **Complete PRD**: [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash

### Debug Log References

- 2026-05-22: RED confirmed with `uv run --with pytest pytest tests/test_smoke.py`; expected failure due to `ModuleNotFoundError: No module named 'universal_memory'`.
- 2026-05-22: GREEN/final validation with `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run pytest` and `uv run python -m universal_memory`.

### Completion Notes List

- Initial Python scaffold created with `uv init --package`, runtime `>=3.12`, `src/` layout, `.python-version`, and `uv.lock`.
- Runtime and dev dependencies configured in `pyproject.toml`, including `pydantic`, `typer`, `tomli-w`, `fastmcp`, `pytest`, `ruff`, and `pyright`.
- Initial structure for package, tests, contracts, and benchmarks created according to the story architecture.
- Smoke test ensures package importability and `__version__` exposure.
- CI configured for push and pull request to `main` and `dev`, running `ruff`, `pyright`, and `pytest`.

### File List

- `.github/workflows/ci.yml`
- `.python-version`
- `benchmarks/__init__.py`
- `pyproject.toml`
- `src/universal_memory/__init__.py`
- `src/universal_memory/__main__.py`
- `tests/application/.gitkeep`
- `tests/conftest.py`
- `tests/contracts/.gitkeep`
- `tests/domain/.gitkeep`
- `tests/infrastructure/.gitkeep`
- `tests/interfaces/.gitkeep`
- `tests/test_smoke.py`
- `uv.lock`

### Change Log

- 2026-05-22: Initialized product Python scaffold, local tooling, smoke test, and CI; story moved to review.


### Review Findings

- [x] [Review][Decision] [Resolved: Dynamic] Duplicated and static package version — Version "0.1.0" is declared in both pyproject.toml and src/universal_memory/__init__.py.
- [x] [Review][Decision] [Resolved: Kept Unbounded] Unbounded dependencies — Pydantic, Typer, Tomli-w, and Fastmcp are declared without upper limits in pyproject.toml.
- [x] [Review][Decision] [Resolved: Standard Checking] Pyright in strict mode in tests — Pyright is configured with strict type checking over the tests/ folder, which can generate excessive friction.
- [x] [Review][Decision] [Resolved: Extended] Restricted Ruff linter ruleset — Ruff selects only rules ["E", "F", "I", "N", "UP", "PL", "RUF"]. We could extend this to bandit (S) and bugbear (B).
- [x] [Review][Patch] Create .gitkeep files for test subdirectories [tests/:1]
- [x] [Review][Patch] Add license and packaging metadata in pyproject.toml [pyproject.toml:1]
- [x] [Review][Patch] Define least privilege permissions in CI [ci.yml:1]
- [x] [Review][Patch] Include benchmarks in Pyright scope [pyproject.toml:38]
- [x] [Review][Patch] Improve smoke test assertion and scope [tests/test_smoke.py:5]
- [x] [Review][Defer] Handle BrokenPipeError in CLI execution [src/universal_memory/__main__.py:1] — deferred, pre-existing
- [x] [Review][Defer] Test matrix for multiple Python versions in CI [.github/workflows/ci.yml:1] — deferred, pre-existing
- [x] [Review][Defer] Add test coverage with pytest-cov in CI [.github/workflows/ci.yml:1] — deferred, pre-existing
