# Story 4.6: Display Terminal Visual Identity Safely

Status: done

## Story

As a user running `universal-memory` commands in an interactive human terminal,
I want to see a compact splash banner in ANSI/ASCII representing a flash drive connecting to the terminal,
so that the tool has a recognizable visual identity without breaking automations, parseable JSON, CI/CD, or environments without color support.

## BDD Acceptance Criteria

1. **Splash displayed only in human interactive onboarding**

   **Given** a human interactive terminal with `stdout.isatty() == True`
   **And** the command execution is in human mode, without `--format json`
   **And** the environment does not indicate CI/CD
   **When** the user starts the interactive onboarding via CLI, for example `umem init`
   **Then** a compact splash banner in ANSI/ASCII is displayed at the top of stdout before the human onboarding result
   **And** the banner must visually represent, in a simple way, a USB/flash drive connection to the terminal
   **And** the banner must fit safely in common terminal widths, without relying on a width greater than 80 columns.

2. **Automation never receives banner or ANSI in stdout**

   **Given** the `--format json` flag, non-interactive mode, or CI/CD environment
   **When** any CLI command is executed, including `umem init`
   **Then** no splash banner is emitted on stdout
   **And** no ANSI escape codes are emitted on stdout due to the splash
   **And** in the case of `--format json`, stdout remains pure and parseable JSON, without Rich text, logs, progress, or banner before/after the JSON object.

3. **Colorless fallback respects `NO_COLOR` and colorless terminals**

   **Given** the `NO_COLOR` environment variable is set or a terminal that does not support colors
   **And** the execution is still interactive and human
   **When** the splash banner is rendered in `umem init`
   **Then** the system displays a readable plain text version, without color escape codes
   **And** the ASCII content remains recognizable without relying on color to convey the brand.

4. **Scope restricted to CLI, without MCP regression/parity**

   **Given** the MCP server and CLI/MCP contracts already validated in Story 4.5
   **When** the terminal visual identity is added
   **Then** no MCP payload, JSON-RPC, CLI/MCP parity contract, or `--format json` output is changed
   **And** existing parity and compliance tests continue to pass.

## Tasks

- [x] Create tests first for the splash display policy in CLI `init`.
- [x] Cover the positive case: human `umem init`, `stdout.isatty() == True`, without `--format json`, without CI, without `NO_COLOR`, renders a compact banner before human output.
- [x] Cover suppression by `--format json`: stdout must continue starting with `{`, be parseable by `json.loads`, and not contain splash branding/borders/escape codes.
- [x] Cover suppression in non-interactive mode: when `stdout.isatty() == False` or `stdin.isatty() == False`, `umem init` does not render splash.
- [x] Cover suppression by CI/CD: when `CI` is set to a truthy value, `umem init` does not render splash.
- [x] Cover `NO_COLOR` fallback: with `NO_COLOR` set and interactive TTY, render a version without ANSI escape codes.
- [x] Implement a small helper in the CLI adapter to decide if the splash should be displayed, avoiding scattered conditionals in the command.
- [x] Implement ASCII/ANSI rendering without new external dependencies, using already available Rich/Console or native ANSI strings according to the architecture.
- [x] Call the splash only in the human workflow of `_run_init`, before the status spinner or before the final output, ensuring it does not appear in stderr and does not contaminate JSON.
- [x] Ensure that `--format json`, MCP, and parity tests are not altered by this story.
- [x] Run focused tests and minimal general validation before marking the story as completed.

### Review Findings

- [x] [Review][Patch] `CI=false`/`CI=0` suppress the splash as if they were active CI [src/universal_memory/interfaces/cli/init_command.py:958] — resolved; explicit falsy values of `CI` do not suppress the splash and there is dedicated coverage.
- [x] [Review][Patch] Splash can emit ANSI when `TERM` is missing or empty [src/universal_memory/interfaces/cli/init_command.py:884] — resolved; missing/empty `TERM` now uses plain ASCII splash without ANSI and there is a dedicated test.

## Context / Developer Guardrails

### Functional source of the story

