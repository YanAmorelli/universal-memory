# Story 2.1: Implement Secret Scanner

Status: done

## Story

As a user who records facts, rules, and instructions,  
I want the system to detect secrets before persisting any data,  
so that credentials and sensitive variables are not accidentally saved to memory.

## Acceptance Criteria

1. **Given** security tests with positive and negative examples of secrets, **When** the scanner receives content with known credential patterns, **Then** it identifies the secret and returns a typed error `SecretDetectedError`, **And** the persistence operation is not executed.
2. **Given** content with suspicious long strings without an explicit pattern, **When** the scanner calculates entropy heuristics, **Then** it blocks values that exceed the configured threshold for a generic secret, **And** records sufficient metadata for auditing without exposing the sensitive value.
3. **Given** legitimate content without secrets, **When** the scanner is executed, **Then** it approves the continuation of the pipeline, **And** does not produce false positives for common examples covered by the test suite.

## Tasks / Subtasks

- [x] **Task 1: Write RED tests for the scanner contract** (AC: 1, 2, 3)
  - [x] Create or update `tests/domain/test_ports.py` to include `SecretScannerPort` as an abstract ABC exported by `universal_memory.domain.ports`.
  - [x] Define a minimum typed signature for the port, for example `scan(content: str, *, origin: str | None = None) -> None`.
  - [x] Ensure that the contract raises `SecretDetectedError` for blocked content and returns `None` for approved content.

- [x] **Task 2: Write RED tests for the infrastructure implementation** (AC: 1, 2, 3)
  - [x] Create `tests/infrastructure/security/test_entropy_secret_scanner.py`.
  - [x] Cover known patterns: AWS access key, modern GitHub PAT, generic bearer token/API key, sensitive `.env` assignments (`API_KEY=...`, `SECRET=...`, `TOKEN=...`, `PASSWORD=...`).
  - [x] Cover entropy heuristics for long tokens without an explicit prefix.
  - [x] Cover common negatives: UUID v4, relative paths, short commit hashes, natural text, non-secret configuration identifiers, and placeholder examples (`your_api_key_here`, `not-a-secret`).
  - [x] Verify that error messages and metadata never include the raw sensitive value.

- [x] **Task 3: Implement `SecretScannerPort` in the domain** (AC: 1)
  - [x] Add `src/universal_memory/domain/ports/secret_scanner_port.py`.
  - [x] Export `SecretScannerPort` in `src/universal_memory/domain/ports/__init__.py`.
  - [x] Keep `domain` without imports from `application`, `infrastructure`, or `interfaces`.
  - [x] Reuse the existing `SecretDetectedError` in `src/universal_memory/domain/exceptions.py`; do not create a parallel error.

- [x] **Task 4: Implement offline scanner without external dependencies** (AC: 1, 2, 3)
  - [x] Create `src/universal_memory/infrastructure/security/__init__.py`.
  - [x] Create `src/universal_memory/infrastructure/security/entropy_secret_scanner.py`.
  - [x] Implement compiled regexes for known patterns and sensitive variable names.
  - [x] Implement Shannon entropy calculation using the standard library (`math`, `collections`) with a threshold configurable via the constructor.
  - [x] Make the class implement `SecretScannerPort`.
  - [x] Return silent approval (`None`) for secure content.

- [x] **Task 5: Ensure secure metadata for future auditing** (AC: 2)
  - [x] Include only secure information in the error: detection type, pattern name, approximate position/range or count, optional `origin`, and recovery hint.
  - [x] Do not include the detected substring, reversible masked token, complete line containing the secret, or the original value.
  - [x] If `SecretDetectedError` needs to carry metadata, evolve the class while preserving compatibility with `tests/domain/test_exceptions.py` and `error.message`.

- [x] **Task 6: Quality and regression verification** (AC: 1, 2, 3)
  - [x] Run `uv run pytest tests/domain/test_ports.py tests/infrastructure/security/test_entropy_secret_scanner.py`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check .`.
  - [x] Run `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Risk of High-Entropy False Positives with Base64 Payloads (images/binaries) — Resolved: Maintained default strict behavior for the MVP for security (avoiding false negatives of secrets in base64).
