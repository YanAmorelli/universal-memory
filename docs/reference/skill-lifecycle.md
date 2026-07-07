# Skill Lifecycle

Universal Memory manages canonical Agent Skills under the active project UMEM
roots. In shared-layout projects, reviewable user-facing skills live under
`umem/skills/`; private and operational skills live under `.umem/skills/`.
Agents can draft, validate, publish, create, adopt, import, share, maintain, and
sync skills through explicit safe commands.

## Lifecycle

1. Draft new work with `skills draft create`, validate it, then publish it with
   `skills publish`. This path is best when a human or agent should inspect the
   content before it becomes canonical.
2. Create a known canonical skill with `skills create`, or adopt/import existing work
   with `skills adopt` or `skills import`.
3. For recurring workflows that are not concrete skills yet, track them with
   `skills track` and promote/generate only after approval.
4. List and inspect canonical, disabled, draft, and candidate skills.
5. Synchronize active canonical skills into native runtime targets with `skills sync`.

## Canonical Vs Native

The canonical source after create, import, publish, promote, or generate is the
`SKILL.md` under the active UMEM skill root. Legacy projects use
`.umem/skills/<slug>/SKILL.md`. Shared-layout projects use
`umem/skills/<slug>/SKILL.md` for shared user-facing project skills and
`.umem/skills/<slug>/SKILL.md` for private or operational project skills. Native
runtime directories such as `.agents/skills/...`, `.opencode/skills/...`, or
`.antigravity/...` are materialized copies for specific agents. `skills sync`
may create or update those runtime directories, so review the resulting
worktree changes and ignore rules intentionally.

This is intentionally not a wrapper model. UMEM keeps one canonical copy under
`umem/skills/` or `.umem/skills/`, then writes complete native copies so each
host can consume skills in its own expected layout. For AGENTS.md/Codex/OpenAI-class
hosts that support Agent Skills, `.agents/skills/<slug>/SKILL.md` is a
native runtime target. It should be managed by the same sync flow as other
runtime targets, not treated as a manual compatibility directory. Wrappers are
only an explicit repository policy exception.

`skills create` and `skills publish` are canonical-only by default. Use `--sync` or
`skills sync` when native runtime target directories should be written. Use
`skills adopt` for existing UMEM skill roots such as `.umem/skills/<slug>` or
`umem/skills/<slug>`, and `skills import` for native directories such as
`.agents/skills/<slug>`. Use `skills share` when an existing project skill
should move into reviewable `umem/skills/`. Use `skills canonical update` to
replace canonical content through validation, `skills rename` to move a slug,
`skills cleanup` for one skill's managed native targets, and `skills repair` for
project-wide orphan target cleanup.

Shared-layout defaults are intentionally conservative:

| Skill kind | Default canonical path |
| --- | --- |
| User-facing project skill | `umem/skills/<slug>/SKILL.md` |
| Private project skill | `.umem/skills/<slug>/SKILL.md` |
| Operational project skill | `.umem/skills/<slug>/SKILL.md` |
| Legacy project skill | `.umem/skills/<slug>/SKILL.md` |

Operational skills cannot be written directly to `umem/skills/` through
`skills create`, `skills import`, `skills adopt`, or `skills publish`. Use
`skills share <skill> --category operational --yes` when a human has explicitly
approved repository-visible operational guidance.

## Adopt Existing Native Skill Into UMEM

Use this path when a local or native skill already exists and should become UMEM-owned:

```bash
umem status --format json
umem context --scope project --format json
umem skills list --format json
umem skills import .agents/skills/review-protocol --scope project --visibility shared --category user-facing --sync --format json
umem skills detail review-protocol --format json
```

Before mutating, confirm the target repository root. Use `--sync` when the import should
also materialize configured native copies from canonical in the same operation. Use
`--replace-native` only when intentionally rewriting the matching managed native source
during import.

If `native_installations` or `targets` is empty, the import still succeeded:
UMEM copied or adopted the source into a UMEM skill root, but no enabled runtime
target was written or adopted during that command. Re-run `umem skills import
... --sync` before other canonical changes, or run `umem skills sync
review-protocol --format json` after import.
Normal `git status` may hide `.umem/`, `.agents/`, `.opencode/`, or other runtime
directories when ignore rules exclude them.

