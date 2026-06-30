# Research: Shared Project Root

## Decision: Use `umem/` as the visible shared project root

Rationale: `umem/` is short, brand-aligned, and visibly commit-friendly because it is not a dot directory. It avoids mixing reviewable repository context with `.umem/` operational data while preserving the existing `.umem` bootstrap, audit, snapshot, and config behavior.

Alternatives considered:

- `.umem/` only: rejected because hidden repository content remains easy to ignore during review.
- `memory/`: rejected because it is generic and more likely to collide with user application directories.
- `docs/umem/`: rejected because skills and machine-readable facts are operational repository context, not documentation pages.

## Decision: Put shared layout metadata in `umem/project.toml`

Rationale: A committed marker lets cloned repositories discover that the shared layout is active without depending on local `.umem/config.toml`. The file can hold the schema version, shared/operational roots, visibility defaults, and allowlists for explicitly shared operational skills.

Alternatives considered:

- `.umem/config.toml` only: rejected because it remains local and does not travel with the shared project context.
- No marker file: rejected because an empty or partially migrated `umem/` directory would be ambiguous.
- JSON metadata: rejected because the project already uses TOML for configuration and has `tomli-w`.

## Decision: Keep operational state and locks out of `umem/`

Rationale: The shared root should contain only reviewable content. Locks, snapshots, audit events, summaries, drafts, and runtime bootstrap skills are local execution state and would create noisy or unsafe repository changes if written under `umem/`.

Alternatives considered:

- Adjacent locks such as `umem/memory/facts.jsonl.lock`: rejected because they violate the shared/operational split.
- Disable locking for shared files: rejected because repository writes still need race protection.

## Decision: Resolve project storage by layout and visibility

Rationale: Existing repositories already own fact, rule, and canonical skill reads/writes. A layout resolver can choose between legacy, shared, and private storage paths without duplicating use case logic. In shared layout, default project facts and user-facing project skills write to `umem/`; private project content and operational skills write to `.umem/`.

Alternatives considered:

- Separate shared repositories: rejected because it would duplicate list/search/write behavior and increase parity risk.
- Migration-only copy with no runtime resolver: rejected because new shared-layout projects need normal commands to write shared content.

## Decision: Shared content takes deterministic precedence over legacy overlaps

Rationale: Once `umem/project.toml` opts into shared layout, shared files are the active repository content. Reads should merge shared and private local records, but if the same project fact ID, rule ID, or skill slug exists in both shared and legacy storage, the shared record wins and doctor reports the overlap.

Alternatives considered:

- Legacy wins: rejected because it would make the shared root misleading after migration.
- Hard failure on any overlap: rejected because partially migrated projects need readable diagnostics and safe next steps.
- Timestamp wins: rejected because it is harder to explain and can produce surprising results after copy-based migration.

## Decision: Migration copies by default and remains idempotent

Rationale: Copying curated project memories and user-facing skills into `umem/` preserves rollback options and avoids data loss. The migration report records copied, already shared, skipped, private, operational, and conflicting items. Re-running migration compares stable IDs, slugs, and content hashes before writing.

Alternatives considered:

- Move by default: rejected because interrupted migration could strand users between layouts.
- Always overwrite shared content: rejected because it could discard intentional shared edits.
- Require manual file moves: rejected because it would not provide a reliable migration report.

## Decision: Treat `use-universal-memory` as operational by default

Rationale: The skill is local agent bootstrap guidance and can expose repository-specific policy. It should stay under `.umem/skills/use-universal-memory/` unless project metadata explicitly allowlists it for shared publication.

Alternatives considered:

- Share all active project skills by default: rejected because it would publish operational guidance unintentionally.
- Hard-code only one private skill name: rejected because repositories may add more operational skills later.

## Decision: Extend `umem doctor` for layout health

Rationale: `umem doctor` is already the project health check. Adding layout mode, shared visibility, operational privacy, and overlap checks keeps users on one diagnostics command and preserves CLI/MCP parity.

Alternatives considered:

- Add only `umem layout doctor`: rejected because users already expect `doctor` to summarize environment health.
- Rely only on migration output: rejected because health needs to be checked repeatedly after edits and Git changes.
