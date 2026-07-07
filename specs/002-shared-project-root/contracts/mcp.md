# MCP Contract: Shared Project Root

Every CLI capability added for the shared project root must have an MCP equivalent with matching behavior and compatible JSON keys where the parity contract applies.

## Tool Description Standard

Each new or changed tool must describe:

- Purpose in one sentence.
- When an agent should use it.
- Whether it mutates shared repository content, operational local state, or both.
- How project-relative paths are reported.
- Whether global memory or global skills are excluded.

## New Tools

### `inspect_project_layout`

Reports the active layout without mutation.

Parameters:

- None.

Returns:

- `operation`: `layout.status`.
- `scope`: `project`.
- `layout`: `legacy`, `shared`, `partial`, or `uninitialized`.
- `shared_root`, `operational_root`, `precedence`, `warnings`, and `recommended_actions`.

### `migrate_project_layout`

Copies curated legacy project content into the shared root.

Parameters:

- `target_layout`: literal `shared`.
- `dry_run`: boolean, default true.
- `include`: optional list containing `facts`, `rules`, and/or `skills`.
- `private_fact_ids`: optional list of project fact IDs to keep local.
- `private_skill_slugs`: optional list of project skill slugs to keep local.
- `shared_operational_skill_slugs`: optional list of operational skill slugs explicitly approved for sharing.

Returns:

- `operation`: `layout.migrate`.
- Layout migration report fields from [data-model.md](../data-model.md).
- `warnings` for conflicts, skipped global content, ignored shared root, or tracked operational state.

## Changed Tools

### `initialize_project`

Adds layout selection.

Parameters:

- `layout`: `legacy` or `shared`, default `legacy`.
- Existing runtime/host selection parameters if exposed by the runtime wrapper.

Returns:

- Existing init payload.
- Added `layout`, `shared_root`, `operational_root`, `shared_paths`, and `operational_paths`.

### `remember_fact`

Adds project fact visibility.

Parameters:

- Existing `content`, `scope`, `source`, `tags`, and metadata fields.
- `visibility`: `shared` or `private`, project scope only.

Returns:

- Existing remember payload.
- Added `visibility` and `storage_path`.

Error behavior:

- Rejects `visibility` for global scope with a validation error.

### `list_facts`

Adds visibility filtering and storage metadata.

Parameters:

- Existing `scope` and `status`.
- `visibility`: `shared`, `private`, or `all`, default `all`.

Returns:

- Existing fact list payload.
- Each project fact includes `visibility` and `storage_path`.

### `create_skill`

Adds project skill visibility and category.

Parameters:

- Existing skill creation parameters.
- `visibility`: `shared` or `private`, project scope only.
- `category`: `user-facing` or `operational`, default `user-facing`.

Returns:

- Existing canonical skill payload.
- Added `visibility`, `category`, and effective canonical path.

### `import_skill`, `adopt_skill`, and `publish_skill`

Follow the same visibility and category parameters as `create_skill`.

Returns:

- Existing payloads plus `visibility`, `category`, and effective canonical path.

### `share_skill`

Explicitly shares an existing project skill.

Parameters:

- `skill_id_or_name`: ID, name, or slug.
- `category`: `user-facing` or `operational`.
- `confirm_operational`: boolean, required true for operational skills.

Returns:

- `operation`: `skills.share`.
- Updated canonical skill payload.
- `old_canonical_path`, `new_canonical_path`, `affected_paths`, `warnings`, and `recommended_actions`.

### `doctor`

Includes shared-layout checks in the existing doctor result.

Returns:

- Existing doctor envelope.
- Additional check names: `project_layout_mode`, `shared_root_visibility`, `operational_root_privacy`, and `layout_overlaps`.

## Parity Rules

- CLI JSON operation names and MCP operation names must match.
- CLI and MCP payloads expose equivalent top-level data keys for the same capability.
- Shared-layout validation errors use existing sanitized validation/storage error handling.
- Paths inside the project are always project-relative.
- Global records are never returned as migration candidates for project shared content.
