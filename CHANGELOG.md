# Changelog

All notable changes to this project are documented in this file.

This project follows semantic versioning while it is in alpha. Dates are based on the
corresponding Git tags when available.

## [0.5.0] - 2026-08-01

### Added

- Added capability-aware support tiers, directed CLI onboarding, and post-initialization
  agent connection planning.
- Added the official portable Universal Memory Agent Skill with optional, deterministic
  `npx skills` distribution and packaged offline fallbacks.
- Added a reviewed agent-to-project-skill-path catalog pinned to the exact external
  installer version.

### Changed

- Consolidated public distribution, package fallback, project initialization, and native
  consumption around the complete `skills/universal-memory/` source tree.
- Reduced fresh external installation from staged discovery and repeated adds to one
  project-scoped `npx skills add` followed by byte-exact validation.
- Preserved `use-universal-memory` as a non-destructive legacy alias and froze the
  Windsurf-specific adapter contract.
- Release provenance now validates prerelease tags against protected `dev` and final tags
  against protected `main`.

### Fixed

- Authorized external skill installation failures now return a non-zero CLI exit code and
  `ok: false` while preserving structured connection diagnostics.

### Security

- Added release provenance gates that require matching package/tag versions and
  byte-identical public, packaged, and wheel Agent Skill assets before publication.
- Unknown external agent IDs now fail closed before subprocess execution, and partial
  external mutations are reported without unsafe automatic cleanup.

## [0.4.0] - 2026-07-07

### Added

- Added shared project root support with commit-friendly `umem/project.toml`,
  `umem/memory/`, and `umem/skills/` paths while preserving private operational state
  under `.umem/`.
- Added shared-layout initialization, status, migration, doctor diagnostics, and
  CLI/MCP parity coverage.
- Added explicit shared skill flows so user-facing project skills can be reviewed and
  committed under `umem/skills/<slug>/`.

### Changed

- Project facts, rules, and user-facing skills now resolve through shared layout
  precedence when `umem/project.toml` is present.
- Migration to shared layout removes successfully migrated project facts from legacy
  `.umem/memory/facts.jsonl` while preserving private, global, conflicting, and
  operational records.
- Agent and user documentation now distinguish commit-friendly shared content from
  private `.umem/` operational state.

### Fixed

- Fixed shared-layout migration to materialize expected shared directories even when no
  shared skills exist.
- Fixed package readiness and doctor diagnostics around shared-root visibility,
  operational-root privacy, and legacy/shared overlaps.
- Fixed Git subprocess checks so inherited hook-local `GIT_*` environment variables do
  not make diagnostics inspect the caller repository instead of the target project.

## [0.3.0] - 2026-06-27

### Added

- Added a draft-first skill authoring flow with `skills draft create`,
  `skills draft validate`, and `skills publish`.
- Added explicit canonical skill adoption, validation, canonical update, slug rename,
  cleanup, and repair flows across CLI and MCP.
- Added `--check-gitignore` diagnostics for native skill sync targets.
- Added agent-facing lifecycle guidance so agents can choose between draft, create,
  adopt, import, canonical update, cleanup, repair, and sync without relying on `--help`.
- Added focused application, CLI, MCP, parity, docs, and quickstart coverage for the
  skill lifecycle flow.

### Changed

- Changed `skills create` and `skills publish` to keep native runtime sync explicit via
  `--sync` or `skills sync`.
- Improved lifecycle summary output with actionable next steps, dry-run/apply clarity,
  managed cleanup reporting, and gitignore diagnostics.
- Improved CLI help and documentation for safe defaults and neighboring skill lifecycle
  commands.

### Fixed

- Fixed canonical skill workflows that previously required manual registry or JSONL
  surgery for adoption, slug rename, canonical updates, and accidental target cleanup.

## [0.2.0] - 2026-06-25

### Added

- Added a refreshed MkDocs information architecture for user, agent, and contributor
  workflows.
- Added contributor guidance for CLI/MCP parity expectations, release readiness, alpha
  validation, and test requirements.
- Added documentation tests that enforce key onboarding, agent, contributor, and
  version metadata contracts.
- Added packaging tests to keep package, runtime fallback, docs metadata, and lockfile
  versions aligned.

### Changed

- Bumped the project version to `0.2.0` for the next alpha milestone.
- Reworked user documentation around agent-first usage, where users give UMEM to the
  agent and let the agent run the memory workflow.
- Reworked agent documentation as an adoption-oriented guide covering the skills
  repository as source of truth, short-term memory, long-term memory, host sync, and
  MCP/CLI parity.
- Replaced outdated contributor alpha pages with release readiness and alpha validation
  pages.
- Clarified supported Python guidance around the active package metadata instead of
  implying Python 3.12 is required.

### Fixed

- Hardened MCP setup UX and added coverage for dependency bounds and MCP server
  behavior.

## [0.1.5] - 2026-06-22

### Changed

- Updated README and user documentation with the 0.1.4 Agent Skills command flow.
- Clarified `.umem/skills` as the canonical Agent Skills source of truth, with complete
  synchronized native copies for supported runtimes.
- Added create, import, sync, recommend, and promote examples across CLI and MCP parity
  documentation.
