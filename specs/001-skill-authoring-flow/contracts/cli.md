# CLI Contract: Skill Authoring Flow

## Output Formats

Skill lifecycle commands accept:

- `--format human`: existing interactive output.
- `--format json`: full success/error envelope for automation.
- `--format summary`: concise interactive summary with status, paths, warnings, and next steps.

Non-skill commands may continue treating `summary` as human output unless explicitly specialized later.

## Help Text Standard

Every new or changed skill command must include CLI help that covers:

- What the command does in one sentence.
- When to use it and when to use the nearest alternative command instead.
- Whether the command mutates canonical files, registry metadata, native runtime targets, or only validates.
- Safety defaults such as no implicit sync, dry-run behavior, managed-only cleanup, and drift handling.
- Required inputs and the smallest common example.

## Draft Commands

### `umem skills draft create`

Creates an editable draft skill without active canonical registration or native sync.

Required inputs:

- `--name <text>`
- `--description <text>`

Optional inputs:

- `--slug <slug>`
- `--scope project|global`
- `--trigger <text>` repeatable
- `--file <relative-markdown-path>`
- `--format human|json|summary`

Expected result:

- Draft record or draft path is created.
- No native runtime target is written.
- Summary output shows draft path and next validation command.

### `umem skills draft validate <draft-or-path>`

Validates a draft skill.

Expected result:

- Pass/fail validation report.
- Blocking issues prevent publish.
- Summary output lists the smallest actionable issue set.

### `umem skills publish <draft-or-path>`

Publishes a valid draft as canonical.

Optional inputs:

- `--slug <slug>`
- `--sync`
- `--target <runtime>` repeatable
- `--format human|json|summary`

Expected result:

- Without `--sync`, only canonical skill files and registry metadata are affected.
- With `--sync`, configured or selected native targets are synchronized.

## Create And Adopt Commands

### `umem skills create`

Default behavior changes to canonical-only.

Inputs:

- Existing `--name`, `--description`, `--trigger`, `--scope`
- New `--slug <slug>`
- New `--sync`
- Existing or compatible `--target <runtime>` repeatable when syncing
- `--format human|json|summary`

Expected result:

- Without `--sync`, affected paths include canonical files and registry only.
- With `--sync`, native runtime targets are included.

### `umem skills adopt <path>`

Registers an existing skill directory or `SKILL.md`.

Optional inputs:

- `--slug <slug>`
- `--scope project|global`
- `--sync`
- `--replace-native`
- `--format human|json|summary`

Expected result:

- Existing `.umem/skills/<slug>` can be adopted in place.
- Existing native skill directories can be copied or adopted according to existing import safety rules.
- Slug conflicts fail with actionable guidance.

### `umem skills import <path>`

Remains compatible. It may share implementation with adopt, but its documented behavior must clearly state whether it copies, adopts, syncs, or replaces native targets.

## Canonical Maintenance Commands

### `umem skills canonical update <skill>`

Updates canonical skill content through the supported canonical flow.

Required input:

- `--file <relative-markdown-path>`

Optional inputs:

- `--sync`
- `--drift-decision keep|overwrite`
- `--format human|json|summary`

Expected result:

- Validates replacement content.
- Writes canonical content safely.
- Syncs native targets only when requested.

### `umem skills rename <skill> --slug <slug>`

Renames a canonical skill slug.

Expected result:

- Updates canonical path and registry metadata.
- Updates or reports affected native target manifests.
- Blocks unmanaged destination conflicts.

### `umem skills validate <skill-or-path>`

Validates draft, canonical, or local skill content.

Expected result:

- Reports pass/fail checks, warnings, and next steps.
- Does not mutate files.

### `umem skills cleanup <skill>`

Cleans accidental or obsolete managed native targets.

Inputs:

- `--targets`
- `--dry-run` default for interactive use
- `--apply`
- `--format human|json|summary`

Expected result:

- Dry-run reports removable and blocked paths.
- Apply removes only managed paths by default.

### `umem skills repair`

Repairs managed skill lifecycle state.

Inputs:

- `--remove-orphan-targets`
- `--dry-run` default for interactive use
- `--apply`
- `--format human|json|summary`

Expected result:

- Reports orphan managed targets.
- Removes only managed orphan targets in apply mode.

## Existing Error Contract

When `umem skills update <id-or-name>` receives a canonical skill selector that the command does not support, the error must include:

- The matched canonical skill name or slug.
- The canonical file path.
- The correct canonical update command or exact edit-and-sync guidance.