When the adoption is a durable project decision, record it and sync host instructions:

```bash
umem remember "Adopted review-protocol as a UMEM canonical skill." --scope project --tag skills
umem host sync --apply --yes --format json
```

After import, edit the returned canonical `skill_file`. In a shared-layout
project this may be `umem/skills/review-protocol/SKILL.md` for user-facing
shared skills or `.umem/skills/review-protocol/SKILL.md` for private or
operational skills. Native wrappers are a repository policy choice, not UMEM's
default behavior. UMEM keeps the canonical source under one UMEM skill root and
synchronizes complete native copies for host runtimes.

Future migration flows should preserve this direction: adopt or import existing native
skills into the appropriate canonical UMEM skill root, validate configured
targets, then synchronize complete managed copies back to native runtime
directories. A `wrap-source` option may exist for repositories that deliberately
want wrappers, but it is not the recommended or default migration result.

## CLI Commands

```bash
umem skills track --name "Review Protocol" --description "Recurring review workflow"
umem skills list
umem skills detail <skill-id-or-name>
umem skills draft create --name "Review Protocol" --description "Recurring review workflow"
umem skills draft validate review-protocol
umem skills publish review-protocol --format summary
umem skills create --name "Review Protocol" --description "Recurring review workflow" --visibility shared --category user-facing --format summary
umem skills create --name "Local Bootstrap Helper" --description "Local bootstrap workflow" --category operational --format summary
umem skills adopt .umem/skills/review-protocol --scope project
umem skills import .agents/skills/review-protocol --scope project --visibility shared --category user-facing --sync
umem skills share use-universal-memory --category operational --yes --format summary
umem skills validate review-protocol
umem skills canonical update review-protocol --file <relative-skill-file>
umem skills rename review-protocol --slug review-checklist
umem skills cleanup review-checklist --targets --format summary
umem skills cleanup review-checklist --targets --apply
umem skills repair --remove-orphan-targets --format summary
umem skills repair --remove-orphan-targets --apply
umem skills sync review-protocol --check-gitignore --format summary
umem skills recommend --scope project
umem skills propose <latent-skill-id> --decision yes
umem skills promote <recommendation-id> --yes
umem skills generate <latent-skill-id> --yes
umem skills activate <latent-skill-id>
umem skills deactivate <latent-skill-id>
umem skills update <latent-skill-id> --name "Updated Skill"
umem update --skills
```

Use `--format summary` for concise human and agent-facing output on lifecycle commands.
It includes relevant paths, warnings, and short next steps; JSON output remains the
automation contract. Use `--check-gitignore` on `skills sync` to warn when generated
native runtime targets are tracked by git or not covered by ignore rules. The warning is
computed after target planning/writes and is diagnostic only: it does not edit `.gitignore`
or untrack files. Use
`umem skills sync <skill-id-or-name>` when validating or refreshing one skill. A bare
`umem skills sync` is project-wide and may report unrelated native targets. `umem update
--skills` is also project-wide maintenance; it preserves managed native drift with `keep`
and does not prompt for overwrite. Use explicit `umem skills sync <skill-id-or-name>
--drift-decision overwrite` when overwriting drift is intentional.

## File Shape

Generated skills use a canonical structure:

```text
umem/skills/<skill-slug>/        # shared user-facing
.umem/skills/<skill-slug>/       # legacy, private, or operational
  SKILL.md
  references/
  scripts/
```

`references/` and `scripts/` are optional, but useful for durable supporting
material and helper automation.

## Safety

Skill mutations should create snapshots and audit events. Native runtime sync should warn
before overwriting manually changed target files. Cleanup and repair are dry-run by default;
they only delete removable managed paths when `--apply` is present. Blocked paths
must be reviewed manually. `--check-gitignore` is a diagnostic warning path only; it does
not edit `.gitignore` or untrack files for you. When sync removes files that were
previously managed by UMEM but no longer exist in the canonical skill directory, the
removed files should be reported separately from written paths.
