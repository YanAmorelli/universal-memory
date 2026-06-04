# Story 5.7: Library Updates, Schema Migration, and Benchmarks

Status: done

## User Story

As a user keeping my `universal-memory` environment updated,
I want the CLI to verify versions, safely migrate configuration schemas, and update local benchmarks,
so that I do not lose my usage history, facts, or custom rules.

**Requirements covered:** FR33.

## BDD Acceptance Criteria

1. **Given** a project initialized with `.umem/` and a local package installation,
   **When** the user executes `umem update --check`,
   **Then** the CLI reports the installed version of `universal-memory`, the supported target schema, and the status of local verifiable artifacts,
   **And** the operation is read-only: it does not create, alter, normalize, or delete files.

2. **Given** `umem update --check --format json`,
   **When** the check is executed,
   **Then** stdout contains only valid JSON in the standard envelope of the DevEx spec,
   **And** `data` contains at least `installed_version`, `target_schema_version`, `project_config_schema_version`, `memory_schema_versions`, `benchmarks_status`, `updates_available`, `migration_required`, and `warnings`,
   **And** field names remain in English and `snake_case` regardless of the configured locale.

3. **Given** `.umem/config.toml` without `schema_version` or with a previously supported schema,
   **When** the user executes `umem update --migrate` or an equivalent explicit update,
   **Then** the system migrates the config TOML to the current target schema,
   **And** preserves the user's existing unknown or custom keys,
   **And** preserves already existing settings such as `[hosts] enabled = [...]` and `[preferences] locale = "en"` when present,
   **And** records a snapshot and audit before/after the mutation.

4. **Given** existing memory files in `.umem/memory/*.jsonl` or `.umem/memory/*.json` contening facts, rules, latent skills, or summaries in a previously supported schema,
   **When** the migration is applied,
   **Then** each valid record is migrated to the target schema without altering `id`, `created_at`, `scope`, `status`, content, tags, metadata, or functional history,
   **And** custom records with safe extra fields are preserved in `metadata` or kept when the model already accepts extensions,
   **And** invalid or corrupted data is not silently discarded.

5. **Given** a failure when creating a snapshot, writing TOML/JSONL, or validating the migration,
   **When** `umem update --migrate` is executed,
   **Then** the operation aborts before replacing the original file,
   **And** returns an actionable domain error (`SnapshotFailedError`, `ValidationFailedError`, `InvalidConfigError`, or `StorageError`, depending on the cause),
   **And** does not leave a partial file as the final state.

6. **Given** new datasets or benchmark definitions available in the local package,
   **When** the user executes `umem update --benchmarks`,
   **Then** local artifacts under `.umem/benchmarks/` are safely updated,
   **And** the file `.umem/benchmarks/retrieval-results.json` is generated or updated by executing the existing local benchmark,
   **And** the user's custom history or results are not overwritten without a snapshot and audit.

7. **Given** `umem update --benchmarks --format json`,
   **When** the benchmark update finishes,
   **Then** the JSON response reports `benchmarks_updated`, `retrieval_results_path`, `query_count`, `fact_count`, `selected_default_strategy`, `p95_latency_ms`, `audit_reference`, and `warnings`,
   **And** does not mix Rich markup, ANSI banners, progress logs, or human-readable text in stdout.

8. **Given** an offline environment after local installation,
   **When** `umem update --check`, `umem update --migrate`, or `umem update --benchmarks` are executed,
   **Then** the workflow works using only local metadata and templates,
   **And** no network calls are required to satisfy the user story,
   **And** if a future remote version check is added, it must be opt-in or degrade to an `unknown` status with a warning without failing the local operation.

## Tasks

- [x] **Task 1: Define update contract and target schema (AC: 1, 2)**
  - [x] Create DTOs/commands/results in `application` for check, migrate, and benchmark updates.
  - [x] Define a single constant for the current target schema version, initially `1`, aligned with the existing models that already persist `schema_version` in entities.
  - [x] Read the installed version via `universal_memory.__version__` or `importlib.metadata.version("universal-memory")`, without duplicating the parsing of `pyproject.toml` at runtime.
  - [x] Represent `updates_available` as `false` or `unknown` when only local metadata is available; do not invent remote integration.

