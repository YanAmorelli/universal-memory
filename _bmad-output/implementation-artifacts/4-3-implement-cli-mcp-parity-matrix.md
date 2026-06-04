# Story 4.3: Implement CLI/MCP Parity Matrix

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a product maintainer,
I want to ensure that capabilities exposed in one interface exist in the other,
so that humans and agents have consistent access to the same behavior.

## Acceptance Criteria

1. **Parity Matrix and Public Use Cases**:
   - **Given** the parity matrix defined in the architecture,
   - **When** a public capability is implemented,
   - **Then** equivalent CLI and MCP entry points must exist for the following capabilities:
     - `init` (CLI: `umem init`, MCP: `initialize_project`)
     - `status` (CLI: `umem status`, MCP: `status`)
     - `context` (CLI: `umem context`, MCP: `context`)
     - `remember` (CLI: `umem remember`, MCP: `remember_fact`)
     - `list facts` (CLI: `umem facts list`, MCP: `list_facts`)
     - `purge fact` (CLI: `umem facts purge`, MCP: `purge_fact`)
     - `facts hygiene` (CLI: `umem facts hygiene` - *optional/mcp if applicable*)
     - `list audit events` (CLI: `umem audit list`, MCP: `list_audit_events`)
     - `list snapshots` (CLI: `umem snapshots list`, MCP: `list_snapshots`)
     - `rollback scope` (CLI: `umem rollback`, MCP: `rollback_scope`)
     - `host setup/check` (CLI: `umem host setup/check`, MCP: `check_host` - *backlog*)
     - `skill proposal/list` (CLI: `umem skills propose/list`, MCP: `propose_skill`, `list_skills` - *backlog*)
   - **And** all internal domain exceptions must be caught and handled in an equivalent and secure manner across both interfaces.

2. **Automated Parity Test Suite**:
   - **Given** the parity test suite under `tests/interfaces/test_parity.py`,
   - **When** the suite runs,
   - **Then** it must dynamically inspect (or via strict contract assertion) both interfaces and fail if a public use case is exposed only in CLI or only in MCP without an explicit justification documented in the test code (preventing drift).
   - **And** it must validate that both the CLI and MCP adapters for the same capability return semantically equivalent data structures (identical JSON keys under the `data` envelope for the same use case).
   - **And** it must validate strict adherence to payload contracts defined in `_bmad-output/planning-artifacts/devex-interaction-spec.md`.

3. **Governance of New Capabilities**:
   - **Given** the design of new future capabilities (e.g., Epic 5 and Epic 6),
   - **When** a new public capability is introduced,
   - **Then** the implementation checklist must require coverage in both interfaces (CLI and MCP).
   - **And** the shared response contract must be updated in the specification before final delivery.

## Tasks / Subtasks

- [x] **Task 1: Implement and Inject Missing Use Cases into Adapters** (AC: 1)
  - [x] Map and import the use cases already implemented in the domain that are missing in CLI or MCP:
    - CLI requires: `AssembleContextSummaryUseCase` (`context` command) and `RememberFactUseCase` (`remember` command).
    - MCP requires: `SetupProjectUseCase` (`initialize_project`), `RememberFactUseCase` (`remember_fact`), `ListFactsUseCase` (`list_facts`), `PurgeFactUseCase` (`purge_fact`), `ListAuditLogUseCase` (`list_audit_events`), `ListSnapshotsUseCase` (`list_snapshots`), and `RollbackUseCase` (`rollback_scope`).
  - [x] Update the CLI bootstrap (`src/universal_memory/bootstrap/cli.py`) to inject `AssembleContextSummaryUseCase` and `RememberFactUseCase` into the CLI.
  - [x] Update the `MCPUseCases` class in `src/universal_memory/interfaces/mcp/server.py` to receive the new use cases.
  - [x] Update the MCP bootstrap (`src/universal_memory/bootstrap/mcp.py`) to instantiate and pass all necessary new use cases to `configure_server`.

- [x] **Task 2: Develop Missing CLI Commands (`context` and `remember`)** (AC: 1)
  - [x] Create the CLI command `umem context` in `init_command.py` supporting `--scope` (project/global), `--max-size-chars`, and human/json format. It must return the canonical JSON payload or concise Rich formatting in accordance with `devex-interaction-spec.md`.
  - [x] Create the CLI command `umem remember` in `init_command.py` to record a fact. It must support the `--scope` (project/global), `--tag` (multiple tags), and `--format` (human/json) flags. It must trigger the secure atomic write pipeline (with secret scan and audit/snapshot).
  - [x] Ensure humanized Rich formatting and pure JSON output envelopes strictly aligned with `devex-interaction-spec.md`.

