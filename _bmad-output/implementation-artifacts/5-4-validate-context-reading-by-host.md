# Story 5.4: Validate Host Context Reading

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user integrating a new agent into my workflow,
I want to verify and validate that the host (agent) can successfully read the universal memory context,
so that I am absolutely sure that the operational identity and project guidelines have been ported correctly.

## Acceptance Criteria

1. **Configuration and Reading Instructions Validation**:
   - **Given** a configured host (for example, `claude_code` or `codex`),
   - **When** the reading `check` command is executed (via CLI `umem host check` or MCP tool `host_check`),
   - **Then** the system must perform a real validation to ensure that:
     - The corresponding instruction file exists (e.g., `CLAUDE.md` for `claude_code`, `AGENTS.md` for `codex`).
     - The file contains the mandatory UMEM delimiter blocks (`<!-- UMEM: START -->` and `<!-- UMEM: END -->`).
     - The managed block contains the guidelines that instruct the agent to use the MCP (e.g., calls to `umem context` or usage of the memory MCP server).
     - The corresponding MCP configuration method is documented or active.
   - **And** the validation must record and return the appropriate status: `"success"`, `"failure"`, or `"manual_pending"`.

2. **Validation Audit Logging**:
   - **Given** the result of a host reading check,
   - **When** the check finishes,
   - **Then** the system must record a corresponding audit event in the audit repository (`.umem/audit/events.jsonl`) with the appropriate fields:
     - `action`: `host_validation.{host_id}` (e.g., `host_validation.claude_code` or `host_validation.codex`)
     - `result`: the validation status (`success`, `failure`, `manual_pending`)
     - `details`: detailed information about the checks that passed or failed (e.g., file existence, presence of UMEM blocks, etc.)
     - `scope`: `AuditEventScope.project`
     - `origin`: `"cli"` or `"mcp"` depending on the interface used.

3. **Validation Status in the Global Memory Status**:
   - **Given** a previously recorded successful or failed validation,
   - **When** the user queries the global memory status (via CLI `umem status` or MCP tool `status`),
   - **Then** the returned `host_validation` field must no longer be static/hardcoded.
   - **And** it must dynamically load the latest validation result for each supported host (`claude_code` and `codex`) from the audit events repository.
   - **And** each entry in `host_validation` must contain:
     - `status`: the status of the latest validation (`success`, `failure`, or `unconfigured` if never validated).
     - `timestamp`: the ISO 8601 UTC timestamp of the latest validation.
     - `method`: the validation strategy used (e.g., `claude_md_delta_validator` or `agents_md_compact_validator`).
     - `audit_reference`: the UUID v4 of the audit event that recorded the validation.

4. **Error Handling and Actionable Messages**:
   - **Given** a validation failure during the host check,
   - **When** the error is reported by the CLI or MCP,
   - **Then** the returned message or payload must explicitly classify the type of failure that occurred:
     - Instruction File Failure (e.g., missing file or file without UMEM blocks).
     - MCP Configuration Failure (e.g., invalid MCP instructions or missing tool references).
     - Read or Write Permission Failure.
   - **And** the system must **never** attempt to automatically fix the file or apply changes without the user's explicit confirmation when there is a risk of overwriting manual content.

5. **CLI and MCP Parity with Strict DevEx Payloads**:
   - **Given** the CLI and MCP interfaces for `host check`,
   - **When** the MCP tool `host_check` or the corresponding CLI command is triggered with `--format json`,
   - **Then** the generated JSON must faithfully follow the project's DevEx interaction contract, containing all required fields:
     ```json
     {
       "ok": true,
       "operation": "host_check",
       "scope": "project",
       "data": {
         "host_id": "claude_code",
         "instruction_targets": ["claude_md"],
         "planned_changes": [],
         "manual_steps": [],
         "validation_status": "success",
         "audit_reference": "uuid-v4-audit-ref",
         "snapshot_reference": "planned",
         "timestamp": "2026-05-29T00:00:00Z"
       },
       "warnings": []
     }
     ```

## Tasks / Subtasks

- [x] **Task 1: Develop Host Reading Validators (Validators)** (AC: 1, 4)
  - [x] Implement the validation logic for `claude_md_delta_validator` and `agents_md_compact_validator` in the application or host infrastructure layer.
  - [x] Validate the presence of the instruction file (`CLAUDE.md` / `AGENTS.md`) under the root directory of the project.
  - [x] Validate that the delimiters `<!-- UMEM: START -->` and `<!-- UMEM: END -->` are present and have non-null content.
  - [x] Verify the presence of MCP references (`universal-memory`, `umem context`, or tool tags).
  - [x] Return the structured validation status and a detailed error message describing the gap.

