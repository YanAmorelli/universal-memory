---
title: 'Harden MCP install and startup UX'
type: 'bugfix'
created: '2026-06-24'
status: 'done'
baseline_commit: '37c5dcc1aac2076fe7d4341a0d7c4e126113ea63'
context:
  - '_bmad-output/planning-artifacts/devex-interaction-spec.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/implementation-artifacts/spec-umem-doctor.md'
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** The MCP setup path has adoption friction that matches known MCP failure modes: the README example uses `uv run --package universal-memory umem-mcp`, which fails outside a `uv` project; published dependency constraints are looser than the architecture; and `umem-mcp` does not provide a clear pre-listen startup failure message.

**Approach:** Make the documented MCP configuration copy-paste safe for a user with no local `pyproject.toml`, align runtime dependency bounds with the architecture, and wrap MCP entrypoint startup validation so dependency/configuration failures emit a concise human-readable stderr message before the server listens.

## Boundaries & Constraints

**Always:** Preserve Python 3.12+ as the runtime floor. Keep essential MCP operation offline after installation. Keep CLI/MCP tool payload contracts unchanged. Use relative project paths in docs, tests, and user-facing errors where possible. Keep startup validation read-only and compatible with an uninitialized project so `initialize_project` remains usable from MCP.

**Ask First:** Adding a required environment variable, changing supported install managers, changing public MCP tool names or payload keys, requiring `.umem/` to exist before `umem-mcp` starts, or introducing network access during startup requires human approval.

**Never:** Do not document an MCP config that requires the user to launch from this repo or any `uv` project. Do not add external service checks, background repair, automatic host setup, or mutations to the MCP startup path. Do not solve dependency drift only in `uv.lock`; the published `pyproject.toml` constraints must carry the compatibility contract.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Claude Desktop copy-paste config | User copies the README MCP config into a machine without a local `pyproject.toml` | Config uses `uvx --from universal-memory umem-mcp` or installed `umem-mcp`, not `uv run --package` | Static docs test blocks regressions to `uv run --package` for published-server config |
| Persistent install config | User has run `uv tool install universal-memory` or `pipx install universal-memory` | Docs show `command: "umem-mcp"` as the stable low-friction option | Troubleshooting points to `umem doctor` and package-manager upgrade commands |
| Startup dependency/config failure | `umem-mcp` fails before or during server construction because of dependency/API/config errors | Process exits non-zero and stderr starts with `Universal Memory MCP startup failed:` plus a recovery hint | Expected errors are sanitized; unexpected errors avoid traceback by default unless existing debug behavior explicitly enables details |
| Dependency resolver drift | Fresh install resolves package metadata from PyPI rather than local `uv.lock` | `fastmcp`, `pydantic`, `typer`, and `tomli-w` constraints match the architecture-compatible lower/upper bounds | Package metadata test fails with the exact dependency whose bound drifted |

</frozen-after-approval>

## Code Map

- `README.md` -- Primary install and Claude Desktop MCP configuration examples.
- `docs/users/getting-started.md` -- User-facing setup path and health check guidance.
- `docs/agents/mcp-and-skills.md` -- Agent-facing MCP explanation and supported launch command pointer.
- `docs/contributors/release-and-alpha.md` -- Clean-environment release checklist for package and MCP startup validation.
- `pyproject.toml` -- Published runtime dependency constraints and console scripts.
- `uv.lock` -- Lockfile refreshed after dependency constraint changes.
- `src/universal_memory/bootstrap/mcp.py` -- MCP entrypoint composition and startup failure handling.
- `src/universal_memory/interfaces/errors.py` -- Existing sanitization helpers to reuse for startup details.
- `tests/interfaces/mcp/test_server.py` -- Existing offline MCP bootstrap coverage to preserve and extend.
- `tests/packaging/test_runtime_dependency_bounds.py` -- New package metadata regression test for runtime dependency bounds.
- `tests/docs/test_mcp_install_docs.py` -- New docs regression test for copy-paste-safe MCP config examples.

## Tasks & Acceptance