- [x] [Review][Patch] Risk of Indirect Exposure of Secrets via the `span` field in Error Metadata [src/universal_memory/infrastructure/security/entropy_secret_scanner.py:L74] (Applied: added security alert in docstrings/comments of SecretDetectedError and SecretScannerPort.scan)

## Dev Notes

- **Scope of this story:** create the scanner and its internal contract. Do not implement snapshot, atomic write, full auditing, CLI/MCP, or the entire mutation pipeline yet; this belongs to stories 2.2, 2.3, and 2.4.
- **Security objective:** block persistence of sensitive content before any future write operation, meeting FR22 and FR23.
- **Expected result for future integration:** mutation use cases will be able to receive `SecretScannerPort` via constructor injection and call `scan(...)` before snapshot/write/audit.

### Technical Requirements

- Python `>=3.12`; fully offline operation.
- Do not add external dependencies for secret scanning in the MVP.
- Use only the standard library for regex and entropy.
- `SecretDetectedError` must be the single typed error for blocked content.
- The scanner must be deterministic and testable, with thresholds configurable via the constructor to facilitate testing.
- Do not leak secrets in exceptions, logs, output fixtures, or audit metadata.
- Implement known patterns and generic heuristics; the heuristics do not replace explicit regex.

### Architecture Compliance

- Mandatory dependency rule: `interfaces -> application -> domain <- infrastructure`.
- `SecretScannerPort` must live in `src/universal_memory/domain/ports/`.
- The concrete implementation must live in `src/universal_memory/infrastructure/security/`.
- `domain` can define the port and the error, but cannot know regex, entropy, or infrastructure details.
- `application` must not import `infrastructure`; future integration must receive the port via constructor injection.
- No adapter can write directly to storage without the future secure pipeline.

### Library / Framework Requirements

- Use `re` for known patterns.
- Use `math.log2` for Shannon entropy.
- Do not use external packages such as detect-secrets, trufflehog, gitleaks, or network calls.
- Do not alter versions in `pyproject.toml` in this story, unless existing tests require an already agreed upon correction.
- The active stack information remains the same as in the planning artifacts: Python 3.12+, Pydantic v2, Typer/Rich, FastMCP, and `tomli-w`; this story does not depend on these libs to execute the scanner.

### File Structure Requirements

- **Expected UPDATE files:**
  - `src/universal_memory/domain/ports/__init__.py`
  - `tests/domain/test_ports.py`
- **Possible UPDATE files, if needed for secure metadata:**
  - `src/universal_memory/domain/exceptions.py`
  - `tests/domain/test_exceptions.py`
- **Expected NEW files:**
  - `src/universal_memory/domain/ports/secret_scanner_port.py`
  - `src/universal_memory/infrastructure/security/__init__.py`
  - `src/universal_memory/infrastructure/security/entropy_secret_scanner.py`
  - `tests/infrastructure/security/test_entropy_secret_scanner.py`

### Testing Requirements

- Follow TDD: RED tests before production code.
- Positive tests must prove blocking for known patterns and high entropy.
- Negative tests must avoid false positives in common project content.
- Tests must prove that the sensitive value does not appear in `str(error)`, `error.message`, or public metadata.
- Tests must prove that secure content returns `None` and produces no side effects.
- Contract tests must continue to ensure that ports are abstract ABCs with typed signatures.

### Current Code State

- `src/universal_memory/domain/exceptions.py` already defines `SecretDetectedError` as a subclass of `UniversalMemoryError`.
- `tests/domain/test_exceptions.py` already ensures that domain errors preserve the `message`; any evolution must maintain this compatibility.
- `src/universal_memory/domain/ports/` already contains repositories and config/layout ports, but does not yet contain `SecretScannerPort`.
- `tests/domain/test_ports.py` centralizes port signature expectations; adding the scanner there maintains the pattern established in Epic 1.
- `src/universal_memory/infrastructure/` currently only contains `config/`; the `security/` folder will be the correct architectural location for the scanner.

### Previous Story Intelligence

- Story 1.5 consolidated the thin adapter pattern and avoided business logic in interfaces.
- Story 1.4 hardened layout/config and reinforced idempotency; do not reimplement filesystem/config for the scanner.
- The stories of Epic 1 established that contracts live in the domain and implementations with side effects or technical details live in infrastructure.
- The current quality standard is to validate with `pytest`, `ruff`, and `pyright` before moving implementation status.