- [x] **Task 2: Integrate the Validation Pipeline into `ConfigureHostUseCase`** (AC: 1, 2)
  - [x] Update the `execute` method of `ConfigureHostUseCase` to run the real validation when executed in check mode (`apply=False`).
  - [x] Integrate the recording of the `AuditEvent` in `events.jsonl` containing the actual details of the validation status and returning the `audit_reference`.
  - [x] Ensure that in case of `apply=False`, the snapshot is marked as `"planned"` or `"none"` since no instruction file mutation is performed.

- [x] **Task 3: Update the `GetMemoryStatusUseCase` Use Case to Load Real Evidence** (AC: 3)
  - [x] Inject the `AuditLogRepository` into the constructor of `GetMemoryStatusUseCase`.
  - [x] Update the logic of the `execute` method of the status use case to list all audit events and filter the latest validations by host (`host_validation.claude_code` and `host_validation.codex`).
  - [x] Map the payload of the `host_validation` dictionary to return the keys: `status`, `timestamp`, `method`, and `audit_reference` based on the last audit event found (or `unconfigured` if empty).
  - [x] Ensure backward compatibility and fault tolerance when reading the audit log.

- [x] **Task 4: Update the CLI and MCP Adapters to Map and Display Results** (AC: 4, 5)
  - [x] Update `_run_host_check` in `src/universal_memory/interfaces/cli/init_command.py` to render the actual validation results (including colors and friendly Rich alerts for `success`, `failure`, and `manual_pending`).
  - [x] Adapt the MCP tool `host_check` in `src/universal_memory/interfaces/mcp/server.py` to return the JSON envelope identical to that required by the DevEx specification.
  - [x] Configure appropriate domain error mapping in case the validation throws typed infrastructure or configuration exceptions.

- [x] **Task 5: Implement TDD Automated Test Suite** (AC: 1, 2, 3, 4, 5)
  - [x] Add unit tests for the new host reading validators in `tests/application/test_setup_host.py` or a new dedicated file.
  - [x] Add integration tests for the host check flow (with missing file, valid file, and corrupted delimiters) verifying correct registration in the audit.
  - [x] Add tests for the status use case, populating the in-memory audit repository and ensuring the status returns the actual evidence successfully.
  - [x] Execute static checks with `uv run pyright` and formatting with `uv run ruff check`.

### Review Findings

- [x] [Review][Defer] Missing implementation of "manual_pending" validation status — deferred: Simplify the MVP with 100% automated and binary validations, postponing manual onboarding treatments. [src/universal_memory/application/host/setup_host_use_case.py:188-194]
- [x] [Review][Patch] Dry-run behavior bypassed during host configure use case [src/universal_memory/application/host/setup_host_use_case.py:63-76]
- [x] [Review][Patch] Weak and overly broad MCP reference checking (checking for "tool") [src/universal_memory/application/host/setup_host_use_case.py:234-244]
- [x] [Review][Patch] Conflation of validation failures and warnings in CLI [src/universal_memory/application/host/setup_host_use_case.py:188-194]
- [x] [Review][Patch] Portuguese accents omitted in error classification prefixes [src/universal_memory/application/host/setup_host_use_case.py:105]
- [x] [Review][Patch] Missing import of HostName in setup_host_use_case.py [src/universal_memory/application/host/setup_host_use_case.py:169]
- [x] [Review][Patch] Missing json import in tests/application/test_setup_host.py [tests/application/test_setup_host.py:763]
- [x] [Review][Patch] Missing uuid4 import in application and test files [src/universal_memory/application/host/setup_host_use_case.py:204]
- [x] [Review][Patch] Potential path resolution error in relative path check [src/universal_memory/application/host/setup_host_use_case.py:101-105]
- [x] [Review][Patch] Shallow copy mutation risk in memory status use case [src/universal_memory/application/memory/get_memory_status_use_case.py:327]
- [x] [Review][Patch] Fragile timezone normalization and datetime comparison [src/universal_memory/application/memory/get_memory_status_use_case.py:339]
- [x] [Review][Patch] Over-broad exception swallow in memory status use case [src/universal_memory/application/memory/get_memory_status_use_case.py:324]
- [x] [Review][Patch] Successful configuration path crashes due to incomplete dataclass instantiation [src/universal_memory/application/host/setup_host_use_case.py:180]
- [x] [Review][Patch] Unhandled UnicodeDecodeError on target file reading [src/universal_memory/application/host/setup_host_use_case.py:118-124]
- [x] [Review][Patch] Unhandled AttributeError when event details is a non-dictionary JSON [src/universal_memory/application/memory/get_memory_status_use_case.py:371-375]
- [x] [Review][Patch] Unhandled exception in drift warnings reader [src/universal_memory/application/host/setup_host_use_case.py:170]
- [x] [Review][Patch] Unhandled storage exception when writing validation audit event [src/universal_memory/application/host/setup_host_use_case.py:224]
- [x] [Review][Defer] In-memory O(N) linear scan scalability bottleneck in audit log listing [src/universal_memory/application/memory/get_memory_status_use_case.py:323-349] — deferred, pre-existing