- Updated the packaged `use-universal-memory` reference template so generated project
  guidance matches the project-owned docs.

### Security

- Bumped `starlette` from `1.0.1` to `1.3.1`, addressing StaticFiles path handling,
  form parser limit enforcement, HTTP method dispatch, and URL authority handling fixes.
- Bumped `python-multipart` from `0.0.29` to `0.0.31`, addressing form parsing,
  Content-Length validation, and parameter smuggling fixes.
- Bumped `cryptography` from `48.0.0` to `48.0.1`, updating packaged wheels to newer
  OpenSSL builds.
- Bumped `pydantic-settings` from `2.14.1` to `2.14.2`, fixing symlink traversal in
  nested secrets settings sources.

## [0.1.4] - 2026-06-22

### Added

- Added canonical Agent Skills lifecycle support with `.umem/skills/<slug>/SKILL.md` as
  the source of truth.
- Added `umem skills import <path> --sync` to adopt existing native skills into UMEM and
  distribute complete native copies to configured targets.
- Added `.agents/skills` as a managed native target for Codex/OpenAI-class hosts when
  supported by the runtime registry.
- Added Agent Skills documentation covering create, import, sync, update, target
  behavior, and CLI/MCP parity expectations.

### Changed

- Changed native skill sync to distribute complete managed skill copies instead of local
  wrapper files by default.
- Changed `update --skills` to keep canonical skill drift intentionally rather than
  overwriting local canonical edits.
- Improved native sync output by separating synced/affected paths from removed managed
  paths.
- Clarified hash semantics for skill sync payloads: canonical `SKILL.md` hashes are
  distinct from native target manifest tree hashes.
- Updated documentation assets to use absolute image URLs for PyPI rendering.
- Added public repository guardrails, grouped dependency update configuration, and SEO
  metadata for the documentation site.

### Fixed

- Fixed native skill sync cleanup so obsolete UMEM-managed target files are removed
  through snapshot/audit-backed safe writes while unmanaged local files are preserved.
- Fixed CLI/MCP parity around import-sync, sync removals, and removed path reporting.
- Fixed target hash reporting by marking native target hashes as
  `manifest_tree_sha256`.

## [0.1.3] - 2026-06-07

### Added

- Added a curated MkDocs documentation site with user, agent, contributor, and reference
  pages.
- Added a documentation publishing workflow for the docs site.
- Added expanded UMEM guide skill references for startup, context, memory facts, host
  sync, skill lifecycle, parity, and guardrails.

### Changed

- Packaged the UMEM guide skill references so installed distributions include the
  expected skill documentation.
- Clarified update command behavior so package upgrades are documented separately from
  project context and skill updates.
- Refined storage bootstrap follow-up documentation.

### Fixed

- Fixed packaged UMEM skill reference paths.
- Fixed UMEM storage and host sync regressions.
- Fixed storage bootstrap read-lock behavior.

## [0.1.2] - 2026-06-04

### Added

- Added `umem doctor` diagnostics for project and environment checks.
- Added project discovery metadata for package indexes and public repositories.
- Added community contribution guidelines and templates.

### Changed

- Translated planning and implementation artifacts to technical English.
- Bumped the package version for PyPI publishing.
- Applied formatting and lint cleanups across the codebase.

## [0.1.1] - 2026-06-04

### Changed

- Fixed README image and badge references for PyPI compatibility.
- Improved package metadata and installation guidance in the README.

## [0.1.0] - 2026-06-03

### Added

- Initial alpha release of Universal Memory as a local, vendor-agnostic memory layer for
  AI agents.
- Added local `.umem` project storage, TOML configuration, and project initialization.
- Added safe atomic writes, local snapshots, audit log listing, and rollback by scope.
- Added local fact storage, listing, purge, context hygiene, offline search, and context
  summary assembly.
- Added CLI commands for initialization, memory facts, context, status, rollback, host
  setup/sync, update, and skills operations.
- Added FastMCP server support with CLI/MCP parity tests and structured error envelopes.
- Added host instruction setup and sync for Codex `AGENTS.md` and Claude Code
  `CLAUDE.md`.
- Added latent skill tracking, proposal, generation, listing, detail, activation,
  deactivation, update, and mutation flows.
- Added native runtime registry groundwork and native skill support.
- Added `umem update`, default locale configuration, terminal splash, and proactive memory
  engagement guidance.
- Added PyPI publishing workflow, MIT license, comprehensive README, CI, pre-commit,
  pyright, ruff, and test coverage.

### Security

- Added secret scanning guardrails.
- Added safe-write snapshots and audit trails before mutations.

[0.5.0]: https://github.com/YanAmorelli/universal-memory/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/YanAmorelli/universal-memory/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/YanAmorelli/universal-memory/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/YanAmorelli/universal-memory/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/YanAmorelli/universal-memory/compare/v0.1.5...v0.2.0
[0.1.5]: https://github.com/YanAmorelli/universal-memory/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/YanAmorelli/universal-memory/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/YanAmorelli/universal-memory/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/YanAmorelli/universal-memory/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/YanAmorelli/universal-memory/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/YanAmorelli/universal-memory/releases/tag/v0.1.0