- [x] **Task 2: Implement read-only `UpdateCheckUseCase` (AC: 1, 2, 8)**
  - [x] Verify the existence of `.umem/`, `.umem/config.toml`, `.umem/memory/`, and `.umem/benchmarks/retrieval-results.json` without creating files.
  - [x] Read `schema_version` from config TOML when it exists; treat its absence as a supported legacy schema.
  - [x] Inspect `.umem/memory/facts.jsonl`, `rules.jsonl`, `latent_skills.jsonl`, and `context_summaries.jsonl` files when they exist, computing found versions without discarding invalid lines.
  - [x] Return safe warnings for missing files, invalid config, corrupt lines, or schemas above the supported version.

- [x] **Task 3: Implement safe migration of config TOML (AC: 3, 5)**
  - [x] Extend `toml_loader.py` or create a dedicated component in `infrastructure/config/` to apply TOML migrations while preserving unknown keys.
  - [x] Add `schema_version = 1` to the project config when missing, keeping `[project]`, `[hosts]`, `[preferences]`, and any custom tables.
  - [x] Use `SafeWriteUseCase` to write `.umem/config.toml` during `--migrate`; do not use direct writes for automatic migrations.
  - [x] Validate the config after rendering and before considering the migration complete.

- [x] **Task 4: Implement safe migration of memory files (AC: 4, 5)**
  - [x] Reuse existing `migrate(target_version)` hooks in repositories, expanding them for real migrations when necessary.
  - [x] Support at least the files currently used by the code: `.umem/memory/facts.jsonl`, `.umem/memory/rules.jsonl`, `.umem/memory/latent_skills.jsonl`, and `.umem/memory/context_summaries.jsonl` when present.
  - [x] Address the `.json` vs `.jsonl` documentation divergence explicitly: the story must preserve the actual existing `.jsonl` files and not rename user data without additional requirements.
  - [x] For invalid lines, block the migration of that file with an actionable error or preserve the line in an audited quarantine; do not silently delete them.
  - [x] Ensure a snapshot is taken per file before any replacement.

- [x] **Task 5: Integrate local benchmark updates (AC: 6, 7, 8)**
  - [x] Reuse `benchmarks/retrieval.py::run_benchmark(project_root=...)` to generate `.umem/benchmarks/retrieval-results.json`.
  - [x] If the existing results file has custom content, create a snapshot before overwriting.
  - [x] Return core metrics from the payload already produced by the benchmark: `fact_count`, `query_count`, `selected_default_strategy`, and p95 of the selected strategy.
  - [x] Keep execution offline and without new network or model dependencies.

- [x] **Task 6: Expose `umem update` CLI (AC: 1, 2, 3, 6, 7, 8)**
  - [x] Add `umem update` sub-command or Typer command in `interfaces/cli/init_command.py` preserving existing `skills update` commands.
  - [x] Support `--check`, `--migrate`, `--benchmarks`, `--format json`, and `--yes` flags when human confirmation is needed.
  - [x] Define safe behavior when no flags are passed: prefer read-only `--check` or return actionable help, without migrating implicitly.
  - [x] For human-readable output, follow `devex-interaction-spec.md`: result, scope, relative paths, audit references for mutations, and the next useful action.
  - [x] In JSON, use the standard envelope `{ "ok": true, "operation": "update...", "scope": "project", "data": ..., "warnings": [] }`.

- [x] **Task 7: Composition/bootstrap (AC: all)**
  - [x] Instantiate update use cases in `src/universal_memory/bootstrap/cli.py` with the required `SafeWriteUseCase`, repositories, and benchmark runner.
  - [x] Avoid importing `infrastructure` inside `domain`; if any use case in `application` needs concrete I/O, introduce a simple port or keep the composition in the bootstrap.
  - [x] Do not expose MCP in this story unless the project's parity matrix already requires update as a public capability; if not exposing MCP, document as a temporary exception because FR33 is explicitly CLI.

- [x] **Task 8: Automated testing and validation (AC: all)**
  - [x] Create application tests for read-only check, config migration, JSONL migration, and snapshot/storage failures.
  - [x] Create CLI tests for `umem update --check`, `--migrate`, `--benchmarks`, and combinations with `--format json`.
  - [x] Create a test ensuring that `--check` does not alter mtimes or content of local files.
  - [x] Create a test ensuring preservation of facts, rules, and custom fields when migrating a legacy fixture.
  - [x] Update or add benchmark tests to validate CLI integration without network access.
  - [x] Run `uv run pytest`, `uv run ruff check .`, and `uv run pyright` before marking as done.

