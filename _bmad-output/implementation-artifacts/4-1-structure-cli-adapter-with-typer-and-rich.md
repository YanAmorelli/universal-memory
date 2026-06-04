# Story 4.1: Structure CLI Adapter with Typer and Rich

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user or agent operating via terminal,
I want consistent CLI commands around the application use cases,
so that I can execute memory capabilities manually or via automation without accessing the infrastructure directly.

## Acceptance Criteria

1. **Use of Typer and Rich**:
   - **Given** the application layer with available use cases,
   - **When** the CLI adapter is implemented or migrated,
   - **Then** it must use the `typer` library to declare commands, arguments, and command-line options;
   - **And** it must use the `rich` library to format and color all standard human output (progress messages, descriptive tables, info panels, and spinners);
   - **And** all business logic must be strictly delegated to the shared application use cases received via dependency injection during initialization.

2. **Separation of Read-only Commands vs Mutations**:
   - **Given** read-only commands (`status`, `facts list`, `audit list`, `snapshots list`) and mutation commands (`init`, `facts purge`, `facts hygiene`, `rollback`),
   - **When** they are executed via the CLI,
   - **Then** read-only commands must never create, modify, delete, or alter any local physical file;
   - **And** mutation commands must go through the secure write pipeline defined in Epic 2 (e.g., using `SafeWriteUseCase` or secure repositories), generating appropriate rollback snapshots and recording a write audit log.

3. **Structured Format Support (Pure JSON)**:
   - **Given** the global `--format json` (or `-f json`) flag on the main CLI command,
   - **When** the user requests JSON format for any command,
   - **Then** the CLI must print only the corresponding valid JSON payload on `stdout`;
   - **And** the successful output must strictly follow the standardized envelope in `devex-interaction-spec.md` (keys: `ok`, `operation`, `scope`, `data`, `warnings`);
   - **And** it must not include any Rich markup, ANSI colors, human line breaks, debugging messages, or text in `stdout` outside of the pure JSON payload.

