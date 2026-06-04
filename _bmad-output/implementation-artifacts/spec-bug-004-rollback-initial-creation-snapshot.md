---
title: 'BUG-004 - Initial creation snapshot rollback'
type: 'bugfix'
created: '2026-05-30'
status: 'done'
baseline_commit: '49edb1de5384942e4532784f918957e997b7d365'
context:
  - '{project-root}/docs/alpha-sandbox-test-plan.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `umem rollback` fails when the most recent snapshot represents the prior state of a file that did not exist yet, because the manifest registers the snapshot but there is no physical backup in `.umem/snapshots/files/<id>`. This blocks rollback immediately after the first memory mutation in a clean sandbox and leaves the fact active.

**Approach:** Enable rollback to correctly restore initial creation snapshots by removing the target file when the snapshot indicates that the prior state was the absence of the file. Preserve the normal path for snapshots with a physical backup and maintain success/failure auditing.

## Boundaries & Constraints

**Always:** Preserve SHA-256 integrity verification for snapshots with a physical backup; keep resolved paths within `project_root`; keep rollback atomic and audited; maintain compatibility with existing manifests when it is safe to distinguish initial creation.

**Ask First:** Any schema migration of the snapshots manifest, change in the CLI/MCP public contract, or decision to delete empty directories other than the target file.

**Never:** Ignore missing physical backup errors for snapshots that should have a copy; relax path traversal protection; remove failure auditing; fix BUG-005 or BUG-006 within this scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Initial creation | Target file did not exist, safe write created `.umem/memory/facts.jsonl`, snapshot has empty bytes hash and no physical backup | Rollback removes the target file or returns it to the absent state, returns success, and logs `success` audit | If the target became a directory or escaped the root, fails with a domain error and `failure` audit |
| Normal snapshot | Target file existed before the mutation and physical backup exists | Rollback reads the backup, validates the hash, and restores the prior bytes | Hash mismatch or missing backup continues to fail without overwriting the target |

</frozen-after-approval>

## Code Map

- `src/universal_memory/application/security/safe_write_use_case.py` -- Creates snapshots before safe writing; currently calculates a hash of `b""` when the target does not exist.
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py` -- Persists the manifest and physical copy; currently registers a snapshot without a physical file when the target does not exist.
- `src/universal_memory/application/security/rollback_use_case.py` -- Chooses the most recent snapshot and always attempts to read the physical backup before restoring.
- `src/universal_memory/domain/entities/snapshot.py` -- Snapshot model; possible location to explicitly represent whether the file existed before.
- `tests/application/security/test_rollback_use_case.py` -- Domain rollback, hash mismatch, and deleted target file coverage.
- `tests/infrastructure/security/test_local_snapshot_repository.py` -- Local repository coverage, including initial creation snapshot without a physical copy.
- `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- BUG-004 log to be updated after fix and verification.

## Tasks & Acceptance

**Execution:**
- [x] `src/universal_memory/domain/entities/snapshot.py` and related producers/consumers -- Securely represent whether the file existed before the snapshot, preferring a minimal change compatible with current manifests -- Prevents confusing an empty file with a non-existent file.
- [x] `src/universal_memory/application/security/rollback_use_case.py` -- Restore initial creation snapshots by removing the target file when appropriate; maintain backup reading and hashing for normal snapshots -- Fixes BUG-004 without relaxing integrity.
- [x] `src/universal_memory/infrastructure/security/local_snapshot_repository.py` -- Persist/load any new metadata needed without breaking existing manifests -- Keeps local snapshots usable.
- [x] `tests/application/security/test_rollback_use_case.py` and/or `tests/infrastructure/security/test_local_snapshot_repository.py` -- Add regression test for safe write of a non-existent file followed by rollback -- Ensures the alpha scenario does not fail again.
- [x] `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Update BUG-004 with the fix and executed commands -- Maintains alpha traceability.

**Acceptance Criteria:**
- Given a clean project where `umem remember "Fato antes do rollback." --scope project` created the first facts file, when `umem rollback --scope project --yes` executes, then the rollback returns success and the file returns to the prior absent or empty state without the fact active.
- Given a snapshot with a valid physical backup, when rollback executes, then the prior content is restored only after validating the SHA-256 hash.
- Given a normal snapshot whose physical backup is missing or corrupted, when rollback executes, then the operation fails and does not overwrite or remove the target.

## Spec Change Log

## Verification

**Commands:**
- `uv run pytest tests/application/security/test_rollback_use_case.py tests/infrastructure/security/test_local_snapshot_repository.py tests/interfaces/cli/test_rollback_command.py tests/interfaces/mcp/test_server.py::test_real_mcp_rollback_removes_file_created_by_first_remember` -- passed: 27 passed.
- Smoke CLI in isolated sandbox with `umem init`, `umem remember "Fato antes do rollback." --scope project`, `umem rollback --scope project --yes --format json\`, and `test ! -e .umem/memory/facts.jsonl` -- passed: rollback `ok=true` and file removed.
- `uv run pytest` -- passed: 395 passed.

## Suggested Review Order

**Rollback Without Physical Backup**

- Main entry point distinguishes between normal, new absent, and legacy safe snapshots.
  [`rollback_use_case.py:64`](../../src/universal_memory/application/security/rollback_use_case.py#L64)

- Removal requires an empty hash to avoid deleting an inconsistent snapshot.
  [`rollback_use_case.py:117`](../../src/universal_memory/application/security/rollback_use_case.py#L117)

- Legacy compatibility is limited to a missing field with an empty hash.
  [`rollback_use_case.py:126`](../../src/universal_memory/application/security/rollback_use_case.py#L126)

**Snapshot Metadata**

- Snapshot carries the semantics of prior existence with a compatible default.
  [`snapshot.py:28`](../../src/universal_memory/domain/entities/snapshot.py#L28)

- Safe write captures existence before registering the snapshot.
  [`safe_write_use_case.py:65`](../../src/universal_memory/application/security/safe_write_use_case.py#L65)

- Persisted snapshot receives the metadata along with the prior hash.
  [`safe_write_use_case.py:168`](../../src/universal_memory/application/security/safe_write_use_case.py#L168)

**Regressions**

- Tests cover new snapshot, legacy without field, and invalid hash.
  [`test_rollback_use_case.py:234`](../../tests/application/security/test_rollback_use_case.py#L234)

- Alpha CLI reproduction validates first mutation followed by rollback.
  [`test_rollback_command.py:93`](../../tests/interfaces/cli/test_rollback_command.py#L93)

- Real MCP reproduction validates initialize, remember, and rollback_scope.
  [`test_server.py:205`](../../tests/interfaces/mcp/test_server.py#L205)
