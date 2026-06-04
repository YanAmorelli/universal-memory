# Story 2.2: Create Snapshot Before Mutation

Status: done

## Story

As a user who allows automatic changes,  
I want the system to create a local snapshot before any write,  
so that I can recover the previous state if an automatic change is undesired.

## Acceptance Criteria

1. **Given** an automatic mutation in memory, rule, skill, or instruction file,  
   **When** the pipeline resolves the write target,  
   **Then** a snapshot is created before the mutation,  
   **And** the manifest records the timestamp, scope, responsible action, relative path, and hash of the previous content.

2. **Given** a failure to create a snapshot,  
   **When** the mutation is requested,  
   **Then** the pipeline aborts before writing any data,  
   **And** returns `SnapshotFailedError`.

3. **Given** multiple snapshots in the same scope,  
   **When** the retention policy is applied,  
   **Then** at least the 5 most recent versions per scope are preserved,  
   **And** old versions are only removed after the new snapshot is confirmed.

## Tasks / Subtasks

- [x] **Task 1: Write contract and unit tests (TDD)** (AC: 1, 2, 3)
  - [x] Create infrastructure test file `tests/infrastructure/security/test_local_snapshot_repository.py`.
  - [x] Test happy path: create a snapshot of an existing file, verify that the file copy is saved in the snapshots subdirectory and the metadata is inserted into the JSON manifest correctly.
  - [x] Test failure scenario: simulate a physical write failure or disk permission error and validate if the repository aborts by raising `SnapshotFailedError`.
  - [x] Test retention scenario: generate more than 5 snapshots for the same scope (`project` or `global`) and ensure that only the 5 most recent are preserved in the manifest and that the physical files associated with the removed snapshots are cleaned up from disk.
  - [x] Test that the removal of old versions only occurs after the new snapshot is fully confirmed and written to the manifest (backup transaction guarantee).

- [x] **Task 2: Implement `LocalSnapshotRepository` in Infrastructure** (AC: 1, 3)
  - [x] Create the file `src/universal_memory/infrastructure/security/local_snapshot_repository.py`.
  - [x] Implement the concrete class `LocalSnapshotRepository` inheriting from `SnapshotRepository` (defined in `src/universal_memory/domain/ports/snapshot_repository.py`).
  - [x] Configure the class to accept the corresponding base data directory (e.g., `.umem/` for project scope and `~/.local/share/umem/` for global scope; updated by BUG-002).
  - [x] Use the canonical structure defined for storage:
    - The control manifest file: `.umem/snapshots/manifest.json` (or the equivalent in the global path).
    - The physical directory for backup copies: `.umem/snapshots/files/` (or the global counterpart).
  - [x] Implement the `write(self, entity: Snapshot)` method:
    - Locate the original file at the absolute path derived from `relative_path` starting from the root directory.
    - If the file exists, read its binary or text content, validate that its SHA-256 hash matches the hash provided in the `Snapshot` entity, and save the copy of the file to `.umem/snapshots/files/{entity.id}`.
    - If the original file does not exist (as it is a new file creation with no previous state), skip the physical copy but record the metadata in the manifest signaling the initial creation.
    - Update the `.umem/snapshots/manifest.json` file, adding the new serialized entity.
    - Execute the retention policy, keeping only the 5 most recent snapshots per scope and deleting the excess ones.
  - [x] Implement the `read(self, id: str) -> Snapshot` and `list(self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None) -> list[Snapshot]` methods:
    - Ensure that reads and listings correctly filter snapshots registered in the manifest in a robust and typed manner.

- [x] **Task 3: Safely export the new repository** (AC: 1)
  - [x] Update `src/universal_memory/infrastructure/security/__init__.py` to export `LocalSnapshotRepository`.
  - [x] Ensure that all domain imports are kept strictly clean (infrastructure knows the domain, but the domain never knows the infrastructure).

