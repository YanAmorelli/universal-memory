# CLI Contract: Shared Project Root

## Output Formats

New and changed commands support the existing formats:

- `--format human`: current interactive output style.
- `--format json`: stable automation envelope.
- `--format summary`: concise status, paths, warnings, and next steps.

All paths in user-facing output must be project-relative.

## Initialization

### `umem init --layout legacy|shared`

Initializes the project layout.

Inputs:

- `--layout legacy|shared`, default `legacy` for compatibility.
- Existing runtime, host, locale, `--yes`, and `--format` options.

Expected result:

- `legacy` creates the existing `.umem` layout.
- `shared` creates `.umem` operational storage plus `umem/project.toml`, `umem/memory`, and `umem/skills`.
- Default operational guidance such as `use-universal-memory` remains under `.umem/skills`.
- JSON payload includes `layout`, `shared_root`, `operational_root`, `shared_paths`, `operational_paths`, and existing init fields.

## Layout Commands

### `umem layout status`

Reports the active project layout without mutating files.

Inputs:

- `--format human|json|summary`.

Expected result:

- Reports `legacy`, `shared`, `partial`, or `uninitialized`.
- Reports effective precedence when both legacy and shared content exist.
- Reports shared and operational roots.

### `umem layout migrate --to shared`

Copies curated legacy project content into the shared root.

Inputs:

- `--to shared`.
- `--dry-run`, default for interactive use.
- `--apply`.
- `--include facts|rules|skills` repeatable; default includes project facts, project rules, and project canonical skills.
- `--private-fact <id>` repeatable to keep selected project facts local.
- `--private-skill <slug>` repeatable to keep selected project skills local.
- `--share-operational-skill <slug>` repeatable for explicit operational skill publication.
- `--format human|json|summary`.

Expected result:

- Dry run reports what would be copied, skipped, kept private, or conflicting.
- Apply writes `umem/project.toml` and missing shared files through safe-write.
- Apply removes migrated project facts from legacy `.umem/memory/facts.jsonl`;
  private, global, and conflicting facts remain local.
- Re-running apply does not duplicate facts, rules, skill registrations, or skill directories.
- Global facts and global skills are reported as skipped out of scope.
- Operational skills are skipped unless explicitly shared.

JSON operation:

- `operation`: `layout.migrate`.
- `scope`: `project`.
- `data`: layout migration report fields from [data-model.md](../data-model.md).

## Memory Commands

### `umem remember`

Adds visibility selection for project-scoped facts.

Inputs:

- Existing content, scope, tag, source, and format options.
- `--visibility shared|private`, project scope only.
- `--private` alias for `--visibility private`.

Expected result:

- In legacy layout, project facts continue writing to `.umem/memory/facts.jsonl`.
- In shared layout, project facts default to `shared` and write to `umem/memory/facts.jsonl`.
- In shared layout, private project facts write to `.umem/memory/private_facts.jsonl`.
- Global facts reject `--visibility shared|private` because global storage remains outside project commit flows.
- JSON payload includes `visibility`, `storage_path`, and existing fact fields.

### `umem facts list`

Reports visibility for project facts.

Inputs:

- Existing scope, status, and format options.
- `--visibility shared|private|all`, default `all`.

Expected result:

- Shared-layout project listings merge shared facts and private local project facts.
- Output includes `visibility` and `storage_path`.
- Legacy facts in a shared-layout project are labeled `legacy` when still present.

## Skill Commands

### `umem skills create`

Adds visibility and category selection for project canonical skills.

Inputs:

- Existing name, description, scope, slug, trigger, sync, target, and format options.
- `--visibility shared|private`, project scope only.
- `--category user-facing|operational`, default `user-facing`.

Expected result:

- In legacy layout, project skills continue writing to `.umem/skills/<slug>/`.
- In shared layout, user-facing project skills default to `umem/skills/<slug>/`.
- Operational project skills default to `.umem/skills/<slug>/`.
- Operational skills require explicit `--visibility shared` plus policy allowlist before writing under `umem/skills`.
- JSON payload includes `visibility`, `category`, and canonical path.

### `umem skills import|adopt|publish`

Follows the same project visibility and category rules as `skills create`.

Expected result:

- Shared user-facing skills become canonical under `umem/skills/<slug>/`.
- Private or operational skills remain canonical under `.umem/skills/<slug>/`.
- Native runtime sync remains explicit and unchanged.

### `umem skills share <skill>`

Explicitly marks an existing project skill as shared.

Inputs:

- `<skill>` ID, name, or slug.
- `--category user-facing|operational`.
- `--yes` for operational skills.
- `--format human|json|summary`.

Expected result:

- Copies the canonical skill into `umem/skills/<slug>/` when allowed.
- Updates project metadata and registry visibility.
- For operational skills, updates `umem/project.toml` allowlist so the decision is reviewable.
- Does not sync native runtime targets unless a separate sync command is run.

## Doctor

### `umem doctor`

Extends existing diagnostics with shared-layout checks.

Expected added checks:

- `project_layout_mode`: legacy, shared, partial, or uninitialized.
- `shared_root_visibility`: warns when `umem/` is ignored or not reviewable.
- `operational_root_privacy`: warns when `.umem` operational files are tracked.
- `layout_overlaps`: reports legacy/shared fact IDs, rule IDs, or skill slugs and active precedence.

JSON payload:

- Existing doctor envelope remains.
- Checks use existing `name`, `status`, `detail`, `error`, and `recovery_hint` fields.
- Warnings do not block unrelated doctor checks from running.