- [x] **Task 3: Develop Missing MCP Tools** (AC: 1)
  - [x] In `src/universal_memory/interfaces/mcp/server.py`, register the tools using FastMCP decorators:
    - `@server.tool(name="initialize_project")`
    - `@server.tool(name="remember_fact")`
    - `@server.tool(name="list_facts")`
    - `@server.tool(name="purge_fact")`
    - `@server.tool(name="list_audit_events")`
    - `@server.tool(name="list_snapshots")`
    - `@server.tool(name="rollback_scope")`
  - [x] Ensure absolute reuse of the same application Use Cases injected into the MCP server.
  - [x] Certify that all payloads returned by the new MCP tools follow the key formats described in `devex-interaction-spec.md`.

- [x] **Task 4: Handle Backlog Capabilities (Rules, Hosts, and Skills)** (AC: 1, 2)
  - [x] For the capabilities of Epic 5 (hosts), Epic 6 (skills), and `propose_rule` that are in the matrix but do not have real business use cases:
    - Add explicit backlog mapping/justification in the authorized exclusion list of the parity test (e.g., `PARITY_EXCLUSIONS = ["propose_rule", "check_host", "propose_skill", "list_skills"]` with clear comments referencing that they will be implemented in their respective future Epics).
    - This ensures that the parity suite passes in green without requiring premature writing of fake business code.

- [x] **Task 5: Implement Parity and Contract Test Suite** (AC: 2)
  - [x] Create the test file `tests/interfaces/test_parity.py`.
  - [x] Implement a test that dynamically loads the Typer CLI application (`create_typer_app`) and the MCP server (`create_mcp_server`), listing all CLI commands and active MCP tools.
  - [x] Validate that, except for items explicitly authorized in the exclusion list, each functionality exposed in the CLI has direct MCP equivalence under the Parity Matrix (preventing drift).
  - [x] Write scheme parity tests, mocking the use case responses and injecting the same dummy data structures into the CLI and MCP. Assert that the output JSON payloads of both interfaces have exactly the same keys under the `data` envelope.
  - [x] Validate that all new MCP tools handle and map domain exceptions properly to the correct JSON-RPC codes defined in `architecture.md#L738-L751`.

## Dev Notes

### Key Architecture and Error Guardrails
- **Thin Adapters**: CLI and MCP are pure delivery layers. No database access code, file writing, secret scanning, or domain rules should be implemented directly within them. They only translate arguments, invoke the use case, and wrap the result.
- **Error Handling and Sanitization**: Every error in the new MCP tools must go through `_error_envelope` and return the correct JSON-RPC codes. Details must be sanitized by `_sanitize_error_detail` to prevent leaking absolute paths or tokens/secrets.
- **Response Semantics**: The envelope returned in the MCP tools and the CLI JSON format must be strictly identical. Pay attention to the correspondence of success keys (`ok`, `operation`, `scope`, `data`, `warnings`) and error keys (`code`, `message`, `detail`).

### Components to Change in the Source Tree
- `src/universal_memory/interfaces/cli/init_command.py` -> Add `context` and `remember` commands.
- `src/universal_memory/interfaces/mcp/server.py` -> Add MCP decorators and payloads for the new tools.
- `src/universal_memory/bootstrap/cli.py` -> Inject new memory use cases into the CLI constructor.
- `src/universal_memory/bootstrap/mcp.py` -> Instantiate and inject new use cases into the MCP use case class.
- `tests/interfaces/test_parity.py` -> Create the strict parity test suite.

