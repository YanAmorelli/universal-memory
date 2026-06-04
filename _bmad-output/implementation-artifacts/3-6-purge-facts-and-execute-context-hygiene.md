# Story 3.6: Purge Facts and Execute Context Hygiene

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user maintaining a clean memory,
I want to archive, purge, and sanitize short-term facts,
so that obsolete context does not degrade future agent decisions.

## Acceptance Criteria

1. **Given** Short Term Memory facts with states `active`, `stale`, `archived`, and `purged`  
   **When** context hygiene is executed after task completion or explicit command  
   **Then** obsolete project facts are marked as `stale` or `archived` before deletion  
   **And** permanent purging only occurs when the user explicitly requests a purge.

2. **Given** a specific fact selected for purging  
   **When** the user confirms the removal  
   **Then** the fact no longer appears in queries and default listings  
   **And** the change passes through the secure mutation pipeline and records an audit log.

3. **Given** an entire base selected for purging  
   **When** the operation is executed  
   **Then** the system applies the scope correctly and avoids removing global data when the user only requested project scope  
   **And** returns a summary of the affected items.

4. **Given** previously archived facts  
   **When** the user executes a diagnostic query  
   **Then** the system can list archived items with lifecycle metadata  
   **And** keeps purged facts out of the active results.

## Tasks / Subtasks

- [x] **Task 1: Develop the Use Cases `PurgeFactUseCase` and `ContextHygieneUseCase`** (AC: 1, 2, 3)
  - [x] Create the file `src/universal_memory/application/memory/purge_fact_use_case.py`.
  - [x] Define the DTOs `PurgeFactCommand` (with fields `id: str | None`, `scope: FactScope | None`, `origin: str = "cli"`) and `PurgeFactResult` (with fields `purged_count: int`, `affected_ids: list[str]`, `audit_reference: str`).
  - [x] Create the use case `PurgeFactUseCase` receiving `fact_repository: FactRepository` in the constructor.
  - [x] Implement the logic of `PurgeFactUseCase`:
    - If `id` is provided: read the fact via `fact_repository.read(id)`. If it does not exist, raise `FactNotFoundError`. If it exists, physically remove it via `fact_repository.purge(id)`.
    - If `scope` is provided: list all facts in that scope using `fact_repository.list(scope=scope)` and call `fact_repository.purge(f.id)` for each one.
    - If neither `id` nor `scope` is provided, raise `ValidationFailedError` ("Deve ser fornecido um id de fato ou um escopo para purga.").
    - Return the number of items purged and the audit reference if applicable.
  - [x] Create the file `src/universal_memory/application/memory/context_hygiene_use_case.py`.
  - [x] Define the DTOs `ContextHygieneCommand` (with field `scope: FactScope`) and `ContextHygieneResult` (with fields `stale_count: int`, `archived_count: int`, `audit_reference: str`).
  - [x] Create the use case `ContextHygieneUseCase` receiving `fact_repository: FactRepository` in the constructor.
  - [x] Implement the logic of `ContextHygieneUseCase`:
    - Filter project facts (Short Term Memory).
    - Transition of obsolete states:
      - Facts with `FactStatus.active` are marked as `FactStatus.stale`.
      - Facts with `FactStatus.stale` are marked as `FactStatus.archived`.
      - Facts with `FactStatus.archived` remain unchanged.
      - For each modified fact, update the repository by calling `fact_repository.write(fact)`.
    - Return the count of transitions performed.

- [x] **Task 2: Export new use cases in the memory package**
  - [x] Update `src/universal_memory/application/memory/__init__.py` to export `PurgeFactUseCase`, `PurgeFactCommand`, `PurgeFactResult`, `ContextHygieneUseCase`, `ContextHygieneCommand`, `ContextHygieneResult`.

- [x] **Task 3: Develop the new CLI commands under the `facts` parser** (AC: 1, 2, 3, 4)
  - [x] Update `src/universal_memory/interfaces/cli/init_command.py`:
    - Add the group parser `facts` in `_build_parser` (e.g., `facts_parser = subparsers.add_parser("facts", help="Gerenciar fatos de memoria")` and `facts_subparsers = facts_parser.add_subparsers(dest="facts_command")`).
    - Add subcommand `list`:
      - Arguments `--scope` (options `project`, `global`, default `None`).
      - Arguments `--status` (options `active`, `stale`, `archived`, `purged`, default `None`).
      - Flag `--format` (`human` or `json`, default `human`).
    - Add subcommand `purge`:
      - Arguments `--id` (specific fact id) and `--scope` (scope for batch purge), mutually exclusive or validated at runtime.
      - Flag `--yes` / `-y` to skip interactive confirmation.
      - Confirmation logic:
        - For `human` format (without `-y`): display detailed purge summary (scope, ID, permanent data loss) and prompt `input("Confirmar purga permanente? [y/N]: ")`. Abort if denied.
        - For `json` format (without `-y`): abort with error `SnapshotFailedError` / `ValidationFailedError` explaining that `--yes` is mandatory in JSON mode.
    - Add subcommand `hygiene`:
      - Flag `--format` (`human` or `json`).
    - Implement the CLI handlers:
      - `_run_facts_list` orchestrating the `ListFactsUseCase`.
      - `_run_facts_purge` orquestrating the `PurgeFactUseCase` with standard prompts and envelopes.
      - `_run_facts_hygiene` orchestrating the `ContextHygieneUseCase`.

