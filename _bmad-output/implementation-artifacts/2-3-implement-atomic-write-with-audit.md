# Story 2.3: Implement Atomic Write with Auditing

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer implementing mutation use cases,  
I want a mandatory safe write pipeline,  
so that no adapter can persist data without validation, scanning, snapshots, and auditing.

## Acceptance Criteria

1. **Given** a use case that modifies persisted data,  
   **When** the mutation is executed,  
   **Then** the pipeline follows the order: validate input, scan for secrets, resolve scope and path, create snapshot, write atomically, and record audit log,  
   **And** the result returns an audit reference.

2. **Given** a CLI or MCP adapter,  
   **When** it executes a mutation,  
   **Then** it invokes the shared use case instead of writing directly to storage,  
   **And** tests prevent pipeline bypass by adapters.

3. **Given** a failure during atomic write,  
   **When** the pipeline captures the exception,  
   **Then** no partial file remains as the final state,  
   **And** a failure audit event is recorded when possible.

## Tasks / Subtasks

- [x] **Task 1: Write unit and contract tests (TDD) for `LocalAuditLogRepository`** (AC: 1, 3)
  - [x] Create test file `tests/infrastructure/security/test_local_audit_log_repository.py`.
  - [x] Test happy path: successfully record an audit event and verify that the corresponding entry is added in JSONL format in the `.umem/audit/events.jsonl` file.
  - [x] Test query/read scenario: filter audit records by scope (`AuditEventScope`) and retrieve by ID, validating correct ordering by timestamp.
  - [x] Test extreme concurrency: simulate multiple simultaneous writes from different threads/processes and validate that the file locking mechanism (`.lock`) guarantees integrity without overwriting or losing logs.
  - [x] Test resilient behavior when the log file is inaccessible or corrupted, ensuring appropriate typed errors.

- [x] **Task 2: Implement `LocalAuditLogRepository` in Infrastructure** (AC: 1)
  - [x] Create `src/universal_memory/infrastructure/security/local_audit_log_repository.py`.
  - [x] Implement the concrete class `LocalAuditLogRepository` inheriting from `AuditLogRepository` (from the port `src/universal_memory/domain/ports/audit_log_repository.py`).
  - [x] Implement append-only JSONL (JSON lines) writing, ensuring that each line is a valid JSON event with a formatted UTC `timestamp`.
  - [x] Implement a robust File Locking mechanism (using a lock similar to the snapshot with a temporary `.lock` file or concurrent `os.open`) to protect concurrent updates in `events.jsonl`.
  - [x] Export the new class in `src/universal_memory/infrastructure/security/__init__.py`.

- [x] **Task 3: Write unit and integration tests for the `SafeWriteUseCase` pipeline** (AC: 1, 2, 3)
  - [x] Create test file `tests/application/security/test_safe_write_use_case.py`.
  - [x] Test ideal scenario: validate input, pass through the secret scanner, create a snapshot of the old file (if it exists), atomically write the new content, and record a success audit event with result `"success"`.
  - [x] Test security block scenario: if the `SecretScannerPort` throws `SecretDetectedError`, validate that no physical write occurs, no snapshot is generated, and the error is propagated immediately.
  - [x] Test snapshot failure scenario: if the `SnapshotRepository` fails to create the backup with `SnapshotFailedError`, validate that the mutation aborts immediately without touching the original file.
  - [x] Test physical write failure scenario: simulate a disk write error (e.g., `OSError` or lack of space), ensure that no corrupted partial state is left on the disk, and validate that a failure audit event with result `"failure"` is persisted in the log.

