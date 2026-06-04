# Story 2.4: List Audit Log and Snapshots

Status: done

## Story

As a user auditing automatic changes,  
I want to query audit events and available snapshots,  
so that I understand what was changed, when, by which action, and how I can recover the previous state.

## Acceptance Criteria

1. **Given** existing events in `.umem/audit/events.jsonl`
   **When** the user queries the audit log via use case or CLI
   **Then** the system lists the timestamp, action, scope, origin, result, and snapshot reference when it exists
   **And** the query can be performed in fewer than 2 commands from the project directory (e.g. `umem audit list`)
   **And** with `--format json`, it returns pure JSON with `events[]` containing `timestamp`, `action`, `scope`, `origin`, `result`, `snapshot_reference`, and `audit_reference`
   **And** the output follows the specification defined in `_bmad-output/planning-artifacts/devex-interaction-spec.md`

2. **Given** existing snapshots in `.umem/snapshots/`
   **When** the user lists snapshots
   **Then** the system shows timestamp, scope, origin, responsible action, relative path, and hash
   **And** the human-readable output is legible and the structured output is suitable for future automation
   **And** with `--format json`, it returns pure JSON with `snapshots[]` containing `timestamp`, `scope`, `origin`, `action`, `relative_path`, `hash`, and `manifest_path`

3. **Given** there are no events or snapshots
   **When** the user executes the queries
   **Then** the system explicitly returns an empty state
   **And** does not treat the absence of data as an error
   **And** with `--format json`, it returns empty lists in `events` or `snapshots`, without mixed Rich/ansi text

## Tasks / Subtasks

- [x] **Task 1: Write unit tests (RED) for the query Use Cases** (AC: 1, 2, 3)
  - [x] Create `tests/application/security/test_list_audit_log_use_case.py` covering the event listing with and without scope filtering.
  - [x] Create `tests/application/security/test_list_snapshots_use_case.py` covering the snapshot listing with and without scope and status filtering.
  - [x] Ensure that both use cases return empty lists if data does not exist, without raising exceptions.

- [x] **Task 2: Implement the query Use Cases in the Application Layer** (AC: 1, 2, 3)
  - [x] Create `src/universal_memory/application/security/list_audit_log_use_case.py` containing the `ListAuditLogUseCase` class that uses `AuditLogRepository`.
  - [x] Create `src/universal_memory/application/security/list_snapshots_use_case.py` containing the `ListSnapshotsUseCase` class that uses `SnapshotRepository`.
  - [x] Export both use cases and their respective commands/results in `src/universal_memory/application/security/__init__.py`.

- [x] **Task 3: Write unit and integration tests (RED) for the CLI** (AC: 1, 2, 3)
  - [x] Create `tests/interfaces/cli/test_list_commands.py` to cover the execution of `umem audit list` and `umem snapshots list` in both human and JSON formats.
  - [x] Test scenarios with a test database containing multiple events and snapshots, ensuring appropriate chronological ordering.
  - [x] Test empty state scenarios (when there are no events or snapshots), validating that the JSON output contains empty arrays.

- [x] **Task 4: Implement subparsers and handlers in the CLI Adapter** (AC: 1, 2)
  - [x] Modify `src/universal_memory/interfaces/cli/init_command.py` to add subparsers for `audit` and `snapshots` with the `list` action.
  - [x] Add support for the `--format` (human or json) argument and the optional `--scope` (project or global) filter in the listing commands.
  - [x] Integrate dependency injection to inject `LocalAuditLogRepository` and `LocalSnapshotRepository` into the use cases inside `bootstrap/cli.py` and pass execution handlers cleanly.

- [x] **Task 5: Ensure strict compliance with DevEx Interaction Specification** (AC: 1, 2, 3)
  - [x] Ensure that `--format json` returns the standard success envelope from `devex-interaction-spec.md` (`"ok": true, "operation": "audit", "scope": "project", "data": {"events": [...]}, "warnings": []}` and `"operation": "snapshots"`, respectively).
  - [x] Make sure the `human` formatting is concise and clean.
  - [x] Handle data absence by returning a clear, friendly message in the human-readable output (e.g., "No audit events found.") and without mixing Rich markup with pure JSON output under `--format json`.

