---
title: 'Expose umem skills track in CLI and MCP'
type: 'feature'
created: '2026-06-03'
status: 'done'
baseline_commit: '702cebc69d5d5e0b476dc46ae052b5e1f24e08f9'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The `TrackLatentSkillUseCase` logic is fully implemented and tested but not exposed to any interface (CLI or MCP). This prevents agents and users from explicitly registering new latent skills to start the skill proposal/generation lifecycle.

**Approach:** Expose the `umem skills track` subcommand in the Typer CLI and the `track_latent_skill` tool in the FastMCP server, allowing explicit registration of latent skills with metadata.

## Boundaries & Constraints

**Always:** 
- Mappings of domain errors to JSON-RPC error codes and standard error envelopes must be respected.
- Mutations must generate audit log entries and snapshot references where configured.
- JSON output formats must follow the standard envelopes.

**Ask First:** 
- None.

**Never:** 
- Do not bypass the safe mutation pipeline when persisting latent skills.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH (CLI) | `umem skills track --name "test" --description "desc" --scope project --tag t1` | Human format output detailing Latent skill ID, scope, recurrence, matched_existing=False, audit reference, and snapshot reference. | N/A |
| HAPPY_PATH (JSON) | `umem skills track --name "test" --description "desc" --format json` | Standard JSON envelope with ok: true, operation: "skills.track", and data keys. | N/A |
| ERROR_CASE (CLI validation) | `umem skills track` (missing name/desc) | CLI error explaining missing required options. | Exit code 2 / Typer error |
| ERROR_CASE (Secret detected) | `umem skills track --name "test" --description "password=123"` | Blocked mutation, returning SecretDetectedError. | Exit code 1 / standard error envelope / JSON-RPC code -32010 |

</frozen-after-approval>

## Code Map

- `src/universal_memory/interfaces/cli/init_command.py` -- Implements CLI subcommands for skills and runners.
- `src/universal_memory/interfaces/mcp/server.py` -- Exposes MCP tools and the MCPUseCases DTO.
- `src/universal_memory/bootstrap/cli.py` -- Implements CLI application and injects use cases.
- `src/universal_memory/bootstrap/mcp.py` -- Implements MCP server and injects use cases.
- `tests/interfaces/cli/test_skills.py` -- CLI tests for skill operations.
- `tests/interfaces/mcp/test_skills.py` -- MCP tool tests for skill operations.
- `tests/interfaces/test_parity.py` -- Parity validation tests.

## Tasks & Acceptance

**Execution:**
- [x] `src/universal_memory/interfaces/cli/init_command.py` -- Expose `@skills_app.command("track")` and define runner `_run_skills_track` to call `TrackLatentSkillUseCase` and format CLI outputs.
- [x] `src/universal_memory/interfaces/mcp/server.py` -- Expose `@server.tool(name="track_latent_skill")` and update `MCPUseCases` to receive and invoke `TrackLatentSkillUseCase`.
- [x] `src/universal_memory/bootstrap/cli.py` -- Instantiate `TrackLatentSkillUseCase` and inject it into `build_main`.
- [x] `src/universal_memory/bootstrap/mcp.py` -- Instantiate `TrackLatentSkillUseCase` and inject it into `MCPUseCases`.
- [x] `tests/interfaces/cli/test_skills.py` -- Add CLI tests for the `skills track` command (both human and JSON formats).
- [x] `tests/interfaces/mcp/test_skills.py` -- Add MCP tests for the `track_latent_skill` tool.
- [x] `tests/interfaces/test_parity.py` -- Add CLI/MCP JSON output parity tests for the track operation.

**Acceptance Criteria:**
- Given a project initialized, when running `umem skills track --name "Name" --description "Desc"`, then a new latent skill is recorded in `latent_skills.jsonl` with status `proposed` and recurrence 1.
- Given an existing latent skill with name "Name", when running track again with a similar name/description, then the recurrence count is incremented to 2 and matched_existing is true.
- Given JSON formatting `--format json`, when running `skills track`, then the standard success envelope with operation `skills.track` and the newly tracked latent skill is returned.

## Verification

**Commands:**
- `uv run pytest tests/interfaces/cli/test_skills.py tests/interfaces/mcp/test_skills.py tests/interfaces/test_parity.py` -- expected: SUCCESS
- `uv run ruff check .` -- expected: SUCCESS
- `uv run ruff format --check .` -- expected: SUCCESS
- `uv run pyright` -- expected: SUCCESS

### Review Findings

- [x] [Review][Patch] Remove out-of-scope host/docs changes from the `skills track` story [`_bmad-output/planning-artifacts/architecture.md:975`]
- [x] [Review][Patch] Verification commands fail for lint/format [`src/universal_memory/application/host/setup_host_use_case.py:40`]
- [x] [Review][Patch] MCP `track_latent_skill` error envelopes hardcode project scope for global failures [`src/universal_memory/interfaces/mcp/server.py:518`]
- [x] [Review][Patch] `skills track` accepts blank name or description without interface/use-case validation [`src/universal_memory/interfaces/cli/init_command.py:807`]
- [x] [Review][Patch] Specified secret-detection scenario is not tested for the new CLI/MCP track surfaces [`tests/interfaces/cli/test_skills.py:319`]
- [x] [Review][Patch] Existing-skill recurrence behavior is not covered on CLI/MCP outputs [`tests/interfaces/cli/test_skills.py:340`]
- [x] [Review][Patch] JSON-mode CLI test does not assert the command passed to the use case [`tests/interfaces/cli/test_skills.py:349`]
- [x] [Review][Patch] MCP `track_latent_skill` lacks negative-path coverage for validation/storage/error mapping [`tests/interfaces/mcp/test_skills.py:320`]

## Suggested Review Order

**CLI Integration**

- Define a CLI subcommand to register or increment recurrence of latent skills.
  [`init_command.py:806`](../../src/universal_memory/interfaces/cli/init_command.py#L806)

- Run track subcommand and format output as human-readable or standard JSON envelope.
  [`init_command.py:2120`](../../src/universal_memory/interfaces/cli/init_command.py#L2120)

- Inject the track use case dependency into the CLI application builder.
  [`cli.py:190`](../../src/universal_memory/bootstrap/cli.py#L190)

**MCP Tool Integration**

- Define the MCP tool to expose latent skill tracking capabilities to AI clients.
  [`server.py:475`](../../src/universal_memory/interfaces/mcp/server.py#L475)

- Inject the track use case dependency into the MCP server builder.
  [`mcp.py:136`](../../src/universal_memory/bootstrap/mcp.py#L136)

**Verification**

- Validate CLI subcommand behavior with both human-readable and JSON format output.
  [`test_skills.py:299`](../../tests/interfaces/cli/test_skills.py#L299)

- Validate MCP tool behavior and payload structure for the track operation.
  [`test_skills.py:316`](../../tests/interfaces/mcp/test_skills.py#L316)

- Enforce schema compliance of the new tool in the MCP compliance test suite.
  [`test_compliance.py:561`](../../tests/interfaces/mcp/test_compliance.py#L561)

- Ensure output schema parity between the CLI and MCP JSON interfaces.
  [`test_parity.py:279`](../../tests/interfaces/test_parity.py#L279)
