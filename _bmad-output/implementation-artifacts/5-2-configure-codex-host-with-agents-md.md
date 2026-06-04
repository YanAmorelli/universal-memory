# Story 5.2: Configure Codex Host with AGENTS.md

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user using Codex in a project,
I want to configure `AGENTS.md` as a compact shared manifest,
so that the agent reads operational rules and pointers to memory without loading excessive knowledge.

## Acceptance Criteria

1. **Given** a project initialized with `.umem/`
   **When** the user executes setup/check of the `codex` host
   **Then** the system detects or proposes the `AGENTS.md` file in the root of the project;
   **And** classifies each proposed instruction as `shared_policy` (stable operational rules), `provider_delta` (host-specific), `scoped_rule` (local rules), or `canonical_doc` (project docs);
   **And** rules of type `canonical_doc` must be saved in the `docs/` folder and only referenced in `AGENTS.md` in a compact way (pointers).

2. **Given** an existing `AGENTS.md` containing content edited manually by the user outside the self-managed blocks,
   **When** the system needs to update it to inject new rules or update the memory bootstrap,
   **Then** the engine preserves the unmanaged manual sections using clear HTML comment delimiters:
     - `<!-- UMEM: START -->` and `<!-- UMEM: END -->` (or structured equivalents);
   **And** any write mutation on the file strictly passes through the safe write pipeline (`SafeWriteUseCase`), generating snapshot, audit, and rollback.

3. **Given** the `AGENTS.md` manifest generated or updated by the setup/check of the `codex` host,
   **When** the host validation is executed,
   **Then** the validator ensures that the `AGENTS.md` file remains below the compact size limit (e.g. configurable maximum recommended size in bytes or lines);
   **And** ensures that it does not become a massive project knowledge dump (rejects raw dumps of facts/memories, requiring long facts to remain in `docs/` or be retrieved dynamically via MCP);
   **And** returns the appropriate validation status with timestamp and audit.

4. **Given** the execution of the CLI or MCP for setup/check of the `codex` host,
   **When** invoked via terminal or MCP tool,
   **Then** the CLI accepts the interactive confirmation flag `--yes` / `-y`;
   **And** displays the detailed change plan, the relative file path, the planned snapshot, and the audit event type before application;
   **And** in `--format json` format, strictly returns the formatted payload:
     ```json
     {
       "ok": true,
       "operation": "host_setup",
       "scope": "project",
       "data": {
         "host_id": "codex",
         "instruction_targets": ["agents_md"],
         "planned_changes": [
           {
             "target": "agents_md",
             "action": "create",
             "path": "AGENTS.md"
           }
         ],
         "manual_steps": [],
         "validation_status": "success",
         "audit_reference": "uuid-v4-reference"
       },
       "warnings": []
     }
     ```

## Tasks / Subtasks

- [x] **Task 1: Implement the Domain Service/Port for Instruction Classification and Partitioning** (AC: 1, 3)
  - [x] Implement the logic that classifies blocks of rules into `shared_policy`, `provider_delta`, `scoped_rule`, or `canonical_doc`.
  - [x] Ensure that long content (`canonical_doc`) is separated for writing to the `docs/` folder and referenced in the main manifest using relative pointers/links (e.g., `[README.md](file:///docs/readme.md)`).
  - [x] Validate that the final resulting manifest in `AGENTS.md` remains strictly compact (configurable limit, e.g., maximum of 100 lines or 4000 characters in the self-managed block).

- [x] **Task 2: Implement Host Setup & Check Use Case** (AC: 1, 2, 3)
  - [x] Create the `ConfigureHostUseCase` (or `SetupHostUseCase`) use case in `src/universal_memory/application/host/setup_host_use_case.py`.
  - [x] Integrate the existing `SafeWriteUseCase` for all mutations on the `AGENTS.md` file.
  - [x] Implement manual section preservation logic in `AGENTS.md` if the file already exists:
    - Look for structured delimiters: `<!-- UMEM: START -->` and `<!-- UMEM: END -->`.
    - Preserve intact any data/comments added by the user before and after these markers.
    - If the markers do not exist, append them cleanly to the end of the file or initialize a new `AGENTS.md`.
  - [x] Implement verification/validation associated with the `codex` host (ensure manifest presence, integrity of the memory bootstrap instruction, validation of the MCP endpoint, and compact size).

