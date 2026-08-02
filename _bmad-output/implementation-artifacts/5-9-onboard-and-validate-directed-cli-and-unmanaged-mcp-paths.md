# Story 5.9: Onboard And Validate Directed CLI And Unmanaged MCP Paths

Status: done

## Story

As a user connecting different agents to UMEM,
I want UMEM to find and connect the right agents with almost no configuration,
so that I can start working normally without understanding tiers or integration mechanics.

**Requirements covered:** FR7, FR8, FR36.

## Acceptance Criteria

1. `umem init` without runtime flags detects relevant workspace agents and recommends a safe project-scoped plan without requiring tier, path, MCP, installer, copy, or symlink choices.
2. A safe and unambiguous interactive plan uses at most one combined confirmation.
3. Native agents use the protected host path and directed-CLI agents use portable instructions or a future external skill installer resolved behind a port.
4. Directed-CLI readiness checks instruction presence, CLI availability, and a successful context read; unmanaged MCP readiness claims only MCP availability.
5. Only validated connections are reported ready, and successful human output ends with natural-work guidance.
6. Initialization succeeds when no agent is detected and provides an actionable later path.
7. JSON output is pure and reports detected agents, recommendations, tiers, channels, validation results, external actions, and pending manual steps.
8. Existing explicit runtime flags and non-interactive automation remain compatible.

## Tasks / Subtasks

- [x] Add a reusable, idempotent agent detection and connection planner.
- [x] Add a port for optional external Agent Skill distribution without invoking `npx skills` in this story.
- [x] Evolve zero-flag `umem init` to use detection and one safe confirmation.
- [x] Validate outcomes and render concise human and pure JSON results.
- [x] Preserve legacy runtime flags and automation payloads.
- [x] Add focused application and CLI tests before implementation.
- [x] Run focused and full validation.
- [x] Resolve review findings for content-aware readiness, injectable MCP availability, unsafe-plan blocking, honest external actions, and shared CLI/MCP initialization execution.

## Developer Context / Guardrails

- Sources: `_bmad-output/implementation-artifacts/spec-agent-support-evolution-tiers-and-mcp-fallback.md`, `_bmad-output/planning-artifacts/devex-interaction-spec.md`, and Story 5.9 in `_bmad-output/planning-artifacts/epics.md`.
- Do not edit the runtime registry in this story. Consume its public capability contract and remain compatible with the legacy registry during parallel implementation.
- Do not invoke `npx skills` directly. Model external distribution behind an application port and return a clean fallback for Story 6.13.
- Keep mutations project-scoped and routed through existing protected host setup paths.
- Keep all project paths in specs, docs, CLI payloads, and tests relative.
- Do not update `_bmad-output/implementation-artifacts/sprint-status.yaml`.

## Dev Agent Record

### Implementation Plan

- Define immutable connection candidate, action, plan, validation, and result contracts in the onboarding application package.
- Detect agents from project-scoped footprints and existing configuration without mutating files.
- Reuse the planner from both `init` and `connect`; keep explicit runtime flags as the automation override.
- Keep external skill installation behind a no-op/pending port until Story 6.13 provides the adapter.
- Extend CLI JSON and human renderers with outcome-oriented connection reporting.

### Debug Log

- BMAD review requested changes for persisted connections, content-aware readiness, real MCP validation, unsafe-plan blocking, external-action honesty, and shared initialization execution. Stories 5.9/5.10 were reopened for TDD corrections.
- Initial planner tests established typed registry detection, capability mapping, idempotency, explicit selection, and unavailable-installer fallback.
- The first full suite exposed legacy tests coupled to the old tier/index prompt and the smaller init JSON contract; those tests were migrated to outcome-oriented onboarding and the expanded DevEx keys.
- CLI/MCP parity initially failed because `initialize_project` lacked the connection-plan keys. The MCP adapter now emits the same semantic planning and validation shape.
- The mutation guardrail rejected string `.replace()` calls in the CLI adapter; agent-ID normalization was rewritten with `split`/`join`.
- Registry review removed false Agent Skill channels from named directed agents. The planner now sends those hosts to an honest action-required fallback while generic directed agents use the portable profile.
- Review follow-up centralized planning execution and validation in `ExecuteAgentConnectionsUseCase`; both CLI initialization and MCP `initialize_project` now consume it, while `umem connect` intentionally remains CLI-only per the architecture contract.
- Existing instruction files are accepted only when their managed block contains recognizable UMEM guidance. Tier 3 readiness now comes from an injectable MCP-availability port rather than a constant.
- Unsafe non-project plans are rejected before confirmation or mutation, including JSON, `--yes`, and non-interactive flows. Planned external `npx skills` actions remain pending unless an executor actually runs them; managed fallback is reported separately.

### Completion Notes

- Added a reusable connection planner that consumes typed `detection_signals` and capability fields from the runtime registry without redefining tier enums.
- `umem init` now detects relevant agents, presents one combined confirmation for the zero-flag interactive path, initializes memory even when declined or no agent is found, and reports only validated readiness.
- Human onboarding hides tier values, paths, MCP mechanics, external commands, and installer mechanics; JSON retains full capability and diagnostic detail.
- Tier 1 connections reuse existing protected host setup/check paths. Generic Tier 2 agents can use the protected `AGENTS.md` writer path, while named agents lacking a portable channel remain action required.
- Tier 3 can be recorded through the advanced unmanaged-MCP path and validates only MCP availability, never agent behavior.
- The Story 6.13 official skill distribution planner is consumed through an adapter that plans argv/environment/fallbacks but never executes the external command in this story.
- Legacy `--runtime` and `--hosts` automation remains supported and covered.
- Optional agent setup failures no longer roll back successful project initialization; the affected connection is reported as action required.

### Validation Results

- Focused onboarding, CLI, MCP, and parity suite — 69 passed.
- Full `uv run pytest -q` — 820 passed.
- `uv run ruff check .` — all checks passed.
- `uv run pyright` — 0 errors, 0 warnings.
- `git diff --check` — passed.

## File List

- `src/universal_memory/application/onboarding/agent_connections.py`
- `src/universal_memory/application/onboarding/execute_agent_connections.py`
- `src/universal_memory/application/onboarding/__init__.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/onboarding/test_agent_connections.py`
- `tests/application/onboarding/test_execute_agent_connections.py`
- `tests/interfaces/cli/test_agent_connect_command.py`
- `tests/interfaces/cli/test_init_command.py`
- `tests/interfaces/mcp/test_compliance.py`
- `_bmad-output/implementation-artifacts/5-9-onboard-and-validate-directed-cli-and-unmanaged-mcp-paths.md`

## Change Log

- 2026-07-31: Story artifact created and implementation started.
- 2026-07-31: Implemented capability-driven zero-flag onboarding, validation outcomes, external distribution port integration, MCP parity, and regression coverage; moved to review.
- 2026-07-31: Resolved BMAD review findings with shared application execution, content-aware readiness, injectable MCP availability, pre-mutation safety enforcement, honest external-action states, and full regression coverage; returned to review.
- 2026-07-31: Independent final review approved the story; the integrated suite passed with 823 tests.
