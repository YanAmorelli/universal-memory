# Story 6.6: Expose Skill Management via CLI and MCP

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user or consuming agent,
I want to propose, list, and manage skills (including activation, deactivation, and secure updates) through unified CLI and MCP interfaces,
so that automations and hosts can interact with the skill lifecycle without duplicating operational or security logic.

## Acceptance Criteria

1. **Given** the latent skills and registry use cases are already implemented (`ActivateSkillUseCase`, `DeactivateSkillUseCase`, `UpdateSkillUseCase`), **When** the CLI interface is triggered, **Then** the system exposes the commands:
   - `umem skills activate <latent_skill_id>`
   - `umem skills deactivate <latent_skill_id>`
   - `umem skills update <latent_skill_id> [options...]`
   **And** these commands execute their respective application use cases using the consistent origin `"cli"`.

2. **Given** the CLI mutation commands (`activate`, `deactivate`, `update`), **When** successfully executed in the default Rich format, **Then** they create snapshots, record events in the audit log, and print a human-readable output detailing the changed scope, affected relative paths, and the audit reference (`audit_reference`), in full compliance with `devex-interaction-spec.md`.

3. **Given** the CLI command `umem skills update <latent_skill_id>`, **When** the user wants to update metadata granularly, **Then** the CLI accepts the options:
   - `--name <text>` to update the name
   - `--description <text>` to update the description
   - `--trigger <text>` (supporting multiple declarations, e.g., `--trigger "trigger A" --trigger "trigger B"`) to update triggers
   - `--file <path>` to pass a physical markdown file as the new skill content
   **And** the CLI passes the cleaned information to the `UpdateSkillCommand`.

4. **Given** the execution with `--format json`, **When** any CLI mutation command (`activate`, `deactivate`, `update`) is called, **Then** it strictly returns a JSON output compatible with the standard success envelope defined in `devex-interaction-spec.md` containing `ok: true`, `operation`, `scope`, and `data` containing the updated skill, file paths, and the generated `audit_reference`.

5. **Given** the MCP server, **When** it is started, **Then** it exposes the tools:
   - `activate_skill(latent_skill_id: str)`
   - `deactivate_skill(latent_skill_id: str)`
   - `update_skill(latent_skill_id: str, name: str | None, description: str | None, triggers: list[str] | None, raw_markdown: str | None)`
   **And** these tools delegate to the same use cases, using `"mcp"` as the origin and respecting the same contracts and JSON return envelopes.

6. **Given** the parity test suite, **When** it runs for skill management, **Then** it validates that:
   - CLI with `--format json` and MCP return equivalent structures.
   - Error handling (`ValidationFailedError`, `SecretDetectedError`, `StorageError`) is mapped correctly to their corresponding JSON-RPC codes and envelopes without leaking sensitive data or secrets.
   - No skill mutation bypasses the secure pipeline.

## Tasks / Subtasks

- [x] **Task 1: Write unit and integration tests (RED) for the new CLI and MCP routes** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Create/update CLI tests in `tests/interfaces/cli/test_skills.py` to cover the `activate`, `deactivate`, and `update` commands (Rich/JSON success scenarios and expected error scenarios).
  - [x] Create/update MCP tests in `tests/interfaces/mcp/test_skills.py` to cover the `activate_skill`, `deactivate_skill`, and `update_skill` tools.
  - [x] Create/update parity tests in `tests/interfaces/test_parity.py` to verify that the JSON responses from CLI and MCP are semantically and structurally equivalent for all skill mutation operations.
  - [x] Ensure domain errors (`ValidationFailedError`, `SecretDetectedError`, `StorageError`) behave identically and securely in both test suites.

