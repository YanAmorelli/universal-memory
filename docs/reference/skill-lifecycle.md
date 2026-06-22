# Skill Lifecycle

Universal Memory manages canonical Agent Skills under `.umem/skills/`. Agents can
create a new canonical skill, import an existing local/native skill, track a recurring
workflow as a latent candidate, and sync canonical skills into native runtime targets.

## Lifecycle

1. Create a new canonical skill with `skills create`, or import an existing skill with
   `skills import`.
2. For recurring workflows that are not concrete skills yet, track them with
   `skills track` and promote/generate only after approval.
3. List and inspect canonical, disabled, and candidate skills.
4. Synchronize active canonical skills into native runtime targets with `skills sync`.

## Canonical Vs Native

`.umem/skills/<slug>/SKILL.md` is the canonical source after create, import, promote, or
generate. Native runtime directories such as `.agents/skills/...`, `.opencode/skills/...`,
or `.antigravity/...` are materialized copies for specific agents. `skills sync` may create
or update those runtime directories, so review the resulting worktree changes and ignore
rules intentionally.

This is intentionally not a wrapper model. UMEM keeps the canonical copy under
`.umem/skills/`, then writes complete native copies so each host can consume skills in its
own expected layout. For AGENTS.md/Codex/OpenAI-class hosts that support Agent Skills,
`.agents/skills/<slug>/SKILL.md` is a native runtime target. It should be managed by the
same sync flow as other runtime targets, not treated as a manual compatibility directory.
Wrappers are only an explicit repository policy exception.

`skills update`, `activate`, and `deactivate` currently target latent/generated skill IDs,
not every canonical Agent Skill ID returned by `skills list`. To edit an imported canonical
skill, modify `.umem/skills/<slug>/SKILL.md`, then run `umem skills sync <slug>`.

## Adopt Existing Native Skill Into UMEM

Use this path when a local or native skill already exists and should become UMEM-owned:

```bash
umem status --format json
umem context --scope project --format json
umem skills list --format json
umem skills import .agents/skills/review-protocol --scope project --sync --format json
umem skills detail review-protocol --format json
```

Before mutating, confirm the target repository root. Use `--sync` when the import should
also materialize configured native copies from canonical in the same operation. Use
`--replace-native` only when intentionally rewriting the matching managed native source
during import.

If `native_installations` or `targets` is empty, the import still succeeded: UMEM copied or
adopted the source into `.umem/skills/`, but no enabled runtime target was written or
adopted during that command. Re-run `umem skills import ... --sync` before other
canonical changes, or run `umem skills sync review-protocol --format json` after import.
Normal `git status` may hide `.umem/`, `.agents/`, `.opencode/`, or other runtime
directories when ignore rules exclude them.

When the adoption is a durable project decision, record it and sync host instructions:

```bash
umem remember "Adopted review-protocol as a UMEM canonical skill." --scope project --tag skills
umem host sync --apply --yes --format json
```

After import, edit `.umem/skills/review-protocol/SKILL.md`. Native wrappers are a
repository policy choice, not UMEM's default 0.1.4 behavior. UMEM keeps the canonical
source under `.umem/skills/` and synchronizes complete native copies for host runtimes.

Future migration flows should preserve this direction: adopt or import existing native
skills into canonical `.umem/skills/`, validate configured targets, then synchronize
complete managed copies back to native runtime directories. A `wrap-source` option may
exist for repositories that deliberately want wrappers, but it is not the recommended or
default migration result.

## CLI Commands

```bash
umem skills track --name "Review Protocol" --description "Recurring review workflow"
umem skills list
umem skills detail <skill-id-or-name>
umem skills create --name "Review Protocol" --description "Recurring review workflow"
umem skills import .agents/skills/review-protocol --scope project --sync
umem skills sync review-protocol
umem skills propose <latent-skill-id>
umem skills generate <latent-skill-id>
umem skills activate <latent-skill-id>
umem skills deactivate <latent-skill-id>
umem skills update <latent-skill-id> --name "Updated Skill"
umem update --skills
```

Use `umem skills sync <skill-id-or-name>` when validating or refreshing one skill. A bare
`umem skills sync` is project-wide and may report unrelated native targets. `umem update
--skills` is also project-wide maintenance; it preserves managed native drift with `keep`
and does not prompt for overwrite. Use explicit `umem skills sync <skill-id-or-name>
--drift-decision overwrite` when overwriting drift is intentional.

## File Shape

Generated skills use a canonical structure:

```text
.umem/skills/<skill-slug>/
  SKILL.md
  references/
  scripts/
```

`references/` and `scripts/` are optional, but useful for durable supporting
material and helper automation.

## Safety

Skill mutations should create snapshots and audit events. Native runtime sync should warn
before overwriting manually changed target files. When sync removes files that were
previously managed by UMEM but no longer exist in the canonical skill directory, the
removed files should be reported separately from written paths.
