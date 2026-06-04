---
title: 'Add umem doctor diagnostics'
type: 'feature'
created: '2026-06-04'
status: 'done'
baseline_commit: '211be86d73849e59bb561ab8fbcb9a9c1c1bc8ac'
context: []
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** Alpha testers need a preflight command that diagnoses local environment, filesystem layout, executable exposure, and host integration problems before they start using `universal-memory`. Today these checks are split across `status`, `host check`, manual shell commands, and opaque storage errors.

**Approach:** Add a read-only `umem doctor` CLI command and an MCP `doctor` tool backed by one application use case. The command returns a structured checklist with actionable recovery hints, supports human and JSON output, and keeps CLI/MCP payloads in parity.

## Boundaries & Constraints

**Always:** The doctor path is read-only and must not repair, initialize, sync, chmod, or mutate host files. JSON responses must use the existing envelope style with `operation: "doctor"` and `scope: "environment"`. CLI and MCP must share the same application result and payload shape. Human output must be plain terminal text without emoji dependency. Paths shown to users should be relative when they are inside the project root.

**Ask First:** Adding an automatic repair mode, changing config discovery semantics, changing host setup behavior, or requiring a new runtime dependency requires human approval.

**Never:** Do not shell out to `which`; use Python APIs such as `shutil.which`. Do not reuse mutation-oriented commands in a way that can write files. Do not treat an uninitialized project as a fatal doctor failure by itself; it should be reported as a layout check finding with a recovery hint.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Healthy environment | Python >= 3.12, initialized `.umem`, writable canonical dirs, executable exposure, valid configured hosts | CLI exits 0, JSON `ok: true`, all checks have `status: "success"` | No error envelope |
| Partial project layout | `.umem` exists but required paths are missing or wrong kind | CLI exits non-zero, JSON `ok: false`, `project_layout` fails with missing/wrong-kind detail and `umem init --yes` recovery hint | Continue running independent checks |
| Uninitialized project | No `.umem` directory | `project_layout` reports a non-fatal failed check with initialization recovery hint; global checks still run | No exception from status repositories |
| Missing executables | `umem` and/or `umem-mcp` not discoverable via `shutil.which` | `path_executables` fails with names missing and install/venv activation hint | Continue other checks |
| Host integration issue | Configured host target is missing or managed block fails read validation | `hosts_integration` fails with host-specific detail and `umem host setup <host_id> --yes` hint | Unsupported or absent host config should not crash the whole doctor |

</frozen-after-approval>

## Code Map

- `docs/umem-doctor-spec.md` -- Source proposal to move into the BMad implementation artifact.
- `src/universal_memory/application/diagnostics/doctor_use_case.py` -- New application use case and result models for read-only diagnostics.
- `src/universal_memory/application/diagnostics/__init__.py` -- Public exports for diagnostics use cases.
- `src/universal_memory/interfaces/cli/init_command.py` -- Register `umem doctor`, render human output, and emit JSON envelope.
- `src/universal_memory/interfaces/mcp/server.py` -- Register MCP `doctor` tool and keep payload parity with CLI.
- `src/universal_memory/bootstrap/cli.py` and `src/universal_memory/bootstrap/mcp.py` -- Compose the doctor use case for CLI and MCP entrypoints.
- `tests/interfaces/cli/test_doctor_command.py` -- CLI contract and output tests.
- `tests/interfaces/mcp/test_server.py` and `tests/interfaces/mcp/test_compliance.py` -- MCP tool registration, structured content, and contract tests.
- `tests/interfaces/test_parity.py` -- Public CLI/MCP capability parity matrix update.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/implementation-artifacts/spec-umem-doctor.md` and `docs/umem-doctor-spec.md` -- Move the proposal into BMad artifacts and remove the loose docs copy -- Keeps implementation flow canonical.
- [x] `src/universal_memory/application/diagnostics/doctor_use_case.py` -- Implement read-only checks for Python version, canonical permissions, project layout, executable exposure, and host integration -- Centralizes diagnostics for CLI/MCP parity.
- [x] `src/universal_memory/interfaces/cli/init_command.py` -- Add `doctor` command with human and JSON output -- Exposes tester-friendly CLI preflight.
- [x] `src/universal_memory/interfaces/mcp/server.py` -- Add `doctor` tool using the same payload shape -- Preserves required MCP parity.
- [x] `src/universal_memory/bootstrap/*.py` -- Wire the doctor use case into CLI and MCP composition -- Makes installed entrypoints work.
- [x] `tests/interfaces/**/*.py` and focused application tests -- Cover success, layout failure, executable failure, uninitialized project, and MCP parity -- Prevents regressions in public contracts.

**Acceptance Criteria:**
- Given a healthy initialized project, when running `umem doctor --format json`, then stdout is a single JSON envelope with `operation: "doctor"`, `scope: "environment"`, `ok: true`, and a `data.summary` matching the checks.
- Given a partial `.umem` layout, when running `umem doctor --format json`, then the command exits non-zero, returns `ok: false`, includes a failed `project_layout` check, and still includes independent check results.
- Given the MCP server is configured, when an MCP client calls `doctor`, then the structured content uses the same `data.checks` and `data.summary` shape as the CLI JSON payload.
- Given `umem` or `umem-mcp` is not discoverable through the configured executable resolver, when doctor runs, then `path_executables` reports a failed check with an actionable recovery hint.

### Review Findings

- [x] [Review][Patch] `filesystem_permissions` creates persistent directories while diagnosing [src/universal_memory/application/diagnostics/doctor_use_case.py:139]
- [x] [Review][Patch] `hosts_integration` writes host validation audit events during doctor [src/universal_memory/application/diagnostics/doctor_use_case.py:235]
- [x] [Review][Patch] Invalid config is silently reported as no configured hosts [src/universal_memory/application/diagnostics/doctor_use_case.py:259]
- [x] [Review][Patch] Uninitialized unwritable project roots are not diagnosed before recommending init [src/universal_memory/application/diagnostics/doctor_use_case.py:133]
- [x] [Review][Patch] Global `config.toml` file permissions are not validated [src/universal_memory/application/diagnostics/doctor_use_case.py:129]
- [x] [Review][Patch] Uninitialized project behavior lacks focused use case coverage [tests/application/diagnostics/test_doctor_use_case.py:8]

## Design Notes

Use a small result model rather than reusing `GetMemoryStatusResult`: doctor checks environment readiness, while status reports memory state. Each check should return `name`, `status`, optional `detail`, optional `error`, and optional `recovery_hint`; the summary can derive totals from that list. Host integration should be read-only and tolerant: configured hosts with missing or invalid files fail the check, while absent host configuration can pass with a detail that no hosts are configured.

## Verification

**Commands:**
- `uv run pytest tests/application/diagnostics tests/interfaces/cli/test_doctor_command.py tests/interfaces/mcp/test_server.py tests/interfaces/mcp/test_compliance.py tests/interfaces/test_parity.py` -- expected: all targeted tests pass.
- `uv run umem doctor --format json` -- expected: JSON envelope includes `operation: "doctor"` and `data.summary`.
- `uv run pyright` -- expected: 0 errors.
