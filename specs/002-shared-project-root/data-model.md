# Data Model: Shared Project Root

## Project Layout Configuration

Represents the active project storage mode and path policy.

- `schema_version`: shared layout metadata version.
- `layout`: `legacy`, `shared`, or `partial`.
- `shared_root`: project-relative visible root, default `umem`.
- `operational_root`: project-relative local root, default `.umem`.
- `precedence`: deterministic conflict policy, default `shared_over_legacy`.
- `visibility_defaults`: defaults for project memories, project skills, rules, and operational skills.
- `shared_operational_skills`: allowlisted operational skill slugs that may be shared.
- `migration`: latest migration status, timestamp, and report reference.

Validation rules:

- Paths must be project-relative and must not contain `..` segments.
- `shared_root` must not equal `operational_root`.
- `layout=shared` requires `umem/project.toml`.
- `operational_root` remains writable for audit, snapshots, locks, and private content.

State transitions:

- `legacy` -> `partial` when `umem/` exists without a complete policy or migration.
- `legacy` -> `shared` after explicit shared initialization or applied migration.
- `partial` -> `shared` after conflicts and missing shared paths are resolved.
- `shared` -> `partial` when doctor detects missing shared paths or conflicts requiring review.

## Project Shared Root

Visible repository content intended for team review.

- `root_path`: `umem`.
- `policy_path`: `umem/project.toml`.
- `memory_path`: `umem/memory`.
- `facts_path`: `umem/memory/facts.jsonl`.
- `rules_path`: `umem/memory/rules.jsonl`.
- `skills_path`: `umem/skills`.

Validation rules:

- Shared root must not be ignored by repository ignore rules.
- Shared root files must use project-relative paths in output.
- Shared root must not contain locks, snapshots, audit events, summaries, drafts, or generated runtime target manifests.

## Project Operational Root

Hidden local storage for runtime state and private project content.

- `root_path`: `.umem`.
- `config_path`: `.umem/config.toml`.
- `audit_path`: `.umem/audit/events.jsonl`.
- `snapshots_path`: `.umem/snapshots`.
- `locks_path`: `.umem/locks`.
- `summaries_path`: `.umem/memory`.
- `private_facts_path`: `.umem/memory/private_facts.jsonl`.
- `private_skills_path`: `.umem/skills`.
- `drafts_path`: `.umem/skills/drafts`.

Validation rules:

- Operational root must stay writable locally.
- Operational root should not be tracked as repository content except explicitly approved bootstrap files.
- Shared-layout locks for shared files are stored under `.umem/locks`, not beside the shared files.

## Curated Project Memory

Project-scoped fact intended to be shared through the repository.

- `id`: stable fact identifier.
- `content`: durable fact text.
- `scope`: `project`.
- `status`: active, stale, archived, or purged.
- `tags`: curated tags.
- `visibility`: `shared`.
- `storage_path`: `umem/memory/facts.jsonl`.
- `source_layout`: `shared` or `migrated_from_legacy`.
- `content_hash`: hash used for idempotent migration checks.
- `metadata`: migration source, privacy decision, and audit references.

Validation rules:

- Global facts must never be stored as curated project memory.
- Shared facts must pass the existing secret scan before write.
- Re-running migration must not duplicate an existing fact ID or identical content hash.

State transitions:

- `legacy_project_fact` -> `curated_project_memory` during migration when not private or skipped.
- `curated_project_memory` -> `private_project_memory` only through explicit visibility change.
- `active` -> `stale` or `archived` through existing fact lifecycle commands.

## Private Project Memory

Project-scoped fact that remains local in shared-layout projects.

- `id`: stable fact identifier.
- `content`: private fact text.
- `scope`: `project`.
- `status`: active, stale, archived, or purged.
- `visibility`: `private`.
- `storage_path`: `.umem/memory/private_facts.jsonl` for new private records.
- `source_layout`: `private`, `legacy`, or `migrated_private`.
- `metadata`: privacy reason and optional migration decision.

Validation rules:

- Private project memories are included in local context assembly but excluded from shared-root migration results unless explicitly selected.
- Private project memories must not be written under `umem/`.

