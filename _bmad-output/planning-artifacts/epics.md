---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
  - "_bmad-output/planning-artifacts/devex-interaction-spec.md"
---

# universal-memory - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for universal-memory, decomposing the requirements from the PRD, UX Design/DevEx Interaction Spec, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: The system must persist facts and user preferences in human-readable local storage compatible with structured metadata.

FR2: The system must logically differentiate between repository-specific Short-Term Memory and global Long-Term Memory.

FR3: The system must retrieve context using local search modes defined by the architecture, with default mode selection based on a benchmark of latency, result quality, operational cost, and offline operation.

FR4: The user must be able to view and manually edit the persistence files directly in the file system.

FR5: The system must allow selective purging of specific facts or complete memory databases.

FR6: The system must execute Context Hygiene routines to archive or remove obsolete short-term facts after task completion.

FR7: During initial setup, the system must allow the user to select one or more supported runtimes/agents from a registry, including at least Claude Code, OpenCode and Codex/OpenAI-class AGENTS.md hosts, with Cursor and Antigravity represented according to their support tier.

FR8: The system must configure the selected runtimes by writing or updating their supported instruction targets and native skill targets, such as `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, `.cursor/`, `.opencode/` or equivalent runtime-specific paths, with snapshot and audit protection before every mutation.

FR9: The user must be able to initialize `universal-memory` in a new project or directory via a CLI command, such as `umem init`.

FR10: The user must be able to query the memory status, including size, active rules, and available skills, via CLI.

FR11: Every capability exposed by the API/MCP must have an equivalent CLI command for manual use.

FR12: The system must expose its capabilities through a native MCP server running over JSON-RPC.

FR13: The system must allow external agents, such as Claude Desktop, to read the updated memory context.

FR14: The system must allow external agents to write new facts and propose rules in memory via MCP commands.

FR15: The system must dynamically update the instructions contained in the agent files, such as `AGENTS.md` and `CLAUDE.md`, as new rules and facts are consolidated in memory.

FR16: The system must make the Short-Term Memory summary available in the initial agent context and expose, via status or audit, evidence of the last read, summary source, and injection failures when they occur.

FR17: The system must ensure that context injection respects size limits, using summarization to avoid causing LLM token overflow.

FR18: The system must track and count Latent Skills, or recurring user instructions/methodologies.

FR19: The system must request explicit approval, with Yes/Always/No options, when reaching the recurrence trigger to create a new Skill.

FR20: The system must generate a canonical Agent Skill structure with `SKILL.md`, optional `scripts/` and optional `references/`, then install or link it into native skill directories for selected runtimes when supported by that runtime adapter.

FR21: The user must be able to list, activate, edit, disable and inspect both canonical skills and per-runtime installed skill targets through CLI and MCP-equivalent capabilities.

FR22: The system must passively scan all received data to intercept API keys, credentials, or sensitive environment variables before saving.

FR23: The system must prevent the persistence of detected secrets, notifying the user of the attempt.

FR24: The system must maintain a local audit log of all changes automatically made to agent configurations and the creation of new skills.

FR25: The system must create a local snapshot before any automatic change in memories, rules, skills, or instruction files.

FR26: The system must block automatic changes when the previous snapshot fails.

FR27: The user must be able to list available snapshots and identify the timestamp, scope, origin, and action responsible for each snapshot.

FR28: The user must be able to roll back the last automatic change per scope via CLI.

FR29: The product must use English as the default language for CLI prompts, help text, generated instructions, skill scaffolds and documentation templates, while allowing an explicit locale configuration for other supported languages such as Portuguese.

FR30: The CLI onboarding experience should include a compact terminal brand element for `umem`, implemented as ANSI/ASCII splash art with a no-color fallback and disabled automatically for JSON/non-interactive output.

FR31: The system must allow the user to trigger updates and synchronize local canonical skills from `.umem/skills/` or local package templates to all active native runtime target paths.

FR32: During synchronization, if a native target file has been modified manually and diverges from the canonical source, the system must interactively prompt the user with choices (Keep Local Target / Overwrite with Canonical) and display a warning that overwriting could break the custom agent workflow.

FR33: The CLI must support checking for new library versions, migrating local configuration schema safely, and updating local benchmark datasets without losing user history or custom rules.

### NonFunctional Requirements

NFR1: Local context queries must respond in less than 150ms at the 95th percentile on a test database with at least 1,000 facts, measured by an automated benchmark on a development machine.

NFR2: Memory reading and initial context building must not add more than 200ms at the 95th percentile to the start of a configured agent session, measured by a local integration test.

NFR3: Local textual search and semantic search must be compared across at least 30 representative queries before the final choice of the default retrieval strategy.

NFR4: The system must block 100% of the secret patterns covered by the security test suite before persistence, with positive and negative examples.

NFR5: Change logs and secret interception alerts must be queryable via CLI in fewer than 2 commands from the project directory.

NFR6: Before any automatic change in instruction files or fact databases, the system must create a recoverable local snapshot.

NFR7: The system must maintain at least the 5 most recent versions per scope, validated by a rollback test.

NFR8: The user must be able to roll back the last automatic change in less than 1 minute using CLI.

NFR9: The MCP server must pass 100% of the compliance suite defined by the architecture, including health check, context recovery, fact writing/proposal, rule proposal, and JSON-RPC error handling.

NFR10: The persistence logic must isolate read, write, list, and versioning operations behind a testable internal contract, allowing backend swapping without changes to the rule engine, MCP, or CLI.

NFR11: The MVP must validate context reading on at least 2 supported hosts/agents, measured by documented manual test or integration test when the host allows automation.

NFR12: CLI, persistence engine, and MCP server must execute reading, writing, querying, auditing, and rollback with the network disabled.

### Additional Requirements

- The first implementation story must initialize the project with `uv init --package universal-memory`, pin Python 3.12+, install versioned dependencies, and create the base scaffold.
- The runtime stack must include `typer>=0.25.1`, `rich>=15.0.0`, `fastmcp>=3.3.1,<4`, `pydantic>=2.13.4,<3`, and `tomli-w>=1.2.0`.
- The development stack must include `pytest`, `pytest-cov`, `ruff`, and `pyright`.
- The structure must follow the `src/` layout with Clean Architecture and dependencies `interfaces -> application -> domain <- infrastructure`.
- `domain` must not import from other layers; `application` must not import from `infrastructure` or `interfaces`; `interfaces` must not access `infrastructure` directly.
- Use cases must be synchronous and receive ports via constructor injection.
- CLI Typer/Rich and MCP FastMCP must be thin adapters over the same application layer.
- All adapters must translate domain exceptions to the appropriate format, Rich in CLI and JSON-RPC in MCP.
- There must be a hierarchy of typed domain exceptions, including `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, and `StorageError`.
- Domain exceptions must map to specific JSON-RPC codes: `-32010`, `-32020`, `-32602`, `-32040`, `-32050`, and `-32060`.
- Persistence must use JSON for structured data and Markdown for documents and instruction files.
- All persisted JSON must use `snake_case`, UUID v4 as string, ISO 8601 UTC timestamps, `lowercase_snake` enums, native JSON booleans, and required fields `schema_version`, `id`, `created_at`, `updated_at`, `scope`, and `status`.
- The persistent layout per project must use `.umem/` with `config.toml`, `memory/`, `audit/events.jsonl`, `snapshots/`, `skills/`, and `benchmarks/retrieval-results.json`.
- The global layout must use `~/.local/share/umem/`.
- Global configuration must live in `~/.config/umem/config.toml` and project configuration in `.umem/config.toml`.
- TOML reading must use `tomllib`; TOML writing must use `tomli-w`.
- Every automatic mutation must follow the mandatory pipeline: validate input, scan secrets, resolve scope and path, create snapshot, abort if snapshot fails, write atomically via storage port, record audit, and return audit reference.
- No adapter may bypass the mutation pipeline.
- There must be a CLI/MCP parity matrix for `init`, `context`, `remember`, list/purge facts, propose rule, audit list, snapshots list, rollback, host setup/check, and skill proposal/list.
- Every new use case must add CLI and MCP coverage, except when explicitly marked as internal.
- CLI/MCP interactions must follow `_bmad-output/planning-artifacts/devex-interaction-spec.md` for human output, parseable JSON, secure confirmations, actionable errors, and semantic parity.
- There must be a benchmark `benchmarks/retrieval.py` with 1,000 facts, 30 representative queries, textual versus local semantic candidate/stub comparison, p95 latency, quality score of 1-5, offline compatibility, and operational complexity.
- The default retrieval strategy must be justified in `.umem/benchmarks/retrieval-results.json`.
- Storage ports must exist in `src/universal_memory/domain/ports/` for facts, rules, latent skills, snapshots, audit, and context summaries.
- Contract tests must live in `tests/contracts/` and validate minimum operations and migration hooks of the repositories.
- The MVP must implement host adapters for `codex`, `claude_code`, and `opencode` as Tier 1, and support Tier 2 detectors for `cursor` and `antigravity`.
- `AGENTS.md` must be treated as a shared manifesto and single-write target per mutation cycle.
- `CLAUDE.md` must contain only Claude-specific deltas that do not fit in `AGENTS.md`.
- Host-specific rule directories must be separate targets and must not duplicate the shared manifesto.
- `AGENTS.md` must remain compact, with stable operational rules and pointers to specialized documents, not a full dump of knowledge.
- Adapters must classify proposed instructions as `shared_policy`, `provider_delta`, `scoped_rule`, or `canonical_doc`.
- STM facts must support states `active`, `stale`, `archived`, and `purged`.
- Context hygiene must archive obsolete project facts before deleting, except when the user explicitly requests a purge.
- Audit logs must be append-only JSONL with timestamp, action, scope, origin, and result.
- Snapshots must use file copy and JSON manifest with timestamp, scope, responsible action, and hash.
- Secret scanning must combine regex for known formats and entropy heuristics for generic secrets, without external dependencies in the MVP.
- Development must follow TDD: each story must explicit the expected tests before implementation, and production code should only be considered complete when the corresponding automated tests are passing.