- [x] **Task 4: Quality Validation and Absence of Regressions** (AC: 1, 2, 3)
  - [x] Run the created tests: `uv run pytest tests/infrastructure/security/test_local_snapshot_repository.py`.
  - [x] Run the entire project test suite to ensure zero regression breakages: `uv run pytest`.
  - [x] Validate formatting and static analysis compliance using `uv run ruff check .` and `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Concurrent Race Condition in the manifest without File Locking — Both the `_load_snapshots()` read and the `_write_manifest()` write access the shared `manifest.json` file without any file locking mechanism (such as `fcntl`). If multiple processes attempt to record a snapshot concurrently, data overlap will occur, leading to loss of snapshot records and accumulation of orphaned physical copies.
- [x] [Review][Patch] Leak of temporary files (`.tmp`) of copies and manifest in case of physical write failure [src/universal_memory/infrastructure/security/local_snapshot_repository.py:84]
- [x] [Review][Patch] Propagation of `StorageError` instead of `SnapshotFailedError` and cascading failure in case of a corrupted manifest [src/universal_memory/infrastructure/security/local_snapshot_repository.py:83]
- [x] [Review][Patch] Pipeline state inconsistency if the post-physical-confirmation deletion of old snapshots fails [src/universal_memory/infrastructure/security/local_snapshot_repository.py:93]
- [x] [Review][Patch] Path Traversal vulnerability when reading source files outside the `project_root` [src/universal_memory/infrastructure/security/local_snapshot_repository.py:108]
- [x] [Review][Patch] Omission of `schema_version` validation when loading the manifest [src/universal_memory/infrastructure/security/local_snapshot_repository.py:104]
- [x] [Review][Patch] Risk of `TypeError` in chronological comparison sorting between Naive and Aware Datetimes [src/universal_memory/infrastructure/security/local_snapshot_repository.py:81]
- [x] [Review][Patch] Retention policy limited only to the altered mutation scope and retroactive expiration [src/universal_memory/infrastructure/security/local_snapshot_repository.py:151]

## Dev Notes

- **Scope of this story:** Create the snapshot repository and its concrete infrastructure (`LocalSnapshotRepository`). It is not within the scope of this story to integrate this into the general mutation pipeline (Story 2.3) or to create the listing CLI commands (Story 2.4); only the contracts and the robust local repository should be implemented and thoroughly tested.
- **Manifest atomic write pattern:** Writing to `.umem/snapshots/manifest.json` must be robust. It is recommended to perform an atomic write (write to an adjacent temporary file and rename) to avoid corrupting the manifest in case of interruption or mid-process failure.
- **UTC Guarantee:** All timestamps and datetimes must use timezone-aware UTC (`datetime.now(UTC)` or similar), respecting the existing validators in the `Snapshot` and `BaseEntity` models.

### Project Structure Notes

- The concrete repository must be created in `src/universal_memory/infrastructure/security/local_snapshot_repository.py`, in symmetry with the secrets scanner (`entropy_secret_scanner.py`).
- The `SnapshotRepository` port is already defined in `src/universal_memory/domain/ports/snapshot_repository.py`, and the tests in `tests/domain/test_ports.py` already guarantee compliance with its signature. Do not modify the abstract signatures of the port or the entity to avoid regressions in already passing tests.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 2, Story 2.2, FR25, FR26)
- `_bmad-output/planning-artifacts/architecture.md` (Backup & Recovery, Persistent Data Layout, Mutation Pipeline)
- `_bmad-output/planning-artifacts/prd.md` (Backup & Recovery guardrails)
- `src/universal_memory/domain/entities/snapshot.py`
- `src/universal_memory/domain/ports/snapshot_repository.py`
- `tests/domain/test_ports.py`
- `_bmad-output/implementation-artifacts/2-1-implementar-scanner-de-segredos.md` (Learn-from reference)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-26: Target story identified as `2-2-criar-snapshot-antes-de-muta-o` from `sprint-status.yaml` as the first pending story (backlog).
- 2026-05-26: Analyzed `epics.md`, `architecture.md`, `prd.md`, `snapshot.py`, and `snapshot_repository.py` to ensure absolute technical compliance.
- 2026-05-26: Detailed specification of the files to be modified and created, as well as TDD and Tref steps.
- 2026-05-26: Story started via `bmad-dev-story`; `sprint-status.yaml` and story moved to `in-progress`.
- 2026-05-26: RED tests created in `tests/infrastructure/security/test_local_snapshot_repository.py`; initially failed due to the absence of `LocalSnapshotRepository`.
- 2026-05-26: Implemented `LocalSnapshotRepository` with physical copy, JSON manifest, atomic write, read/list, and retention by scope.
- 2026-05-26: Validations run successfully: `uv run pytest tests/infrastructure/security/test_local_snapshot_repository.py`, `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- `LocalSnapshotRepository` implemented in infrastructure, inheriting from `SnapshotRepository`.
- Existing snapshots are copied to `.umem/snapshots/files/{id}` after validation of the SHA-256 hash provided by the entity.
- Manifest `.umem/snapshots/manifest.json` is written with atomic replacement and contains snapshots serialized by the domain model.
- New files without a previous state are recorded in the manifest without a physical copy.
- Retention keeps the 5 most recent versions per scope and only removes old files after the new manifest is confirmed.
- Copy failures, hash mismatches, and persistence issues abort the operation with `SnapshotFailedError` before registering the snapshot.
- Story validated and moved to `review`.

### File List

- `_bmad-output/implementation-artifacts/2-2-criar-snapshot-antes-de-muta-o.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/infrastructure/security/__init__.py`
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py`
- `tests/infrastructure/security/test_local_snapshot_repository.py`

### Change Log

- 2026-05-26: Implemented local snapshot repository for Story 2.2; status moved to `review`.
