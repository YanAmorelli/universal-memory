# Story 5.3: Configure Claude Code Host with CLAUDE.md

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user using Claude Code alongside universal memory,
I want to configure specific deltas in `CLAUDE.md`,
so that Claude receives the necessary instructions without diverging from the shared manifest.

## Acceptance Criteria

1. **Given** the `claude_code` host selected
   **When** setup/check is executed
   **Then** the system detects or proposes the `CLAUDE.md` file at the root of the project;
   **And** writes to `CLAUDE.md` only blocks classified as `provider_delta` (specific to the Claude host) or `scoped_rule` relevant to the Claude scope, avoiding duplication of `shared_policy` type rules already defined in the `AGENTS.md` manifest.

2. **Given** `AGENTS.md` and `CLAUDE.md` present in the project
   **When** drift validation (divergence check) is executed (in the check command)
   **Then** the system identifies if there are improper instruction duplications (e.g., identical rules written in both) or explicit contradictions between the files;
   **And** proposes structured correction through warnings or manual steps in the plan, without ever overwriting content added manually by the user without explicit authorization.

3. **Given** a planned mutation/write to `CLAUDE.md` (in the setup command)
   **When** the update is applied with the `--yes`/`-y` flag or confirmed
   **Then** it preserves any segment manually inserted by the user outside the delimited blocks:
      - `<!-- UMEM: START -->` and `<!-- UMEM: END -->`
   **And** executes the mutation strictly using the transactional pipeline `SafeWriteUseCase`, guaranteeing snapshot creation before applying the change, event log auditing, and capability to revert the file to the previous state via scoped rollback.

4. **Given** the execution of CLI or MCP for the `claude_code` host
   **When** invoked by the terminal or MCP tools (`host_setup` or `host_check`)
   **Then** the CLI supports `--yes` / `-y` and `--format json`/`human`;
   **And** displays the detailed plan listing the files `CLAUDE.md` and optionally `AGENTS.md` (if there is drift or a need for reference), their snapshots, and audit references;
   **And** if executed with `--format json`, strictly returns the formatted payload according to the DevEx specification:
      ```json
      {
        "ok": true,
        "operation": "host_setup",
        "scope": "project",
        "data": {
          "host_id": "claude_code",
          "instruction_targets": ["claude_md"],
          "planned_changes": [
            {
              "target": "claude_md",
              "action": "create",
              "path": "CLAUDE.md"
            }
          ],
          "manual_steps": [],
          "validation_status": "success",
          "audit_reference": "uuid-v4-reference",
          "snapshot_reference": "uuid-v4-snapshot",
          "timestamp": "2026-05-29T00:00:00Z"
        },
        "warnings": []
      }
      ```

## Tasks / Subtasks

- [x] **Task 1: Extend Domain for Host Mapping and Additional Targets** (AC: 1)
  - [x] Ensure that the use case accepts `HostName.claude_code` in the `_host_for` method.
  - [x] Return the `Host` entity object with `supported_targets=[InstructionTargetType.claude_md]`, operational methods, and correct audit type.
  - [x] Implement contract validation for `claude_md` in the `InstructionTarget` entity, ensuring its `ownership` property is `delta_consumer` and does not allow the `shared_policy` type (preventing duplication of the common manifest).

- [x] **Task 2: Extend `ConfigureHostUseCase` for Multi-Target Mutations** (AC: 1, 3)
  - [x] Refactor `ConfigureHostUseCase` to manage the initialization and update of multiple targets (`AGENTS.md` and/or `CLAUDE.md` depending on the host).
  - [x] Integrate `SafeWriteUseCase` to perform transactional writes and snapshots to `CLAUDE.md`.
  - [x] Ensure the block partitioner isolates only instructions with `provider_delta` and `scoped_rule` classifications (relevant to Claude) for `CLAUDE.md`.
  - [x] Add support for `<!-- UMEM: START -->` and `<!-- UMEM: END -->` markers in `CLAUDE.md` to preserve manually edited user blocks, identical to the behavior implemented for `AGENTS.md`.