4. **Actionable Error Handling and Consistent Mapping**:
   - **Given** known domain exceptions (e.g., `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, `StorageError`),
   - **When** they occur during the execution of a CLI command,
   - **Then** the CLI adapter must catch the exception and format a user-friendly message using Rich (standard human output) with the error title, safe detail, and recovery hint (without displaying stack traces, unless a debug option is enabled);
   - **And** in JSON format, it must respond with the standardized error envelope (`ok: false` with the keys `code`, `message`, `detail`, `recovery_hint`) and return an appropriate non-zero exit code;
   - **And** unclassified unexpected errors must be handled with a generic safe error, without exposing secrets.

5. **Confirmation and Interactivity for Critical Operations**:
   - **Given** critical mutation actions (such as `facts purge`, `facts hygiene`, or `rollback`),
   - **When** executed by the CLI,
   - **Then** the system must display an interactive Typer prompt requesting the user's confirmation (`Yes`, `No`), summarizing the expected impact (scope, affected paths, and whether a snapshot will be taken);
   - **And** it must accept a `--yes` (or `-y`) flag to bypass any human interaction/confirmation, which is essential for execution by agents and CI/CD.

## Tasks / Subtasks

- [x] **Task 1: Install and configure dependencies in pyproject.toml** (AC: 1)
  - [x] Validate the presence and minimum versions of `typer` (>=0.25.1 or >=0.9.0 as compatible) and `rich` (>=15.0.0) in the local environment.
  - [x] Ensure that the development environment is up to date (`uv sync`).

- [x] **Task 2: Structure the Typer App composition in the interfaces/cli package** (AC: 1)
  - [x] Create or adapt the Typer app root in `src/universal_memory/interfaces/cli/main.py` or restructure `src/universal_memory/interfaces/cli/init_command.py`.
  - [x] Ensure that the main callback declares the global `--format` option (accepting `"human"` or `"json"`, with `"human"` as the default).
  - [x] Implement the signature of `build_main` to expose an interface compatible with `bootstrap/cli.py` (receiving ports and application use cases and returning a callable `(argv: Sequence[str] | None) -> int`).
  - [x] Ensure secure execution through Typer's internal Click invocation (e.g., `app(args=list(argv))` or by converting arguments) so that existing tests calling `main(["init"])` continue to work without invasive changes to existing test signatures.

- [x] **Task 3: Migrate CLI commands to Typer** (AC: 1, 2, 3)
  - [x] Migrate `init` command (`umem init`) delegating to the project setup use case.
  - [x] Migrate `status` command (`umem status`) delegating to `GetMemoryStatusUseCase`.
  - [x] Migrate `facts list` subcommands (`umem facts list`) with support for `--scope` and `--status` filtering options.
  - [x] Migrate `facts purge` subcommands (`umem facts purge`) with support for `--id`, `--scope`, and the global bypass `--yes` / `-y` flag.
  - [x] Migrate `facts hygiene` subcommands (`umem facts hygiene`).
  - [x] Migrate `audit list` subcommands (`umem audit list`) with optional `--scope` filter.
  - [x] Migrate `snapshots list` subcommands (`umem snapshots list`) with optional `--scope` filter.
  - [x] Migrate `rollback` command (`umem rollback`) with optional `--scope` and bypass flag `--yes` / `-y`.

- [x] **Task 4: Implement Premium Rich Visuals (Human Output)** (AC: 1, 2)
  - [x] Create professional and aesthetically pleasing layouts using Rich:
    - [x] Formatted tables for facts, audits, and snapshots listing.
    - [x] Colored panels for errors (red/orange) and recovery hints.
    - [x] Modern title or elegant emojis in rollback or purge confirmations.
  - [x] Ensure that standard human messages inform the result of mutations, including the reference of the generated audit event.

- [x] **Task 5: Implement Strict JSON Output** (AC: 3)
  - [x] Ensure that any stdout print under the `--format json` flag goes through `json.dumps` of the exact envelope.
  - [x] Prevent any call to the `rich` library from sending ANSI codes or extra characters to stdout when JSON format is active (warnings can be redirected to stderr if necessary, but stdout must contain only pure JSON).

- [x] **Task 6: Consolidate Error Handling and Confirmations** (AC: 4, 5)
  - [x] Centralize the translation of domain exceptions (`SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, `StorageError`) in the CLI adapter.
  - [x] Implement the interactive mutation confirmation prompt (using Typer or Rich features) with the correct choices (`Yes` and `No`).
  - [x] Ensure that when passing `--yes`, the prompt is completely bypassed.

- [x] **Task 7: Testing, Linting, and Validation** (AC: 1, 2, 3, 4, 5)
  - [x] Validate the integrity of the existing test suite by running `uv run pytest`.
  - [x] Ensure that the migration from argparse to Typer did not break any integration tests or CLI contracts.
  - [x] Run type checks with `uv run pyright` and check linting rules with `uv run ruff check .`.

### Review Findings

- [x] [Review][Patch] Color deactivation in Rich console (`color_system=None` and `force_terminal=False`) [src/universal_memory/interfaces/cli/init_command.py:530]
- [x] [Review][Patch] Absence of spinners and visual progress indication for humans [src/universal_memory/interfaces/cli/init_command.py]
- [x] [Review][Patch] Inappropriate use of raw Python `input()` instead of Typer/Rich confirmation prompt [src/universal_memory/interfaces/cli/init_command.py:601]
- [x] [Review][Patch] Absence of confirmation prompt and `--yes` flag in the critical mutation command `facts hygiene` [src/universal_memory/interfaces/cli/init_command.py:258]
- [x] [Review][Patch] Missing `audit_reference` field in JSON error envelope [src/universal_memory/interfaces/cli/init_command.py:867]
- [x] [Review][Patch] Absence of proper handling for CLI syntax/usage exceptions and traceback risks [src/universal_memory/interfaces/cli/init_command.py:106]
- [x] [Review][Patch] Absence of mapping and catching critical domain exceptions in CLI flows [src/universal_memory/interfaces/cli/init_command.py:614]
- [x] [Review][Patch] Fragility and complex coupling in global format calculation (`_effective_format`) [src/universal_memory/interfaces/cli/init_command.py]
- [x] [Review][Patch] Signatures returning `Any` in Rich table formatting functions [src/universal_memory/interfaces/cli/init_command.py]
- [x] [Review][Patch] Unit tests with fragile static assertion in `pyproject.toml` [tests/interfaces/cli/test_typer_rich_adapter.py:13]
- [x] [Review][Patch] Duplication and redundancy in `--format` / `-f` option declaration [src/universal_memory/interfaces/cli/init_command.py]

