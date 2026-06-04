# Story 1.6: Configure Default Language and Locale

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user or agent initializing memory,  
I want English to be the default language with explicit locale configuration,  
so that CLI output, generated instructions, and skill templates are consistent and safe for automation.

## Acceptance Criteria

1. **Given** a clean configuration without `.umem/config.toml`, **When** `umem init` is executed, **Then** the default locale configured in the project TOML is `en`, **And** the default human help and initialization outputs are displayed in English.
2. **Given** the `--format json` flag or an MCP request, **When** any CLI command or MCP tool is executed, **Then** JSON field names, error identifiers, structured values, and tool payloads remain stable in English, **And** do not change according to the locale configured for human output.
3. **Given** an explicit locale configuration set to Portuguese (`pt-BR`), **When** human CLI commands are executed, **Then** only human-facing labels, prompts, and messages are translated.

## Tasks / Subtasks

- [x] **Task 1: Write RED tests for default locale and canonical English** (AC: 1, 2)
- [x] Update `tests/application/test_setup_project.py` to require `.umem/config.toml` with `locale = "en"` or an equivalent clear locale table in the project.
- [x] Update `tests/interfaces/cli/test_init_command.py` to require that human `umem init` uses English messages by default, including the hosts prompt and help/options when testable.
- [x] Add a test ensuring that `umem init --format json` remains pure JSON with English keys and no translated text or Rich markup.
- [x] Add a test ensuring that expected JSON errors maintain `ok`, `error`, `code`, `message`, `detail`, `recovery_hint`, and `audit_reference` in stable English.

- [x] **Task 2: Persist default locale in the config TOML without breaking hosts** (AC: 1)
- [x] Update `src/universal_memory/application/onboarding/setup_project.py` to write the default locale `en` during `setup_project(...)` along with `hosts.enabled`.
- [x] Preserve idempotency: re-running `umem init` must not overwrite an existing manual locale, including `pt-BR`.
- [x] Preserve existing TOML merging in `update_project_config(...)`; do not create a parallel TOML parser.
- [x] Validate that the resulting clean config remains readable with `tomllib` and written by `tomli-w`.

- [x] **Task 3: Introduce a minimal overlay of human messages** (AC: 1, 3)
- [x] Create or update a presenter/catalog in `src/universal_memory/interfaces/cli/` to resolve human messages: English as the canonical string, Portuguese (`pt-BR`) translation as an optional overlay.
- [x] Apply the overlay first to human texts directly related to Story 1.6: `init`, host selection/configuration prompts, success/no-op messages, and expected error messages used by the CLI.
- [x] Write new strings natively in English in the code; the `pt-BR` catalog should map literal English to Portuguese when the configured locale is `pt-BR`.
- [x] Accept `pt-BR` as the configured locale; if the locale is unknown, use `en` without failing.

- [x] **Task 4: Protect CLI/MCP automation against translation** (AC: 2)
- [x] Ensure that `--format json` bypasses the translation catalog and does not read/apply the locale for structured fields.
- [x] Ensure that JSON success/error envelopes in `interfaces/cli/init_command.py` remain in English for keys and codes.
- [x] Review `src/universal_memory/interfaces/mcp/server.py` and `src/universal_memory/bootstrap/mcp.py` to confirm that MCP payloads do not use a human presenter or translation.
- [x] If necessary, add a minimal MCP test ensuring that `initialize_project`/status keeps structured keys in English even with `.umem/config.toml` set to `pt-BR`.

- [x] **Task 5: Migrate existing Portuguese texts in the affected scope without broad refactoring** (AC: 1, 3)
- [x] Migrate human texts of `init` and directly related prompts from Portuguese to canonical English in `src/universal_memory/interfaces/cli/init_command.py`.
- [x] Do not attempt to translate the entire CLI in this story; commands from other epics can keep legacy strings if they are not required for the ACs, but they should not be used as a default for new code.
- [x] Update the seeded content of the default skill `use-universal-memory` to canonical English, keeping commands and structured fields in English.
- [x] Preserve existing command/flag names (`init`, `--format json`, `--hosts`, `--yes`) and aliases.

