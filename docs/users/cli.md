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
umem host sync --apply
```

Host commands configure instruction targets such as `AGENTS.md`, `CLAUDE.md`,
and supported native rule or skill directories.

## Skills

```bash
umem skills list
umem skills detail <skill-id-or-name>
umem skills track --name "Review Protocol" --description "Recurring review workflow"
umem skills propose <latent-skill-id>
umem skills generate <latent-skill-id>
umem skills activate <latent-skill-id>
umem skills deactivate <latent-skill-id>
umem skills update <latent-skill-id> --name "Updated Skill"
```

Skill mutations use the same safe mutation pipeline as other persistent changes.

## JSON Output

Most commands accept:

```bash
--format json
```

Use JSON output for scripts, tests, and agent workflows. JSON responses use a
standard envelope with `ok`, `operation`, `scope`, `data`, and `warnings`.