### UX Design Requirements

There is no visual/web/mobile UX in the MVP. The relevant UX is DevEx for CLI, MCP, local files, confirmations, and errors. The canonical interaction contract is in `_bmad-output/planning-artifacts/devex-interaction-spec.md` and must be used by interface stories as an intentional replacement for a visual UX specification.

### FR Coverage Map

FR1: Epic 1 - Readable and structured local persistence
FR2: Epic 1 - Logical STM/LTM separation
FR3: Epic 3 - Local context retrieval and benchmark
FR4: Epic 1 - Manually readable/editable files
FR5: Epic 3 - Selective fact purging
FR6: Epic 3 - Context Hygiene routines
FR7: Epic 5 - Selection of multiple runtimes
FR8: Epic 5 - Automatic configuration of native targets
FR9: Epic 1 - CLI initialization and scaffold
FR10: Epic 3 - Memory status display
FR11: Epic 4 - CLI/MCP command parity
FR12: Epic 4 - FastMCP JSON-RPC Server
FR13: Epic 4 - External context reading
FR14: Epic 4 - External writing and rule proposal
FR15: Epic 5 - Dynamic host instruction synchronization
FR16: Epic 3 - STM summary and injection with status
FR17: Epic 3 - Summarization and token limits
FR18: Epic 6 - Latent Skills tracking
FR19: Epic 6 - Explicit Yes/Always/No confirmation
FR20: Epic 6 - Agent Skill folder and structure generation
FR21: Epic 6 - Skill operations via CLI/MCP
FR22: Epic 2 - Passive secrets scanning
FR23: Epic 2 - Secret persistence prevention
FR24: Epic 2 - Append-only audit logging
FR25: Epic 2 - Pre-mutation local snapshots
FR26: Epic 2 - Fail-safe (blocking if snapshot fails)
FR27: Epic 2 - Snapshot listing and metadata
FR28: Epic 2 - Rollback per scope
FR29: Epic 1 - Configuração de idioma (English by default, locale config)
FR30: Epic 4 - Identidade visual (CLI interactive terminal splash banner)
FR31: Epic 6 - Sincronização de skills canônicas para caminhos nativos
FR32: Epic 6 - Alerta interativo de conflito manual (Keep/Overwrite)
FR33: Epic 5 - CLI schema migrations, library check and benchmark updates

## Epic List

### Epic 1: Local Foundation, Models, Contracts, and Locale
The user can initialize the local base of `universal-memory` with a Python 3.12+ scaffold, `.umem/` and `.local/share/umem/` layouts, domain models with support for `schema_version`, exceptions, storage ports, and TOML configuration (English by default, output locale support), and testable persistence contracts that unlock parallel work without coupling the layers.
**FRs covered:** FR1, FR2, FR4, FR9, FR29.

