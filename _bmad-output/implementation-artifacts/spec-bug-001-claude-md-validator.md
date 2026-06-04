---
title: 'BUG-001 - Align CLAUDE.md with claude_code validator'
type: 'bugfix'
created: '2026-05-29'
status: 'done'
baseline_commit: '727312869dfac8fc3e2da73fec7c80508c6abf4b'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `umem init` can generate `CLAUDE.md` for `claude_code` that fails in `umem status` itself, because the renderer does not include a reference accepted by the `claude_md_delta_validator` validator when there are no specific deltas.

**Approach:** Adjust the default managed block of `CLAUDE.md` to always document how Claude Code should access the `universal-memory` context, keeping the file as a consumer of deltas and without duplicating shared policies.

## Boundaries & Constraints

**Always:** Preserve UMEM delimiters, manually preserved content outside the managed block, compact manifest limit, and filtering of `CLAUDE.md` for `provider_delta` and `scoped_rule`.

**Ask First:** Any change in validator semantics, host/target names, or the public CLI/MCP payload contract.

**Never:** Copy entire shared rules to `CLAUDE.md`, relax `_has_mcp_reference`, or remove the guidance to read `AGENTS.md` when it exists.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Setup without deltas | `ConfigureHostCommand(host_id="claude_code", apply=True)` without instruction blocks | `CLAUDE.md` contains a UMEM block with reference to `universal-memory`/`umem context` and `umem status` returns `success` | N/A |
| Setup with deltas | `provider_delta` and `scoped_rule` present | Deltas remain rendered and shared policies continue to be excluded | N/A |

</frozen-after-approval>

## Code Map

- `src/universal_memory/application/host/setup_host_use_case.py` -- Contains the `CLAUDE.md` renderer, reading validator, and list of accepted MCP references.
- `tests/application/test_setup_host.py` -- Setup/check coverage for hosts, including `CLAUDE.md` behavior and `claude_code` validation.
- `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- BUG-001 registry to be updated after fix and verification.

## Tasks & Acceptance

**Execution:**
- [x] `src/universal_memory/application/host/setup_host_use_case.py` -- Include fixed operational reference to `universal-memory`/`umem context` in the managed block of `CLAUDE.md` -- Ensures the generated file satisfies the validator without depending on existing deltas.
- [x] `tests/application/test_setup_host.py` -- Add test that applies `claude_code` setup without deltas and then validates with `check=True` -- Reproduces the smoke test bug and protects against regression.
- [x] `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Mark BUG-001 as fixed/verified with commands run -- Maintains alpha traceability.

**Acceptance Criteria:**
- Given a project without `CLAUDE.md`, when `claude_code` setup and check run in sequence, then `validation_status` and `checks["managed_block_has_mcp_reference"]` indicate success.
- Given `claude_code` setup with `shared_policy`, `provider_delta`, and `scoped_rule` blocks, when `CLAUDE.md` is generated, then the supported deltas appear and the shared policy remains absent.

## Spec Change Log

## Verification

**Commands:**
- `uv run pytest tests/application/test_setup_host.py` -- expected: all host setup tests pass.
- `uv run pytest` -- expected: complete suite passes.
- `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem init --hosts claude_code --yes --format json` in temporary sandbox -- expected: `claude_code` setup returns `validation_status: success`.
- `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem status --format json` in temporary sandbox -- expected: `host_validation.claude_code.status: success`.

## Suggested Review Order

- Renderer includes MCP reference without duplicating shared policy.
  [`setup_host_use_case.py:739`](../../src/universal_memory/application/host/setup_host_use_case.py#L739)

- Regression reproduces setup without deltas followed by the validator itself.
  [`test_setup_host.py:322`](../../tests/application/test_setup_host.py#L322)

- BUG-001 records correction and alpha verification.
  [`alpha-bug-log.md:78`](alpha-bug-log.md#L78)