- [x] **Task 4: Register the commands in the Bootstrap** (AC: 1)
  - [x] Modify `src/universal_memory/bootstrap/cli.py` to inject `PurgeFactUseCase` and `ContextHygieneUseCase` into the CLI main build.
  - [x] Pass the correct dependencies of real repositories in the bootstrap.

- [x] **Task 5: Write Unit and Integration Test Suite** (AC: 1, 2, 3, 4)
  - [x] Create unit tests for the use cases:
    - `tests/application/memory/test_purge_fact_use_case.py` covering purge by id, batch purge by scope, parameter validations, and behavior with repository.
    - `tests/application/memory/test_context_hygiene_use_case.py` covering the state machine (active -> stale -> archived), updates in the repository, and counting.
  - [x] Create integration tests for the CLI interface:
    - `tests/interfaces/cli/test_facts_commands.py` exhaustively testing `umem facts list`, `umem facts purge` (flow with simulated interactive prompt using `monkeypatch`, flow with `--yes`, JSON mode), and `umem facts hygiene`.
    - Ensure that the JSON format outputs comply with the standard success and error envelopes described in `devex-interaction-spec.md`.

- [x] **Task 6: Validation of Style, Types, and Full Regression**
  - [x] Run `uv run pytest` and achieve 100% success.
  - [x] Run `uv run ruff check .` for style validation.
  - [x] Run `uv run pyright` for static typing validation.

### Review Findings

- [x] [Review][Decision] Default listing behavior hides facts with 'stale' status — The 'umem facts list' command filters by default by 'active' status, hiding 'stale' facts. Resolved: Current behavior kept (only active by default).
- [x] [Review][Patch] Sequential loops in batch generate I/O overhead and audit logs [src/universal_memory/application/memory/context_hygiene_use_case.py:28-42]
- [x] [Review][Patch] Lack of combined validation for 'id' and 'scope' parameters [src/universal_memory/application/memory/purge_fact_use_case.py:27-28]

## Dev Notes

- **Mutation Security:** The fact repository `LocalFactRepository.purge` uses `_write_facts_unlocked`, which delegates to `SafeWriteUseCase` if configured. Therefore, every persisted batch or individual change automatically passes through snapshots and compliance audit logs.
- **Scope Isolation:** In batch purging by scope, ensure that the `FactRepository.list` query filters strictly by the requested scope. Deleting a `project` scope must never interfere with the global file in `~/.umem/`.
- **Hygiene State Machine:**
  - `active` -> `stale`
  - `stale` -> `archived`
  - Archived facts are not modified or exposed in listings without explicit filtering, but they can be actively retrieved via `facts list --status archived` (AC 4).
  - Purges physically remove the line from the JSONL file, leaving it out of both active and historical data.

### Project Structure Notes

- The use case `PurgeFactUseCase` must reside in: `src/universal_memory/application/memory/purge_fact_use_case.py`.
- The use case `ContextHygieneUseCase` must reside in: `src/universal_memory/application/memory/context_hygiene_use_case.py`.
- Tests must reside in:
  - `tests/application/memory/test_purge_fact_use_case.py`
  - `tests/application/memory/test_context_hygiene_use_case.py`
  - `tests/interfaces/cli/test_facts_commands.py`

### References

- [PRD: FR5, FR6](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md#L317-L318)
- [Architecture: Context Hygiene Lifecycle](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L817-L827)
- [Architecture: CLI to MCP Parity Matrix](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L695-L710)
- [DevEx Interaction Spec: Confirmation Contract](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md#L73-L92)
- [Local Fact Repository](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/infrastructure/storage/local_fact_repository.py#L217-L230)
- [List Facts Use Case](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/memory/list_facts_use_case.py)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest tests/application/memory/test_purge_fact_use_case.py tests/application/memory/test_context_hygiene_use_case.py tests/interfaces/cli/test_facts_commands.py` -> 13 passed
- `uv run pytest` -> 192 passed
- `uv run ruff check .` -> All checks passed
- `uv run pyright` -> 0 errors, 0 warnings, 0 information

### Completion Notes List

- Implemented `PurgeFactUseCase` and `ContextHygieneUseCase` with DTOs, command validation, purge by id/scope, and transitions `active -> stale` and `stale -> archived`.
- Added commands `umem facts list`, `umem facts purge`, and `umem facts hygiene` with human/json output, mandatory confirmation for interactive purge, and requirement of `--yes` in JSON mode.
- Bootstrap now composes real fact repository with `SafeWriteUseCase`, secrets scanner, snapshots, and auditing for purge/hygiene mutations.
- Added unit and integration coverage for purge, hygiene, diagnostic listing of archived facts, scope isolation, and JSON envelopes.

### File List

- `src/universal_memory/application/memory/context_hygiene_use_case.py`
- `src/universal_memory/application/memory/purge_fact_use_case.py`
- `src/universal_memory/application/memory/__init__.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/memory/test_context_hygiene_use_case.py`
- `tests/application/memory/test_purge_fact_use_case.py`
- `tests/interfaces/cli/test_facts_commands.py`
- `_bmad-output/implementation-artifacts/3-6-purgar-fatos-e-executar-context-hygiene.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-05-27: Created specification for Story 3.6 for fact purging and context hygiene.
- 2026-05-27: Implemented Story 3.6 with purge/hygiene use cases, `facts` CLI commands, real bootstrap, and complete tests.