### Epic 2: Secure Mutation Pipeline and Audit
The user can trust that any automatic mutation passes through validation, passive secret scanning, mandatory pre-mutation snapshot, atomic writing, `jsonl` audit log, and rollback via CLI, preventing leaks and data corruption.
**FRs covered:** FR22, FR23, FR24, FR25, FR26, FR27, FR28.

### Epic 3: Memory, Search, and Context Hygiene
The user and external agents can write, list, search, summarize, and manage the lifecycle (active, stale, archived, purged) of local Short-Term Memory (repository) and Universal Memory (global) facts with token limits, STM lifecycle, and search latency/quality benchmarking to keep memory useful and controlled.
**FRs covered:** FR3, FR5, FR6, FR10, FR16, FR17.

### Epic 4: Interfaces and Parity (CLI and MCP)
Humans and external agents can operate the same system capabilities consistently through the terminal (with a secure ANSI/ASCII visual brand splash) or a FastMCP JSON-RPC server, with uniform handling of mapped errors.
**FRs covered:** FR11, FR12, FR13, FR14, FR30.

### Epic 5: Runtimes, Hosts, and Instruction Synchronization
The user can select and configure multiple supported runtimes (Claude Code, OpenCode, Codex, Cursor, Antigravity) using a declarative model registry, manage instruction targets (shared `AGENTS.md`, delta `CLAUDE.md`), and update local schemas/benchmarks in a secure and transparent manner.
**FRs covered:** FR7, FR8, FR15, FR33.

### Epic 6: Latent Skills and Skill Management
The user can transform recurring instructions into canonical Agent Skills (`SKILL.md`) and install them in a synchronized manner into native directories of supported runtimes, with interactive alerts for manual conflicts (Keep Local vs Overwrite Canonical).
**FRs covered:** FR18, FR19, FR20, FR21, FR31, FR32.

## Epic 1: Local Foundation, Models, and Contracts

The user can initialize the local base of `universal-memory` with a Python 3.12+ scaffold, `.umem/` layout, domain models, exceptions, ports, and testable contracts that unlock parallel work without coupling the layers.

### Story 1.1: Initialize Product Python Scaffold

As a universal-memory developer,
I want to initialize the Python package with defined structure, dependencies, and tooling,
So that the project has a reproducible base for TDD development and parallel work.

**Requirements covered:** FR9.

**Acceptance Criteria:**

**Given** a repository without a complete Python scaffold
**When** the project is initialized with `uv`
**Then** `pyproject.toml`, `uv.lock`, `.python-version`, `src/universal_memory/`, `tests/`, `tests/contracts/`, and `benchmarks/` exist
**And** the runtime is Python 3.12+ and versioned runtime/dev dependencies are configured

**Given** the initial scaffold
**When** the verification commands are executed
**Then** `ruff`, `pyright`, and `pytest` run without failures on the minimal base
**And** there is at least one initial test that would fail if the package were not importable

**Given** the initial scaffold versioned in the repository
**When** a change is pushed or a pull request is submitted
**Then** a CI workflow in `.github/workflows/ci.yml` runs `ruff`, `pyright`, and `pytest`
**And** the workflow fails when lint, type check, or automated tests fail

### Story 1.2: Define Domain Models for Memory

As an agent or adapter using the memory,
I want validated domain models for facts, rules, latent skills, snapshots, audits, and context summaries,
So that all components share consistent data contracts.

**Requirements covered:** FR1, FR2.

**Acceptance Criteria:**

**Given** the domain tests written first
**When** the Pydantic models are implemented
**Then** each persistable entity contains `schema_version`, `id`, `created_at`, `updated_at`, `scope`, and `status`
**And** JSON fields follow `snake_case`, UUID v4 string, ISO 8601 UTC timestamps, and `lowercase_snake` enums

**Given** invalid inputs for domain entities
**When** the model validation runs
**Then** invalid data is rejected with a typed and testable error
**And** STM supports `active`, `stale`, `archived`, and `purged` states

### Story 1.3: Define Domain Exceptions and Ports

As a developer implementing use cases and adapters,
I want stable domain exceptions and ports,
So that infrastructure, CLI, and MCP can evolve in parallel without undue coupling.

**Requirements covered:** FR1, FR2, FR11, FR12.

**Acceptance Criteria:**

**Given** import boundary and contract tests written first
**When** the domain ports are implemented
**Then** ports exist for facts, rules, latent skills, snapshots, audit, and context summaries
**And** the ports expose minimum operations of read, list, write, delete/purge when applicable and migration hooks

**Given** expected domain errors
**When** they are raised by future use cases or adapters
**Then** typed exceptions exist such as `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, and `StorageError`
**And** no layer needs to use generic `ValueError` or `RuntimeError` for known business errors

### Story 1.4: Create Local Layout `.umem/` and TOML Configuration

As a user initializing a project,
I want `universal-memory` to create and recognize a readable local structure,
So that I can version, inspect, and manually edit the project memory.

**Requirements covered:** FR1, FR2, FR4, FR9.

**Acceptance Criteria:**

**Given** project initialization tests written first
**When** the initialization command/use case runs in a clean directory
**Then** the `.umem/` structure is created with `config.toml`, `memory/`, `audit/events.jsonl`, `snapshots/`, `skills/`, and `benchmarks/`
**And** the initial files are human-readable and safe for manual editing

**Given** a global configuration and a project configuration
**When** the configuration is loaded
**Then** TOML is read with `tomllib` and prepared for writing with `tomli-w`
**And** global and local paths are resolved without network dependency

### Story 1.5: Implement Minimal CLI Initialization

As a `universal-memory` user,
I want to execute an initial project command,
So that I can activate local memory in a new repository with clear feedback.

**Requirements covered:** FR9.

**Acceptance Criteria:**

**Given** CLI tests written before implementation
**When** the user executes `umem init` in a directory without `.umem/`
**Then** the command creates the local project structure
**And** returns a human message indicating the created paths
**And** with `--format json`, returns pure JSON with keys `project_path`, `config_path`, `memory_path`, `audit_path`, `snapshots_path`, `created`, `already_initialized`, and `audit_reference`
**And** the output follows `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** a directory that already contains `.umem/`
**When** the user executes `umem init` again
**Then** the command is idempotent and does not corrupt existing files
**And** informs that the local memory was already initialized
**And** with `--format json`, returns `already_initialized: true`, `created: []` and the same resolved paths from the original initialization

