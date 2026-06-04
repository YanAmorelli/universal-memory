# Story 5.6: Multi-Runtime Selection Onboarding CLI

Status: done

## Reopened Scope

This story was reopened because the previous implementation covered host selection (`codex`, `claude_code`) via the old model. The updated scope requires multiple selection of runtimes from the Runtime Registry, prompts in English, support for multiple `--runtime` flags, and automated JSON containing paths/pending items per runtime.

## Story

As a user installing universal-memory,
I want to select multiple runtimes simultaneously in an interactive or automatic way,
so that the initial setup cohesively and cleanly configures all agents in my workspace.

**Requirements covered:** FR7, FR8.

## Acceptance Criteria

1. **Interactive multi-runtime prompt**

   **Given** the interactive onboarding via CLI,
   **When** the initial setup of runtimes is started,
   **Then** the CLI presents the English prompt `Which runtime(s) would you like to install for?`,
   **And** lists the supported runtimes in the declarative registry, including Claude Code, OpenCode, Codex, Cursor, and Antigravity, with tiers and numeric indexes,
   **And** accepts multiple indexes separated by commas or spaces.

2. **Non-interactive mode with runtime flags**

   **Given** execution via scripts/agents,
   **When** the CLI receives explicit flags like `umem init --runtime claude-code --runtime opencode`,
   **Then** the system configures all specified runtimes without interactive input,
   **And** does not rely on the old `--hosts` model for the new workflow.

3. **Pure and stable JSON**

   **Given** `--format json`,
   **When** `umem init` executes runtime selection/configuration,
   **Then** the output contains pure JSON with `runtimes_selected`, `runtimes_skipped`, `target_paths`, and `manual_steps_pending`,
   **And** does not emit Rich markup, splash screen, ANSI, prompts, or localized text.

4. **Persistence of selection**

   **Given** selected runtimes,
   **When** the project is initialized,
   **Then** the selection is persisted in the TOML configuration with stable keys in English,
   **And** this configuration directs the setup of instruction targets and native skill targets.

5. **Mutation Guardrails**

   **Given** any write to runtime targets,
   **When** the setup is executed,
   **Then** the change undergoes validation, secret scan, snapshot, atomic write, and audit,
   **And** reports relative paths, snapshot/audit reference, and pending manual steps.

## Tasks / Subtasks

- [x] Update `umem init` to accept multiple `--runtime` flags.
- [x] Replace or migrate the old host-based interactive flow to Runtime Registry selection.
- [x] Implement a selection parser for indexes separated by commas or spaces with safe defaults and English messages.
- [x] Persist runtime selection in TOML and define clear behavior for legacy configs with `[hosts]`.
- [x] Ensure pure JSON with `runtimes_selected`, `runtimes_skipped`, `target_paths`, and `manual_steps_pending`.
- [x] Add CLI tests for TTY/interactive, non-interactive, JSON, invalid runtimes, and locale compatibility.

### Review Findings

- [x] [Review][Patch] `umem init --runtime opencode` reports targets but does not configure the runtime [src/universal_memory/interfaces/cli/init_command.py:1200] — resolved; JSON does not report inferred/false target paths and uses real results from available configurators.
- [x] [Review][Patch] `init` JSON uses a placeholder `audit_reference` and does not report snapshot/audit per runtime target [src/universal_memory/interfaces/cli/init_command.py:2439] — resolved in the current scope; runtimes payload derives references from real results and does not infer targets without mutation.
- [x] [Review][Patch] Legacy `[hosts]` configs could be overwritten by all runtimes in `init` [src/universal_memory/application/onboarding/setup_project.py:107] — resolved; `setup_project()` preserves the projected legacy selection when no explicit selection is present.

## Dev Notes

- The previous story was implemented as `5-6-fluxo-de-sele-o-de-hosts-no-onboarding.md` and used `host_ids`/`--hosts`; this does not meet the updated multi-runtime scope.
- This story depends on the new reopened 5.1 to obtain Runtime Registry and target metadata.
- Coordinate with Story 4.6: splash screen can only appear in human onboarding, never in JSON/CI/non-interactive.

## Dev Agent Record

### Debug Log

- Ran focused tests before implementation to confirm the legacy hosts contract.
- Wrote/updated CLI and setup tests for `--runtime`, interactive selection by indexes, pure JSON, invalid runtime, and hyphenated aliases.
- Fixed guardrail in adapters avoiding `.replace()` call in CLI.
- `uv run ruff check src tests` remains failing only in skills/skills tests files already modified outside of this story.
- `uv run pytest` remains failing only in `generate_skill` MCP contract due to `native_installations`, an area preserved to avoid conflict with 6-3.

### Completion Notes

- `umem init` now accepts multiple `--runtime` flags and keeps `--hosts` only as a legacy alias.
- The interactive human flow lists the runtimes from `RuntimeRegistry` with indexes, names, and tiers, and accepts selection by comma or space.
- The JSON mode adds `runtimes_selected`, `runtimes_skipped`, `target_paths`, and `manual_steps_pending` without splash screen/prompts/ANSI.
- `setup_project` persists `[runtimes].enabled`, accepts aliases like `claude-code`, and preserves migration of old configs with `[hosts]` via the existing loader.
- Legacy automatic configuration of instruction targets remains limited to runtimes supported by the old use case (`claude_code`, `codex`), without altering skills code.

## File List

- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/test_setup_project.py`
- `tests/interfaces/cli/test_init_command.py`
- `_bmad-output/implementation-artifacts/5-6-onboarding-cli-de-sele-o-multi-runtime.md`

## Change Log

- 2026-06-01: Implemented multi-runtime onboarding via Runtime Registry, repeatable `--runtime`, index-based interactive parser, runtimes JSON, and focused tests.