### References
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L695-L712) - Original CLI to MCP Parity Matrix definition.
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L738-L751) - JSON-RPC and CLI error mapping table.
- [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md#L226-L244) - Parity Contract and Integration Test Requirements.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest tests/interfaces/test_parity.py` initially failed, confirming the absence of `context_command`, `remember_command`, and new fields in `MCPUseCases`.
- `uv run pytest tests/interfaces/test_parity.py tests/interfaces/mcp/test_server.py tests/interfaces/cli` passed after implementing CLI/MCP adapters and parity contracts.
- `uv run ruff check .` passed.
- `uv run pyright` passed with 0 errors.
- `uv run pytest` passed with 211 tests.

### Completion Notes List

- Injected `AssembleContextSummaryUseCase` and `RememberFactUseCase` into the CLI bootstrap, preserving thin adapters and secure write pipeline.
- Expanded MCP composition for initialization, memory, auditing, snapshots, and rollback using the same application use cases.
- Added CLI commands `context` and `remember` with human/json output aligned with `devex-interaction-spec.md`.
- Registered missing MCP tools: `initialize_project`, `remember_fact`, `list_facts`, `purge_fact`, `list_audit_events`, `list_snapshots`, and `rollback_scope`.
- Created parity suite with explicit exclusions for backlog capabilities (`propose_rule`, `check_host`, `propose_skill`, `list_skills`) and validation of equivalent `data` keys.
- MCP now returns numeric JSON-RPC codes for domain errors and maintains sanitization of absolute paths/secrets.

### File List

- `_bmad-output/implementation-artifacts/4-3-implementar-matriz-de-paridade-cli-mcp.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/interfaces/mcp/test_server.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-05-28: Implemented CLI/MCP parity for existing public capabilities, added automated contracts, and moved the story to review.

### Review Findings

#### Decision Needed
- [x] [Review][Decision] Missing Confirmation Prompt/Mechanisms for Destructive MCP Mutations — The DevEx spec dictates that confirmations are strictly required before purging facts and rolling back snapshots. While the CLI does this interactively, the MCP server executes them instantly without any confirmation checkpoints or arguments. We need to decide if we should require a confirmation boolean parameter in the MCP tool call, or if we accept instant execution for agents in MCP.
- [x] [Review][Decision] Option Drift on `context` Command (`agent_session_key`) — The MCP `context` tool accepts `agent_session_key`, but the CLI `context` command does not, creating an option drift between interfaces. Should we add `--agent-session-key` to the CLI command?

#### Action Items (Patches)
- [x] [Review][Patch] Python Runtime TypeError Crash Risk on Non-Empty Logs in MCP `_entry_dict` [src/universal_memory/interfaces/mcp/server.py:375]
- [x] [Review][Patch] Inconsistent Scope Parameter Parsing and Lack of Typo/Case Handling in MCP Tools [src/universal_memory/interfaces/mcp/server.py:395]
- [x] [Review][Patch] Global Configured Project Root Ignored in MCP Path Calculations [src/universal_memory/interfaces/mcp/server.py:379]
- [x] [Review][Patch] Swallowed Stack Traces in MCP Tool Exception Handlers [src/universal_memory/interfaces/mcp/server.py:103]
- [x] [Review][Patch] Duplicated Fallback Constant for Max Context Size [src/universal_memory/interfaces/cli/init_command.py:206]
- [x] [Review][Patch] Inconsistent ISO 8601 Datetime Serialization [src/universal_memory/interfaces/mcp/server.py:314]
- [x] [Review][Patch] Direct Port Instantiation Bypassing Dependency Injection [src/universal_memory/bootstrap/mcp.py:116]
- [x] [Review][Patch] Duplicate Exception Handling Boilerplate in CLI Command Runners [src/universal_memory/interfaces/cli/init_command.py:299]
- [x] [Review][Patch] Unhandled `ValueError` in CLI `_run_remember` [src/universal_memory/interfaces/cli/init_command.py:336]
- [x] [Review][Patch] Generic JSON-RPC Error Mapping for standard ValueError or OSError in MCP [src/universal_memory/interfaces/mcp/server.py:421]
- [x] [Review][Patch] MCP Error Envelope Missing Standard Keys `recovery_hint` and `audit_reference` [src/universal_memory/interfaces/mcp/server.py:407]

#### Deferred Items (Pre-existing)
- [x] [Review][Defer] Localization Bleed (Portuguese in CLI Option Help vs English Codebase) [src/universal_memory/interfaces/cli/init_command.py:195] — deferred, pre-existing
- [x] [Review][Defer] Crude and Hardcoded Token Count Estimation [src/universal_memory/interfaces/cli/init_command.py:1008] — deferred, pre-existing
- [x] [Review][Defer] Hardcoded `"not-implemented-yet"` Placeholders in Production Contracts [src/universal_memory/interfaces/cli/init_command.py:64] — deferred, pre-existing