**Given** the environment is offline
**When** `umem init` is executed
**Then** the initialization works without external connectivity

### Story 1.6: Configure Default Language and Locale

As a user or agent initializing memory,
I want English to be the default language with an explicit locale configuration,
So that CLI output, generated instructions, and skill templates are consistent and safe for automation.

**Requirements covered:** FR29.

**Acceptance Criteria:**

**Given** a clean configuration (no `config.toml` file)
**When** `umem init` is executed
**Then** the default locale configured in the project's TOML is `en`
**And** the default human help and initialization outputs are displayed in English

**Given** the `--format json` flag or an MCP request
**When** any CLI command or MCP tool is executed
**Then** JSON field names and error identifiers remain stable in English
**And** do not change according to the configured human output locale

**Given** an explicit locale configuration set to Portuguese (`pt-BR`)
**When** human-facing CLI commands are executed
**Then** only human-facing labels and messages are translated

## Epic 2: Secure Mutation Pipeline and Audit

The user can trust that any automatic mutation passes through validation, secret scanning, snapshot, atomic writing, audit, and rollback, preventing data loss or accidental secret persistence.

### Story 2.1: Implement Secrets Scanner

As a user writing facts, rules, and instructions,
I want the system to detect secrets before persisting any data,
So that credentials and sensitive variables are not accidentally saved in memory.

**Requirements covered:** FR22, FR23.

**Acceptance Criteria:**

**Given** security tests with positive and negative examples of secrets
**When** the scanner receives content with known credential patterns
**Then** it identifies the secret and returns a typed `SecretDetectedError`
**And** the persistence operation is not executed

**Given** content with suspicious long strings without an explicit pattern
**When** the scanner calculates entropy heuristics
**Then** it blocks values that exceed the configured threshold for generic secrets
**And** records sufficient metadata for auditing without exposing the sensitive value

**Given** legitimate content without secrets
**When** the scanner is executed
**Then** it approves the continuation of the pipeline
**And** does not produce false positives for common examples covered by the test suite

### Story 2.2: Create Snapshot Before Mutation

As a user allowing automatic changes,
I want the system to create a local snapshot before any write,
So that I can recover the previous state if an automatic change is unwanted.

**Requirements covered:** FR25, FR26.

**Acceptance Criteria:**

**Given** an automatic mutation in memory, rule, skill, or instruction file
**When** the pipeline resolves the write target
**Then** a snapshot is created before the mutation
**And** the manifest records timestamp, scope, responsible action, relative path, and hash of the previous content

**Given** a failure while creating a snapshot
**When** the mutation is requested
**Then** the pipeline aborts before writing any data
**And** returns `SnapshotFailedError`

**Given** multiple snapshots in the same scope
**When** the retention policy is applied
**Then** at least the 5 most recent versions per scope are preserved
**And** old versions are only removed after the new snapshot is confirmed

### Story 2.3: Implement Atomic Writing with Audit

As a developer implementing mutation use cases,
I want a mandatory safe write pipeline,
So that no adapter can persist data without validation, scanning, snapshot, and auditing.

**Requirements covered:** FR22, FR23, FR24, FR25, FR26.

**Acceptance Criteria:**

**Given** a use case that changes persisted data
**When** the mutation is executed
**Then** the pipeline follows the order: validate input, scan secrets, resolve scope and path, create snapshot, write atomically, and record audit
**And** the result returns an audit reference

**Given** a CLI or MCP adapter
**When** it executes a mutation
**Then** it invokes the shared use case instead of writing directly to storage
**And** tests prevent bypassing the pipeline by adapters

**Given** a failure during atomic writing
**When** the pipeline catches the exception
**Then** no partial file remains as the final state
**And** a failure audit event is recorded when possible

### Story 2.4: List Audit and Snapshots

As a user auditing automatic changes,
I want to query audit events and available snapshots,
So that I understand what was changed, when, by which action, and how I can recover the previous state.

**Requirements covered:** FR24, FR27.

**Acceptance Criteria:**