### Review Findings

- [x] [Review][Patch] `umem update --check/--migrate` ignores `.json` memory files [src/universal_memory/application/update/update_use_cases.py:27] — resolved; legacy `.json` files are detected, migrated with snapshot/audit, and validated.
- [x] [Review][Patch] JSONL migration might mark invalid records as target schema without validating the resulting model [src/universal_memory/application/update/update_use_cases.py:427] — resolved; migrated records are validated against actual domain models before writing.
- [x] [Review][Patch] `umem update` tests do not protect the offline requirement against network usage [tests/interfaces/cli/test_update_command.py:13] — resolved; tests block socket/network usage in update flows.
- [x] [Review][Patch] Config migration with `schema_version = 0` preserves the old schema instead of migrating to the target [src/universal_memory/application/update/update_use_cases.py:328] — resolved; merge corrected and test with explicit legacy schema added.
- [x] [Review][Patch] Migration can leave the project partially migrated if a subsequent write fails [src/universal_memory/application/update/update_use_cases.py:281] — resolved; migration prepares snapshots before the first commit and applies reverse rollback of already committed writes if a later commit fails.
- [x] [Review][Patch] Tests do not cover explicit legacy schema or invalid schema [tests/application/test_update_use_cases.py:80] — resolved; added coverage for explicit legacy schema, invalid string type, boolean in config/check, and boolean in JSONL.

## Developer Context / Guardrails

- Primary source for this story: current `epics.md` of the main worktree, lines from Story 5.7, covering FR33: version checking, safe schema migration, and benchmark updates without loss of history or rules.
- The PRD defines FR33 as a CLI capability and enforces offline-first, preservation of local data, and no loss of history or custom rules.
- The architecture defines Clean Architecture: `interfaces -> application -> domain <- infrastructure`; `domain` does not import other layers and `application` must not import `infrastructure` directly.
- The architecture also defines a mandatory mutation pipeline: validate input, scan secrets, resolve scope/path, create snapshot, abort if snapshot fails, write atomically via storage port, audit, and return the audit reference.
- The DevEx spec requires that read-only commands do not cause side effects and that `--format json` produces pure JSON without Rich markup, logs, or banners.
- The story must preserve English as the canonical base for prompts/help/JSON fields. This specification is in PT-BR, but code and product messages must follow the English-first decision.
- Do not update `_bmad-output/implementation-artifacts/sprint-status.yaml`; consolidation is the orchestrator's responsibility.

## Probable Files

- `src/universal_memory/interfaces/cli/init_command.py`: add general `umem update` without breaking the existing `umem skills update`.
- `src/universal_memory/bootstrap/cli.py`: compose new use cases and dependencies.
- `src/universal_memory/__init__.py`: current source of `__version__`; avoid duplicating the version.
- `src/universal_memory/infrastructure/config/toml_loader.py`: existing TOML read/write; currently `update_project_config()` may write directly when `write_options` is absent, but automatic migrations must use `SafeWriteUseCase`.
- `src/universal_memory/infrastructure/config/project_layout.py`: current layout includes `.umem/benchmarks/retrieval-results.json`; the story must preserve this path.
- `src/universal_memory/application/onboarding/setup_project.py`: currently materializes host defaults and locale; migration must preserve these keys.
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`: uses `.umem/memory/facts.jsonl`; `migrate()` currently only accepts target 1 without transforming.
- `src/universal_memory/infrastructure/storage/local_rule_repository.py`: uses `.umem/memory/rules.jsonl`; `migrate()` currently only accepts target 1 without transforming.
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`: uses `.umem/memory/latent_skills.jsonl`; `migrate()` currently only accepts target 1 without transforming.
- `src/universal_memory/infrastructure/storage/local_context_summary_repository.py`: likely participant in summaries migration.
- `benchmarks/retrieval.py`: existing benchmark with `run_benchmark(project_root=...)` and output `.umem/benchmarks/retrieval-results.json`.
- `tests/interfaces/cli/test_init_command.py` or new `tests/interfaces/cli/test_update_command.py`: CLI coverage.
- `tests/infrastructure/test_retrieval_benchmark.py`: can be expanded for `umem update --benchmarks` integration.
- `tests/infrastructure/config/test_toml_loader.py`: TOML preservation/migration coverage.

## Technical Requirements

