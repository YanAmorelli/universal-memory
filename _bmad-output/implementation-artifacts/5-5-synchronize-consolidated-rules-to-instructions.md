# Story 5.5: Sync Consolidated Rules to Instructions

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user who approves new behavior rules,
I want to sync consolidated rules to supported instruction files,
So that different agents operate with consistent guidelines.

## Acceptance Criteria

1. **Given** an approved rule for promotion
   **When** instruction synchronization runs
   **Then** the system decides if the rule belongs to `shared_policy`, `provider_delta`, `scoped_rule`, or `canonical_doc`
   **And** updates only the corresponding targets

2. **Given** multiple configured hosts
   **When** a shared rule is synchronized
   **Then** `AGENTS.md` is written only once per mutation cycle
   **And** hosts that consume `AGENTS.md` do not produce divergent copies

3. **Given** a rule pointing to detailed content
   **When** it is synchronized
   **Then** the instruction file includes a compact pointer to the canonical source
   **And** the long-form content remains in docs or memory, as classified

## Tasks / Subtasks

- [x] **Task 1: Implement the `SyncInstructionsUseCase` in Domain and Application (AC: 1, 2, 3)**
  - [x] Create the command and result classes `SyncInstructionsCommand` and `SyncInstructionsResult` in `src/universal_memory/application/host/sync_instructions_use_case.py`.
  - [x] Implement the `SyncInstructionsUseCase` class in `src/universal_memory/application/host/sync_instructions_use_case.py`.
  - [x] Have the use case load active rules from `RuleRepository` and group/classify them according to their categories (`shared_policy`, `provider_delta`, `scoped_rule`, `canonical_doc`).
  - [x] Orchestrate the joint execution of safe writes such that `AGENTS.md` is generated and updated only once per synchronization cycle (even if multiple hosts consume it).
  - [x] Handle the conversion of rules classified as `canonical_doc` so that their long-form content is written to a file in the `docs/` folder and only a canonical link is included in the instruction manifests (`AGENTS.md`).
  - [x] Properly log audit events and manage snapshots and coordinated rollbacks in the safe write pipeline for multiple files in case of failure.

- [x] **Task 2: Add the corresponding CLI command `umem host sync` (AC: 1, 2)**
  - [x] In the file `src/universal_memory/interfaces/cli/init_command.py`, add the `@host_app.command("sync")` command.
  - [x] Configure parameters for `--apply` / `--no-apply` (for dry-run/preview) and `--format json` / `--format human`.
  - [x] Ensure full compliance with `devex-interaction-spec.md` by displaying the operation scope, affected paths, planned snapshots, audit references, and friendly confirmation prompts (with Yes, Always, and No options where appropriate).
  - [x] Return the standardized JSON envelope when the corresponding flag is used.

- [x] **Task 3: Expose the synchronization functionality as an MCP tool (AC: 1)**
  - [x] Register the `sync_instructions` tool in the MCP server bootstrap in `src/universal_memory/bootstrap/mcp.py`.
  - [x] Properly map input parameters and format returns in compliance with the JSON-RPC protocol.

- [x] **Task 4: Create comprehensive tests for the sync flow (AC: 1, 2, 3)**
  - [x] Write unit tests in `tests/application/host/test_sync_instructions.py` validating rule routing behavior, the single write of `AGENTS.md`, and the replacement of canonical documents with pointers.
  - [x] Write integration tests for the CLI command in `tests/interfaces/cli/test_host_sync.py`.

### Review Findings