- [x] **Task 3: Integrate CLI for the `umem host setup` and `umem host check` Commands** (AC: 4)
  - [x] Create or update the corresponding CLI commands in the `src/universal_memory/interfaces/cli/host_command.py` file or directly in `init_command.py`.
  - [x] Expose common options: `--yes` / `-y` (to bypass confirmation in setup) and `--format json`/`human`.
  - [x] Display the detailed plan in a rich format (Rich Panels/Tables) before the write mutation in the terminal.
  - [x] Format the JSON output exactly according to the standard success/error envelope of the DevEx specification.

- [x] **Task 4: Expose the Equivalent MCP Tools** (AC: 4)
  - [x] Register the MCP tools in `src/universal_memory/bootstrap/mcp.py` / `src/universal_memory/interfaces/mcp/`:
    - `host_setup(host_id: str, force: bool = False)`
    - `host_check(host_id: str)`
  - [x] Map MCP method calls identically to the central Use Case, maintaining compliance and the same JSON field structure as the CLI.

- [x] **Task 5: Complete Suite of Unit and Integration Tests** (AC: 1, 2, 3, 4)
  - [x] Create unit tests for the manual block preservation parser (`test_manual_block_preservation.py`).
  - [x] Create integration tests for `ConfigureHostUseCase` simulating setup in new and brownfield repositories.
  - [x] Write compliance tests for the CLI command (`umem host setup` and `umem host check`) validating the human-rich and JSON return format.
  - [x] Validate static typing with `uv run pyright` and code style with `uv run ruff check`.
  - [x] Ensure 100% coverage in critical rollback and snapshot scenarios resulting from host mutations.

### Review Findings

- [x] [Review][Decision] Proposed instructions and blocks are not injectable/passed via CLI or MCP — The CLI and MCP call the setup/check use case without passing any `instruction_blocks`, resulting in an empty list and preventing the classification flow of real rules in normal usage.
- [x] [Review][Decision] Non-existence of parameterization for compact limits in CLI and MCP — Compact limits (`max_managed_lines` and `max_managed_chars`) are not exposed as parameters in the CLI or MCP tools, preventing users from configuring these limits as required by AC 3.
- [x] [Review][Patch] Silent substitution of snapshot/audit references and lack of transactionality in the write loop [src/universal_memory/application/host/setup_host_use_case.py:179-202]
- [x] [Review][Patch] Path Traversal vulnerability on Windows and lack of preemptive validation in the plan [src/universal_memory/application/host/setup_host_use_case.py:365]
- [x] [Review][Patch] Collision of path/slug of canonical documents with identical or similar titles [src/universal_memory/application/host/setup_host_use_case.py:143]
- [x] [Review][Patch] Pointer paths do not use the `file:///` protocol prefix [src/universal_memory/application/host/setup_host_use_case.py:121]
- [x] [Review][Patch] Removal of graphical accentuation in proposed text in the UMEM block [src/universal_memory/application/host/setup_host_use_case.py:263-286]
- [x] [Review][Patch] Incomplete UMEM delimiters bar execution and block auto-correction [src/universal_memory/application/host/setup_host_use_case.py:307]
- [x] [Review][Patch] Incompatibility with Windows line endings (CRLF) [src/universal_memory/application/host/setup_host_use_case.py:298]
- [x] [Review][Patch] Broken Markdown formatting in multiline blocks [src/universal_memory/application/host/setup_host_use_case.py:276]
- [x] [Review][Patch] Obstructive validation of existing content [src/universal_memory/application/host/setup_host_use_case.py:148]
- [x] [Review][Patch] Presence of UMEM delimiters in the blocks content [src/universal_memory/application/host/setup_host_use_case.py:323]
- [x] [Review][Patch] Dependency on `datetime.now(UTC)` in old Python versions [src/universal_memory/application/host/setup_host_use_case.py:222]
- [x] [Review][Patch] False positives with memory dump terms [src/universal_memory/application/host/setup_host_use_case.py:319]
- [x] [Review][Patch] Absence of Symlink checks pointing outside the project [src/universal_memory/application/host/setup_host_use_case.py:256]
- [x] [Review][Patch] Omission of `snapshot_reference` and `timestamp` in the return Payload [src/universal_memory/application/host/setup_host_use_case.py:91]

## Dev Notes