- `epics.md` defines Story 4.6 as part of Epic 4, covering FR30.
- FR30 requires that the CLI onboarding experience includes a compact terminal branding element for `umem`, implemented as ANSI/ASCII splash art, with a colorless fallback and automatically disabled for JSON/non-interactive output.
- The PRD reinforces the multi-runtime onboarding journey: `umem init` shows minimalist ASCII/ANSI art simulating a flash drive connection to the terminal before the interactive prompt.
- The architecture, in the patch of 05/31/2026, specifies that the splash must use native ANSI escape codes without external dependencies and be disabled when stdout is redirected, `CI=true`, `--format json`, or `NO_COLOR` is present.

### Current state of relevant code

- `src/universal_memory/interfaces/cli/init_command.py` concentrates the Typer/Rich CLI adapter and all public commands.
- `_run_init(...)` executes host selection, project setup, host configuration, and final rendering of the `init` output.
- `_run_init(...)` already separates the JSON flow from the human flow: JSON uses `print(json.dumps(...))`; human uses `_stdout_console().print(...)`.
- `_selected_init_hosts(...)` already avoids interactive prompt in JSON, with `--yes`, or when `sys.stdin.isatty()` is false.
- `_stdout_console()` and `_stderr_console()` return `Console(file=sys.stdout/stderr, width=200)`. The splash helper must consider `sys.stdout.isatty()` directly or a testable abstraction, because the current `Console` fixes the width at 200 and should not be used as the sole evidence of real width.
- No current implementation of `splash`, `banner`, `NO_COLOR`, `CI`, or equivalent policy was found in the CLI.
- `tests/interfaces/cli/test_init_command.py` already covers human `init`, pure JSON, interactive host selection, locale, module execution, idempotency, offline, and error envelopes.
- `tests/interfaces/test_parity.py` validates the CLI/MCP matrix and must remain green; the splash must not affect structured payloads.
- `src/universal_memory/interfaces/cli/message_catalog.py` exists with a `pt-BR` catalog, but the current rendering of `_format_human_init_output` still uses hardcoded strings in Portuguese. This is an inherited/concurrent inconsistency from a previous story. This story should not become a broad i18n refactoring; only correct strings directly touched by the splash if necessary to comply with English-first.

### Behaviors to preserve

- `umem init --format json` must emit exactly a parseable JSON on stdout, without Rich, without logs, without banner, and without ANSI.
- Expected errors in JSON must continue to use the current envelope of `error_payload`/`_print_expected_error`.
- `umem init` continues creating/reutilizing `.umem/` and returning relative paths as per existing tests.
- Offline mode must remain without network access.
- Default host selection in JSON/`--yes`/non-interactive must continue to use `DEFAULT_ENABLED_HOST_IDS`.
- The splash is a CLI presentation only; it does not create files, does not change `.umem/config.toml`, does not record audit logs, and does not pass through the mutation pipeline.

## Likely Files

- `src/universal_memory/interfaces/cli/init_command.py`
  - Add private helper(s) like `_should_render_init_splash(...)`, `_render_init_splash(...)`, or equivalent.
  - Call the rendering in the human flow of `_run_init(...)` only when permitted by the policy.
  - Keep business logic out of the adapter; the splash is presentation, so it belongs to the CLI adapter.

- `tests/interfaces/cli/test_init_command.py`
  - Add focused tests for splash display/suppression/fallback.
  - Prefer monkeypatching `sys.stdin.isatty`, `sys.stdout.isatty`, `os.environ`, and using `capsys` capture.

- `src/universal_memory/interfaces/cli/message_catalog.py` *(possible, only if necessary)*
  - If the banner contains human text other than `umem`/ASCII, keep canonical English and, if translatable, register a `pt-BR` overlay without altering machine fields.
  - Inference: as FR29/Architecture Patch 2 establishes English-first, new human texts must be written in English by default. Evidence: `architecture.md` lines 909-918 and `prd.md` FR29.

## Technical requirements

- Do not add new dependencies. `rich` is already part of the stack (`rich>=15.0.0`) and can be used for human style, but the colorless fallback must be deterministic.
- The banner must be compact and ASCII-safe. Use only ASCII characters to avoid issues on minimal terminals and to comply with the ANSI/ASCII requirement.
- The art must fit in 80 columns. Pragmatic recommendation: keep each line to a maximum of 60 characters.
- Minimum mandatory detection to display splash:
  - `output_format != "json"`
  - `sys.stdout.isatty() is True`
  - `sys.stdin.isatty() is True` for interactive onboarding, since the story mentions interactive human terminal and the architecture refers to non-interactive automation.
  - `CI` variable missing or not having a truthy value.