- [x] **Task 6: Quality check and regression validation** (AC: 1, 2, 3)
- [x] Run `uv run pytest tests/application/test_setup_project.py tests/interfaces/cli/test_init_command.py`.
- [x] Run relevant MCP tests if the MCP payload is touched: `uv run pytest tests/interfaces/mcp/test_server.py`.
- [x] Run full `uv run pytest`.
- [x] Run `uv run ruff check .` and `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Typer/Click parsing errors break `--format json` [src/universal_memory/interfaces/cli/init_command.py:221] — resolved; `ClickException` with `--format json` now emits a standard JSON envelope.
- [x] [Review][Patch] Interactive runtimes prompt ignores locale `pt-BR` [src/universal_memory/interfaces/cli/init_command.py:1017] — resolved; interactive selection of runtimes uses `human_message(...)` and `pt-BR` overlay.
- [x] [Review][Patch] Default human help still exposes Portuguese text, violating English-first [src/universal_memory/interfaces/cli/init_command.py:237] — resolved; CLI/help/public human outputs migrated to canonical English by default, maintaining explicit `pt-BR` overlay.
- [x] [Review][Patch] Human error fallback uses `pt-BR` when no locale has been resolved [src/universal_memory/interfaces/cli/init_command.py:2685] — resolved; fallback without an explicit locale is now `en`.
- [x] [Review][Patch] Message catalog imports infrastructure directly in the CLI layer [src/universal_memory/interfaces/cli/message_catalog.py:3] — resolved; locale resolution moved to bootstrap via `locale_resolver`, keeping the catalog pure.
- [x] [Review][Patch] Unsupported hosts error does not apply `pt-BR` overlay in human details [src/universal_memory/interfaces/cli/init_command.py:991] — resolved; human details use `human_message(...)` and JSON remains canonical in English.

## Dev Notes

- **Scope of this story:** configure default language and locale behavior. Do not implement a visual splash screen (Story 4.6), do not implement a complete schema update/migration (Story 5.7), and do not refactor the CLI beyond what is necessary for the ACs.
- **Core decision:** English is the canonical base of the product. Portuguese is a human presentation overlay, not the language of data, APIs, or error codes.
- **Main risk:** translating JSON/MCP or changing keys/codes would break automations and agents. Treat any translation on a structured surface as a regression.

### Current State of Relevant Code

- `src/universal_memory/application/onboarding/setup_project.py` currently only writes `hosts.enabled` via `update_project_config(...)`; the expected TOML in current tests does not yet include the locale.
- The seeded content `DEFAULT_UMEM_SKILL_MARKDOWN` and its triggers are in Portuguese. This story must change this seed to canonical English because FR29 requires skill templates in English by default.
- `src/universal_memory/interfaces/cli/init_command.py` already uses Typer/Rich and contains many human-facing strings in Portuguese, including help text, prompts, and error messages. For this story, prioritize `init`, host prompts, and expected errors covered by tests.
- `src/universal_memory/__main__.py` is just delegation to `bootstrap.cli.main`; do not recreate the old CLI in `__main__.py`.
- `src/universal_memory/bootstrap/cli.py` composes concrete dependencies. If the presenter needs to read the config, the reading must be done without creating side effects and without breaking tests that inject fake commands.
- `src/universal_memory/infrastructure/config/toml_loader.py` already implements `load_config`, `update_project_config`, deep merge, and writing with `tomli-w`. Reuse this; do not introduce PyYAML or another parser.

### Technical Requirements

- Python `>=3.12`; offline operation is mandatory.
- TOML persistence must continue using `tomllib` for reading and `tomli-w` for writing.
- Default locale must be `en` for a new project. Recommended name in the config: a simple and explicit key like `[preferences] locale = "en"` or `[project] locale = "en"`. Choose one way and cover it in tests; avoid duplicating the locale in multiple tables.
- `pt-BR` must only affect human output. Also accept defensive normalization (`pt_BR` -> `pt-BR`) if simple, but do not expand to a full i18n system.
- CLI JSON must remain a single parseable structure in stdout, without Rich markup, status spinner, prompt, logs, or translation.
- MCP must return semantic fields in English and must not consume a human presenter.

### Architecture Compliance

- Dependency rule: `interfaces -> application -> domain <- infrastructure`.
- The `application` layer can define/propagate the locale value in the result/config, but it must not format human messages.
- The presenter/message catalog belongs to the `interfaces/cli` layer; do not put translations in `domain` or in use cases.
- `infrastructure/config` remains responsible for TOML and path resolution; it must not know Rich, Typer, or MCP.
- Do not use locale to change command names, flags, JSON keys, enum values, runtime IDs, MCP tool names, or error codes.

### Library / Framework Requirements

- Current project stack: `typer`, `rich`, `fastmcp`, `pydantic`, `tomli-w`, `pytest`, `ruff`, `pyright`.
- Do not add an i18n dependency in this story; the overlay should be a simple table/dictionary.
- Version information already registered in the architecture: `typer>=0.25.1`, `rich>=15.0.0`, `fastmcp>=3.3.1,<4`, `pydantic>=2.13.4,<3`, `tomli-w>=1.2.0`.

### File Structure Requirements

- **Likely UPDATE files:**
  - `src/universal_memory/application/onboarding/setup_project.py`
  - `src/universal_memory/interfaces/cli/init_command.py`
  - `tests/application/test_setup_project.py`
  - `tests/interfaces/cli/test_init_command.py`
- **Possible NEW files:**
  - `src/universal_memory/interfaces/cli/message_catalog.py` or a minimal equivalent for a human overlay.
  - `tests/interfaces/cli/test_message_catalog.py` if the catalog has enough logic of its own for an isolated test.
- **Files that can be touched if necessary:**
  - `src/universal_memory/bootstrap/cli.py` to inject/resolve the locale in a controlled manner.
  - `src/universal_memory/interfaces/mcp/server.py` and `tests/interfaces/mcp/test_server.py` only to protect AC 2 if there is a real risk of translation in the MCP.
  - `src/universal_memory/infrastructure/config/toml_loader.py` only if a small helper for reading locale is needed; prefer not to modify if `load_config(...)` is sufficient.

### Testing Requirements

- TDD Strategy: RED -> GREEN -> REFACTOR.
- Test new project: `.umem/config.toml` contains default locale `en` and hosts remain persisted.
- Test idempotency: manual locale `pt-BR` is not overwritten to `en` when `umem init` is run again.
- Test default human output of `init` in English: must not depend on Portuguese like `criada` (created), `Deseja configurar` (Do you want to configure), `Operacao cancelada` (Operation cancelled) in tests on this surface.
- Test human output with `pt-BR` locale: only selected human messages/prompts appear translated; the equivalent JSON payload remains English.
- Test `--format json`: `json.loads(captured.out)` passes, `captured.err == ""`, keys/codes in English and no translated text surrounding them.
- Test MCP if touched: structured response maintains English keys when local config defines `pt-BR`.

### Previous Story Intelligence (1.5)

- Story 1.5 implemented `umem init`, human/JSON output, idempotency, and offline-first.
- Review of Story 1.5 fixed direct access of CLI to infrastructure and JSON envelope out of spec; do not reintroduce these issues.
- The CLI evolved after Story 1.5 to Typer/Rich in `interfaces/cli/init_command.py`; do not follow the old note to implement a minimal CLI with `argparse`.
- Existing tests still assert Portuguese strings (`criada` [created], `Deseja configurar...` [Do you want to configure...]). They must change to canonical English in this story.
- `audit_reference` can still be a stable placeholder where real auditing is not implemented; do not invent a new audit for locale.

### Git Intelligence Summary

- Recent commit `d24dd2d docs(bmad): update PRD and architecture with 2026-05-31 Sprint Change Proposal` introduced FR29 and the English-first/localization overlay architecture.
- Recent commits also added memory guidance, skills, and MCP; therefore, the story must preserve structured payloads and not break existing tools.
- Sprint planning revealed this story as a backlog item added after the first stories of Epic 1, so it must adapt existing code rather than assuming an initial scaffold.

### Project Structure Notes

- The project already contains the complete structure of Clean Architecture and multiple interfaces. Story 1.6 is a small cross-cutting change, but it should be concentrated in onboarding/config and the CLI presenter.
- Avoid creating generic i18n abstractions beyond what is necessary. A simple overlay catalog is sufficient for AC 3.
- Do not move `DEFAULT_UMEM_SKILL_MARKDOWN` out if that increases scope; translating the seeded content in the file itself is acceptable.

### References

- `_bmad-output/planning-artifacts/epics.md` (Story 1.6 / FR29 / Epic 1)
- `_bmad-output/planning-artifacts/prd.md` (FR29, Language & Visual Identity Guardrails, Journey 4)
- `_bmad-output/planning-artifacts/architecture.md` (Architecture Patch 2, English-First & Localization Overlay)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (JSON structure, human output, error envelope, MCP parity)
- `_bmad-output/implementation-artifacts/1-5-implementar-inicializa-o-cli-m-nima.md` (learnings and regressions to avoid)
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/infrastructure/config/toml_loader.py`
- `tests/application/test_setup_project.py`
- `tests/interfaces/cli/test_init_command.py`

