# Data Model: Skill Authoring Flow

## Draft Skill

Represents skill work that is not yet active canonical content.

- `id`: stable identifier.
- `name`: public skill name from frontmatter.
- `slug`: requested project/global slug.
- `description`: frontmatter description.
- `scope`: project or global.
- `status`: draft.
- `draft_path`: project-relative path to draft `SKILL.md`.
- `created_at`, `updated_at`: lifecycle timestamps.
- `validation`: latest validation summary, if present.
- `metadata`: triggers, source path, authoring flow, and warnings.

Validation rules:

- Name, description, and skill file must be present.
- Slug must be unique among active canonical skills before publish.
- Draft paths must stay inside UMEM-managed authoring storage.
- Draft content must pass skill validation before publish.

State transitions:

- `created` -> `draft`
- `draft` -> `draft_invalid` when validation finds blocking issues
- `draft_invalid` -> `draft` after content changes and validation passes
- `draft` -> `active` when published

## Canonical Skill

Represents the UMEM-owned source of truth for a published skill.

- `id`: stable identifier.
- `name`: public skill name.
- `slug`: public and filesystem slug.
- `description`: frontmatter description.
- `scope`: project or global.
- `status`: active, disabled, or draft.
- `canonical_path`: project-relative path to canonical `SKILL.md`.
- `origin`: command or tool that last changed the skill.
- `content_hash`: hash of canonical content.
- `native_installations`: managed runtime targets.
- `source_recommendation_id`: optional latent-skill source.
- `metadata`: triggers, creation flow, import/adopt source, validation status, and sync metadata.

Validation rules:

- Active canonical skills must have a readable valid `SKILL.md`.
- Slug must be unique within scope.
- Canonical paths must stay under the expected project/global skill root.
- Rename must not overwrite an unmanaged canonical directory.

State transitions:

- `draft` -> `active` on publish.
- `active` -> `disabled` through existing deactivate flow.
- `disabled` -> `active` through existing activate flow.
- `active` -> `active` on update, rename, sync, validate, or cleanup.

## Native Runtime Target

Represents a runtime-specific synchronized copy or rule directory.

- `runtime`: runtime identifier.
- `path`: project-relative runtime target path.
- `status`: synced, drifted, skipped, removed, or blocked.
- `tree_hash`: managed content hash.
- `manifest`: managed file list and hashes.
- `drift_detected`: whether target content differs from the last managed state.
- `warnings`: unmanaged target, gitignore, tracked-file, or drift warnings.

Validation rules:

- UMEM may overwrite only managed drift when the user explicitly chooses overwrite.
- UMEM may remove only files recorded as managed unless unsafe cleanup is explicitly requested.
- Target paths must stay inside supported runtime roots.

## Skill Validation Report

Represents validation output for draft, canonical, or local skill content.

- `subject`: skill selector or local path.
- `status`: pass, warning, or fail.
- `checks`: ordered check results.
- `blocking_issues`: issues that prevent publish/adopt/update.
- `warnings`: non-blocking quality or repository-state issues.
- `affected_paths`: paths inspected.
- `recommended_next_steps`: concise recovery guidance.

Checks:

- Frontmatter has name and description.
- Triggers are well-formed when present.
- No placeholder markers remain.
- Relative links resolve within the skill directory.
- Referenced local scripts or files exist.
- Paths are relative and remain inside allowed roots.
- Risky command patterns are reported.

## Cleanup Plan

Represents a dry-run or apply cleanup operation.

- `skill`: skill selector.
- `mode`: targets or orphan-targets.
- `dry_run`: whether no files are deleted.
- `removable_paths`: managed paths eligible for deletion.
- `blocked_paths`: paths UMEM cannot prove are managed.
- `warnings`: drift, unmanaged content, or repository-state warnings.

Validation rules:

- Dry-run never deletes files.
- Apply mode deletes only managed paths by default.
- Cleanup reports blocked paths instead of guessing ownership.