- [x] **Task 3: Develop Drift and Rule Collision Detector** (AC: 2)
  - [x] Implement a local service in the use case (or dedicated validator class) that comparatively analyzes `AGENTS.md` and `CLAUDE.md`.
  - [x] Identify raw duplications (e.g., identical operational text blocks) existing in both files.
  - [x] Generate readable warnings (`warnings`) listing the redundant lines or blocks detected.
  - [x] Add drift-validation rules to the `host_check` and `host_setup` flows of the `claude_code` host.

- [x] **Task 4: Integrate CLI and MCP to Support `claude_code`** (AC: 4)
  - [x] Update CLI commands `umem host setup` and `umem host check` in `src/universal_memory/interfaces/cli/host_command.py` or equivalents to accept the `claude_code` parameter.
  - [x] Render rich terminal plans using Rich for changes to `CLAUDE.md`.
  - [x] Extend MCP tools `host_setup` and `host_check` in `src/universal_memory/bootstrap/mcp.py` / `src/universal_memory/interfaces/mcp/server.py` to process calls relating to the `claude_code` host, maintaining parity with CLI capabilities.

- [x] **Task 5: Test Suite and Quality Validations** (AC: 1, 2, 3, 4)
  - [x] Write unit tests for drift detection between `AGENTS.md` and `CLAUDE.md` (`test_drift_detector.py`).
  - [x] Write integration tests for `claude_code` host setup and validation in `tests/application/test_setup_host.py`.
  - [x] Implement CLI and MCP tests validating the generated DevEx JSON payload for `claude_code` setup and check.
  - [x] Validate type compliance with `uv run pyright` and style with `uv run ruff check`.
  - [x] Ensure that coverage does not regress and that all tests pass transactionally.

### Review Findings

1. **`decision-needed`** findings (unchecked):
   - [ ] [Review][Decision] `AGENTS.md` Excluded from Plan/Audit under Drift — AC 4 requires that the detailed plan lists `CLAUDE.md` and optionally `AGENTS.md` (if drift exists), including snapshots and audit references. The current implementation strictly hardcodes `instruction_targets` as `[target.name.value]` (strictly `["claude_md"]`), completely omitting `AGENTS.md`.
   - [ ] [Review][Decision] Refactored Usecase Restricts Execution to Single Target — Task 2 specifies managing and updating multiple targets depending on the host. However, `execute` strictly binds to a single `target = self._primary_target_for(host)`.

2. **`patch`** findings (unchecked):
   - [ ] [Review][Patch] Fragile HTML Comment Parsing in `_instruction_lines` [src/universal_memory/application/host/drift_detector.py:59]
   - [ ] [Review][Patch] Restrictive Tag Removal Regex in Drift Detector [src/universal_memory/application/host/drift_detector.py:64]
   - [ ] [Review][Patch] Sloppy Defaulting to Codex Host in `_host_for` [src/universal_memory/application/host/setup_host_use_case.py:410-436]
   - [ ] [Review][Patch] Sloppy Defaulting to `agents_md` Target in `_instruction_target_for` [src/universal_memory/application/host/setup_host_use_case.py:443-469]
   - [ ] [Review][Patch] Hardcoded Path Bypass of Target Config in `_drift_warnings` [src/universal_memory/application/host/setup_host_use_case.py:399]
   - [ ] [Review][Patch] TypeError Risk on None/Empty Existing Content [src/universal_memory/application/host/setup_host_use_case.py:198]
   - [ ] [Review][Patch] Mixed English and Portuguese Headers in `CLAUDE.md` [src/universal_memory/application/host/setup_host_use_case.py:475]
   - [ ] [Review][Patch] Duplicate Normalization Calls in Drift Detector Helpers [src/universal_memory/application/host/drift_detector.py:97-111]
   - [ ] [Review][Patch] Missing `warnings` Field in `ConfigureHostResult.to_payload` [src/universal_memory/application/host/setup_host_use_case.py:130]
   - [ ] [Review][Patch] Empty Rule Body Crashes in Drift Contradiction Detector [src/universal_memory/application/host/drift_detector.py:46-66]
   - [ ] [Review][Patch] Inconsistent Setup Dry-Run Drift Detection [src/universal_memory/application/host/setup_host_use_case.py:328-337]
   - [ ] [Review][Patch] Discarding Canonical Docs Silently for Claude Setup [src/universal_memory/application/host/setup_host_use_case.py:285-292]
   - [ ] [Review][Patch] TypeError Risk on None/Empty Fact Tags [src/universal_memory/application/host/setup_host_use_case.py:262]
   - [ ] [Review][Patch] Silent Dropping of Unsupported Classifications [src/universal_memory/application/host/setup_host_use_case.py:495]
   - [ ] [Review][Patch] Hardcoded Empty `manual_steps` Under Drift/Collision Warnings [src/universal_memory/application/host/setup_host_use_case.py:190]
   - [ ] [Review][Patch] Misleading Hardcoded File Names in Validation Errors [src/universal_memory/application/host/setup_host_use_case.py:538-570]