### Git Intelligence Summary

- `44dbe15 feat: implement clean cli init` moved CLI to a clean composition and kept initialization as an adapter over the application.
- `05f7abf feat: harden project init layout and config loading` reinforced infrastructure ports and adapters for layout/config.
- `facd129 feat(domain): implementar excecoes e ports de dominio...` established the pattern of typed exceptions and abstract ports.
- The implementation of this story should be incremental: add a port and a concrete implementation without refactoring existing layers.

### Latest Technical Information

- There is no new external dependency to research or version in this story.
- The relevant technical decision is to use the Python 3.12 standard library to keep the offline-first requirement and zero external dependency in the scanner.
- Entropy heuristics should be treated as an auxiliary signal, not as an absolute detector; negative tests are a mandatory part of controlling false positives.

### Project Structure Notes

- Creating `infrastructure/security/` aligns the code with the tree expected in `_bmad-output/planning-artifacts/architecture.md`.
- Do not create `application/security/` yet, unless the implementation requires an internal use case; the scope of this story is port + infrastructure.
- Do not touch `interfaces/cli/` or `interfaces/mcp/` in this story.
- Do not use absolute paths in messages, specs, fixtures, or documentation.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 2, Story 2.1, FR22, FR23, NFR4)
- `_bmad-output/planning-artifacts/architecture.md` (Security & Guardrails, Clean Architecture, Project Structure, Mutation Pipeline)
- `_bmad-output/planning-artifacts/prd.md` (Secret & ENV Guardrails, Backup & Recovery guardrails)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (No secret exposure, actionable errors, relative project paths)
- `_bmad-output/implementation-artifacts/1-5-implementar-inicializa-o-cli-m-nima.md` (recent adapter, quality, and verification patterns)
- `src/universal_memory/domain/exceptions.py`
- `src/universal_memory/domain/ports/__init__.py`
- `tests/domain/test_ports.py`
- `tests/domain/test_exceptions.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-26: target story resolved from "epic 2" as the first backlog story of the epic: `2-1-implementar-scanner-de-segredos`.
- 2026-05-26: analyzed `sprint-status.yaml`, `epics.md`, `architecture.md`, `prd.md`, and `devex-interaction-spec.md`.
- 2026-05-26: inspected `src/universal_memory/domain/exceptions.py`, `src/universal_memory/domain/ports/`, `tests/domain/test_ports.py`, `tests/domain/test_exceptions.py`, and the current structure of `infrastructure/`.
- 2026-05-26: there is no `project-context.md` in the repository; workflow proceeded with planning artifacts and previous stories.
- 2026-05-26: RED tests added for `SecretScannerPort` contract and `EntropySecretScanner` implementation; initially failed due to a missing import.
- 2026-05-26: implemented domain port, offline scanner with regex and Shannon entropy, and secure metadata in `SecretDetectedError`.
- 2026-05-26: validations executed successfully: `uv run pytest tests/domain/test_ports.py tests/infrastructure/security/test_entropy_secret_scanner.py`, `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story ready for dev with scope delimited to internal scanner and domain port.
- Guardrails included to avoid leaking secrets in errors, metadata, and tests.
- Expected files and verification commands defined.
- `SecretScannerPort` was added to the domain with the signature `scan(content: str, *, origin: str | None = None) -> None`.
- `EntropySecretScanner` blocks known patterns, sensitive assignments, and high-entropy tokens without external dependencies.
- `SecretDetectedError` preserves `message` and can now carry secure metadata for future auditing without exposing sensitive values.
- Legitimate content covered by negatives returns `None`, including UUIDs, relative paths, short commits, natural text, and placeholders.
- Story validated and moved to `review`.

### File List

- `_bmad-output/implementation-artifacts/2-1-implementar-scanner-de-segredos.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/domain/exceptions.py`
- `src/universal_memory/domain/ports/__init__.py`
- `src/universal_memory/domain/ports/secret_scanner_port.py`
- `src/universal_memory/infrastructure/security/__init__.py`
- `src/universal_memory/infrastructure/security/entropy_secret_scanner.py`
- `tests/domain/test_ports.py`
- `tests/infrastructure/security/test_entropy_secret_scanner.py`

### Change Log

- 2026-05-26: Implemented offline secret scanner and domain contract for Story 2.1; status moved to `review`.