**Given** existing events in `.umem/audit/events.jsonl`
**When** the user queries the audit via use case or CLI
**Then** the system lists timestamp, action, scope, origin, result, and snapshot reference when it exists
**And** the query can be made in fewer than 2 commands from the project directory
**And** with `--format json`, returns pure JSON with `events[]` containing `timestamp`, `action`, `scope`, `origin`, `result`, `snapshot_reference`, and `audit_reference`
**And** the output follows `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** existing snapshots in `.umem/snapshots/`
**When** the user lists snapshots
**Then** the system shows timestamp, scope, origin, responsible action, relative path, and hash
**And** the human output is readable and the structured output is suitable for future automation
**And** with `--format json`, returns pure JSON with `snapshots[]` containing `timestamp`, `scope`, `origin`, `action`, `relative_path`, `hash`, and `manifest_path`

**Given** there are no events or snapshots
**When** the user executes the queries
**Then** the system returns an empty state explicitly
**And** does not treat the absence of data as an error
**And** with `--format json`, returns empty lists in `events` or `snapshots`, without mixed Rich text

### Story 2.5: Revert Last Mutation per Scope

As a user recovering from an automatic change,
I want to revert the last mutation per scope,
So that I can quickly restore memories, rules, skills, or instruction files.

**Requirements covered:** FR28.

**Acceptance Criteria:**

**Given** valid snapshots for a scope
**When** the user requests a rollback for that scope
**Then** the system restores the content of the most recent applicable snapshot
**And** records a new audit event for the rollback

**Given** no snapshot exists for the requested scope
**When** the rollback is executed
**Then** the system returns a typed error and a clear message
**And** no file is modified

**Given** a corrupted snapshot or one with a mismatched hash
**When** rollback attempts to restore it
**Then** the operation is blocked
**And** the failure event preserves sufficient evidence for investigation without exposing secrets

**Given** the environment is offline
**When** the user executes rollback per scope
**Then** the rollback works without external connectivity
**And** completes in less than 1 minute in a local test project

## Epic 3: Memory, Search, and Context Hygiene

The user and agents can write, list, retrieve, summarize, and clean local context with search benchmarking, token limits, and STM lifecycle to keep memory useful and controlled.

### Story 3.1: Write and List Memory Facts

As a user or agent working on a project,
I want to write and list memory facts per scope,
So that relevant context is available for future sessions without re-explanation.

**Requirements covered:** FR1, FR2.

**Acceptance Criteria:**

**Given** the repositories and domain models from Epic 1
**When** a valid fact is written by a use case
**Then** it is persisted with `schema_version`, `id`, `created_at`, `updated_at`, `scope`, `status`, `source`, `tags`, and `metadata`
**And** the write passes through the secure mutation pipeline of Epic 2 before writing
**And** if Story 3.1 is implemented before the full pipeline, it must use a mutation pipeline port/stub with the same contract and replace the stub before marking the story as completed

**Given** facts of `project` and `global` scope
**When** the user lists facts
**Then** the system returns only facts matching the requested filter
**And** preserves the logical separation between Short-Term Memory and Universal Memory

**Given** there are no facts in the requested scope
**When** listing is executed
**Then** the system returns an explicit empty list
**And** does not treat the absence of facts as an error

### Story 3.2: Query Local Context with Textual Search

As an external agent needing context before acting,
I want to query relevant facts via local search,
So that I can retrieve useful memory without depending on the network or external services.

**Requirements covered:** FR3, FR16.

**Acceptance Criteria:**

**Given** a local base with active facts
**When** a textual query is executed
**Then** the system returns relevant facts using local search by substring, normalization, or regex as defined by the architecture
**And** results include the identifier, scope, snippet or match reason, and relevant timestamp

**Given** archived, obsolete, or purged facts
**When** the default query is executed
**Then** the system excludes these facts from active results
**And** allows including non-active states only via an explicit diagnostic option

**Given** the environment is offline
**When** the context query is executed
**Then** it works without external connectivity
**And** does not attempt to access remote services

### Story 3.3: Implement Retrieval Benchmark

As a universal-memory maintainer,
I want to compare local textual search with a local semantic candidate or stub,
So that the default retrieval strategy is justified by latency, quality, and simplicity data.

**Requirements covered:** FR3.

**Acceptance Criteria:**

**Given** the `benchmarks/retrieval.py` script
**When** the benchmark is executed
**Then** it creates or uses a database of at least 1,000 test facts
**And** runs at least 30 representative queries derived from the PRD journeys and requirements

**Given** two comparable strategies
**When** the benchmark completes
**Then** it records p95 latency, a quality score of 1-5, offline compatibility, and operational complexity
**And** saves the result in `.umem/benchmarks/retrieval-results.json`

**Given** the benchmark results
**When** the default strategy is selected
**Then** the justification is recorded alongside the results
**And** the choice does not contradict the 150ms p95 limits for local queries

### Story 3.4: Build Context Summary with Token Limits

As an agent starting a new session,
I want to receive a compact summary of the applicable memory,
So that the initial context helps without causing overflow or noise in the prompt.

**Requirements covered:** FR16, FR17.

**Acceptance Criteria:**

**Given** project facts, global preferences, and active rules
**When** the context summary is built
**Then** it prioritizes items by scope, recency, status, and relevance
**And** clearly separates `project_summary`, `universal_preferences`, and `active_rules`

**Given** a size limit configuration
**When** the retrieved content exceeds the limit
**Then** the system summarizes or cuts lower-priority items
**And** preserves references to the facts used to build the summary

**Given** a context read by an agent
**When** the operation completes or fails
**Then** the system exposes evidence of the last read, summary source, and injection failures via status or audit
**And** does not expose secrets or content blocked by the scanner

### Story 3.5: Display Memory Status

As a user verifying the health of the local memory,
I want to query the database status, size, and activity,
So that I know if the project is configured and which data are active.

**Requirements covered:** FR10, FR16.

**Acceptance Criteria:**

**Given** an initialized `.umem/` database
**When** the status is queried via use case or CLI
**Then** the system shows the count of facts by scope and status, active rules, registered skills, approximate database size, and last known health check
**And** the human output is clear for reading in the terminal
**And** with `--format json`, returns pure JSON with `initialized`, `project_path`, `fact_counts`, `active_rules_count`, `registered_skills_count`, `approximate_size_bytes`, `last_health_check`, and `host_validation`
**And** the output follows `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** the current directory does not have `.umem/`
**When** the status is queried
**Then** the system returns an actionable message indicating that the project was not initialized
**And** does not automatically create files during a read-only query
**And** with `--format json`, returns `initialized: false`, `project_path`, and `recommended_action`

**Given** the environment is offline
**When** the status is queried
**Then** the operation works using only local data
**And** does not depend on external hosts

### Story 3.6: Purge Facts and Execute Context Hygiene

As a user keeping the memory clean,
I want to archive, purge, and clean up short-term facts,
So that obsolete context does not degrade future agent decisions.

**Requirements covered:** FR5, FR6.

**Acceptance Criteria:**

**Given** Short-Term Memory facts with states `active`, `stale`, `archived`, and `purged`
**When** context hygiene is executed after task completion or explicit command
**Then** obsolete project facts are marked as `stale` or `archived` before deletion
**And** final purging only occurs when the user explicitly requests a purge

**Given** a specific fact selected for purging
**When** the user confirms the removal
**Then** the fact stops appearing in default queries and listings
**And** the change passes through the secure mutation pipeline and records an audit

**Given** an entire database selected for purging
**When** the operation is executed
**Then** the system applies scope correctly and avoids removing global data when the user only requested project scope
**And** returns a summary of the affected items

**Given** previously archived facts
**When** the user executes a diagnostic query
**Then** the system can list archived items with lifecycle metadata
**And** keeps purged facts out of active results

## Epic 4: CLI and MCP Parity

Humans and agents can operate the same capabilities via CLI and MCP, with thin adapters, a parity matrix, consistent error handling, and JSON-RPC validation.

### Story 4.1: Structure CLI Adapter with Typer and Rich

As a user or agent operating via terminal,
I want consistent CLI commands over application use cases,
So that I can execute memory capabilities manually or via automation without accessing infrastructure directly.

**Requirements covered:** FR11.

**Acceptance Criteria:**

**Given** the application layer with available use cases
**When** the CLI adapter is implemented
**Then** it uses Typer for commands and Rich for human output
**And** delegates business logic to the shared use cases