**Execution:**
- [x] `README.md` and `docs/users/getting-started.md` -- Replace the MCP config example with a no-project-required `uvx --from universal-memory umem-mcp` option and a persistent-install `umem-mcp` option -- Removes the documented setup trap.
- [x] `docs/agents/mcp-and-skills.md` and `docs/contributors/release-and-alpha.md` -- Add concise MCP launch/troubleshooting guidance and require clean-environment validation of `uvx --from universal-memory umem-mcp --help` or equivalent installed entrypoint -- Keeps agent and release docs aligned.
- [x] `pyproject.toml` and `uv.lock` -- Tighten published runtime dependency bounds to the architecture-compatible ranges, including `fastmcp>=3.3.1,<4`, `pydantic>=2.13.4,<3`, `typer>=0.25.1`, and `tomli-w>=1.2.0` -- Prevents silent breakage from incompatible resolver choices.
- [x] `src/universal_memory/bootstrap/mcp.py` -- Add read-only startup guard around MCP server construction and `run()`, printing a clear sanitized failure title and recovery hint to stderr before exiting non-zero -- Makes pre-listen failures attributable to UMEM rather than the MCP host.
- [x] `tests/interfaces/mcp/test_server.py` -- Extend MCP bootstrap tests to cover successful offline startup composition and startup failure messaging without opening sockets or depending on network access -- Protects the entrypoint behavior.
- [x] `tests/packaging/test_runtime_dependency_bounds.py` -- Parse `pyproject.toml` and assert required runtime dependency lower/upper bounds -- Prevents dependency-bound drift from returning.
- [x] `tests/docs/test_mcp_install_docs.py` -- Assert published MCP examples avoid `uv run --package` and include the supported `uvx --from universal-memory umem-mcp` command -- Prevents docs regression.

**Acceptance Criteria:**
- Given a user copies the README Claude Desktop MCP config into a directory without `pyproject.toml`, when the documented command is inspected, then it does not depend on `uv run` project context.
- Given the published package metadata is parsed, when runtime dependency constraints are checked, then FastMCP has a `<4` upper bound and all listed lower bounds match the architecture.
- Given `umem-mcp` encounters an exception before serving tools, when the entrypoint runs, then stderr contains `Universal Memory MCP startup failed:` and a recovery hint, and the process exits non-zero without a raw traceback by default.
- Given the existing offline MCP bootstrap test runs, when the server is built and `status` is called, then the existing success envelope behavior remains unchanged.

## Spec Change Log

## Design Notes

The startup guard should stay at the bootstrap boundary, not inside individual MCP tools. Tool-level errors already return structured MCP payloads; this spec covers failures that happen before a client can list or call tools. Prefer reusing existing sanitization from `interfaces/errors.py` so paths and secret-like values are not echoed in startup diagnostics.

Recommended user docs pattern:

```json
{
  "command": "uvx",
  "args": ["--from", "universal-memory", "umem-mcp"]
}
```

## Verification

**Commands:**
- `uv run pytest tests/interfaces/mcp/test_server.py tests/packaging/test_runtime_dependency_bounds.py tests/docs/test_mcp_install_docs.py` -- expected: targeted startup, dependency metadata, and docs regression tests pass.
- `uv run pytest tests/interfaces/mcp/test_compliance.py tests/interfaces/test_parity.py` -- expected: MCP tool inventory and CLI/MCP payload parity remain green.
- `uv run ruff check .` -- expected: no lint regressions.
- `uv run pyright` -- expected: no type errors.

## Suggested Review Order

**Startup boundary**

- Lazy imports let the entrypoint report dependency failures before serving.
  [`mcp.py:22`](../../src/universal_memory/bootstrap/mcp.py#L22)

- Entrypoint handles help and startup failures in one narrow boundary.
  [`mcp.py:280`](../../src/universal_memory/bootstrap/mcp.py#L280)

- Fallback sanitization keeps startup diagnostics safe even when formatters fail.
  [`mcp.py:296`](../../src/universal_memory/bootstrap/mcp.py#L296)

**MCP setup docs**

- README now offers project-independent and persistent MCP launch configs.
  [`README.md:194`](../../README.md#L194)

- User docs mirror the copy-paste-safe host configuration.
  [`getting-started.md:86`](../../docs/users/getting-started.md#L86)

- Agent docs explain launch troubleshooting without requiring project context.
  [`mcp-and-skills.md:21`](../../docs/agents/mcp-and-skills.md#L21)

- Release checklist validates the published `uvx` MCP path.
  [`release-and-alpha.md:37`](../../docs/contributors/release-and-alpha.md#L37)

**Dependency contract**

- Published metadata now carries the architecture-compatible runtime bounds.
  [`pyproject.toml:35`](../../pyproject.toml#L35)

**Regression coverage**

- MCP tests cover offline bootstrap, help, import failure, and sanitized stderr.
  [`test_server.py:1048`](../../tests/interfaces/mcp/test_server.py#L1048)

- Docs tests block the old project-dependent MCP command.
  [`test_mcp_install_docs.py:13`](../../tests/docs/test_mcp_install_docs.py#L13)

- Packaging tests pin the runtime dependency compatibility contract.
  [`test_runtime_dependency_bounds.py:7`](../../tests/packaging/test_runtime_dependency_bounds.py#L7)