- The initial target schema must be `1`, unless the developer finds evidence of another value in the current code.
- Version checking must work offline. Do not add a mandatory remote call to PyPI/GitHub in this story.
- Migration must be idempotent: running `umem update --migrate` twice must not duplicate data, reorder files unnecessarily, or create new changes when nothing changed.
- Mutations of config, memory, and benchmarks must go through `SafeWriteUseCase` or an equivalent port that preserves snapshots, secret scanning, atomic writing, and auditing.
- Read-only `--check` must not call `ensure_project_layout()`, `run_benchmark()`, or any write method.
- When dealing with `.json` vs `.jsonl`, prioritize the actual state of the current code (`*.jsonl`) and document warnings for legacy or unexpected files. Do not perform destructive renames without an explicit requirement.
- When rendering TOML, semantically preserve unknown keys. Comments might not survive `tomli_w`; if this is unavoidable, declare a warning in human/JSON output before migration.
- Errors must use existing domain exceptions where possible: `InvalidConfigError`, `ValidationFailedError`, `SnapshotFailedError`, `StorageError`.
- The general `umem update` command must not conflict with the already implemented `umem skills update` namespace.

## Testing Requirements

- Initial RED test must demonstrate the absence of `umem update --check` or the absence of required fields.
- Test pure JSON with `json.loads(stdout)` and stderr without Rich/unexpected progress for `--format json`.
- Test that `umem update --check` in an initialized project does not alter the content or mtimes of `.umem/config.toml`, `.umem/memory/*.jsonl`, and `.umem/benchmarks/retrieval-results.json`.
- Test config migration without `schema_version`, with `[hosts] enabled = ["codex"]`, `[preferences] locale = "pt_BR"`, and a custom table; the result must preserve data and add the target schema.
- Test migration of legacy JSONL fixture with at least one fact and one rule; `id`, `created_at`, `scope`, `status`, `content`/equivalent fields, and metadata must remain intact.
- Test snapshot failure: migration must abort and the original file must remain byte-for-byte identical.
- Test memory file with invalid JSON line: it must not be silently discarded; expect an error or an explicit audited quarantine mechanism.
- Test `umem update --benchmarks` creates/updates `.umem/benchmarks/retrieval-results.json` with at least 1,000 synthetic facts, 30 queries, and a registered default strategy.
- Test offline by design: monkeypatch or fixture that fails if `socket`/network is used, or assertion of the absence of remote calls when applicable.
- Run the full suite and checks: `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

## Previous Story Context

- The relevant previous story was reopened as `5-6-onboarding-cli-de-sele-o-multi-runtime.md` to align the sprint status with the updated multi-runtime scope.
- Story 5.6 was marked `done`, but its implemented scope uses `hosts` and mostly covers `codex` and `claude_code`, while the updated `epics.md` mentions multi-runtime with Claude Code, OpenCode, Codex, Cursor, and Antigravity. Do not expand runtime support in this story beyond what is necessary for FR33.
- Story 5.6 recorded open review findings that may impact this story, especially insecure writing/duplicate I/O in `update_project_config()`, writing config before validation, fragility of hosts in config, and lack of exception handling. When touching these points, fix them locally and test them without altering unrelated behavior.
- Onboarding already writes `[hosts] enabled = [...]` and default locale; schema migration needs to preserve this data so as not to break future synchronization of instructions.
- The benchmark results file already exists in the layout, and the benchmark from Story 3.3 is `done`; this story must reuse it, not reimplement it from scratch.

## Risks / Edge Cases

- **Data loss through TOML normalization:** `tomli_w` may remove comments or reorder formatting. Mitigate by preserving semantics, using snapshots, and displaying a warning when relevant.
- **Documentary divergence `.json` vs code `.jsonl`:** PRD/epics mention `.umem/memory/*.json`, but current repositories use `.jsonl`. Treat as an inference based on code: preserve the actual `.jsonl` and do not automatically rename.
- **Future schema higher than supported:** if a local file has a `schema_version` greater than the target, do not attempt to downgrade; return a safe warning/error.
- **Corrupted line in JSONL:** do not discard; block migration or quarantine with explicit auditing.
- **Benchmark overwriting custom results:** create a snapshot before updating `retrieval-results.json`.
- **Remote update command:** FR33 talks about checking library versions, but the documents also require offline-first. For this story, the check must be local; any network activity must be post-MVP or opt-in.
- **Conflict with `skills update`:** keep namespaces clear so as not to break already implemented skills workflows.
- **Global files:** FR33 cites local config/schema. If the developer decides to include `~/.config/umem/config.toml` or `~/.local/share/umem`, mark as an inferred extension and ensure isolated tests; this is not mandatory unless additional evidence arises.

## Validation Checklist

- [x] `umem update --check` exists, is read-only, and returns local version/schema/status.
- [x] `umem update --check --format json` returns pure JSON with required fields.
- [x] `umem update --migrate` adds/updates the target schema with a snapshot, audit, and data preservation.
- [x] Migration of `.umem/config.toml` preserves `[hosts]`, `[preferences]`, and custom tables.
- [x] Memory migration preserves existing facts, rules, latent skills, and summaries without silent loss.
- [x] Snapshot/storage/validation failures abort without corrupting files.
- [x] `umem update --benchmarks` reuses `benchmarks/retrieval.py` and updates `.umem/benchmarks/retrieval-results.json` with snapshot/audit when overwriting.
- [x] All workflows function offline.
- [x] The command does not alter `sprint-status.yaml` or BMad artifacts outside this story.
- [x] `uv run pytest`, `uv run ruff check .`, and `uv run pyright` pass.

## Dev Agent Record

### Implementation Plan

- Create `application.update` contract with commands/results for check, migrate, and benchmarks, keeping a single target schema version `TARGET_SCHEMA_VERSION = 1` and installed version via `universal_memory.__version__`.
- Implement `UpdateCheckUseCase` strictly read-only, without `ensure_project_layout`, benchmark execution, or writes.
- Implement `UpdateMigrateUseCase` with pre-validation of config/memory before any write and mutations via `SafeWriteUseCase` for snapshots, atomic writes, and audits.
- Implement `UpdateBenchmarksUseCase` generating an offline payload in a temp directory and writing to `.umem/benchmarks/retrieval-results.json` only via `SafeWriteUseCase`.
- Expose `umem update` on the CLI with pure JSON, human output, `--yes` confirmation for mutations, and a safe default to `--check`.
- Compose use cases in the CLI bootstrap without exposing MCP in this story; temporary exception: FR33 is explicitly CLI.

### Debug Log

- Initial RED test failed due to missing `universal_memory.application.update`, confirming the story gap.
- The first focused suite revealed TOML assertions coupled to the formatting of `tomli_w`; tests were adjusted for semantic validation.
- Full `uv run pytest` initially revealed a regression in the `python -m universal_memory init` subprocess caused by a top-level import of `benchmarks`; fixed with a lazy import.
- Manual verification outside the repo revealed that `benchmarks.retrieval` was not resolved in an editable/installation outside of the cwd; added the `src/benchmarks` package with an equivalent packaged offline runner.
- `sprint-status.yaml` was neither read nor altered, as per user guardrails.

### Completion Notes

- `umem update --check` implemented as local offline read with required JSON fields, safe warnings, and `updates_available=false`.
- `umem update --migrate` migrates config TOML and memory JSONL to schema 1, preserving custom keys/tables and safe extra fields in `metadata`.
- Invalid JSONL lines block migration with a `StorageError`, with no silent discarding.
- Mutations of config, memory, and benchmarks use `SafeWriteUseCase`, creating a snapshot and audit before replacement.
- `umem update --benchmarks` runs the offline benchmark, returns main metrics, and writes results via the safe pipeline.
- The general `umem update` command does not conflict with `umem skills update`; without flags, it defaults to a read-only `--check`.

### Validation Results

- `uv run pytest` - passed, 406 passed.
- `uv run ruff check .` - passed, All checks passed.
- `uv run pyright` - passed, 0 errors, 0 warnings.

## File List

- `src/benchmarks/__init__.py`
- `src/benchmarks/retrieval.py`
- `src/universal_memory/application/update/__init__.py`
- `src/universal_memory/application/update/update_use_cases.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/test_update_use_cases.py`
- `tests/interfaces/cli/test_update_command.py`
- `_bmad-output/implementation-artifacts/5-7-atualiza-es-de-biblioteca-migra-o-de-schema-e-benchmarks.md`

## Change Log

- 2026-06-01: Implemented `umem update` command with `--check`, `--migrate`, `--benchmarks`, pure JSON, target schema 1, safe migration, packaged offline benchmark, and automated coverage.