- Minimum mandatory detection to disable coloring:
  - `NO_COLOR` present in the environment disables color.
  - Colorless terminal/console must fall back to plain text. If using Rich, configure styling to not depend on ANSI when `NO_COLOR` is present; if using native ANSI strings, do not include escape sequences in that path.
- Do not use stderr for the splash. The requirement refers to onboarding output; JSON suppression refers to stdout. Keeping the splash in stdout only when allowed avoids mixing branding with progress/status.
- Avoid snapshot/audit/mutation pipeline; rendering the banner is read-only and must not generate events.
- Do not change MCP. This story is about terminal visual identity, not about JSON-RPC.
- Do not change `sprint-status.yaml`; the orchestrator will consolidate it.

## Test requirements

- Follow TDD according to the general planning requirement: tests before implementation.
- Expected unit/adapter tests in `tests/interfaces/cli/test_init_command.py`:
  - `test_init_human_interactive_renders_terminal_splash` or equivalent.
  - `test_init_json_never_renders_terminal_splash_or_ansi` or equivalent.
  - `test_init_non_interactive_does_not_render_terminal_splash` or equivalent.
  - `test_init_ci_environment_does_not_render_terminal_splash` or equivalent.
  - `test_init_no_color_renders_plain_ascii_splash` or equivalent.
- Suggested assertions:
  - Positive: stdout contains `umem` and some stable ASCII marker of the art, for example `USB`, `[]`, `==`, or another chosen by the dev. Avoid fragile tests that depend on all the spaces in the art.
  - JSON: `json.loads(captured.out)` works; stdout starts with `{`; does not contain `\x1b[`; does not contain the splash text marker.
  - `NO_COLOR`: stdout contains the banner/branding but does not contain `\x1b[`.
  - CI/non-interactive: stdout does not contain the splash marker.
- Perform minimum validation:
  - `uv run pytest tests/interfaces/cli/test_init_command.py`
  - `uv run pytest tests/interfaces/test_parity.py`
  - `uv run pytest tests/interfaces/mcp/test_compliance.py`
  - If time permits, `uv run pytest`.
  - `uv run ruff check .` and `uv run pyright` if the Python code is modified.

## Previous story intelligence

Relevant previous story: `4-5-validar-conformidade-mcp-e-contratos-de-interface.md`, status `done`.

Applicable lessons and guardrails:

- Story 4.5 expanded the offline MCP compliance suite and CLI vs MCP parity. Any changes in this story must keep these tests green.
- MCP compliance validates public tools, success envelopes, domain errors, unexpected errors, and mandatory confirmations for destructive mutations. The splash must not create any new MCP requirements.
- CLI vs MCP parity was expanded to `init` and recursively validates keys, types, and scalar values in structured payloads. Therefore, `init`'s `--format json` cannot receive fields, prefixes, banners, or logs.
- Story 4.5 corrected relative paths in the `init` JSON; do not reintroduce absolute `Path.cwd()` in JSON payloads.
- Files touched by Story 4.5 and relevant to this story: `src/universal_memory/interfaces/cli/init_command.py`, `src/universal_memory/interfaces/mcp/server.py`, `tests/interfaces/mcp/test_compliance.py`, `tests/interfaces/test_parity.py`. This story should likely only touch the first one and CLI tests.
- Previous review pointed out relative path issues and filesystem exceptions in the CLI adapter. When adding terminal helpers, handle environment/TTY access simply and robustly, without letting terminal detection exceptions break the command.

## Risks / Edge Cases

- **JSON Contamination:** the biggest risk of this story. Any printing before/after the JSON breaks automation and tests.
- **TTY in tests:** `capsys` can cause `sys.stdout.isatty()` to return false. Positive case tests must explicitly monkeypatch `sys.stdout.isatty` and `sys.stdin.isatty`.
- **Variable CI:** some tools define `CI` as `true`, `1`, or another non-empty value. Implement a simple policy: any present and non-empty `CI` disables the splash. If you choose to treat `CI=false` as false, document it in the test.
- **`NO_COLOR`:** the presence of the variable, even if empty, conventionally disables color. Do not require a truthy value for `NO_COLOR`.
- **Colorless terminal:** if using Rich, it may decide color support based on the environment. Do not write tests dependent on the real terminal; test `NO_COLOR` as a deterministic path.
- **Terminal width:** the architecture asks for safety in common widths. Do not use wide art or rely on the current `Console.width` of 200.
- **Concurrent i18n:** there is a current inconsistency between English-first tests and Portuguese hardcoded strings in `init_command.py`. Do not expand the scope to refactor all messages; if adding text, use canonical English.
- **Order of human output:** the AC requests the banner at the top. If there is a spinner/status on stderr before stdout, this should not affect stdout, but visually it may appear first in some terminals. Prefer rendering the splash before the status spinner to fulfill the intent.