## Dev Notes

- **Mutation Safety**: The `umem host check` command operates in read-only mode (`apply=False`) and, consequently, is free of side effects on the project's instruction files. However, it performs writes to the audit repository to persist the validation evidence. This is considered an allowed and desirable side effect under the security policy, as it does not change the host's behavior or active preferences.
- **MCP Identification in Instructions**: For the reading validation to be successful (`"success"`), the content within the UMEM block must include keywords confirming the MCP integration, such as `"universal-memory"`, `"mcp"`, `"fastmcp"`, or equivalent CLI commands for context retrieval (`"umem context"` or `"umem status"`).
- **JSON-RPC Error Consistency**: If the MCP validation encounters errors in the underlying transport or permissions infrastructure that cause the usecase execution to fail, use the domain error mapping to map to the strict JSON-RPC codes of DevEx (e.g., `StorageError` maps to `-32060`).

### Project Structure Notes

- The new reading validation logic should integrate cleanly into the application layer, preferably inside `src/universal_memory/application/host/setup_host_use_case.py`.
- The updated status usecase will remain under `src/universal_memory/application/memory/get_memory_status_use_case.py`.

### References

- **PRD Requirements**: FR7 (Provider/host selection), FR8 (Automatic instruction configuration), NFR10 (Host Compatibility - MVP needs to validate reading on 2 hosts). [Source: _bmad-output/planning-artifacts/prd.md]
- **DevEx Contract**: Specific formatting details for CLI Rich envelopes and JSON payloads for `umem host check` and `umem status`. [Source: _bmad-output/planning-artifacts/devex-interaction-spec.md#umem-host-setupcheck]
- **Architecture Mapping**: Host support matrix (`codex` and `claude_code`) and single-write ownership (`AGENTS.md` vs `CLAUDE.md`). [Source: _bmad-output/planning-artifacts/architecture.md#host-support-matrix]

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash

### Implementation Plan

- Implement `host check` as a read-only path separate from the setup preview, preserving zero mutation in instruction files and recording only audit events.
- Keep validators close to `ConfigureHostUseCase`, using the existing host metadata (`read_validation_method`) for `claude_code` and `codex`.
- Make `GetMemoryStatusUseCase` consume `AuditLogRepository` in an optional and fault-tolerant way, returning `unconfigured` when there is no reliable evidence.
- Preserve existing CLI/MCP envelopes and update only the internal `host_validation` payload and human rendering.

### Debug Log References

- `uv run pytest tests/application/test_setup_host.py tests/application/memory/test_get_memory_status_use_case.py` - 18 passed
- `uv run pytest` - 280 passed
- `uv run ruff check` - All checks passed
- `uv run pyright` - 0 errors, 0 warnings, 0 informations

### Completion Notes List

- Implemented real reading validation path for `codex`/`AGENTS.md` and `claude_code`/`CLAUDE.md`, with checks for existence, reading, UMEM delimiters, non-empty content, compact manifest, and MCP/UMEM references.
- `ConfigureHostUseCase` now records `host_validation.{host_id}` event in audit for `apply=False`, including JSON `details` with method, checks, and failures, and returns `planned_changes: []` with `snapshot_reference: "planned"`.
- `GetMemoryStatusUseCase` started loading the latest validation event per host from the audit log, with a tolerant fallback to `unconfigured`.
- CLI renders `host check` with a status-colored Rich panel, and `umem status` displays method and audit reference; MCP preserves the DevEx envelope with the updated payload.
- Tests added/updated for host validation, audit, dynamic status, and CLI/MCP contracts.

### File List

- `src/universal_memory/application/host/setup_host_use_case.py`
- `src/universal_memory/application/memory/get_memory_status_use_case.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/test_setup_host.py`
- `tests/application/memory/test_get_memory_status_use_case.py`
- `tests/interfaces/cli/test_status_command.py`
- `tests/interfaces/mcp/test_server.py`
- `_bmad-output/implementation-artifacts/5-4-validar-leitura-de-contexto-por-host.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-05-29T01:07:33Z: Implemented real host reading validation with auditing, dynamic status based on audit log, updated CLI/MCP adapters, and complete tests.
