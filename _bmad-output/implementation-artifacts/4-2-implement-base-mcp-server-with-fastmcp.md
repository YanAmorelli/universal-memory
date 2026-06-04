# Story 4.2: Implement Base MCP Server with FastMCP

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an external agent compatible with MCP,
I want to access `universal-memory` via a native MCP server,
so that I can read context and invoke capabilities without relying on CLI subprocesses.

## Acceptance Criteria

1. **Structure and Base Registration of FastMCP**:
   - **Given** the Python package initialized with the `fastmcp>=0.1.0` dependency configured,
   - **When** the MCP server is executed,
   - **Then** it must instantiate and expose a FastMCP server named `"universal-memory"`;
   - **And** must register the base tools or resources cleanly using the declarative FastMCP API (`@mcp.tool` or `@mcp.resource`).

2. **Status (Health Check) Exposure and Context Reading**:
   - **Given** the MCP server running,
   - **When** a client invokes status reading (health check) or context retrieval,
   - **Then** the server must expose at least:
     - A tool/resource corresponding to the `status` command (`GetMemoryStatusUseCase`).
     - A tool/resource corresponding to the `context` command (`AssembleContextSummaryUseCase`).
   - **And** the MCP responses must preserve exactly the same semantic fields defined in `_bmad-output/planning-artifacts/devex-interaction-spec.md` for the respective JSON CLI (exact envelope containing `ok: true`, `operation`, `scope`, and `data` with corresponding keys).

3. **Clean Architecture and Zero Coupling with Repositories**:
   - **Given** a call to any MCP endpoint,
   - **When** the MCP adapter processes the request,
   - **Then** it must delegate execution strictly to the Use Cases layer of the application (dependency injection via bootstrap);
   - **And** must never instantiate or access the repositories, local persistence, or business logic layer directly within the MCP decorators.

4. **Offline-First Operations and Local Robustness**:
   - **Given** an offline environment with no internet connectivity,
   - **When** the MCP server initializes or executes local capabilities (such as reading the status or obtaining the project memory context),
   - **Then** it must function without freezing, without making external requests, and without depending on any cloud host;
   - **And** failures in external infrastructure services must not prevent the functioning of basic local operations.

## Tasks / Subtasks

- [x] **Task 1: Structure the MCP Adapter Directory** (AC: 1, 3)
  - [x] Create the adapter folder at `src/universal_memory/interfaces/mcp/`.
  - [x] Create the file `src/universal_memory/interfaces/mcp/__init__.py`.
  - [x] Create `src/universal_memory/interfaces/mcp/server.py` containing the FastMCP initialization:
    ```python
    from fastmcp import FastMCP
    mcp = FastMCP("universal-memory")
    ```
  - [x] Define the injection interface for Use Cases in the MCP server (for example, by creating a configuration function or class to dynamically register routes from the provided use cases).

- [x] **Task 2: Create the MCP Server Bootstrap** (AC: 1, 3)
  - [x] Create the module `src/universal_memory/bootstrap/mcp.py` responsible for instantiating the infrastructure (ports, repositories, layout) and injecting the Use Cases at server startup.
  - [x] Ensure absolute reuse of the same dependencies and use cases injected into the CLI (`bootstrap/cli.py`), maintaining dependency injection integrity and avoiding reinventing the wheel.
  - [x] Add a CLI command `mcp start` or create an entry script to allow the user to easily start the MCP server (e.g., via `umem mcp start` or `python -m universal_memory.bootstrap.mcp`).

- [x] **Task 3: Implement the `status` Tool / Resource** (AC: 2, 3)
  - [x] Expose the `status` endpoint as a FastMCP tool (or resource `@mcp.resource`).
  - [x] Delegate execution to the injected `GetMemoryStatusUseCase`.
  - [x] Ensure that the returned response payload has the canonical structure defined in `devex-interaction-spec.md` (keys `initialized`, `project_path`, `fact_counts`, `active_rules_count`, `registered_skills_count`, `approximate_size_bytes`, `last_health_check`, `host_validation`, `recommended_action` when uninitialized).

- [x] **Task 4: Implement the `context` Tool / Resource** (AC: 2, 3)
  - [x] Expose the `context` endpoint as a FastMCP tool.
  - [x] Delegate execution to the injected `AssembleContextSummaryUseCase`.
  - [x] Ensure that the response payload preserves the fields defined in `devex-interaction-spec.md` (keys `project_summary`, `universal_preferences`, `active_rules`, `source_fact_ids`, `truncated`, `token_estimate`, `last_read_at`).

- [x] **Task 5: Initial Error Handling and Exception Mapping** (AC: 2)
  - [x] Although exact mapping of JSON-RPC codes is the focus of Story 4.4, implement basic handling in the MCP adapter to capture domain exceptions and return them with clean, safe debugging messages.
  - [x] Ensure that secrets or leaked absolute paths are not exposed in MCP error messages.