- [x] **Task 6: Final quality verification and regressions** (AC: 1, 2, 3)
  - [x] Run the entire test suite using `.venv/bin/pytest`.
  - [x] Ensure clean linting by running `.venv/bin/ruff check .`.
  - [x] Ensure strict typing without errors by running `.venv/bin/pyright`.

## Dev Notes

- **Scope of this story:** Total focus on reading and displaying data in structured and human-readable formats. No mutations or writes should occur in these commands.
- **Architectural Coupling:** CLI calls application use cases, which access repositories (ports in the domain, implemented in infrastructure). Dependency injection must be centralized in the Composition Root (`src/universal_memory/bootstrap/cli.py`).
- **Secrets Security:** Even though these are read operations, ensure that paths or sensitive configuration data are never exposed and that no part of the metadata strings in audits contains raw secrets.

### Project Structure Notes

- Use Cases must reside in the `src/universal_memory/application/security/` folder.
- Tests must be structured in `tests/application/security/` and `tests/interfaces/cli/`.
- Follow the snake_case naming convention for JSON properties.

### References

- `_bmad-output/planning-artifacts/epics.md#Story 2.4` (Acceptance criteria for listing audit log and snapshots)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md#umem audit list` and `umem snapshots list` (JSON output envelope, data format)
- `src/universal_memory/domain/ports/audit_log_repository.py` (Audit Port signature)
- `src/universal_memory/domain/ports/snapshot_repository.py` (Snapshot Port signature)
- `src/universal_memory/infrastructure/security/local_audit_log_repository.py`
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-26: Story `2-4-listar-auditoria-e-snapshots` identified from `sprint-status.yaml` as the next pending story (backlog).
- 2026-05-26: Deep analysis of the `AuditLogRepository` and `SnapshotRepository` port contracts, as well as the `devex-interaction-spec.md` specifications.
- 2026-05-26: Structuring of detailed tasks following TDD methodology (RED unit tests first).
- 2026-05-26: RED confirmed with import failures for the non-existent use cases.
- 2026-05-26: GREEN confirmed with 12 focused tests passing for use cases and CLI.
- 2026-05-26: Full regression confirmed with 118 passing tests; clean `ruff` and `pyright`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented `ListAuditLogUseCase` and `ListSnapshotsUseCase` with ordered query DTOs and filters by scope/status.
- Added commands `umem audit list` and `umem snapshots list` with concise human-readable output and pure JSON in the DevEx envelope.
- Snapshots now load `origin` with an `unknown` fallback for legacy data, and `SafeWriteUseCase` persists the origin of new mutations.
- Configured `pyright` to use `.venv`, maintaining type checking executable by the command required by the story.
- Executed validations: `.venv/bin/pytest` (118 passed), `.venv/bin/ruff check .` (passed), `.venv/bin/pyright` (0 errors).

### File List

- `_bmad-output/implementation-artifacts/2-4-listar-auditoria-e-snapshots.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `pyproject.toml`
- `src/universal_memory/application/security/__init__.py`
- `src/universal_memory/application/security/list_audit_log_use_case.py`
- `src/universal_memory/application/security/list_snapshots_use_case.py`
- `src/universal_memory/application/security/safe_write_use_case.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/domain/entities/snapshot.py`
- `src/universal_memory/infrastructure/security/local_audit_log_repository.py`
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/security/test_list_audit_log_use_case.py`
- `tests/application/security/test_list_snapshots_use_case.py`
- `tests/interfaces/cli/test_list_commands.py`
- `tests/interfaces/test_adapter_mutation_guardrails.py`

### Change Log

- 2026-05-26: Implemented story 2.4 with audit log/snapshot listing, CLI JSON/human contracts, and complete validations.

### Review Findings

- [x] [Review][Patch] ValidationError not caught in CLI [src/universal_memory/interfaces/cli/init_command.py:653]
- [x] [Review][Patch] Duplication of the helper _format_utc [src/universal_memory/application/security/list_audit_log_use_case.py:264]
- [x] [Review][Patch] Coupling of manifest_path in the application layer [src/universal_memory/application/security/list_snapshots_use_case.py:286]
- [x] [Review][Defer] Static STALE_LOCK_SECONDS of 10.0 seconds [src/universal_memory/infrastructure/security/local_audit_log_repository.py:34] — deferred, pre-existing
- [x] [Review][Defer] Concurrent audit log read without lock [src/universal_memory/infrastructure/security/local_audit_log_repository.py:102] — deferred, pre-existing
