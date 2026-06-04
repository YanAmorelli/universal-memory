# Story 4.5: Validate MCP Compliance and Interface Contracts

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer of universal-memory,
I want a robust validation suite for the MCP server and interface contract tests,
so that future changes or refactoring do not break reading, writing, and error handling by external agents.

## Acceptance Criteria

1. **Local MCP Compliance Suite (Offline)**:
   - **Given** the MCP server with its configured public capabilities (`initialize_project`, `status`, `context`, `remember_fact`, `list_facts`, `purge_fact`, `list_audit_events`, `list_snapshots`, `rollback_scope`),
   - **When** the compliance test suite runs,
   - **Then** it must test all MCP tools in an integrated manner without depending on connections or an external network (offline-first).
   - **And** it must validate success envelopes and the handling of domain/unexpected exceptions mapped to structured JSON-RPC errors from MCP (`CallToolResult` with `isError=True` and populated `structuredContent`).

2. **CLI vs MCP Interface Contract Tests**:
   - **Given** the outputs of the CLI executed with the `--format json` flag and the structured outputs of the equivalent MCP tools,
   - **When** the contract tests compare both results for the same operation,
   - **Then** the essential structured fields of the payloads must be semantically equivalent and identical in format (as per `devex-interaction-spec.md`).
   - **And** differences in adapters must remain strictly restricted to the presentation layer (Rich UI in the CLI vs pure structured JSON in MCP).

3. **Actionability Guarantee on Validation Failure**:
   - **Given** an MCP compliance validation failure or a contract key mismatch between interfaces,
   - **When** the test fails,
   - **Then** the failure message must clearly point out which capability, contract key, or structured field is mismatched or missing.
   - **And** the compliance suite must act as a blocker in CI for new interface developments.

## Tasks / Subtasks

- [x] **Task 1: Develop the MCP Compliance Suite** (AC: 1, 3)
  - [x] Create or expand the integrated compliance test suite in `tests/interfaces/mcp/test_compliance.py` covering the full MCP protocol cycle for the exposed tools.
  - [x] Ensure validation of health checks, context reading and writing, proposals, and secure mutation cycles (including permissions or audit stubs and rollbacks).
  - [x] Block external network access during bootstrapping and tests of the MCP server to ensure local offline compliance.

- [x] **Task 2: Implement CLI vs MCP Contract Tests** (AC: 2, 3)
  - [x] Refine and extend the contract validator in `tests/interfaces/test_parity.py` to compare key and type equality of JSON-RPC payloads versus CLI `--format json`.
  - [x] Ensure that keys such as `initialized`, `project_path`, `fact_counts`, `audit_reference`, `snapshots`, `events`, etc., have the same canonical data structure across both interfaces.
  - [x] Create developer-friendly assertions that, when failing, print exactly which key or type is inconsistent between the two interfaces.

- [x] **Task 3: Validate Operational Parity and CI Guardrails** (AC: 1, 2)
  - [x] Ensure that intentional parity exclusions are documented and that new capabilities trigger alerts or contract errors.
  - [x] Validate that all tests pass successfully via `uv run pytest`.

### Review Findings

- [x] [Review][Dismiss] Dangerous cast on MCP tool error returns [src/universal_memory/interfaces/mcp/server.py:111-289] — dismissed, required by FastMCP runtime reflection behavior
- [x] [Review][Patch] Uncaught filesystem exceptions in _relative_path [src/universal_memory/interfaces/cli/init_command.py:1306-1313]
- [x] [Review][Patch] Inconsistent relative path roots and Path.cwd() dependency [src/universal_memory/interfaces/cli/init_command.py:981]

## Dev Notes

- **Adapters and Cleanliness**: The structured JSON outputs of the CLI and MCP must share the same design origins and domain data serializers. Application use cases should produce the same DTOs that map directly to JSON on both ends.
- **Offline-First Protocol**: The FastMCP server and its dependencies must not initialize listening sockets or request network ports unless requested. Tests should simulate tool calls directly through the `server.call_tool` exposed by FastMCP without instantiating a real network.
- **Exception Handling**: Exhaustively test if domain exceptions are intercepted by middleware or handled compliantly, returning the correct JSON-RPC codes defined in the error mapping.

### Project Structure Notes

- The MCP server resides in `src/universal_memory/interfaces/mcp/server.py`.
- The CLI adapter resides in `src/universal_memory/interfaces/cli/init_command.py`.
- The parity matrix and CLI/MCP interaction rules reside in `tests/interfaces/test_parity.py` and `tests/interfaces/test_errors.py`.
- Compliance must inherit existing patterns without reinventing data structures or business logic in the tests.

### References

- [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md) - Specification of envelopes, expected keys, and error envelopes.
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L847-L851) - Residual Gap Analysis of the MCP compliance suite.
- [test_parity.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/tests/interfaces/test_parity.py) - Parity matrix and stubs of CLI and MCP interfaces.

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- `uv run pytest tests/interfaces/mcp/test_compliance.py` - initial red adjusted for actual FastMCP envelope; then 4 passed.
- `uv run pytest tests/interfaces/test_parity.py` - absolute path red in `initialize_project.audit_path`; fixed in CLI serializer.
- `uv run ruff check` - import order and error constant fixed; final green.
- `uv run pyright` - type error in MCP returns handled with `cast` without changing FastMCP serialization; final green.
- `uv run pytest` - 230 passed.

### Completion Notes List

- Implemented offline MCP compliance suite covering full public inventory, success envelopes, domain errors, unexpected errors, and mandatory confirmation for destructive mutations.
- Expanded CLI vs MCP parity for `init`, recursive validation of keys, types, and scalar values, plus non-empty fixtures for `events` and `snapshots`.
- Fixed CLI `init` JSON output to emit relative project paths, aligned with the MCP contract and `devex-interaction-spec.md`.
- Adjusted MCP server internal annotations to satisfy Pyright without altering the runtime format expected by FastMCP.

### File List

- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-05-28: Added offline MCP compliance, recursive CLI vs MCP parity, and fixed relative paths in `init` JSON.