## Validation Checklist

- [x] Story implemented with changes restricted to the CLI adapter/relevant tests.
- [x] Banner appears only in allowed interactive human `umem init`.
- [x] Banner does not appear in `--format json` and JSON remains parseable.
- [x] Banner does not appear in CI/CD.
- [x] Banner does not appear in non-interactive/redirected mode.
- [x] `NO_COLOR` removes all ANSI escapes from the splash and keeps the art readable.
- [x] No MCP behavior was changed.
- [x] CLI/MCP parity tests continue to pass.
- [x] No new dependencies were added.
- [x] There was no change to `sprint-status.yaml`.
- [x] Dev Agent Record must record executed commands, results, and any residual divergence.

## References

- `_bmad-output/planning-artifacts/epics.md` lines 796-818: Story 4.6 definition and original ACs.
- `_bmad-output/planning-artifacts/prd.md` lines 153-160 and 385-388: onboarding journey and FR30.
- `_bmad-output/planning-artifacts/architecture.md` lines 1008-1019: splash architecture, suppression by JSON/CI/redirection/NO_COLOR, and onboarding.
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` lines 35-44: pure JSON contract without Rich/logs/prose.
- `_bmad-output/implementation-artifacts/4-5-validar-conformidade-mcp-e-contratos-de-interface.md`: learnings on parity and compliance.

## Completion Note

Ultimate context engine analysis completed - comprehensive developer guide created.

## Dev Agent Record

### Implementation Plan

- Add CLI adapter tests for splash policy before implementation.
- Keep the splash restricted to interactive human `init`, with a private helper to centralize `format`, TTY, and CI.
- Render compact ASCII art with native ANSI only when color is allowed, preserving plain text fallback with `NO_COLOR`.
- Validate that JSON, CLI/MCP parity, and MCP compliance remain without contract changes.

### Debug Log

- `uv run pytest tests/interfaces/cli/test_init_command.py` after adding tests: failed initially as expected due to missing splash; test adjustments isolated host dependencies and kept failures focused on missing USB.
- `uv run pytest tests/interfaces/cli/test_init_command.py`: 18 passed.
- `uv run pytest tests/interfaces/test_parity.py`: 16 passed.
- `uv run pytest tests/interfaces/mcp/test_compliance.py`: 4 passed.
- `uv run ruff check .`: failed initially due to long lines; formatting adjusted.
- `uv run ruff check .`: All checks passed.
- `uv run pyright`: 0 errors, 0 warnings, 0 informations.
- `uv run pytest`: 403 passed.
- `uv run pytest tests/interfaces/test_parity.py`: 16 passed.
- `uv run pytest tests/interfaces/mcp/test_compliance.py`: 4 passed.

### Completion Notes

- Implemented compact ASCII/ANSI splash for `umem init` only when `output_format != "json"`, `stdin` and `stdout` are TTY, and `CI` is not set to a truthy value.
- Implemented colorless fallback when `NO_COLOR` is present or `TERM=dumb`, keeping the brand and the ASCII marker `USB` readable.
- Splash is written only to stdout in the human flow of `_run_init`, before host selection, spinner, and final output.
- `init` JSON, MCP payloads, and parity contracts were not changed.
- No new dependencies were added.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` was not changed, per the user's guardrail.

## File List

- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/interfaces/cli/test_init_command.py`
- `_bmad-output/implementation-artifacts/4-6-exibir-identidade-visual-de-terminal-de-forma-segura.md`

## Change Log

- 2026-06-01: Added safe `umem init` splash for human interactive terminals, with suppression in JSON, CI, and non-interactive mode, plus `NO_COLOR` fallback.
- 2026-06-01: Added focused splash policy tests and performed full story validation.
