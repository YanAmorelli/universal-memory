---
title: 'Expose installed version in CLI and status'
type: 'feature'
created: '2026-06-04'
status: 'done'
route: 'one-shot'
---

# Expose installed version in CLI and status

## Intent

**Problem:** Users installing `universal-memory` from PyPI need a direct way to confirm which installed package version is being executed. The current CLI help does not expose `--version`, and `umem status` reports memory health without showing the installed application version.

**Approach:** Add a root-level `umem --version` option and include `installed_version` in CLI and MCP status payloads, plus the human-readable status output.

## Code Map

- `src/universal_memory/application/memory/get_memory_status_use_case.py` -- Extends `GetMemoryStatusResult` with the installed package version.
- `src/universal_memory/interfaces/cli/init_command.py` -- Adds the root `--version` option and renders `installed_version` in status output.
- `src/universal_memory/interfaces/mcp/server.py` -- Keeps MCP status payloads in parity with CLI status payloads.
- `tests/interfaces/cli/test_status_command.py` -- Covers `umem --version` and status payload/output version rendering.
- `tests/interfaces/mcp/test_compliance.py` -- Updates MCP contract keys and types for status.
- `tests/interfaces/mcp/test_server.py` -- Updates the MCP status structured-content regression expectation.

## Tasks & Acceptance

**Execution:**
- [x] `src/universal_memory/interfaces/cli/init_command.py` -- Add `--version` to the root command -- Gives users a short command for checking the installed package.
- [x] `src/universal_memory/application/memory/get_memory_status_use_case.py` -- Add `installed_version` to status results -- Makes version data available through the status use case.
- [x] `src/universal_memory/interfaces/cli/init_command.py` -- Include `installed_version` in JSON and human status output -- Supports both agent-readable and human-readable checks.
- [x] `src/universal_memory/interfaces/mcp/server.py` -- Include `installed_version` in MCP status payloads -- Preserves CLI/MCP parity.
- [x] `tests/interfaces/cli/test_status_command.py` and `tests/interfaces/mcp/*.py` -- Update regression coverage -- Prevents future loss of version visibility.

**Acceptance Criteria:**
- Given a user has installed `universal-memory`, when they run `umem --version`, then the CLI prints the installed version and exits successfully.
- Given a user runs `umem status`, when the project is initialized or uninitialized, then the human output includes the installed version.
- Given a user or agent runs `umem status --format json`, then `data.installed_version` is present.
- Given an MCP client calls `status`, then `data.installed_version` is present and the MCP compliance contract accepts it.

## Suggested Review Order

- [CLI root option](../../src/universal_memory/interfaces/cli/init_command.py) -- confirm `--version` is eager, does not require a subcommand, and prints only the package version line.
- [Status use case result](../../src/universal_memory/application/memory/get_memory_status_use_case.py) -- confirm the version comes from package metadata without touching memory storage.
- [CLI status payload/output](../../src/universal_memory/interfaces/cli/init_command.py) -- confirm initialized and uninitialized status both include `installed_version`.
- [MCP status payload](../../src/universal_memory/interfaces/mcp/server.py) -- confirm CLI/MCP status parity.
- [Regression tests](../../tests/interfaces/cli/test_status_command.py) -- confirm root version and CLI status assertions cover the new behavior.
- [MCP contract tests](../../tests/interfaces/mcp/test_compliance.py) -- confirm public MCP contract keys and types are updated.

## Verification

**Commands:**
- `uv run umem --version` -- expected: prints `umem 0.1.2`.
- `uv run umem status --format json` -- expected: `data.installed_version` is present.
- `uv run pyright` -- expected: `0 errors`.
- `uv run pytest` -- expected: all tests pass.

### Review Findings

- [x] [Review][Patch] Spec lifecycle is marked `done` before review completion [_bmad-output/implementation-artifacts/spec-cli-version-status.md:5]
- [x] [Review][Defer] Version fallback is hardcoded when package metadata is unavailable [src/universal_memory/__init__.py:5] -- deferred, pre-existing