## User-Facing Project Skill

Canonical skill intended for repository collaborators and future agents.

- `id`: stable skill identifier.
- `name`: public skill name.
- `slug`: filesystem-safe slug.
- `description`: frontmatter description.
- `scope`: `project`.
- `status`: active, disabled, or draft.
- `visibility`: `shared`.
- `category`: `user_facing`.
- `canonical_path`: `umem/skills/<slug>/SKILL.md`.
- `content_hash`: hash of canonical content.
- `native_installations`: managed runtime targets.
- `metadata`: validation, migration source, and sync metadata.

Validation rules:

- Slugs must be unique within shared and private project skill registries.
- Shared skill directories must contain a valid `SKILL.md`.
- Native runtime sync remains explicit and writes generated runtime copies separately.

State transitions:

- `legacy_canonical_skill` -> `user_facing_project_skill` during migration when classified as user-facing.
- `private_project_skill` -> `user_facing_project_skill` through explicit share command.
- `active` -> `disabled` through existing deactivate flow.

## Operational Skill

Skill used for local agent bootstrap or repository workflow operation.

- `id`: stable skill identifier.
- `slug`: filesystem-safe slug.
- `scope`: `project`.
- `status`: active, disabled, or draft.
- `visibility`: `private` by default.
- `category`: `operational`.
- `canonical_path`: `.umem/skills/<slug>/SKILL.md`.
- `shared_allowed`: whether repository policy explicitly allows publication.
- `metadata`: operational reason and bootstrap target references.

Validation rules:

- `use-universal-memory` is operational and private by default.
- Operational skills can be shared only when `shared_allowed=true` or the slug is listed in `shared_operational_skills`.
- Shared operational skills must still pass normal skill validation.

## Layout Migration Report

User-facing summary of a dry run or applied migration.

- `operation`: `layout.migrate`.
- `source_layout`: usually `legacy`.
- `target_layout`: `shared`.
- `dry_run`: whether no files were written.
- `copied`: shared records written.
- `already_shared`: records already present with matching ID, slug, or hash.
- `skipped`: global, private, operational, invalid, or unsupported records.
- `conflicts`: overlapping IDs, slugs, or divergent content.
- `remaining_local`: operational and private paths left under `.umem/`.
- `affected_paths`: project-relative paths written or inspected.
- `next_steps`: commit, review, ignore, or resolve guidance.

Validation rules:

- Applied migration must be safe to re-run.
- Migration must report every legacy project memory and canonical project skill as copied, already shared, skipped, private, operational, or conflicting.
- Global facts and global skills must be reported as out of scope, not copied.

## Layout Health Check

Diagnostic result produced by `umem doctor`.

- `layout_mode`: `legacy`, `shared`, `partial`, or `uninitialized`.
- `shared_visibility`: status for shared root ignore/tracking visibility.
- `operational_privacy`: status for tracked operational paths.
- `overlaps`: legacy/shared fact IDs, rule IDs, and skill slugs with active precedence.
- `git_status_available`: whether Git metadata was available.
- `status`: success, warning, or failed.
- `recovery_hint`: concise next step.

Validation rules:

- Healthy shared layout requires complete shared paths, visible shared content, private operational state, and no unresolved overlaps.
- In a non-Git directory, repository visibility checks degrade to warnings with a clear explanation.

## Repository Visibility Policy

Repository review decision for shared and operational paths.

- `shared_paths`: paths expected to be reviewable, default `umem/`.
- `operational_paths`: paths expected to remain local, default `.umem/`.
- `allowed_tracked_operational_paths`: explicit exceptions.
- `ignored_shared_paths`: shared paths currently hidden by ignore rules.
- `tracked_operational_paths`: operational paths currently tracked by Git.

Validation rules:

- `umem/` should not be ignored when layout is shared.
- `.umem/audit`, `.umem/snapshots`, `.umem/locks`, `.umem/memory/private_facts.jsonl`, and default operational skills should not be tracked.
- Explicit exceptions must be visible in `umem/project.toml`.
