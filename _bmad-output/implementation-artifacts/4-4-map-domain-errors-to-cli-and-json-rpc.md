# Story 4.4: Map Domain Errors to CLI and JSON-RPC

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user or client agent consuming the interface,
I want to receive consistent and actionable errors,
so that I can understand failures without depending on internal system details.

## Acceptance Criteria

1. **Domain Exception Handling in the CLI**:
   - **Given** that a known domain exception occurs (`SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, `StorageError`),
   - **When** it is caught by the CLI adapter (`init_command.py`),
   - **Then** the CLI must render a clear message using Rich components (`Panel`, `Text`), presenting a user-friendly summary, safe details, and a recovery hint.
   - **And** the CLI must not print a stack trace by default for these expected business errors.
   - **And** the CLI must terminate execution with a non-zero exit status code (e.g., `1`).
   - **And** if the output format is `--format json`, it must return strictly the JSON error envelope specified in `devex-interaction-spec.md`.

2. **Domain Exception Mapping in MCP**:
   - **Given** that a known domain exception occurs,
   - **When** it is caught by the MCP adapter (`server.py`),
   - **Then** it must be mapped to an appropriate JSON-RPC code:
     - `SecretDetectedError` -> `-32010`
     - `SnapshotFailedError` -> `-32020`
     - `ValidationFailedError` -> `-32602` (JSON-RPC standard for Invalid Params)
     - `FactNotFoundError` -> `-32040`
     - `InvalidConfigError` -> `-32050`
     - `StorageError` -> `-32060`
   - **And** the response must include `data.detail` sanitized securely against secrets or local filesystem absolute paths.
   - **And** it must include `data.recovery_hint` to guide safe corrective actions.

3. **Secure Handling of Unexpected Errors**:
   - **Given** that an unexpected and unclassified error occurs (any generic subclass of `Exception` that is not a domain error),
   - **When** it occurs in any adapter (CLI or MCP),
   - **Then** the system must return a generic safe error (e.g., `"Unexpected error."` in the CLI or code `-32603` in MCP).
   - **And** the complete stack trace and raw details must be logged only to appropriate diagnostic channels (such as stderr or internal audit log) to protect against secret leakage in the main output delivered to the user or agent.

## Tasks / Subtasks

- [x] **Task 1: Unify and Centralize Error Detail Sanitization** (AC: 1, 2, 3)
  - [x] Ensure that sanitization logic for absolute paths (Unix and Windows) and strings resembling API keys and secrets (e.g., `sk-`, `pk-`) is executed centrally and consistently for both adapters (CLI and MCP).
  - [x] Make sure that the `SecretDetectedError` error never echoes the secret or parts of the secret in the terminal output or the error response payload.
  - [x] Develop or refine error formatting/redaction helpers in the domain or interfaces.

- [x] **Task 2: Refine Error Logic in the CLI Adapter** (AC: 1, 3)
  - [x] Map exception catches (`except`) in the CLI execution helpers (`_run_remember`, `_run_facts_list`, `_run_context`, `_run_rollback`, etc.) to ensure that all known domain exceptions are passed cleanly to `_print_expected_error`.
  - [x] Ensure that for unexpected errors (`except Exception`), the CLI prints an appropriate stack trace if debug or verbose mode is enabled, but by default returns a clean panel informing of an "Unexpected error" with status code `1`.
  - [x] Ensure that CLI error JSON payloads follow exactly the canonical structure:
    ```json
    {
      "ok": false,
      "error": {
        "code": "validation_failed",
        "message": "Configuration is invalid.",
        "detail": "Missing project memory path.",
        "recovery_hint": "Run umem init from the project root.",
        "audit_reference": null
      }
    }
    ```

- [x] **Task 3: Refine Error Signaling Logic in the MCP Server** (AC: 2, 3)
  - [x] Resolve the architecture/deferred-work feedback from Epic 4-2: The MCP tool intercepts all domain exceptions and returns `{"ok": False, "error": ...}` inside a FastMCP success envelope. This prevents the JSON-RPC client host from detecting the actual failure of the tool.
  - [x] Adjust MCP tool endpoints in `server.py` to raise appropriate exceptions (like `ValidationError` or wrap the exception in an exception that FastMCP interprets as a tool execution failure with the correct JSON-RPC code and message) if necessary, OR ensure explicit compliance with the expected error handling behavior of the MCP protocol.
  - [x] Validate that all MCP tools (`initialize_project`, `status`, `context`, `remember_fact`, `list_facts`, `purge_fact`, `list_audit_events`, `list_snapshots`, `rollback_scope`) implement and respect error mapping and sanitization.

- [x] **Task 4: Implement Error and Robustness Test Suite** (AC: 1, 2, 3)
  - [x] Create tests under `tests/interfaces/test_errors.py` or expand `tests/interfaces/test_parity.py` to inject use cases with mocked failures.
  - [x] Test the CLI under `human` and `json` outputs for each of the known domain exceptions. Assert exit code `1` and the Rich and JSON structure respectively.
  - [x] Test MCP for each exception, ensuring the JSON-RPC code (`-32010`, `-32020`, `-32602`, `-32040`, `-32050`, `-32060`) is correct and that mocked paths and secrets are properly masked in `detail`.
  - [x] Test unexpected error scenarios (e.g., raising a generic `RuntimeError`), asserting that raw stack traces are omitted from friendly output and that diagnostic logs contain the data for maintenance.

### Review Findings

- [x] [Review][Patch] Exposure of native generic exceptions (ValueError/OSError) as expected domain errors [src/universal_memory/interfaces/errors.py]
- [x] [Review][Patch] Fragility and potential secrets leakage in recovery_hint extraction via "Hint:" [src/universal_memory/interfaces/errors.py:129-134]
- [x] [Review][Patch] Inconsistent format (Human instead of JSON) for uncaught exceptions in CLI global main [src/universal_memory/interfaces/cli/init_command.py:125-135]
- [x] [Review][Patch] Crash (TypeError) if UniversalMemoryError has a message attribute equal to None [src/universal_memory/interfaces/errors.py:142-146]
- [x] [Review][Patch] Omission of return typing -> dict[str, Any] in MCP tools [src/universal_memory/interfaces/mcp/server.py]
- [x] [Review][Defer] Redundant import and polluted namespace in server.py [src/universal_memory/interfaces/mcp/server.py:44-50] — deferred, pre-existing
- [x] [Review][Defer] Simplistic regular expressions in sanitization of absolute paths and keys [src/universal_memory/interfaces/errors.py] — deferred, pre-existing
- [x] [Review][Defer] Hardcoded internationalization (locale) logic in error payloads [src/universal_memory/interfaces/errors.py:157-165] — deferred, pre-existing
- [x] [Review][Defer] Direct access to environment variables (os.environ) in CLI adapters [src/universal_memory/interfaces/cli/init_command.py:1282] — deferred, pre-existing
- [x] [Review][Defer] DRY violation in repeating OSError exception catch logic in CLI [src/universal_memory/interfaces/cli/init_command.py] — deferred, pre-existing

## Dev Notes


### Architectural Guidelines and Cleanup
- **Thin Adapters and Reuse**: CLI and MCP only adapt inputs and outputs. The logic of which error to raise and the essential details reside in the Use Case or Domain Repository. The interfaces only perform translation and sanitization.
- **Sanitization of Local Paths**: Crucial for privacy and DevEx. Absolute paths like `/Users/amorelliaoyan/projects/...` must be transformed into `<path>` or paths relative to the project to avoid exposing the local user's directory structure.
- **MCP Protocol and FastMCP Error Handling**: In FastMCP, if a tool raises an exception, it is caught by the server and converted into a JSON-RPC error. We must ensure that raised exceptions are converted with the corresponding customized codes (`-32010`, etc.) according to the specification, or that the returned payload correctly signals failure if FastMCP requires the tool to raise a specific error exception.

### Components to Modify in the Source Tree
- `src/universal_memory/interfaces/cli/init_command.py` -> Review capture and display in `_print_expected_error`, ensuring that the entire CLI suite catches exceptions in a homogeneous manner.
- `src/universal_memory/interfaces/mcp/server.py` -> Adjust tool wrappers for JSON-RPC error handling and compliance with hosts.
- `tests/interfaces/test_parity.py` (or `tests/interfaces/test_errors.py`) -> Test error path coverage and sanitization.

### References
- [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md#L93-L113) - Domain Error Mapping Table and Canonical Error Envelope.
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L738-L751) - Technical mapping of JSON-RPC codes to exceptions.
- [deferred-work.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/implementation-artifacts/deferred-work.md#L28-L32) - MCP Tool Calls Catch-all feedback.

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Implementation Plan
- Centralize error descriptors, codes, hints, and sanitization in a shared interface helper.
- Make the CLI consume the helper for expected errors and return a generic unexpected error by default.
- Make the MCP consume the same helper, preserve JSON-RPC codes, and mark failures as tool results with `isError=true`.
- Cover domain, CLI, and MCP with tests for envelopes, phrasing, and unexpected failures.

### Debug Log References
- 2026-05-28: `uv run pytest tests/interfaces/test_errors.py tests/interfaces/test_parity.py tests/interfaces/mcp/test_server.py` -> 29 passed.
- 2026-05-28: `uv run pytest` -> 225 passed.
- 2026-05-28: `uv run ruff check .` -> All checks passed.
- 2026-05-28: `uv run pyright` -> 0 errors, 0 warnings, 0 informations.

### Completion Notes List
- Implemented shared error contract and sanitization helper in `src/universal_memory/interfaces/errors.py`.
- CLI now uses homogeneous catching of known domain exceptions, canonical JSON envelope, and Rich panel with sanitized detail.
- Unexpected errors in CLI return a generic message by default; stack trace is only emitted when `UMEM_DEBUG_ERRORS=1`.
- MCP now centralizes mapping to JSON-RPC codes, includes `data.detail` and `data.recovery_hint`, and returns tool results with `isError=true` for structured failures.
- Coverage added for domain exceptions, secret/absolute path masking, human/json CLI output, MCP errors, and unexpected scenarios.

### File List
- `src/universal_memory/interfaces/errors.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/interfaces/test_errors.py`
- `tests/interfaces/test_parity.py`
- `tests/interfaces/mcp/test_server.py`

### Change Log
- 2026-05-28: Implemented centralized CLI/MCP error mapping, shared sanitization, and robustness test suite.