- [x] **Task 4: Implement the Safe Pipeline Use Case (`SafeWriteUseCase`)** (AC: 1, 3)
  - [x] Create `src/universal_memory/application/security/safe_write_use_case.py`.
  - [x] Implement the `SafeWriteUseCase` class (or similar) receiving the ports `SecretScannerPort`, `SnapshotRepository`, and `AuditLogRepository` via dependency injection in the constructor.
  - [x] Implement the strict workflow:
    1. **Validation**: Verify input format/parameters.
    2. **Secret Scanning**: Execute `secret_scanner.scan(...)` before any changes.
    3. **Snapshot**: If the target file already exists, calculate its SHA-256 and save a snapshot before writing; if it does not exist, record it as a creation without prior physical backup (default hash).
    4. **Atomic Write**: Write the content to a temporary `.tmp` file in the same directory and rename it via `os.replace` to atomically replace the original file.
    5. **Audit**: In case of success, save a success `AuditEvent`; in case of physical write failure, clean up the temporary `.tmp` file, save a failure `AuditEvent`, and propagate the original exception.

- [x] **Task 5: Ensure parity and prevent bypass by adapters** (AC: 2)
  - [x] Create tests and validations to ensure that CLI (Typer) adapters and future MCP adapters invoke the `SafeWriteUseCase` use case to write memories/rules/skills instead of using direct writing via `pathlib` or filesystem hooks.
  - [x] Update references and document the mandatory use of the safe use case in adapters.

