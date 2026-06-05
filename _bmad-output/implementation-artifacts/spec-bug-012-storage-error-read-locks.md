---
title: 'BUG-012 - Avoid storage_error on read-only bootstrap commands'
type: 'bugfix'
created: '2026-06-05'
status: 'done'
baseline_commit: '5374baf37b98e53b9d076f7466da2fb59840fa85'
context:
  - '_bmad-output/implementation-artifacts/alpha-bug-log.md'
  - '_bmad-output/implementation-artifacts/deferred-work.md'
  - '_bmad-output/implementation-artifacts/spec-bug-002-global-xdg-umem-storage.md'
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** `umem context --scope project --format json` and `umem skills list --format json` can fail with `storage_error` during mandatory agent bootstrap even when the current operation is logically read-only. The reproduced failure is tied to repository reads acquiring JSONL lock files under global/project storage, which requires write access and can also mutate partial `.umem` layouts during inspection.

**Approach:** Make read paths for facts and latent skills non-mutating and tolerant of missing storage files/directories, while preserving exclusive locks for write/delete/purge operations. Add regression coverage proving read-only list/context behavior does not create lock files or directories in missing global storage.

## Boundaries & Constraints

**Always:** Keep write operations protected by the existing lock and SafeWrite paths; preserve global XDG data roots from BUG-002; preserve corrupt JSONL validation behavior where reads currently raise; use only relative paths in docs/specs.

**Ask First:** Any migration of legacy global storage, changes to public CLI/MCP payload contracts, or broad replacement of the repository locking strategy beyond read-only operations.

**Never:** Do not bypass SafeWrite for mutations; do not make corrupt active storage silently pass for latent skills; do not initialize or repair project layout from read-only commands.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Missing global facts | Repository reads all facts with no `~/.local/share/umem/memory/facts.jsonl` and no parent dir | Returns project facts plus empty global facts without creating global dirs or lock files | No `StorageError` |
| Missing global latent skills | Skills list reads all skills with no global latent skills file and no parent dir | Returns project skills or empty list without creating global dirs or lock files | No `StorageError` |
| Existing corrupt storage | Existing facts/latent skills JSONL contains invalid lines in paths that are actually present | Existing corrupt-line behavior is preserved | Typed `StorageError` where current contract requires it |
| Mutations | Fact or latent skill writes/deletes/purges run concurrently | Existing exclusive lock behavior remains in force | Existing lock acquisition `StorageError` remains |

</frozen-after-approval>

## Code Map

- `src/universal_memory/infrastructure/storage/local_fact_repository.py` -- Fact list/read currently calls `_lock` before reading, creating lock files and parent directories for read-only commands.
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py` -- Latent skill list/read currently calls `_lock` before reading, creating lock files and parent directories for read-only `skills list`.
- `src/universal_memory/application/memory/assemble_context_summary_use_case.py` -- `umem context` reads active facts/rules and writes the generated summary/audit.
- `src/universal_memory/application/skills/list_skills.py` -- `umem skills list` reads latent skills through the repository.
- `tests/infrastructure/storage/test_local_fact_repository.py` -- Add read-only no-lock regression for missing global facts.
- `tests/infrastructure/storage/test_local_latent_skill_repository.py` -- Add read-only no-lock regression for missing global latent skills.
- `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Add BUG-012 with fix and verification results.

## Tasks & Acceptance

**Execution:**
- [x] `src/universal_memory/infrastructure/storage/local_fact_repository.py` -- Remove lock acquisition from read-only fact loading and keep direct read tolerant of missing files -- Prevents read-only bootstrap from writing global lock files.
- [x] `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py` -- Remove lock acquisition from read-only latent skill loading and keep direct read tolerant of missing files -- Prevents `skills list` from writing global lock files.
- [x] `tests/infrastructure/storage/test_local_fact_repository.py` -- Add regression asserting global-scope reads with missing XDG storage return empty data and create no global directories/locks -- Protects the bootstrap failure mode.
- [x] `tests/infrastructure/storage/test_local_latent_skill_repository.py` -- Add equivalent regression for latent skills -- Protects the `umem skills list` failure mode.
- [x] `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Record BUG-012 as fixed/verified after checks -- Maintains alpha traceability.

**Acceptance Criteria:**
- Given missing global fact storage, when `LocalFactRepository.list()` reads both scopes, then it returns available project facts or an empty list without creating `memory/` or `*.lock` under the global XDG root.
- Given missing global latent skill storage, when `LocalLatentSkillRepository.list()` reads both scopes, then it returns available project skills or an empty list without creating `memory/` or `*.lock` under the global XDG root.
- Given fact or latent skill writes, when the storage file is updated, then the existing lock-based write path and SafeWrite audit/snapshot behavior continue to run.
- Given focal tests and relevant CLI smoke checks, when they run in the bugfix worktree, then read-only bootstrap commands no longer fail due to missing read locks.

## Spec Change Log

## Verification

**Commands:**
- `uv run pytest tests/infrastructure/storage/test_local_fact_repository.py tests/infrastructure/storage/test_local_latent_skill_repository.py` -- passed: 27 tests.
- `uv run pytest tests/application/memory/test_assemble_context_summary_use_case.py tests/application/skills/test_list_skills.py tests/interfaces/cli/test_skills_list.py` -- passed: 18 tests.
- `uv run pytest` -- passed: 489 tests.
- `uv --project /private/tmp/umem-worktrees/umem-storage-bugfix run umem context --scope project --format json` in an initialized sandbox with isolated HOME/XDG -- passed: `ok: true`.
- `uv --project /private/tmp/umem-worktrees/umem-storage-bugfix run umem skills list --format json` in an initialized sandbox with isolated HOME/XDG -- passed: `ok: true`.
- `find <sandbox-home>/.local/share/umem -name '*.lock' -print` -- passed: no UMEM lock files after read-only commands.

## Suggested Review Order

**Read-Only Storage**

- Facts now read without creating lock files or parent directories.
  [`local_fact_repository.py:295`](../../src/universal_memory/infrastructure/storage/local_fact_repository.py#L295)

- Latent skills mirror the non-mutating read path.
  [`local_latent_skill_repository.py:216`](../../src/universal_memory/infrastructure/storage/local_latent_skill_repository.py#L216)

**Regression Coverage**

- Missing global fact storage stays empty and non-mutating.
  [`test_local_fact_repository.py:159`](../../tests/infrastructure/storage/test_local_fact_repository.py#L159)

- Missing global skill storage stays empty and non-mutating.
  [`test_local_latent_skill_repository.py:212`](../../tests/infrastructure/storage/test_local_latent_skill_repository.py#L212)

**Traceability**

- BUG-012 documents reproduction, root cause, fix, and verification.
  [`alpha-bug-log.md:76`](alpha-bug-log.md#L76)
