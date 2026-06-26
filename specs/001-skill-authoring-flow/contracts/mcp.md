# MCP Contract: Skill Authoring Flow

Every new CLI capability must have an MCP tool with matching behavior and compatible JSON data keys where the existing parity contract applies.

## Tool Description Standard

Every new MCP tool must describe:

- Purpose in one sentence.
- When an agent should use it.
- When an agent should use a neighboring tool instead.
- Required inputs and side effects.
- Whether native runtime targets can be changed by the call.

## Tools

### `create_skill_draft`

Creates a draft skill.

Parameters:

- `name`: string.
- `description`: string.
- `scope`: `project` or `global`, default `project`.
- `slug`: optional string.
- `triggers`: optional list of strings.
- `raw_markdown`: optional full `SKILL.md` content.

Returns:

- Operation `skills.draft.create`.
- Draft identifier, slug, draft path, affected paths, validation status, warnings.

### `validate_skill`

Validates a draft, canonical skill, or local path.

Parameters:

- `skill_or_path`: string.
- `scope`: optional `project` or `global`.

Returns:

- Operation `skills.validate`.
- Validation report with status, checks, blocking issues, warnings, affected paths.

### `publish_skill`

Publishes a draft as canonical.

Parameters:

- `draft_or_path`: string.
- `slug`: optional string.
- `sync`: boolean, default false.
- `targets`: optional list of runtime IDs.

Returns:

- Operation `skills.publish`.
- Canonical skill payload, affected paths, native installations when sync is requested.

### `adopt_skill`

Adopts an existing skill path into UMEM.

Parameters:

- `path`: string.
- `scope`: `project` or `global`, default `project`.
- `slug`: optional string.
- `sync_after_adopt`: boolean, default false.
- `replace_native`: boolean, default false.

Returns:

- Operation `skills.adopt`.
- Canonical skill payload, adopted source, affected paths, warnings, native installations.

### `rename_skill`

Renames a canonical skill slug.

Parameters:

- `skill_id_or_name`: string.
- `slug`: string.

Returns:

- Operation `skills.rename`.
- Updated canonical skill payload, old path, new path, affected paths, warnings.

### `update_canonical_skill`

Updates canonical skill content.

Parameters:

- `skill_id_or_name`: string.
- `raw_markdown`: string.
- `sync`: boolean, default false.
- `drift_decision`: `keep` or `overwrite`, default `keep`.

Returns:

- Operation `skills.canonical.update`.
- Updated canonical skill payload, validation report, affected paths, native installations when sync is requested.

### `cleanup_skill`

Cleans managed targets for a skill.

Parameters:

- `skill_id_or_name`: string.
- `targets`: boolean, default true.
- `dry_run`: boolean, default true.

Returns:

- Operation `skills.cleanup`.
- Cleanup plan, removed paths when apply mode is used, blocked paths, warnings.

### `repair_skills`

Repairs managed orphan target state.

Parameters:

- `remove_orphan_targets`: boolean.
- `dry_run`: boolean, default true.

Returns:

- Operation `skills.repair`.
- Repair plan, removed paths when apply mode is used, blocked paths, warnings.

## Parity Rules

- CLI JSON operation names and MCP operation names must match.
- CLI and MCP payloads must expose equivalent top-level data keys for the same capability.
- Errors must use existing sanitized validation/storage error handling.
- Paths inside the project must be project-relative.