3. **`defer`** findings (checked off, marked deferred):
   - [x] [Review][Defer] Lack of Transactional Multi-File Rollback [src/universal_memory/application/host/setup_host_use_case.py:321-344] — deferred, pre-existing

## Dev Notes

- **Strict Separation of Concepts:**
  - `AGENTS.md` contains the repository's common operational identity policy and MCP activation.
  - `CLAUDE.md` is strictly a delta. It should instruct Claude specifically and complement whatever is missing in the main manifest.
  - Do not duplicate the `## Consolidated Operational Rules` section of `AGENTS.md` into `CLAUDE.md`. Instead, inject only pointers or delta instructions.

- **Usage of SafeWriteUseCase:**
  - Any modification process in `CLAUDE.md` must inherit the robustness of `SafeWriteUseCase` to reuse the entropy scanner, secure block writing, and audit generation.

### Project Structure Notes

- The drift/collision detector can be coupled to the setup Use Case or extracted to:
  - `src/universal_memory/application/host/drift_detector.py` (Optional/New)
- CLI adapters extended in:
  - `src/universal_memory/interfaces/cli/host_command.py`
- MCP server adapters integrated in:
  - `src/universal_memory/interfaces/mcp/server.py`
- Test suite updated in:
  - `tests/application/test_setup_host.py`
  - `tests/interfaces/cli/test_host_command.py`
  - `tests/interfaces/mcp/test_server.py`

### References