- [x] **Task 6: Add Parity and Integration Tests for MCP** (AC: 1, 2, 3, 4)
  - [x] Create file `tests/interfaces/mcp/test_server.py`.
  - [x] Test that the MCP server instance initializes offline successfully.
  - [x] Test the `status` tool by injecting a mock of the Use Case and asserting that the returned payload follows exactly the structure of `devex-interaction-spec.md`.
  - [x] Test the `context` tool with a mock of the equivalent use case, validating fields and semantic coherence.
  - [x] Run the entire suite using `pytest` and ensure 100% success.

### Review Findings

- [x] [Review][Decision] Missing Compiled Context Content in context Tool Response — The context tool processes all metadata but omits the actual assembled context string (context_markdown) in the returned data envelope. Since the devex-interaction-spec.md spec does not list a specific key for the full markdown text in the JSON keys, we need to decide how to return this.
- [x] [Review][Decision] Hardcoded Portuguese Error Messages — The error message mappings return Portuguese text (e.g. "Conteudo sensivel bloqueado."), whereas the rest of the codebase and exceptions are in English. While consistent with user-facing CLI localization, we should confirm if this is the desired behavior for MCP tools.
- [x] [Review][Patch] Registered MCP tools lack docstrings [src/universal_memory/interfaces/mcp/server.py:56]
- [x] [Review][Patch] Unused global FastMCP instance [src/universal_memory/interfaces/mcp/server.py:32]
- [x] [Review][Patch] Secondary AttributeError risk in sanitization handler [src/universal_memory/interfaces/mcp/server.py:198]
- [x] [Review][Patch] Unix-centric regular expression in path sanitization [src/universal_memory/interfaces/mcp/server.py:199]
- [x] [Review][Patch] scope parameter type validation and json schema auto-docs [src/universal_memory/interfaces/mcp/server.py:143]
- [x] [Review][Patch] Path.cwd() exception risk in build_server [src/universal_memory/bootstrap/mcp.py:27]
- [x] [Review][Defer] Tool calls catch-all wrapper prevents JSON-RPC standard error signaling [src/universal_memory/interfaces/mcp/server.py:58] — deferred, pre-existing
- [x] [Review][Defer] Static project root binding prevents dynamic multi-project directory switching [src/universal_memory/bootstrap/mcp.py:26] — deferred, pre-existing

## Dev Notes

- **Reuse, Don't Reinvent**: Do not recreate status reading logic or facts/rules grouping! All business behavior resides in `GetMemoryStatusUseCase` and `AssembleContextSummaryUseCase`. The FastMCP adapter must be an extremely thin shell (~thin adapter~).
- **Synchronous Use Cases & FastMCP Threading**: According to the architecture, local I/O Use Cases are synchronous. FastMCP automatically manages the execution of synchronous functions in its internal thread pool, ensuring asynchronous compatibility with the JSON-RPC protocol without you needing to make the use cases asynchronous.
- **Strict Separation of Concerns**:
  - `interfaces/mcp/server.py` contains the decorators and route initialization.
  - `bootstrap/mcp.py` instantiates the real repositories and injects them into the use cases, which are then injected into the server routes.

### Project Structure Notes

Strictly follow the modular Clean Arch layout:
- The logic for exposing the MCP protocol resides under `src/universal_memory/interfaces/mcp/`.
- The actual server bootstrapper resides under `src/universal_memory/bootstrap/mcp.py`.

### References

- [epics.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/epics.md#L702-L726) - Original specification for Story 4.2.
- [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md#L133-L162) - Definition of Status and Context semantic fields.
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L392-L397) - Recommended MCP adapter file structure.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-28T11:50:25-03:00: Initial RED with `uv run pytest tests/interfaces/mcp/test_server.py` failed due to absence of `universal_memory.interfaces.mcp`.
- 2026-05-28T11:50:25-03:00: Focused GREEN with `uv run pytest tests/interfaces/mcp/test_server.py` passed with 5 tests.
- 2026-05-28T11:50:25-03:00: Regression and quality validated with `uv run pytest` (201 passed), `uv run ruff check .` and `uv run pyright`.

### Completion Notes List

- Implemented thin MCP adapter in `src/universal_memory/interfaces/mcp/server.py`, with `FastMCP("universal-memory")`, explicit injection via `MCPUseCases`, and declarative tools `status` and `context`.
- Implemented MCP bootstrap in `src/universal_memory/bootstrap/mcp.py`, reusing the same local dependencies from the CLI composition for `GetMemoryStatusUseCase` and `AssembleContextSummaryUseCase`.
- Added entry script `umem-mcp` in `pyproject.toml`; `python -m universal_memory.bootstrap.mcp` also starts the server.
- Added basic error handling for the MCP adapter with semantic codes and details sanitization to prevent leakage of secrets and absolute paths.
- Added parity/integration coverage in `tests/interfaces/mcp/test_server.py` for offline startup, `status` and `context` payloads, error sanitization, and real bootstrap.

### File List

- `_bmad-output/implementation-artifacts/4-2-implementar-servidor-mcp-base-com-fastmcp.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `pyproject.toml`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/mcp/__init__.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/interfaces/mcp/test_server.py`

### Change Log

- 2026-05-28T11:50:25-03:00: Implemented base MCP server with FastMCP, local bootstrap, `status`/`context` tools, error sanitization, and parity/offline tests.
