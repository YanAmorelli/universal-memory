# CLI Guide

The CLI is the canonical Universal Memory surface. MCP exposes equivalent
operations for agents and hosts, but the CLI is the clearest way to inspect and
debug behavior.

## Main Commands

```bash
umem --help
umem init
umem status
umem doctor
umem context
umem remember
umem rollback
```

## Facts

```bash
umem facts list
umem facts purge <fact-id>
umem facts hygiene
```

Facts support project and global scope. Project facts live with the repository;
global facts are user-level preferences and durable context.

## Hosts

```bash
umem host setup codex
umem host check codex
umem host sync --apply --yes
```

Host commands configure instruction targets such as `AGENTS.md`, `CLAUDE.md`,
and supported native rule or skill directories.

## Skills

Use `.umem/skills/<slug>/SKILL.md` as the canonical source. Native runtime folders are
complete synchronized copies, not the place to evolve the skill long term.

```bash
umem skills list
umem skills detail <skill-id-or-name>
umem skills create --name "Review Protocol" --description "Recurring review workflow"
umem skills import .agents/skills/review-protocol --scope project --sync
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

Use `skills create` for a new canonical skill. Use `skills import <path> --sync` when a
skill already exists under a native directory such as `.agents/skills/...`. Use
`skills sync <skill-id-or-name>` when validating or refreshing one skill; a bare
`skills sync` and `umem update --skills` are project-wide maintenance operations.

`skills update`, `activate`, and `deactivate` currently operate on latent/generated skill
IDs. To change an imported canonical skill, edit `.umem/skills/<slug>/SKILL.md`, then run
`umem skills sync <slug>`.

Skill mutations use the same safe mutation pipeline as other persistent changes, including
snapshots and audit events for managed writes and removals.

## JSON Output

Most commands accept:

```bash
--format json
```

Use JSON output for scripts, tests, and agent workflows. JSON responses use a
standard envelope with `ok`, `operation`, `scope`, `data`, and `warnings`.
