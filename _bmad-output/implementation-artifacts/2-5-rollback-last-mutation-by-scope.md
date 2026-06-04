# Story 2.5: Revert Last Mutation by Scope

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user recovering from an automatic change,  
I want to revert the last mutation by scope,  
so that I can quickly restore memories, rules, skills, or instruction files to their previous state.

## Acceptance Criteria

1. **Given** valid snapshots for a scope (`project` or `global`)  
   **When** the user requests a rollback of that scope  
   **Then** the system identifies the most recent snapshot applicable to that scope  
   **And** successfully restores the content of the original backup back to the destination file (using safe atomic write)  
   **And** logs a new audit event for the `rollback` action in the requested scope with result `success` and status `logged`.

2. **Given** that no snapshot exists for the requested scope  
   **When** the rollback is executed  
   **Then** the system aborts the operation and returns a typed domain error (`SnapshotFailedError`) with a clear message and an actionable recovery hint  
   **And** ensures that no project file is altered in any way.

3. **Given** a snapshot whose backup bytes are corrupted or have a SHA-256 hash incompatible with the hash originally recorded in the manifest  
   **When** the rollback attempts to restore it  
   **Then** the operation is immediately blocked (no changes are made to the original file)  
   **And** the system logs a failure audit event for the `rollback` action with result `failure` containing sufficient evidence of the integrity failure in the log without exposing any raw secrets  
   **And** throws a typed domain error (`SnapshotFailedError`).

4. **Given** a local offline development environment  
   **When** the user executes the rollback by scope  
   **Then** the rollback works robustly locally, without any external network connectivity  
   **And** completes in less than 1 minute on a local test project.

5. **Given** default interactive execution via the CLI (without the `--yes`/`-y` flag)  
   **When** the rollback command is triggered: `umem rollback --scope <scope>`  
   **Then** the system clearly displays to the human output the rollback details (target scope, ID and timestamp of the selected snapshot, the original action that caused the mutation, and the relative path of the affected file)  
   **And** displays an explicit confirmation question (interactive prompt `Deseja prosseguir com o rollback? [s/N]: `)  
   **And** performs the write only upon positive confirmation, safely cancelling in case of a negative response without altering files.

6. **Given** execution via the CLI with `--format json`  
   **When** the rollback is successful  
   **Then** the system emits on stdout only the standard JSON envelope with keys `"ok": true`, `"operation": "rollback"`, `"scope": "<scope>"` and, in `"data"`, the following payload:
   ```json
   {
     "ok": true,
     "operation": "rollback",
     "scope": "project",
     "data": {
       "scope": "project",
       "snapshot_reference": "uuid-do-snapshot-restaurado",
       "restored_paths": ["caminho/relativo/do/arquivo/restaurado"],
       "audit_reference": "uuid-do-evento-de-auditoria-do-rollback"
     },
     "warnings": []
   }
   ```

7. **Given** rollback failure under the `--format json` format  
   **When** the command fails or is aborted  
   **Then** the system emits the standard error JSON envelope with `"ok": false` and the corresponding error object mapped according to the specification, ensuring clean output without Rich ANSI colors.

## Tasks / Subtasks

- [x] **Task 1: Extend the Snapshot Repository Port** (AC: 1, 3)
  - [x] Add the abstract method `get_content(self, id: str) -> bytes` in the `SnapshotRepository` class in `src/universal_memory/domain/ports/snapshot_repository.py` to allow safe reading of the backup bytes associated with the snapshot ID.
  - [x] Implement the `get_content(self, id: str) -> bytes` method in `LocalSnapshotRepository` in `src/universal_memory/infrastructure/security/local_snapshot_repository.py`. It must load the file located at `self.files_root / id`. If the physical backup file does not exist, it must raise `StorageError`.

- [x] **Task 2: Write Unit Tests (RED) for the Rollback Use Case** (AC: 1, 2, 3, 4)
  - [x] Create the test file `tests/application/security/test_rollback_use_case.py`.
  - [x] Test success scenario: given multiple snapshots, sort by timestamp, select the most recent from the correct scope, read the backup, write to the destination file, and create the audit record with status `logged` (for successful rollback).
  - [x] Test failure scenario due to missing snapshot: ensure that an empty list results in a `SnapshotFailedError` being raised, without causing side effects on files.
  - [x] Test integrity failure scenario due to incompatible hash: simulate corrupted bytes in the physical backup file (generating a SHA-256 hash different from the one recorded in the `Snapshot` entity). Ensure that writing is blocked, raises `SnapshotFailedError`, and logs an audit event with `result="failure"` and status `failed`.
  - [x] Validate network independence (native offline behavior).

