# Story 6.3: Generate Canonical Skill and Install in Native Targets

Status: done

## Reopened Scope

This story was reopened because the previous implementation covered the generation of the canonical skill in `.umem/skills/`, but did not cover installation/synchronization to native runtime directories, manual drift detection, nor the Keep/Overwrite prompt required by the updated PRD.

## Story

As a user who has approved a new skill,
I want the system to generate the canonical skill and install it in the native skill directories of the selected runtimes,
so that the capability is immediately usable by compatible agents without losing local customizations.

**Requirements covered:** FR20, FR31, FR32.

## Acceptance Criteria

1. **Canonical skill preserved as the source of truth**

   **Given** an approved skill,
   **When** the generation is executed,
   **Then** the system creates or updates the canonical skill under `.umem/skills/` with `SKILL.md`, `scripts/`, and `references/` as applicable,
   **And** this folder remains the source of truth, not the native targets.

2. **Installation in native skill targets**

   **Given** runtimes selected and active in the configuration,
   **When** the canonical skill is generated or synchronized,
   **Then** the system installs, copies, renders, or links the skill in the native skill targets declared by the adapters,
   **And** covers at least compatible targets for Claude Code, OpenCode, and Cursor when declared by the registry.

3. **Metadata and audit trail per target**

   **Given** a native installation,
   **When** the target is written,
   **Then** the system records the source skill ID, target runtime, relative path, canonical hash/version, timestamp, and audit reference.

4. **Manual drift protected**

   **Given** a native file that has diverged from the installed canonical version,
   **When** `umem update --skills` or automatic synchronization runs,
   **Then** the system detects the conflict before overwriting,
   **And** displays the warning in English: `Warning: Native target has manual changes. Overwriting it might break your current agent workflow. Keep local version or Overwrite with canonical library version? [Keep/Overwrite]`.

5. **Snapshot before overwrite**

   **Given** the user chooses to overwrite a native target with drift,
   **When** the write is applied,
   **Then** the system creates a backup snapshot before overwriting,
   **And** aborts without writing if the snapshot fails.

6. **Deactivation does not delete canonical by default**

   **Given** a skill installed in native runtimes,
   **When** the skill is deactivated,
   **Then** native targets are disabled/removed according to the adapter's policy,
   **And** the canonical skill in `.umem/skills/` is not deleted by default.

## Tasks / Subtasks

- [x] Integrate skill generation with Runtime Registry and native skill targets.
- [x] Implement canonical skill installer/synchronizer for native targets per runtime.
- [x] Record metadata per native installation, including runtime, path, hash, and audit reference.
- [x] Implement manual drift detection based on the previous canonical hash/version.
- [x] Implement Keep/Overwrite prompt in English and safe JSON/non-interactive mode.
- [x] Ensure snapshot before any native target overwrite.
- [x] Add tests for installation in `.claude/skills/`, `.opencode/skills/`, and `.cursor/rules/` according to available adapters.
- [x] Add tests for drift, Keep, Overwrite, snapshot failure, and deactivation without deleting the canonical skill.

### Review Findings

- [x] [Review][Patch] `umem update --skills` does not exist, so AC4 has no mandatory entry point [src/universal_memory/interfaces/cli/init_command.py:336] — resolved; `umem update --skills` synchronizes active skills with a safe default of `keep`.
- [x] [Review][Patch] `skills update` and MCP `update_skill` discard drift warnings and do not show Keep/Overwrite [src/universal_memory/interfaces/cli/init_command.py:2078] — resolved; warnings are preserved in CLI/MCP, and the human flow prompts for Keep/Overwrite when drift is detected.
- [x] [Review][Patch] Native installation copies only `SKILL.md` and loses applicable `scripts/`/`references/` [src/universal_memory/application/skills/native_skill_sync.py:60] — resolved; `sync_directory` replicates the allowed canonical tree.
- [x] [Review][Patch] Deactivation ignores the adapter's policy and always overwrites the target with a stub [src/universal_memory/application/skills/native_skill_sync.py:141] — resolved; native targets are removed according to the adapter's default policy, preserving the canonical skill.

## Dev Notes

- The previous story was implemented as `6-3-gerar-estrutura-agent-skills.md`; it remains a useful base for the canonical store, but does not satisfy FR31-FR32.
- This story depends on the reopened 5.1 for native skill target metadata and 5.6 for active runtimes persistence.
- Use the mandatory mutation pipeline: validate, secrets scan, resolve path/scope, snapshot, atomic write, audit log.

## Dev Agent Record

### Debug Log

- Loaded context for story 6-3 and confirmed that `sprint-status.yaml`, stories 5-1/5-6, and `_bmad-output/planning-artifacts/epics.md` should not be modified.
- Wrote focused tests prior to implementation for native installation, Keep/Overwrite drift, snapshot failure, and deactivation preserving canonical.
- Ran focused tests, `ruff`, and the full test suite after implementation.

### Completion Notes

- Implemented a shared native synchronizer with the Runtime Registry and reading of `runtimes.enabled` when configured.
- Skill generation now installs the canonical skill in declared native targets, records `native_installations` metadata, and keeps `.umem/skills/` as the source of truth.
- Manual drift is detected by the hash of the previously installed target; `keep` preserves the local version, `overwrite` uses `SafeWriteUseCase` with a mandatory snapshot before overwriting.
- The CLI adds an English Keep/Overwrite prompt for drift in the interactive flow; JSON and non-interactive modes remain safe by default with Keep.
- Deactivation marks the skill as ignored and disables registered native targets without deleting the canonical one.

## File List

- `src/universal_memory/application/skills/native_skill_sync.py`
- `src/universal_memory/application/skills/generate_skill.py`
- `src/universal_memory/application/skills/update_skill.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/skills/test_generate_skill.py`
- `tests/application/skills/test_update_skill.py`
- `tests/interfaces/cli/test_skills_generate.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_server.py`

## Change Log

- 2026-06-01: Implemented native skill installation/synchronization with metadata, drift protection, Keep/Overwrite prompt, mandatory snapshot, and full tests.