- **Mandatory Reuse of Existing Components:**
  - **DO NOT** attempt to write files using `Path.write_text` directly. You **MUST** use the `SafeWriteUseCase` imported from `universal_memory.application.security` to apply mutations to `AGENTS.md`. It ensures secret validation (entropy scanning), UUID generation for snapshots, and atomic writing with native audit log in the repository.
  - Use the domain entity models (`Host`, `HostName`, `InstructionTarget`, and `InstructionTargetType`) created in Story 5.1 to validate the invariants of the `codex` host.

- **Format of the Self-Managed Section in AGENTS.md:**
  - The mandatory memory bootstrap in `AGENTS.md` must contain a clear pointer urging the reading agent to query the universal-memory MCP server or local routines. Example bootstrap instruction:
    ```markdown
    <!-- UMEM: START -->
    # Universal Memory Active Policy
    > [!IMPORTANT]
    > Before starting any coding task, consult the Short Term Memory of this repository by executing the CLI `umem context` or using the corresponding MCP tools.
    
    ## Consolidated Operational Rules:
    - [Active rules from memory injected here in a compact format]
    
    ## Canonical Pointers:
    - Additional guidelines in [docs/PROJECT_GUIDES.md](file:///docs/PROJECT_GUIDES.md)
    <!-- UMEM: END -->
    ```

- **Error Mapping and Security:**
  - If a secret is detected in the `AGENTS.md` manifest during the setup process, the system must raise a `SecretDetectedError` and abort the operation, ensuring that no secrets are written to the public manifest.

### Project Structure Notes

- The application use case must be allocated in:
  - `src/universal_memory/application/host/setup_host_use_case.py` (New)
- The CLI logic and Typer extensions must go in:
  - `src/universal_memory/interfaces/cli/host_command.py` (New)
  - And registered in the console bootstrap file `src/universal_memory/bootstrap/cli.py`.
- The MCP adapter and tool registration must be extended in:
  - `src/universal_memory/bootstrap/mcp.py`
- The automated tests for the Story must be inserted in:
  - `tests/application/test_setup_host.py`
  - `tests/interfaces/test_host_cli.py`

### References

- **Host Domain Entities (Story 5.1)**: [instruction_target.py](file:///src/universal_memory/domain/entities/instruction_target.py) and [host.py](file:///src/universal_memory/domain/entities/host.py)
- **DevEx Interaction Specification**: [devex-interaction-spec.md](file:///_bmad-output/planning-artifacts/devex-interaction-spec.md#L197-L209)
- **Architecture Instruction Strategy**: [architecture.md](file:///_bmad-output/planning-artifacts/architecture.md#L753-L827)
- **PRD Automations (FR8, FR15)**: [prd.md](file:///_bmad-output/planning-artifacts/prd.md#L322-L339)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-28: `uv run pytest tests/application/test_setup_host.py tests/interfaces/cli/test_host_command.py`
- 2026-05-28: `uv run pytest tests/interfaces/mcp/test_server.py tests/application/test_setup_host.py tests/interfaces/cli/test_host_command.py`
- 2026-05-28: `uv run ruff check`
- 2026-05-28: `uv run pyright`
- 2026-05-28: `uv run pytest`

### Completion Notes List

- Implemented `ConfigureHostUseCase` for the `codex` host, including partitioning of instructions, generation/preservation of the self-managed `UMEM` block, relative pointers to canonical documents in `docs/`, validation of compactness, and blocking of raw memory dumps.
- All mutations of `AGENTS.md` and canonical documents pass through `SafeWriteUseCase`, generating snapshot/audit log and respecting the secret scanner.
- Integrated `umem host setup` and `umem host check` commands with `--yes`/`-y`, human output with plan, and JSON output matching the DevEx contract.
- Exposed MCP tools `host_setup` and `host_check` with the same use case and payload contract as the CLI.
- Completed validations: `uv run ruff check`, `uv run pyright`, `uv run pytest` (`264 passed`).

### File List

- `src/universal_memory/application/host/__init__.py`
- `src/universal_memory/application/host/setup_host_use_case.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/test_setup_host.py`
- `tests/application/test_manual_block_preservation.py`
- `tests/interfaces/cli/test_host_command.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_server.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-2-configurar-host-codex-com-agents-md.md`

### Change Log

- 2026-05-28: Implemented configuration/check of the Codex host with AGENTS.md, CLI, MCP, validations, and automated tests.
