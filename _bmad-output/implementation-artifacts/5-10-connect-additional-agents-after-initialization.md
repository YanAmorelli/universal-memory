# Story 5.10: Connect Additional Agents After Initialization

Status: done

## Story

As a user who installs or adopts another agent,
I want to connect it to the existing UMEM project with one simple command,
so that I do not need to reinitialize memory or understand integration internals.

**Requirements covered:** FR37.

## Acceptance Criteria

1. `umem connect` detects agents not yet connected and reuses valid existing connections without rewriting them.
2. It reuses the same project-scoped resolver and single-confirmation contract as `umem init`.
3. With no new agent, it returns a clear no-change or manual-selection result and never recreates or resets `.umem/`.
4. Results distinguish connected and validated, skipped, and action required, directing unresolved environment failures to `umem doctor`.
5. JSON is pure and reports detection, existing connections, recommendations, tiers, channels, validations, external actions, pending steps, and audit references.
6. Explicit runtime selection remains available for scripts and advanced control.

## Tasks / Subtasks

- [x] Add the `umem connect` command without invoking project initialization.
- [x] Reuse the Story 5.9 planner, executor, validation, and result renderers.
- [x] Preserve valid connections and avoid duplicate host writes.
- [x] Add pure JSON, no-change, fallback, and initialized-project guard coverage.
- [x] Run focused and full validation.
- [x] Resolve review findings for persisted runtime state, content-aware idempotency, safety enforcement, and external-action honesty.

## Developer Context / Guardrails

- Sources: `_bmad-output/implementation-artifacts/spec-agent-support-evolution-tiers-and-mcp-fallback.md`, `_bmad-output/planning-artifacts/devex-interaction-spec.md`, and Story 5.10 in `_bmad-output/planning-artifacts/epics.md`.
- `connect` must not call project layout creation or reset `.umem/`.
- Do not edit the runtime registry or integrate `npx skills` directly in this story.
- Keep all project paths in specs, docs, CLI payloads, and tests relative.
- Do not update `_bmad-output/implementation-artifacts/sprint-status.yaml`.

## Dev Agent Record

### Implementation Plan

- Expose `connect` as a thin CLI adapter over the shared connection planner/executor.
- Require an existing initialized layout, discover only new candidates by default, and reuse valid existing connections as no-ops.
- Preserve explicit runtime selection for deterministic automation and render the same outcome vocabulary as initialization.

### Debug Log

- BMAD review requested changes for persisted connections, content-aware readiness, real MCP validation, unsafe-plan blocking, external-action honesty, and shared initialization execution. Stories 5.9/5.10 were reopened for TDD corrections.
- Added RED coverage for missing initialization, no detected agent, JSON purity, unmanaged MCP, idempotent existing connection, confirmation refusal, and legacy automation.
- Environment executable detection made early tests host-dependent; focused tests now inject the typed project-signal detector while production continues to honor all declared registry signals.
- Generic agent selection originally passed through the closed runtime-ID validator. A separate safe agent-ID normalizer now preserves known aliases and accepts portable profile IDs such as `windsurf`.
- Review follow-up persists successfully validated known runtimes into `[runtimes].enabled` through protected configuration writes, without invoking initialization or replacing existing runtime selections.
- Empty markers or unrelated content no longer count as an existing connection, including runtime-specific Cursor and Antigravity targets.
- `umem connect` rejects unsafe plans before confirmation or execution in every output mode. External installer plans are action required until an injected executor reports that the action actually completed.
- Final review exposed a reconciliation gap for already-valid targets whose known runtime was absent from configuration. The executor now persists every known validated connection, not only newly recommended ones, while keeping existing target setup a no-op.

### Completion Notes

- Added `umem connect` without any call to project layout creation; an uninitialized project receives an actionable error and no `.umem/` mutation.
- The command reuses the same planner, one-confirmation contract, protected host setup, validation, JSON schema, and outcome renderer as `umem init`.
- Existing connections are checked and reused without calling host setup or rewriting their instruction target.
- `--agent <id>` supports known runtimes and generic Directed CLI agents. Generic agents use the registry portable profile and managed `AGENTS.md` fallback when available.
- `--unmanaged-mcp <host>` records an advanced Tier 3 plan with MCP-availability-only validation and an explicit pending step.
- Human failures point to `umem doctor`; healthy completion uses natural-work guidance.
- JSON exposes `persisted_connections`, and the persisted configuration mutation carries an audit reference without resetting `.umem/` state.

### Validation Results

- Focused onboarding, CLI, MCP, and parity suite — 69 passed.
- Full `uv run pytest -q` — 822 passed.
- `uv run ruff check .` — all checks passed.
- `uv run pyright` — 0 errors, 0 warnings.
- `git diff --check` — passed.

## File List

- `src/universal_memory/application/onboarding/agent_connections.py`
- `src/universal_memory/application/onboarding/execute_agent_connections.py`
- `src/universal_memory/application/onboarding/__init__.py`
- `src/universal_memory/infrastructure/config/runtime_connection_state.py`
- `src/universal_memory/infrastructure/config/__init__.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/onboarding/test_agent_connections.py`
- `tests/application/onboarding/test_execute_agent_connections.py`
- `tests/interfaces/cli/test_agent_connect_command.py`
- `tests/interfaces/cli/test_init_command.py`
- `tests/interfaces/mcp/test_compliance.py`
- `_bmad-output/implementation-artifacts/5-10-connect-additional-agents-after-initialization.md`

## Change Log

- 2026-07-31: Story artifact created and implementation started.
- 2026-07-31: Implemented idempotent post-init agent connection, generic Directed CLI and unmanaged MCP paths, pure JSON, and regression coverage; moved to review.
- 2026-07-31: Resolved BMAD review findings with protected runtime persistence, content-aware reuse, shared execution, plan safety enforcement, honest external-action states, and full regression coverage; returned to review.
- 2026-07-31: Closed final review follow-up by idempotently reconciling validated existing runtimes into configuration without rerunning host setup; 822-test suite passed and story returned to review.
- 2026-07-31: Independent final re-review approved the story; the integrated suite passed with 823 tests.