- [x] **Task 2: Implement the mutation CLI commands in the Typer interface** (AC: 1, 2, 3, 4)
  - [x] Update `src/universal_memory/interfaces/cli/init_command.py` to expose the new commands in the `skills_app` subgroup:
    - Add `@skills_app.command("activate")` and its respective helper runner `_run_skills_activate`.
    - Add `@skills_app.command("deactivate")` and its respective helper runner `_run_skills_deactivate`.
    - Add `@skills_app.command("update")` and its respective helper runner `_run_skills_update` supporting `--name`, `--description`, `--trigger` (accumulative) and `--file` (with secure content reading).
  - [x] Map the Rich responses, formatting elegant returns containing scope, relative path of the skill in the filesystem, and audit IDs.
  - [x] Map the pure JSON return with the standard envelope from `devex-interaction-spec.md` when using `--format json`.
  - [x] Map domain errors and exceptions caught in the runners to user-friendly CLI returns.

- [x] **Task 3: Expose equivalent skill tools on the MCP server** (AC: 5, 6)
  - [x] Update `src/universal_memory/interfaces/mcp/server.py`:
    - Add `@server.tool(name="activate_skill")`.
    - Add `@server.tool(name="deactivate_skill")`.
    - Add `@server.tool(name="update_skill")` accepting optional parameters (`name`, `description`, `triggers`, `raw_markdown`).
  - [x] Delegate the execution of these tools to the same injected `ActivateSkillUseCase`, `DeactivateSkillUseCase`, and `UpdateSkillUseCase`.
  - [x] Ensure returns use the standard MCP success envelope and that domain errors are properly translated to JSON-RPC codes using the compliance table (e.g., `SecretDetectedError` -> `-32010`, `ValidationFailedError` -> `-32602`).

- [x] **Task 4: Wire and bootstrap dependencies in the CLI and MCP factories** (AC: 1, 5)
  - [x] Update `src/universal_memory/bootstrap/cli.py` to inject the use cases `_activate_skill_use_case`, `_deactivate_skill_use_case`, and `_update_skill_use_case` into the `build_main` factory.
  - [x] Update the signature and calls of `build_main` in `src/universal_memory/interfaces/cli/init_command.py` to receive the new skill mutation command handlers.
  - [x] Update `src/universal_memory/bootstrap/mcp.py` to inject the new use cases into `MCPUseCases` and the MCP server constructor.
  - [x] Update the signature and properties of `MCPUseCases` in `src/universal_memory/interfaces/mcp/server.py` to include the new use cases.