**Given** read-only commands and mutation commands
**When** they are executed by the CLI
**Then** read-only commands do not create or modify files
**And** mutation commands pass through the secure pipeline defined in Epic 2

**Given** a structured output flag
**When** the user requests JSON format
**Then** the CLI returns pure JSON suitable for programmatic parsing
**And** does not mix Rich markup or human text in the structured payload
**And** the human output, JSON output, confirmations, and errors follow `_bmad-output/planning-artifacts/devex-interaction-spec.md`

### Story 4.2: Implement Base MCP Server with FastMCP

As an external agent compatible with MCP,
I want to access `universal-memory` via a native MCP server,
So that I can read context and invoke capabilities without depending on the CLI.

**Requirements covered:** FR12, FR13.

**Acceptance Criteria:**

**Given** the initialized Python package
**When** the MCP server runs
**Then** it registers base tools or resources via FastMCP
**And** exposes at least a health check and initial context reading

**Given** a valid MCP call
**When** it invokes an implemented capability
**Then** the MCP adapter delegates to the same use case used by the CLI
**And** does not access repositories or infrastructure directly
**And** MCP responses preserve the semantic fields defined in `_bmad-output/planning-artifacts/devex-interaction-spec.md` for the equivalent capability

**Given** the environment is offline
**When** the MCP server executes local capabilities
**Then** it works without external connectivity
**And** external host failures do not prevent local memory operations

### Story 4.3: Implement CLI/MCP Parity Matrix

As a product maintainer,
I want to ensure that capabilities exposed in one interface exist in the other,
So that humans and agents have consistent access to the same behavior.

**Requirements covered:** FR11, FR12, FR13, FR14.

**Acceptance Criteria:**

**Given** the parity matrix of the architecture
**When** a public capability is implemented
**Then** equivalent CLI input and MCP input exist for `init`, `context`, `remember`, list/purge facts, propose rule, audit list, snapshots list, rollback, host setup/check, and skill proposal/list
**And** internal exceptions are explicitly documented

**Given** parity tests
**When** the suite runs
**Then** it fails if a public use case is exposed only in CLI or only in MCP without justification
**And** validates that both return semantically equivalent data
**And** validates adherence to the interaction contracts of `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** a new future capability
**When** it is registered as public
**Then** the implementation checklist requires coverage in both interfaces
**And** the shared response contract is updated before delivery

### Story 4.4: Map Domain Errors to CLI and JSON-RPC

As a user or agent consuming the interface,
I want to receive consistent and actionable errors,
So that I can understand failures without depending on internal details.

**Requirements covered:** FR12, FR14.

**Acceptance Criteria:**

**Given** known domain exceptions
**When** they reach the CLI adapter
**Then** the CLI renders a clear Rich message and exits with non-zero status
**And** does not print a stack trace by default for expected business errors
**And** the message includes safe details and a recovery hint as per `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** known domain exceptions
**When** they reach the MCP adapter
**Then** MCP returns a JSON-RPC error with mapped codes: `SecretDetectedError` `-32010`, `SnapshotFailedError` `-32020`, `ValidationFailedError` `-32602`, `FactNotFoundError` `-32040`, `InvalidConfigError` `-32050`, and `StorageError` `-32060`
**And** includes safe `data.detail` for automation
**And** includes `data.recovery_hint` when there is a recommended safe action

**Given** unclassified unexpected error
**When** it occurs in any adapter
**Then** the system returns a safe generic error
**And** records audit or diagnostic log without exposing secrets

### Story 4.5: Validate MCP Compliance and Interface Contracts

As a maintainer ensuring integration with MCP hosts,
I want a validation suite for the MCP server and interface contracts,
So that future changes do not break reading, writing, and error handling by external agents.

**Requirements covered:** FR12, FR13, FR14.

**Acceptance Criteria:**

**Given** the MCP server with public capabilities
**When** the compliance suite runs
**Then** it validates health check, context recovery, fact writing/proposal, rule proposal, and JSON-RPC error handling
**And** all cases pass without external network

**Given** CLI and MCP responses for the same capability
**When** contract tests compare the results
**Then** essential fields are equivalent even if human formatting is different
**And** adapter differences are restricted to the presentation layer

**Given** an MCP validation failure
**When** the test reports the error
**Then** the message points to the capability and the broken contract
**And** the failure blocks the story until correction

### Story 4.6: Display Terminal Visual Identity Safely

As a user executing commands in the terminal interactively,
I want to see a compact ANSI/ASCII splash banner representing a USB flash drive connected to the terminal,
So that the tool has a recognizable visual identity without breaking automation.

**Requirements covered:** FR30.

**Acceptance Criteria:**

**Given** a human interactive TTY terminal (stdout.isatty() == True)
**When** the user starts interactive onboarding via CLI (e.g., `umem init`)
**Then** a compact ANSI/ASCII splash banner illustrating a USB/flash drive connection is displayed at the top
**And** the banner size is safe for common terminal widths

**Given** the `--format json` flag, non-interactive mode, or CI/CD environment
**When** any CLI command is executed
**Then** no splash banner or ANSI escape codes are emitted to the standard output

**Given** the `NO_COLOR` environment variable defined or a terminal that does not support colors
**When** the splash banner is rendered in interactive mode
**Then** the system displays the banner in plain text (without color escape codes) in a readable manner

## Epic 5: Runtimes, Hosts, and Instruction Synchronization

The user can select and configure multiple supported runtimes (Claude Code, OpenCode, Codex, Cursor, Antigravity) using a declarative model registry, manage instruction targets (shared `AGENTS.md`, delta `CLAUDE.md`), and update local schemas/benchmarks in a secure and transparent manner.

### Story 5.1: Model Runtimes and Targets Registry

As a maintainer configuring agent integrations,
I want a declarative model of the runtimes and targets registry (instruction and native skill targets),
So that each runtime has well-defined paths, capabilities, and support tiers.

**Requirements covered:** FR7, FR8, FR15.

**Acceptance Criteria:**

**Given** a declarative registry of runtimes
**When** the adapters and Pydantic models are defined in the domain
**Then** each runtime explicitly declares: `runtime_id`, display name, support tier (Tier 1 or 2), default paths (global and project), instruction targets, and native skill targets
**And** the registry includes support for Claude Code, OpenCode, and Codex/OpenAI as Tier 1, and Cursor and Antigravity as Tier 2