- [x] **Task 3: Implement the Rollback Use Case in the Application Layer** (AC: 1, 2, 3, 4)
  - [x] Create the `RollbackUseCase` class in `src/universal_memory/application/security/rollback_use_case.py` accepting in the constructor `project_root: Path`, `snapshot_repository: SnapshotRepository`, and `audit_log_repository: AuditLogRepository`.
  - [x] Define the `RollbackCommand` and `RollbackResult` data classes. The command must contain `scope: SnapshotScope`, `origin: str`, and `action: str` ("rollback").
  - [x] In the `execute(self, command: RollbackCommand) -> RollbackResult` method:
    - [x] List all snapshots of the provided scope.
    - [x] Raise `SnapshotFailedError` with a recovery hint if no snapshot is returned.
    - [x] Select the most recent snapshot based on chronological `timestamp`.
    - [x] Read the corresponding backup bytes by calling `snapshot_repository.get_content(snapshot.id)`.
    - [x] Calculate the SHA-256 of the read bytes and compare it with the registered `snapshot.hash`. If there is a discrepancy, log a failure audit event (`result="failure"`, `status="failed"`) and raise `SnapshotFailedError` reporting integrity breach.
    - [x] Write back to the original file (`self.project_root / snapshot.relative_path`) using the same safe atomic writing mechanism (writing to a `.tmp` file with uuid4 and subsequent `os.replace`) established in the `SafeWriteUseCase` to prevent file corruption in case of abrupt interruption.
    - [x] Log the new success audit event for the rollback (`result="success"`, `status="logged"`, `snapshot_reference=snapshot.id`).
    - [x] Return the `RollbackResult` containing the necessary references.
  - [x] Export `RollbackCommand`, `RollbackResult`, and `RollbackUseCase` in `src/universal_memory/application/security/__init__.py`.

- [x] **Task 4: Write Integration and CLI Tests (RED) for Rollback** (AC: 5, 6, 7)
  - [x] Create the test file `tests/interfaces/cli/test_rollback_command.py`.
  - [x] Test execution with the `--yes` / `-y` flag to validate the non-interactive flow (success and failure, checking human and JSON outputs).
  - [x] Test interactive confirmation flow with mocks for `builtins.input` returning `s` (Yes) and `n` (No).
  - [x] Ensure that `--format json` returns the exact wrapped DevEx structure without mixing ANSI/Rich.
  - [x] Ensure the return of the standard error envelope in JSON format for domain failures.

- [x] **Task 5: Implement the `rollback` Subcommand in the CLI Adapter** (AC: 5, 6, 7)
  - [x] Modify `src/universal_memory/interfaces/cli/init_command.py` to register the `rollback` subcommand with the `--scope`, `--format`, and `--yes` / `-y` arguments.
  - [x] Add UI handlers in the CLI command file:
    - [x] Get the list of snapshots and identify the candidate for rollback.
    - [x] If `--yes` or `-y` is not passed, display the concise and formatted prompt and safely capture user confirmation.
    - [x] Handle domain exceptions by mapping them to user-friendly codes and messages on the human console and in the JSON envelope.
  - [x] Register and integrate the dependency of `RollbackUseCase` in `src/universal_memory/bootstrap/cli.py`.

- [x] **Task 6: Final Quality Verification and Regressions** (AC: all)
  - [x] Execute the entire test suite with `.venv/bin/pytest`.
  - [x] Validate stylistic compliance and strict linting with `.venv/bin/ruff check .`.
  - [x] Validate type-checking without errors by running `.venv/bin/pyright`.

### Review Findings

- [x] [Review][Decision] Transactional inconsistency between physical file alteration and audit log registration — Physical file writing occurs before persisting the audit event in the log. If auditing fails (e.g. disk full), the rollback has already physically changed the file, causing transactional inconsistency in the use case.
- [x] [Review][Decision] Restored snapshot remains with 'created' status in persistence — The status of the restored snapshot is never updated to `SnapshotStatus.restored` post-rollback, leaving the enum unused and the snapshot listable as 'created'. If marked as `restored`, it cannot be used in new rollbacks, which affects business rules of multiple mutability.
- [x] [Review][Decision] Physical audit log lacks a field for persisting integrity failure evidence — AC 3 requires saving "sufficient evidence of the integrity failure in the log". The `AuditEvent` model does not support extra details or payload to store such data, requiring a change in the audit domain model.
- [x] [Review][Patch] Time zone discrepancy and sorting issues when selecting the most recent snapshot [src/universal_memory/bootstrap/cli.py:54]
- [x] [Review][Patch] Path Traversal vulnerability in the snapshot repository [src/universal_memory/infrastructure/security/local_snapshot_repository.py:88]
- [x] [Review][Patch] Hangs due to EOFError and KeyboardInterrupt in CLI human interaction [src/universal_memory/interfaces/cli/init_command.py:301]
- [x] [Review][Patch] Bypass of interactive rollback confirmation in JSON format without the --yes flag [src/universal_memory/interfaces/cli/init_command.py:298]
- [x] [Review][Patch] Permanent loss of special permissions of the destination file post-rollback [src/universal_memory/application/security/rollback_use_case.py:110]
- [x] [Review][Patch] Bypassed security validation on target Path due to TOCTOU and unresolved return [src/universal_memory/application/security/rollback_use_case.py:100]
- [x] [Review][Patch] Unprotected `StorageError` exception during backup read, without failure auditing [src/universal_memory/application/security/rollback_use_case.py:60]
- [x] [Review][Patch] Generic and incorrect 'recovery_hint' message in the JSON error envelope [src/universal_memory/interfaces/cli/init_command.py:503]
- [x] [Review][Patch] Generic 'BaseException' capture intercepting vital interpreter signals [src/universal_memory/application/security/rollback_use_case.py:78]
- [x] [Review][Patch] OOM (Out of Memory) risk due to full loading in memory for Hash calculation [src/universal_memory/application/security/rollback_use_case.py:60]
- [x] [Review][Patch] Test coverage gap for rollback when the original file has been deleted [tests/application/security/test_rollback_use_case.py:1]