- [x] **Task 5: Run tests and final quality validations (GREEN)** (AC: 6)
  - [x] Run the entire integration and regression test suite: `uv run pytest`.
  - [x] Validate formatting and linting: `uv run ruff check .` and `uv run ruff format --check .`.
  - [x] Validate static typing: `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Validate conflict between `--file` and explicit fields in skill update [src/universal_memory/application/skills/update_skill.py:227]
- [x] [Review][Patch] `update_skill` fails for valid skills materialized in non-canonical slug [src/universal_memory/application/skills/update_skill.py:179]
- [x] [Review][Patch] CLI reports incorrect affected path for global skill mutations [src/universal_memory/interfaces/cli/init_command.py:2501]
- [x] [Review][Patch] Non-existent skill leaks as `storage_error` instead of validation/not-found error [src/universal_memory/interfaces/cli/init_command.py:1775]
- [x] [Review][Patch] MCP `update_skill` does not normalize inputs like the CLI [src/universal_memory/interfaces/mcp/server.py:525]

## Dev Notes

- **Clean Architecture & Separation of Layers**:
  - The CLI (`init_command.py`) and MCP (`server.py`) adapters should only translate user/host input to corresponding command DTOs (`ActivateSkillCommand`, `DeactivateSkillCommand`, `UpdateSkillCommand`) and dispatch them to the application use cases.
  - No file validation or frontmatter checking logic should be re-implemented in the CLI or MCP adapters. This is already properly encapsulated in the application use cases (`update_skill.py`).

- **JSON Structural Parity (CLI vs MCP)**:
  - According to `devex-interaction-spec.md`, the JSON output of `--format json` in the CLI and the JSON return of the MCP tools must share the same semantic keys and success/error enveloping.
  - The standard success envelope must be respected:
    ```json
    {
      "ok": true,
      "operation": "skills.activate",
      "scope": "project",
      "data": {
        "latent_skill": {
          "id": "6-6-expor-gest-o-de-skills-por-cli-e-mcp",
          "name": "Expor Gestão de Skills por CLI e MCP",
          "status": "active",
          "scope": "project"
        },
        "skill_file": "skills/6-6-expor-gest-o-de-skills-por-cli-e-mcp/SKILL.md",
        "audit_reference": "evt_abc123",
        "snapshot_reference": "snp_xyz789"
      },
      "warnings": []
    }
    ```

- **Reading the Update File (`--file`)**:
  - When using `umem skills update <latent_skill_id> --file <path>`, the CLI must load the physical content of the specified markdown file using UTF-8 encoding and pass it as `raw_markdown` to the `UpdateSkillCommand`.
  - If the file does not exist at the path provided to the CLI, raise a user-friendly, explanatory CLI validation error.

### Project Structure Notes

- CLI interfaces reside in `src/universal_memory/interfaces/cli/init_command.py`.
- MCP interfaces reside in `src/universal_memory/interfaces/mcp/server.py`.
- The main bootstrappers that wire everything together reside in `src/universal_memory/bootstrap/cli.py` and `src/universal_memory/bootstrap/mcp.py`.
- Tests should be located under `tests/interfaces/cli/test_skills.py`, `tests/interfaces/mcp/test_skills.py`, and `tests/interfaces/test_parity.py`.

### References

- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (Output & Error Contracts, MCP Parity) - [devex-interaction-spec.md](file:///{project-root}/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- `_bmad-output/planning-artifacts/prd.md` (FR11, FR12, FR18, FR21) - [prd.md](file:///{project-root}/_bmad-output/planning-artifacts/prd.md)
- `src/universal_memory/application/skills/update_skill.py` - [update_skill.py](file:///{project-root}/src/universal_memory/application/skills/update_skill.py)

## Dev Notes (Customizations / Past Learnings)

- **State preservation**: According to the previous story (6.5), deactivation operations (`deactivate_skill`) only change the status of the latent skill to `ignored` in the repository, ensuring that the physical `SKILL.md` file remains intact to avoid losing history.
- **Reactivation validation**: Reactivation (`activate_skill`) requires that the physical `SKILL.md` file exists on disk and has readable/valid frontmatter before returning the status to `active`.

## Dev Agent Record

### Agent Model Used

Codex GPT-5

### Debug Log References

- `uv run pytest tests/interfaces/cli/test_skills.py tests/interfaces/mcp/test_skills.py` confirmed the RED/GREEN cycle of the new routes.
- `uv sync` was necessary to resolve the MCP environment after the sandbox blocked access to the uv cache.
- `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright` executed successfully.

### Completion Notes List

- Implemented the CLI commands `skills activate`, `skills deactivate`, and `skills update`, all delegating to the application use cases with origin `cli`.
- Implemented the MCP tools `activate_skill`, `deactivate_skill`, and `update_skill`, all delegating to the same use cases with origin `mcp`.
- Standardized JSON skill mutation envelopes, human-readable output with relative paths, snapshots and audits, and secure mapping of domain errors.
- Added CLI, MCP, parity, and compliance tests covering success, expected errors, and structural equivalence.

### File List

- `_bmad-output/implementation-artifacts/6-6-expor-gest-o-de-skills-por-cli-e-mcp.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/skills/update_skill.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/__init__.py`
- `tests/interfaces/__init__.py`
- `tests/interfaces/cli/__init__.py`
- `tests/interfaces/cli/test_skills.py`
- `tests/interfaces/mcp/__init__.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_skills.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-05-29: Exposed skill mutations via CLI and MCP with JSON parity, testing, and final validations.