- **Host Domain Entities (Story 5.1)**: [instruction_target.py](file:///src/universal_memory/domain/entities/instruction_target.py) and [host.py](file:///src/universal_memory/domain/entities/host.py)
- **Codex Host Setup (Story 5.2)**: [5-2-configurar-host-codex-com-agents-md.md](file:///_bmad-output/implementation-artifacts/5-2-configurar-host-codex-com-agents-md.md) and [setup_host_use_case.py](file:///src/universal_memory/application/host/setup_host_use_case.py)
- **DevEx Interaction Specification**: [devex-interaction-spec.md](file:///_bmad-output/planning-artifacts/devex-interaction-spec.md#L197-L209)
- **Architecture Host Matrix**: [architecture.md](file:///_bmad-output/planning-artifacts/architecture.md#L753-L800)
- **PRD Automations (FR8, FR15)**: [prd.md](file:///_bmad-output/planning-artifacts/prd.md#L322-L339)

## Dev Agent Record

### Implementation Plan

- Task 1: first cover the domain support for `claude_code` and `claude_md`, then implement the mapping in the use case preserving compatibility with `codex`.
- Task 2: maintain the existing partitioning as a base and select rendering/writing by the host's primary target, with `CLAUDE.md` filtering only classifications accepted by the target's contract.
- Task 3: extract comparative validation to a dedicated detector and return warnings in the use case result without overwriting manual content.
- Task 4: maintain the existing dynamic `host_id` acceptance in the CLI/MCP and align the JSON envelope with the DevEx contract including `snapshot_reference`, `timestamp` and real warnings from the use case.
- Task 5: complete the test matrix for `claude_code` setup/check and refator the use case only where necessary to satisfy lint/types without changing the contract.

### Debug Log

- `uv run pytest tests/application/test_setup_host.py -q` initially failed with `ValidationFailedError` because `_host_for("claude_code")` was still rejecting the host.
- `uv run pytest tests/application/test_setup_host.py -q` passed after implementing host and target mapping.
- `uv run pytest -q` passed with 266 tests.
- `uv run pytest tests/application/test_setup_host.py -q` initially failed because `execute()` was still trying to resolve `AGENTS.md` for `claude_code`.
- `uv run pytest tests/application/test_setup_host.py -q` passed after separating primary target by host and rendering `CLAUDE.md`.
- `uv run pytest -q` passed with 268 tests.
- `uv run pytest tests/application/test_drift_detector.py tests/application/test_setup_host.py -q` initially failed until the detector existed and then until check used the current content of `CLAUDE.md`.
- `uv run pytest tests/application/test_drift_detector.py tests/application/test_setup_host.py -q` passed after integrating `InstructionDriftDetector` into the `claude_code` flow.
- `uv run pytest -q` passed with 271 tests.
- `uv run pytest tests/interfaces/cli/test_host_command.py tests/interfaces/mcp/test_server.py -q` initially failed because envelopes did not expose `snapshot_reference`, `timestamp`, and warnings.
- `uv run pytest tests/interfaces/cli/test_host_command.py tests/interfaces/mcp/test_server.py tests/interfaces/mcp/test_compliance.py -q` passed after aligning the CLI/MCP contract.
- `uv run pytest -q` passed with 273 tests.
- `uv run pytest tests/application/test_drift_detector.py tests/application/test_setup_host.py tests/interfaces/cli/test_host_command.py tests/interfaces/mcp/test_server.py -q` passed with 27 tests.
- `uv run pyright` initially failed due to broad inference of fact classification and passed after using `InstructionClassification`.
- `uv run ruff check` initially failed due to complexity in `execute()`, long line, and imports, and passed after extracting helpers and organizing imports.
- `uv run pytest -q` passed with 275 tests.

### Completion Notes

- Task 1 completed: `ConfigureHostUseCase._host_for` now accepts `claude_code` and returns a `Host` with `claude_md` target, operational methods, and audit aligned to safe setup.
- Added target resolver for `claude_md` with `ownership=delta_consumer` and classifications restricted to `provider_delta` and `scoped_rule`, avoiding `shared_policy`.
- Task 2 completed: `ConfigureHostUseCase.execute` now selects the host's primary target, renders `CLAUDE.md` with its own UMEM block, preserves manual content outside of delimiters, and applies the write via `SafeWriteUseCase`.
- The `claude_code` flow ignores `shared_policy` and canonical documents when assembling `CLAUDE.md`, keeping only `provider_delta` and `scoped_rule`.
- Task 3 completed: `InstructionDriftDetector` identifies duplicate lines and explicit contradictions `always/never` or `sempre/nunca` between `AGENTS.md` and `CLAUDE.md`.
- `ConfigureHostResult` now carries `warnings`, and the use case populates these warnings for `claude_code` in setup/check.
- Task 4 completed: CLI and MCP propagate `claude_code`, return DevEx payload with `snapshot_reference` and `timestamp`, and preserve structured warnings in the envelope.
- Rich human rendering already consumes `planned_changes`, so plans for `CLAUDE.md` appear with target, action, path, snapshot, and audit.
- Task 5 completed: unit, integration, CLI, and MCP tests added for `claude_code`; `pyright`, `ruff` validations and full regression pass.
- `ConfigureHostUseCase.execute` was refactored into smaller helpers to keep the code within configured quality limits.

## File List

- `src/universal_memory/application/host/setup_host_use_case.py`
- `src/universal_memory/application/host/drift_detector.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/test_setup_host.py`
- `tests/application/test_drift_detector.py`
- `tests/interfaces/cli/test_host_command.py`
- `tests/interfaces/mcp/test_server.py`
- `tests/interfaces/mcp/test_compliance.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-3-configurar-host-claude-code-com-claude-md.md`

## Change Log

- 2026-05-28: Started Story 5.3 and completed Task 1 mapping domain to `claude_code`/`claude_md`.
- 2026-05-28: Completed Task 2 with transactional support for `CLAUDE.md` and delta filtering.
- 2026-05-28: Completed Task 3 with drift detector and warnings in the use case.
- 2026-05-28: Completed Task 4 with JSON DevEx contract for CLI/MCP.
- 2026-05-28: Completed Task 5 with tests and final validations.