## Dev Notes

- **Atomic Writing in Restoration:** Do not perform direct writing using `Path.write_bytes()`. Strictly follow the atomic write pattern of `SafeWriteUseCase` (creating a temporary file in the same destination directory and performing atomic replacement via `os.replace`), preventing partial failures that would leave the final file empty or corrupted in case of a process crash.
- **Port / Adapters:** The backup file reading logic belongs to the infrastructure layer (`LocalSnapshotRepository`), not the use case. The use case accesses only the port abstraction (`SnapshotRepository.get_content`).
- **Snapshot Integrity:** It is vital to perform the SHA-256 check on the physical backup file before any writing to the project's destination file to maintain the security guarantee of rollback.
- **Rich Format:** Human messages must be elegant using Rich's default terminal, but `--format json` must completely deactivate additional printing and return strict JSON.

### Project Structure Notes

- New `RollbackUseCase` class in `src/universal_memory/application/security/rollback_use_case.py`.
- New unit test file for the use case in `tests/application/security/test_rollback_use_case.py`.
- New CLI test file in `tests/interfaces/cli/test_rollback_command.py`.

### References

- `_bmad-output/planning-artifacts/epics.md#Story 2.5` (Acceptance criteria for rollback by scope)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md#umem rollback` (CLI interface specification, JSON envelope, and confirmation contract)
- `src/universal_memory/domain/ports/snapshot_repository.py` (Snapshot port to be extended)
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py` (Concrete snapshot repository)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- 2026-05-26: Story `2-5-reverter-ltima-muta-o-por-escopo` identified from `sprint-status.yaml` as the next pending story (backlog).
- 2026-05-26: In-depth analysis of the `SnapshotRepository` port contract and the rollback flow defined in `devex-interaction-spec.md`.
- 2026-05-26: Structure of detailed tasks following the TDD methodology (RED unit tests first).
- 2026-05-26: RED of the use case confirmed with `ModuleNotFoundError` for `rollback_use_case` before implementation.
- 2026-05-26: Focused tests for the use case, port, and repository passed after initial implementation.
- 2026-05-26: RED of the CLI confirmed with parser failures for command `rollback` before implementation of the adapter.
- 2026-05-26: Complete suite, ruff, and pyright executed successfully before marking for review.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented `SnapshotRepository.get_content` and concrete physical backup byte reading in `LocalSnapshotRepository`, raising `StorageError` for a missing file.
- Implemented `RollbackUseCase` with selection of the most recent snapshot by scope, SHA-256 validation prior to writing, atomic restoration via temporary file and `os.replace`, success auditing, and integrity failure auditing.
- Implemented `umem rollback` in the CLI with `--scope`, `--format`, `--yes`/`-y`, human preview of the selected snapshot, interactive confirmation, and clean JSON envelopes for success/failure.
- Validated with `.venv/bin/pytest` (129 passed), `.venv/bin/ruff check .` (passed) and `.venv/bin/pyright` (0 errors).

### File List

- `_bmad-output/implementation-artifacts/2-5-reverter-ltima-muta-o-por-escopo.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/security/__init__.py`
- `src/universal_memory/application/security/rollback_use_case.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/domain/ports/snapshot_repository.py`
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/security/test_list_snapshots_use_case.py`
- `tests/application/security/test_rollback_use_case.py`
- `tests/application/security/test_safe_write_use_case.py`
- `tests/domain/test_ports.py`
- `tests/infrastructure/security/test_local_snapshot_repository.py`
- `tests/interfaces/cli/test_rollback_command.py`

### Change Log

- 2026-05-26: Implemented rollback by scope with integrity validation, atomic writing, auditing, and CLI adapter; story moved to `review`.