**Given** the shared `agents_md` target
**When** multiple runtimes support and consume `AGENTS.md`
**Then** only the single write target of `AGENTS.md` is authorized to write to the shared manifesto
**And** consumer runtime adapters only reference and validate the reading of the shared manifesto, without duplicating the file or overwriting it independently

**Given** a runtime-specific target like `CLAUDE.md` (`claude_md`)
**When** runtime-specific rules or deltas need to be applied
**Then** they are saved under the runtime file without duplicating the compact general rules contained in `AGENTS.md`

### Story 5.2: Configure Codex Host with `AGENTS.md`

As a user using Codex in a project,
I want to configure `AGENTS.md` as a compact shared manifesto,
So that the agent reads operational rules and pointers to memory without loading excessive knowledge.

**Requirements covered:** FR8, FR15.

**Acceptance Criteria:**

**Given** a project initialized with `.umem/`
**When** the user executes setup/check of the `codex` host
**Then** the system detects or proposes the `AGENTS.md` file
**And** classifies each proposed instruction as `shared_policy`, `provider_delta`, `scoped_rule`, or `canonical_doc`

**Given** an existing `AGENTS.md`
**When** the system needs to update it
**Then** it preserves unmanaged manual content whenever possible
**And** the change passes through the secure mutation pipeline with snapshot, audit, and rollback

**Given** the generated or updated manifesto
**When** host validation runs
**Then** `AGENTS.md` remains compact, with stable operational rules and pointers to docs or memory
**And** does not become a complete project knowledge dump

### Story 5.3: Configure Claude Code Host with `CLAUDE.md`

As a user using Claude Code alongside universal memory,
I want to configure specific deltas in `CLAUDE.md`,
So that Claude receives necessary instructions without diverging from the shared manifesto.

**Requirements covered:** FR8, FR15.

**Acceptance Criteria:**

**Given** the selected `claude_code` host
**When** setup/check is executed
**Then** the system detects or proposes `CLAUDE.md`
**And** writes only specific deltas that do not fit in `AGENTS.md`

**Given** both `AGENTS.md` and `CLAUDE.md` present
**When** drift validation runs
**Then** the system identifies undue duplication or contradictions between the files
**And** proposes correction without overwriting manual content without confirmation

**Given** an update in `CLAUDE.md`
**When** the mutation is applied
**Then** it uses snapshot, atomic writing, and auditing
**And** rollback per scope can restore the previous file state

### Story 5.4: Validate Context Reading by Host

As a user integrating a new agent,
I want to verify that the host can read memory context,
So that I know the operational identity has been correctly ported.

**Requirements covered:** FR7, FR8.

**Acceptance Criteria:**

**Given** a configured host
**When** the reading check is executed
**Then** the system validates that the host has instructions to query memory and that MCP is configured or documented for the host
**And** records a result of success, failure, or manual pending

**Given** a successful validation
**When** the user queries the memory status
**Then** the last validation result of the host appears with timestamp, host, method, and audit reference when applicable
**And** the evidence helps meet the requirement of at least 2 supported hosts in the MVP

**Given** a validation failure
**When** the system reports the problem
**Then** the message indicates whether the failure is related to the instruction file, MCP configuration, write permission, or context reading
**And** does not attempt to auto-correct without confirmation when there is a risk of overwriting content

### Story 5.5: Synchronize Consolidated Rules to Instructions

As a user approving new behavior rules,
I want to synchronize consolidated rules to supported instruction files,
So that different agents operate with consistent guidelines.

**Requirements covered:** FR15.

**Acceptance Criteria:**

**Given** a rule approved for promotion
**When** instruction synchronization runs
**Then** the system decides whether the rule belongs to `shared_policy`, `provider_delta`, `scoped_rule`, or `canonical_doc`
**And** updates only the corresponding targets

**Given** multiple configured runtimes
**When** a shared rule is synchronized
**Then** `AGENTS.md` is written only once per mutation cycle
**And** runtimes consuming `AGENTS.md` do not produce diverging copies

**Given** a rule pointing to detailed content
**When** it is synchronized
**Then** the instruction file includes a compact pointer to the canonical source
**And** the long content remains in docs or memory, as classified

### Story 5.6: Multi-Runtime Selection CLI Onboarding

As a user installing `universal-memory`,
I want to select multiple runtimes simultaneously in an interactive or automatic manner,
So that the initial setup configures all agents in my workspace in a cohesive and clean way.

**Requirements covered:** FR7, FR8.

**Acceptance Criteria:**

**Given** interactive onboarding via CLI
**When** the initial setup of runtimes is started
**Then** the CLI presents the highlighted prompt in English: `Which runtime(s) would you like to install for?`
**And** lists the supported runtimes in the declarative registry (Claude Code, OpenCode, Codex, Cursor, Antigravity) with their respective tiers and numerical indexes
**And** accepts the selection of multiple indexes (separated by comma or space) with visible safe defaults

**Given** execution in non-interactive mode (scripts/agents)
**When** the CLI receives explicit runtime options (e.g., `umem init --runtime claude-code --runtime opencode`)
**Then** the system executes the setup for all specified runtimes without requiring user input
**And** with `--format json`, returns pure JSON containing `runtimes_selected`, `runtimes_skipped`, `target_paths`, and `manual_steps_pending` in an automatable way

**Given** any confirmation or runtime file change plan
**When** setup is executed
**Then** the information displayed strictly follows the scope, relative path, and snapshot guidelines of `_bmad-output/planning-artifacts/devex-interaction-spec.md`

### Story 5.7: Library Updates, Schema Migration, and Benchmarks

As a user keeping my `universal-memory` environment updated,
I want the CLI to verify versions, migrate configuration schemas safely, and update local benchmarks,
So that I do not lose my usage history, facts, or customized rules.

**Requirements covered:** FR33.

**Acceptance Criteria:**

**Given** an update check command (e.g., `umem update --check`)
**When** executed via CLI
**Then** the system checks the current version of the local library and reports status

**Given** a library version change with modifications to the TOML configuration schema
**When** the CLI initializes or updates the environment
**Then** the system automatically and safely migrates the `.umem/config.toml` and `.umem/memory/*.json` files
**And** does not corrupt or delete saved facts data, audit history, or custom rules configured by the user

**Given** new datasets or updates in local test definitions
**When** the benchmark update is executed
**Then** the new local benchmark datasets under `.umem/benchmarks/` are updated