## Dev Notes

- **Compatibility Preservation in `build_main`**:
  - The file `bootstrap/cli.py` instantiates `build_main(...)` and calls the result passing the raw arguments (`argv`). To maintain this harmony without breaking the internal API or the 190+ tests validating CLI behavior, the adapter must transparently wrap the Typer app call:
    ```python
    def build_main(
        *,
        layout_port: ProjectLayoutPort,
        config_validation_port: ConfigValidationPort,
        # ... other commands / use cases ...
    ):
        # Configure global/static state of dependencies that the Typer app will use
        # ...
        def configured_main(argv: Sequence[str] | None = None) -> int:
            if argv is None:
                argv = sys.argv[1:]
            try:
                # Typer runs inside the CLI and intercepts Click exceptions
                # To prevent abrupt exits, we can catch SystemExit
                # or pass the exact list to the Typer app
                typer_app(args=list(argv))
                return 0
            except SystemExit as e:
                return e.code
            except Exception as e:
                # Fallback unexpected error handling
                return 1
        return configured_main
    ```
- **Human Output Formatting (Rich)**:
  - Use elegant tables (`rich.table.Table`) with styled borders to list data.
  - Use `rich.console.Console` writing directly to `sys.stderr` for helper or progress messages, ensuring that `stdout` remains clean for pipe or JSON streams.
- **Exception Handling**:
  - Map each domain error to the appropriate JSON code in the JSON envelope (for example, `SecretDetectedError` => `validation_failed` or similar) and to a red/orange formatted human output.

### Project Structure Notes

- The CLI adapter must reside in `src/universal_memory/interfaces/cli/`.
- Avoid creating business logic in the adapter. All operational validation and actual persistence occur in the domain and application use cases.

### References

- **DevEx Interaction Specification**: [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- **Software Architecture**: [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md)
- **PRD**: [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

Codex GPT-5

### Debug Log References

- 2026-05-28: Compatibility validation of the pytest suite before writing the story: 194 tests passing successfully.
- 2026-05-28: `uv sync` executed successfully after authorization to access the global uv cache.
- 2026-05-28: `uv run pytest` executed successfully: 196 tests passing.
- 2026-05-28: `uv run ruff check .` executed successfully.
- 2026-05-28: `uv run pyright` executed successfully: 0 errors.

### Completion Notes List

- Migrated the CLI adapter from `argparse` to `typer.Typer` composition, preserving the public signature `main(argv)` and the integration of `build_main` with `bootstrap/cli.py`.
- Maintained business logic delegation to injected use cases, including `init`, `status`, `facts list`, `facts purge`, `facts hygiene`, `audit list`, `snapshots list`, and `rollback`.
- Added global `--format` / `-f` option and maintained compatibility with `--format` on existing commands so as not to break test and automation contracts.
- Added use of Rich for human output, with tables for facts, audit log, and snapshots, Rich panels for human errors, and separate consoles for `stdout`/`stderr`.
- Preserved pure JSON on `stdout` for `--format json`, including existing success and error envelopes.
- Centralized mapping of `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, and `StorageError`.
- Added adapter tests to ensure exposure of the Typer app and direct runtime dependencies on `typer` and `rich`.

### File List

- `pyproject.toml`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/interfaces/cli/test_typer_rich_adapter.py`
- `uv.lock`
- `_bmad-output/implementation-artifacts/4-1-estruturar-adapter-cli-com-typer-e-rich.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-05-28: Implemented migration of CLI adapter to Typer/Rich with compatibility of existing contracts, additional tests, and complete validations.