- [x] **Task 6: Quality Verification and Regression Testing** (AC: 1, 2, 3)
  - [x] Run the entire test suite of the project: `uv run pytest`.
  - [x] Validate formatting compliance and static analysis: `uv run ruff check .` and `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Audit bypass on success log write failure — Physical writing (`_atomic_write`) occurs before success audit logging (`_record_audit`). If the audit logging fails (e.g., disk full), an exception is thrown suggesting the entire operation failed, but the physical file on disk has already been modified, creating an unaudited state change and bypassing security compliance.
- [x] [Review][Decision] Write blocks by Secret Scanner are not audited in the log — When `secret_scanner.scan` detects secrets and throws `SecretDetectedError`, the use case aborts immediately and no lock/security failure audit is recorded to notify security teams of potential leakage attempts.
- [x] [Review][Patch] Risk of Stale Lock causing permanent Denial of Service (DoS) [src/universal_memory/infrastructure/security/local_audit_log_repository.py:25]
- [x] [Review][Patch] Catastrophic read failure due to corruption and concurrency risks [src/universal_memory/infrastructure/security/local_audit_log_repository.py:86]
- [x] [Review][Patch] Linear O(N) Full Table Scan on audit event reads and searches [src/universal_memory/infrastructure/security/local_audit_log_repository.py:57]
- [x] [Review][Patch] Vulnerable Path Traversal validation using backslashes (`\`) on POSIX [src/universal_memory/application/security/safe_write_use_case.py:96]
- [x] [Review][Patch] Fragility and blind spots in the AST-Guardrail test for adapters [tests/interfaces/test_adapter_mutation_guardrails.py:1]
- [x] [Review][Patch] Inconsistent timezone normalization in nested dictionaries [src/universal_memory/infrastructure/security/local_audit_log_repository.py:99]
- [x] [Review][Patch] Race Condition (TOCTOU) when reading original file for snapshot [src/universal_memory/application/security/safe_write_use_case.py:75]
- [x] [Review][Patch] Snapshot write failures abort mutation without recording failure audit [src/universal_memory/application/security/safe_write_use_case.py:77]
- [x] [Review][Patch] Leak of non-OSError exception causes temporary file leak and audit failure [src/universal_memory/application/security/safe_write_use_case.py:82]

## Dev Notes

- **Scope of this story**: Implement the robust local audit repository (`LocalAuditLogRepository`), the safe write pipeline use case (`SafeWriteUseCase`), and integrated resilience tests. Full CLI/MCP updates for viewing audit logs and listing snapshots belong to Story 2.4.
- **Atomic Write**: Writing to a temporary file followed by `os.replace` is essential to prevent corrupted files or inconsistent states in case of crashes or power failures during the process.
- **Audit Security**: Never record sensitive strings or detected secrets in any audit log, error metadata, or public messages. Only use safe metadata (IDs, timestamps, scope, etc.).
- **Guaranteed UTC**: Ensure all timestamps generated for audit logs and snapshots use timezone-aware UTC to prevent chronological inconsistencies.

### Project Structure Notes

- The concrete audit class must live in `src/universal_memory/infrastructure/security/local_audit_log_repository.py`.
- The safe pipeline use case must live in the application layer in `src/universal_memory/application/security/safe_write_use_case.py`.
- Unit tests must follow the mirrored structure in `tests/infrastructure/security/` and `tests/application/security/`.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 2, Story 2.3, FR22, FR23, FR24, FR25, FR26)
- `_bmad-output/planning-artifacts/architecture.md` (Security & Guardrails, Clean Architecture, Persistence Format, Mutation Pipeline)
- `_bmad-output/planning-artifacts/prd.md` (Secret & ENV Guardrails, Backup & Recovery guardrails)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (Relative paths, structured output)
- `_bmad-output/implementation-artifacts/2-1-implementar-scanner-de-segredos.md` (Learn-from reference)
- `_bmad-output/implementation-artifacts/2-2-criar-snapshot-antes-de-muta-o.md` (Learn-from reference)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

GPT-5 Codex

### Debug Log References

- 2026-05-26: target story resolved from "sprint-status.yaml": `2-3-implementar-escrita-at-mica-com-auditoria`.
- 2026-05-26: analyzed `sprint-status.yaml`, `epics.md`, `architecture.md`, `prd.md`, and `devex-interaction-spec.md`.
- 2026-05-26: inspected `src/universal_memory/domain/`, `src/universal_memory/infrastructure/`, `tests/`, and previous commits in the repository.
- 2026-05-26: defined the structure of Story 2.3 in Brazilian Portuguese with detailed TDD tasks for concrete JSONL audit repository with file locking and `SafeWriteUseCase` with physical atomic writing.
- 2026-05-26: executed RED phase with focused tests; failure expected due to the absence of `LocalAuditLogRepository` and `application.security`.
- 2026-05-26: implemented `LocalAuditLogRepository`, `SafeWriteUseCase`, command/result DTOs, and adapter static guardrail.
- 2026-05-26: final validations completed with `uv run pytest`, `uv run ruff check .`, and `uv run pyright`.

### Implementation Plan

- First implement contract tests for append-only JSONL auditing, scope querying, ID reads, concurrency with locking, and log corruption.
- Implement the local audit repository following the locking pattern already used in snapshots and UTC serialization in JSONL.
- Implement `SafeWriteUseCase` as a synchronous application layer use case, receiving the scanner, snapshots, and audit log via ports.
- Cover the mandatory workflow: validate relative path, scan content, create a snapshot, write via temporary file + `os.replace`, and audit success or physical failure.
- Add guardrail test to prevent direct writing in interface adapters.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Scope delimited to a concrete local audit repository in JSONL with file locking and a safe pipeline use case with physical atomic writing.
- Detailed TDD, UTC, log security against secret leaks, and CLI/MCP adapter bypass prevention guardrails.
- `LocalAuditLogRepository` implemented with `.umem/audit/events.jsonl`, append-only JSONL, locking via exclusive creation of `events.jsonl.lock`, timestamp-ordered read, and `StorageError` for typed failures.
- `SafeWriteUseCase` implemented with relative path validation, scanner before any write, previous state snapshot, atomic write with `.tmp`, and success/failure auditing.
- Interface guardrail added to detect direct mutation calls in adapters (`open`, `write_text`, `write_bytes`, `os.replace`/equivalents).
- Validations executed successfully: `uv run pytest` (`105 passed`), `uv run ruff check .`, `uv run pyright`.

### File List

- `_bmad-output/implementation-artifacts/2-3-implementar-escrita-at-mica-com-auditoria.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/security/__init__.py`
- `src/universal_memory/application/security/safe_write_use_case.py`
- `src/universal_memory/domain/__init__.py`
- `src/universal_memory/infrastructure/security/__init__.py`
- `src/universal_memory/infrastructure/security/local_audit_log_repository.py`
- `tests/application/security/test_safe_write_use_case.py`
- `tests/infrastructure/security/test_local_audit_log_repository.py`
- `tests/interfaces/test_adapter_mutation_guardrails.py`

### Change Log

- 2026-05-26: Implemented secure atomic write with local auditing and contract tests for the mandatory pipeline.