- [x] [Review][Decision] Empty Repository Dependency in Production — In bootstrap files (cli.py and mcp.py), the SyncInstructionsUseCase is instantiated with EmptyRuleRepository(), rendering synchronization inoperable in production. Should we plug in a real repository or keep it this way temporarily?
- [x] [Review][Decision] Extreme Coupling with Private Methods — The SyncInstructionsUseCase class directly accesses multiple private methods (starting with '_') of ConfigureHostUseCase (such as _drift_content, _host_for, etc.). Should we refactor to expose clean public methods or proceed with the current private access?
- [x] [Review][Patch] Crash due to AttributeError when rule.metadata is null [src/universal_memory/application/host/sync_instructions_use_case.py:405-408]
- [x] [Review][Patch] Absence of coordinated rollbacks in case of write failure [src/universal_memory/application/host/sync_instructions_use_case.py:330-363]
- [x] [Review][Patch] host_ids filter ignored forcing Codex sync [src/universal_memory/application/host/sync_instructions_use_case.py:372-383]
- [x] [Review][Patch] Path Traversal vulnerability in rule paths [src/universal_memory/application/host/sync_instructions_use_case.py:405-430]
- [x] [Review][Patch] Omission of warnings in the JSON payload of SyncInstructionsResult [src/universal_memory/application/host/sync_instructions_use_case.py:100-115]
- [x] [Review][Patch] Misleading message in the CLI Dry-Run and lack of a rich table [src/universal_memory/interfaces/cli/init_command.py:673-724]
- [x] [Review][Patch] Absence of Scope in the CLI preview table [src/universal_memory/interfaces/cli/init_command.py:762-781]
- [x] [Review][Patch] Lack of integration tests for human UX and CLI interactivity [tests/interfaces/cli/test_host_sync.py:1-82]
- [x] [Review][Patch] Contaminated references with concatenated not-applied/planned values [src/universal_memory/application/host/sync_instructions_use_case.py:330-363]
- [x] [Review][Patch] Hijacking of host_ids parameter when passed empty [src/universal_memory/application/host/sync_instructions_use_case.py:120-130]
- [x] [Review][Patch] Omission of conflicting actions on duplicate physical paths [src/universal_memory/application/host/sync_instructions_use_case.py:250-260]

## Dev Notes

- **Leveraging Existing Resources:** `ConfigureHostUseCase` in `setup_host_use_case.py` already has advanced logic for partitioning instructions (`partition_instruction_blocks`), preserving content outside the UMEM block (`_merge_managed_block`), handling canonical documents (`_render_canonical_document`), and validating drift for Claude Code. The new usecase `SyncInstructionsUseCase` must integrate and leverage these methods instead of duplicating them.
- **RuleRepository:** Currently, `bootstrap/cli.py` and `bootstrap/mcp.py` inject an `EmptyRuleRepository`. To test and implement the real flow, ensure the correct repository can provide the registered rules, or provide a local fake implementation in the tests.
- **Single Write:** When planning changes for multiple hosts (such as `codex` and `claude_code`), both may reference the `docs/` folder or require the validation of `AGENTS.md`. Ensure that the physical mutation of `AGENTS.md` occurs in a single logical transaction of safe writing with a single snapshot and corresponding audit event.

### Project Structure Notes

- The code must follow the established DDD / Clean Architecture pattern, placing the use case in `application/host/sync_instructions_use_case.py` and registering the dependencies in `bootstrap/cli.py` and `bootstrap/mcp.py`.

### References

- [Architecture Guidelines: Host Support Matrix](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#Host%20Support%20Matrix)
- [Architecture Guidelines: Rules and Manifest Strategy](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#Rules%20and%20Manifest%20Strategy)
- [Acceptance Criteria: Epic 5 Story 5.5](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/epics.md#Story%205.5)
- [DevEx CLI & Mutation Specifications](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- `uv run pytest tests/application/host/test_sync_instructions.py tests/interfaces/cli/test_host_command.py tests/interfaces/mcp/test_server.py`
- `uv run ruff check src tests`
- `uv run pytest`

### Completion Notes List

- Implemented `SyncInstructionsUseCase` with its own command/result, reading of active rules from the `RuleRepository`, classification by metadata, and reuse of existing host rendering/validation.
- Joint synchronization writes `AGENTS.md` only once per cycle, preserves `CLAUDE.md` deltas, moves `canonical_doc` to `docs/`, and keeps only compact pointers in the manifest.
- Added `umem host sync` with preview, `--apply/--no-apply`, standardized JSON, and confirmation for mutations in human/JSON apply mode with `--yes`.
- Exposed MCP tool `sync_instructions` and updated the MCP compliance contract.
- Validation completed with clean `ruff` and complete suite: `287 passed`.

### File List

- `src/universal_memory/application/host/sync_instructions_use_case.py`
- `src/universal_memory/application/host/__init__.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/host/test_sync_instructions.py`
- `tests/interfaces/cli/test_host_sync.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_server.py`
- `_bmad-output/implementation-artifacts/5-5-sincronizar-regras-consolidadas-para-instru-es.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-05-29: Implemented instruction synchronization for approved rules, CLI `host sync`, MCP tool `sync_instructions`, test/compliance coverage, and Code Review fixes.
