# Story 5.1: Model Runtime Registry and Targets

Status: done

## Reopened Scope

This story was reopened because the previous implementation only covered the old hosts model (`codex`, `claude_code`) and instruction targets. The PRD, architecture, and epics were updated on 2026-05-31 to require a declarative Runtime Registry, support tiers, native instruction targets, and native skill targets.

## Story

As a maintainer configuring agent integrations,
I want a declarative runtime registry and target model,
so that each runtime has well-defined paths, capabilities, support tiers, instruction targets, and native skill targets.

**Requirements covered:** FR7, FR8, FR15.

## Acceptance Criteria

1. **Declarative runtime registry model**

   **Given** a declarative runtime registry,
   **When** the Pydantic models and adapters are defined,
   **Then** each runtime explicitly declares `runtime_id`, display name, support tier, default global and project paths, instruction targets, native skill targets, MCP configuration/method, validation strategy, mutation/rollback behavior, and known limitations.

2. **Minimum runtime coverage for the updated MVP**

   **Given** the updated multi-runtime requirements,
   **When** the registry is loaded,
   **Then** it includes Claude Code, OpenCode, and Codex/OpenAI-class as Tier 1,
   **And** includes Cursor and Antigravity as Tier 2,
   **And** maintains stable English/snake_case IDs for config, CLI JSON, and MCP.

3. **Shared targets ownership**

   **Given** the shared `agents_md` target,
   **When** multiple runtimes consume `AGENTS.md`,
   **Then** only the single writer target of `AGENTS.md` can write to the shared manifest,
   **And** consuming runtimes only reference or validate reads without independently duplicating or overwriting the file.

4. **Native skill targets**

   **Given** runtimes that natively consume skills or rules,
   **When** the registry declares runtime capabilities,
   **Then** each native skill target declares path, format, installation strategy, drift strategy, and rollback policy.

5. **Compatibility with existing code**

   **Given** projects already initialized with `[hosts] enabled = [...]`,
   **When** the new runtimes configuration is loaded,
   **Then** the implementation must define an explicit migration or replacement decision for the old key,
   **And** must not maintain two competing models without a clear contract.

## Tasks / Subtasks

- [x] Create or update domain models for `RuntimeAdapter`, `RuntimeRegistry`, `RuntimeTarget`, `InstructionTarget`, and `NativeSkillTarget`.
- [x] Implement declarative registry including `claude_code`, `opencode`, `codex`, `cursor`, and `antigravity` with correct tiers.
- [x] Update the code currently using `HostName`/`host_ids` to consume runtime IDs or register a controlled migration.
- [x] Ensure single-writer ownership for `AGENTS.md` in the new model.
- [x] Add domain/config tests for tiers, paths, targets, native skill targets, and stable IDs.
- [x] Update story internal documentation with any migration decision from `[hosts]` to `[runtimes]`.

### Review Findings

- [x] [Review][Patch] `sync_instructions` breaks after default `umem init` with complete Runtime Registry [src/universal_memory/application/host/sync_instructions_use_case.py:366] — resolved; legacy sync filters unsupported runtimes and operates only on syncable hosts.
- [x] [Review][Patch] Cursor/Antigravity bypass Pydantic validation with `InstructionTarget.model_construct()` [src/universal_memory/domain/entities/runtime.py:341] — resolved; generic targets now use validated `RuntimeInstructionTarget`.
- [x] [Review][Patch] Native skill target tests do not cover Antigravity despite the registry declaring the target [tests/application/skills/test_generate_skill.py:270] — resolved; coverage includes Antigravity's native target.

## Dev Notes

- The previous story was implemented as `5-1-modelar-hosts-e-alvos-de-instru-o.md` and was reopened because it did not cover OpenCode, Cursor, Antigravity, native skill targets, or Runtime Registry.
- Sources of truth: `_bmad-output/planning-artifacts/epics.md` Story 5.1, `_bmad-output/planning-artifacts/architecture.md` Architecture Patch 2, `_bmad-output/planning-artifacts/prd.md` FR7-FR8.
- Do not change `sprint-status.yaml` to `review` without implementing and verifying the new coverage.

## Dev Agent Record

### Debug Log

- 2026-06-01: RED tests added for Runtime Registry, tiers, native skill targets, single-writer of `AGENTS.md`, and migration `[hosts]` -> `[runtimes]`.
- 2026-06-01: `uv run pytest tests/domain/test_host.py tests/application/test_setup_project.py tests/infrastructure/config/test_toml_loader.py` failed initially due to the absence of `universal_memory.domain.entities.runtime`, confirming RED.
- 2026-06-01: Adjusted contract to allow read-only consumers of `AGENTS.md` via runtime target, keeping legacy `InstructionTarget` validating the actual writer.
- 2026-06-01: `uv run ruff check src tests` and `uv run pytest` passed.

### Completion Notes

- Created domain model `runtime.py` with `RuntimeId`, `RuntimeSupportTier`, `RuntimeTarget`, `NativeSkillTarget`, `RuntimeInstructionTarget`, `RuntimeAdapter`, `RuntimeRegistry`, and `default_runtime_registry()`.
- Declarative registry includes `claude_code`, `opencode`, `codex`, `cursor`, and `antigravity`; Claude Code/OpenCode/Codex as Tier 1; Cursor/Antigravity as Tier 2.
- Ownership of `AGENTS.md`: `codex` is the only `single_writer` writer; `opencode` references `AGENTS.md` as a read-only consumer in the runtime model.
- Migration decision: `[runtimes] enabled = [...]` is the new canonical key; `[hosts] enabled = [...]` remains only as a legacy entry. `load_config()` maps `[hosts]` to `[runtimes]` when the new key does not exist, `setup_project()` writes `[runtimes]`, `sync_instructions` reads/writes `[runtimes]`, and `update --migrate` materializes `[runtimes]` while preserving the legacy `[hosts]`.
- Maintained operational compatibility of the CLI/existing use cases that still expose `host_id`/`--hosts` names, treating these values as stable runtime IDs until a subsequent public renaming.

## File List

- `src/universal_memory/domain/entities/runtime.py`
- `src/universal_memory/domain/entities/__init__.py`
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/application/host/sync_instructions_use_case.py`
- `src/universal_memory/application/update/update_use_cases.py`
- `src/universal_memory/infrastructure/config/toml_loader.py`
- `tests/domain/test_host.py`
- `tests/application/test_setup_project.py`
- `tests/application/test_update_use_cases.py`
- `tests/infrastructure/config/test_toml_loader.py`
- `tests/interfaces/cli/test_init_command.py`
- `tests/interfaces/cli/test_update_command.py`
- `_bmad-output/implementation-artifacts/5-1-modelar-registro-de-runtimes-e-alvos.md`

## Change Log

- 2026-06-01: Implemented declarative Runtime Registry, controlled migration `[hosts]` -> `[runtimes]`, single-writer of `AGENTS.md`, and related domain/config/update/CLI tests.