## Epic 6: Latent Skills and Skill Management

The user can transform recurring methodologies into formal Agent Skills, with recurrence tracking, explicit approval, and CLI management.

### Story 6.1: Record Latent Skills by Recurrence

As a user who repeats methodologies and instructions,
I want the system to record latent skill opportunities,
So that recurring patterns can become reusable capabilities without me re-explaining everything.

**Requirements covered:** FR18.

**Acceptance Criteria:**

**Given** a recurring instruction or methodology detected by an agent or CLI
**When** it is registered as a latent skill
**Then** the system persists the description, scope, origin, recurrence counter, timestamps, status, and metadata
**And** the persistence uses the secure mutation pipeline

**Given** the same methodology appears again
**When** the system associates the occurrence with an existing latent skill
**Then** the recurrence counter is incremented
**And** the source evidence is preserved without storing secrets

**Given** an ambiguous occurrence
**When** the system cannot associate with confidence
**Then** it records a separate candidate or requests confirmation instead of merging automatically
**And** avoids inflating the recurrence of unrelated skills

### Story 6.2: Propose Skill Creation with Explicit Approval

As a user controlling the system's evolution,
I want to approve or refuse the creation of a skill when a recurrence is detected,
So that the system learns without automating sensitive behavioral decisions.

**Requirements covered:** FR19.

**Acceptance Criteria:**

**Given** a latent skill reaches the configured recurrence trigger
**When** the proposal is presented to the user
**Then** the system offers explicit `Yes`, `Always`, and `No` options
**And** explains the suggested name, purpose, scope, and summarized evidence of the recurrence
**And** the confirmation follows the decision and safety pattern of `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** the user chooses `Yes`
**When** the proposal is accepted
**Then** the system creates a skill generation request for that occurrence
**And** keeps future occurrences subject to new confirmation

**Given** the user chooses `Always`
**When** the proposal is accepted
**Then** the system records a preference to automatically approve equivalent proposals within the configured scope
**And** the decision is auditable and reversible

**Given** the user chooses `No`
**When** the proposal is refused
**Then** the system marks the latent skill as refused or reduces its priority
**And** does not create skill files

### Story 6.3: Generate Canonical Skill and Install in Native Targets

As a user who approved a new skill,
I want the system to generate the canonical skill and install it in the native skill directories of the selected runtimes,
So that the capability is immediately usable by compatible agents.

**Requirements covered:** FR20, FR31, FR32.

**Acceptance Criteria:**

**Given** an approved skill
**When** generation is executed
**Then** the system creates the canonical skill under `.umem/skills/` with `SKILL.md`, `scripts/`, and `references/` following the specification

**Given** runtimes selected and active in the configuration (e.g., `claude_code`, `opencode`)
**When** the canonical skill is generated or updated
**Then** the system installs or creates symbolic links to the skill in the corresponding native directories (e.g., `.claude/skills/`, `.opencode/skills/`, `.cursor/rules/`)
**And** each native installation records timestamp, target runtime, relative path, and audit reference

**Given** a synchronization or write to a native target file that has been manually edited by the user (diverging from the canonical version)
**When** the `umem update --skills` command or automatic synchronization runs
**Then** the system detects the conflict and displays a highlighted interactive warning prompt in English: `Warning: Native target has manual changes. Overwriting it might break your current agent workflow. Keep local version or Overwrite with canonical library version? [Keep/Overwrite]`
**And** creates a backup snapshot of the modified skill before any overwrite

### Story 6.4: Register and List Skills

As a user managing learned capabilities,
I want to list and inspect registered skills,
So that I know which methodologies have been formalized and are available.

**Requirements covered:** FR21.

**Acceptance Criteria:**

**Given** registered skills in the local or global database
**When** the user lists skills via use case or CLI
**Then** the system shows name, scope, status, relative path, creation date, last update, and origin
**And** differentiates active, disabled, and candidate skills
**And** with `--format json`, returns pure JSON with `skills[]` containing `name`, `scope`, `status`, `relative_path`, `created_at`, `updated_at`, `origin`, and `audit_reference`
**And** the output follows `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** no skills registered
**When** the listing is executed
**Then** the system returns an explicit empty state
**And** suggests a command or proposal flow without automatically creating artifacts
**And** with `--format json`, returns `skills: []` and `recommended_action`

**Given** a specific skill
**When** the user requests details
**Then** the system shows metadata, relative path, usage triggers, and audit reference
**And** does not load large files from `references/` without explicit request
**And** with `--format json`, returns `name`, `scope`, `status`, `relative_path`, `triggers`, `audit_reference`, and `references_loaded: false` by default

### Story 6.5: Activate, Disable, and Edit Skills Safely

As a user adjusting existing skills,
I want to activate, disable, and edit registered skills with guardrails,
So that I control which capabilities are available without losing history.

**Requirements covered:** FR21.

**Acceptance Criteria:**

**Given** an active skill
**When** the user requests disablement
**Then** the status of the skill changes to disabled
**And** the change is audited and does not remove files by default

**Given** a disabled skill
**When** the user requests activation
**Then** the status changes back to active if the required files still exist
**And** the system reports a clear error if `SKILL.md` is missing or invalid

**Given** an edit to the skill metadata or content
**When** the change is applied
**Then** the system creates a snapshot before writing
**And** keeps rollback per scope available for the change

### Story 6.6: Expose Skill Management via CLI and MCP

As a user or consuming agent,
I want to propose, list, and manage skills via CLI and MCP,
So that automations and hosts can use the same flow without duplicate logic.

**Requirements covered:** FR18, FR19, FR20, FR21.

**Acceptance Criteria:**

**Given** use cases of latent skills and registry implemented
**When** the CLI interface is exposed
**Then** commands exist to propose skill, list skills, view details, activate, disable, and update allowed metadata
**And** mutation commands pass through the secure pipeline

**Given** the MCP server implemented
**When** MCP tools for skills are exposed
**Then** equivalent capabilities exist to propose and list skills according to the parity matrix
**And** mutation capabilities use the same use cases as the CLI

**Given** CLI/MCP parity tests
**When** they run for skill management
**Then** they validate semantic equivalence of responses
**And** fail if a public skill capability exists in only one interface without justification
**And** validate the confirmation, error, and output contracts defined in `_bmad-output/planning-artifacts/devex-interaction-spec.md`
