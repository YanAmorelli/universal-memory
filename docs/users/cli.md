# CLI Guide

The CLI is the canonical Universal Memory surface. MCP exposes equivalent
operations for agents and hosts, but the CLI is the clearest way to inspect and
debug behavior.

## Main Commands

```bash
umem --help
umem init
umem connect
umem bootstrap --format json
umem init --layout shared --yes
umem status
umem layout status
umem layout migrate --to shared --dry-run
umem doctor
umem context
umem remember
umem rollback
```

## Session Bootstrap

At the beginning of a conversation or agent session, use one bootstrap call instead of
separate status, project-context, and skills-list commands:

```bash
umem bootstrap --format json
```

The response keeps the existing payloads under `data.status`, `data.context`, and
`data.skills.list`. Treat `data.context` as active project guidance, inspect the catalog,
and retrieve details only for selected relevant skills:

```bash
umem skills detail <skill-id-or-name> --format json
```

Run bootstrap only once per conversation or session. It does not install, synchronize,
configure, or automatically expand skills. When MCP is available, prefer the semantically
equivalent `bootstrap()` tool.

## Project Layout

Shared-layout projects keep reviewable project context under `umem/` and
private operational state under `.umem/`.

```bash
umem init --layout shared --yes --format summary
umem layout status --format json
umem layout migrate --to shared --dry-run --format summary
umem layout migrate --to shared --apply --format json
```

Use `layout migrate --to shared --dry-run` before applying so facts, rules, and
skills can be reviewed. Use `--include facts`, `--include rules`, or
`--include skills` to narrow a migration. Use `--private-fact <fact-id>` or
`--private-skill <slug>` when legacy project content must remain under `.umem/`.
Use `--share-operational-skill <slug>` only after intentionally approving an
operational skill for repository sharing.

When migration is applied, migrated project facts are written to
`umem/memory/facts.jsonl` and removed from legacy `.umem/memory/facts.jsonl`.
Private, global, or conflicting legacy facts stay local. Operational files such
as context summaries remain under `.umem/`.

## Facts

```bash
umem remember "Project uses shared UMEM root." --scope project --visibility shared --tag architecture
umem remember "Local-only investigation note." --scope project --visibility private --tag private
umem facts list
umem facts list --scope project --visibility all
umem facts purge <fact-id>
umem facts hygiene
```

Facts support project and global scope. In shared-layout projects, project facts
default to shared and write to `umem/memory/facts.jsonl`; private project facts
write under `.umem/memory`. Global facts remain user-level preferences and
durable context outside the repository commit flow. JSON fact output includes
`visibility` and `storage_path` for project facts.

## Hosts

```bash
umem host setup codex
umem host check codex
umem host sync --apply --yes
```

Host commands configure instruction targets such as `AGENTS.md`, `CLAUDE.md`,
and supported native rule or skill directories.

`umem init` and `umem connect` keep portable installation simple: after consent,
UMEM uses the target pinned to the selected `skills` CLI version, executes one
project-scoped add, and validates the complete installed `universal-memory` tree.
Windsurf retains its legacy adapter, but receives no new host-specific behavior.

Projects containing only `.umem/skills/use-universal-memory/` continue using that
legacy root without automatic duplication or overwrite. If both legacy and
canonical Universal Memory roots exist, `init`, `update --skills`, and host setup
report a conflict and preserve both trees for an explicit migration decision.

## Skills

Skill placement depends on project layout and visibility. In legacy projects,
`.umem/skills/<slug>/SKILL.md` remains the canonical project source. In
shared-layout projects, user-facing shared skills use
`umem/skills/<slug>/SKILL.md`; private skills and operational skills use
`.umem/skills/<slug>/SKILL.md`. Native runtime folders are complete synchronized
copies, not the place to evolve the skill long term.

```bash
umem skills list
umem skills detail <skill-id-or-name>
umem skills create --name "Review Protocol" --description "Recurring review workflow" --visibility shared --category user-facing
umem skills create --name "Local Bootstrap Helper" --description "Local agent bootstrap" --category operational
umem skills import .agents/skills/review-protocol --scope project --visibility shared --category user-facing --sync
umem skills share universal-memory --category operational --yes --format summary
umem skills sync review-protocol
umem skills sync review-protocol --drift-decision overwrite
umem skills track --name "Review Protocol" --description "Recurring review workflow"
umem skills recommend --scope project
umem skills propose <latent-skill-id> --decision yes
umem skills promote <recommendation-id> --yes
umem skills generate <latent-skill-id> --yes
umem skills activate <latent-skill-id>
umem skills deactivate <latent-skill-id>
umem skills update <latent-skill-id> --name "Updated Skill"
umem update --skills
```

Use `skills create` for a new canonical skill. Use `skills import <path> --sync`
when a skill already exists under a native directory such as
`.agents/skills/...`. Use `skills share <skill>` when an existing project skill
should move from private or operational storage into `umem/skills`. Operational
skills, including `universal-memory`, require explicit confirmation before
they can be shared.

Use `skills sync <skill-id-or-name>` when validating or refreshing one skill; a
bare `skills sync` and `umem update --skills` are project-wide maintenance
operations.

`skills update`, `activate`, and `deactivate` currently operate on latent/generated skill
IDs. To change an imported canonical skill, edit the canonical `SKILL.md` under
`umem/skills/<slug>/` or `.umem/skills/<slug>/`, then run `umem skills sync
<slug>`.

Skill mutations use the same safe mutation pipeline as other persistent changes, including
snapshots and audit events for managed writes and removals.

## JSON Output

Most commands accept:

```bash
--format json
```

Use JSON output for scripts, tests, and agent workflows. JSON responses use a
standard envelope with `ok`, `operation`, `scope`, `data`, and `warnings`.