## Dev Agent Record

### Agent Model Used

openai/gpt-5.5

### Debug Log References

- 2026-06-01: automatic discovery of the next backlog story via `sprint-status.yaml`.
- 2026-06-01: analysis of `epics.md`, `architecture.md`, `prd.md`, `devex-interaction-spec.md`, and Story 1.5.
- 2026-06-01: current code inspection confirmed CLI Typer/Rich in `interfaces/cli/init_command.py`, composition in `bootstrap/cli.py`, and config TOML in `infrastructure/config/toml_loader.py`.
- 2026-06-02: RED tests added for default locale `en`, preservation of `pt-BR`, English-first human `init` output, pure JSON, and JSON errors in English.
- 2026-06-02: implementation added `[preferences] locale = "en"`, minimal human `pt-BR` catalog, default skill seed in English, and JSON/MCP envelopes with recovery hints in English.
- 2026-06-02: validations executed: `uv run pytest tests/application/test_setup_project.py tests/interfaces/cli/test_init_command.py`, `uv run pytest tests/interfaces/mcp/test_server.py tests/interfaces/test_errors.py`, `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

### Completion Notes List

- Story contextualized as an implementation guide ready for development.
- Guardrails added to prevent JSON/MCP translation and automation regressions.
- Scope delimited to locale and canonical English, without anticipating visual splash screen or complete schema migration.
- Implemented default locale `[preferences] locale = "en"` in the config TOML of new projects, preserving existing manual locale like `pt-BR`.
- Introduced a minimal catalog of human messages in the CLI with canonical English and a `pt-BR` overlay only for human output of `init`/hosts/expected errors.
- Kept CLI JSON and MCP payloads in stable English; JSON error now uses message and `recovery_hint` in English.
- Default skill `use-universal-memory` seeded in canonical English, with commands and structured fields preserved.
- Complete suite validated with 399 passing tests, Ruff without errors, and Pyright without errors.

### File List

- `_bmad-output/implementation-artifacts/1-6-configurar-idioma-padr-o-e-locale.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/cli/message_catalog.py`
- `src/universal_memory/interfaces/errors.py`
- `tests/application/test_setup_project.py`
- `tests/interfaces/cli/test_init_command.py`

### Change Log

- 2026-06-01: Story created with status `ready-for-dev`.
- 2026-06-02: Implemented default English-first locale with human overlay `pt-BR`, JSON/MCP protection, and regression tests; status updated to `review`.
