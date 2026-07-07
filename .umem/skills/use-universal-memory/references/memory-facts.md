# Memory Facts

Use this reference for durable facts: storing useful knowledge, inspecting stored facts,
and removing obsolete or incorrect memory.

## Use Cases

- Store a stable project decision, architecture note, workflow, bug fix, command, or
  constraint.
- Store a global user preference that should apply across repositories.
- List facts to verify current memory before updating it.
- Purge an outdated or incorrect fact by ID.
- Avoid storing transient task progress, raw command output, secrets, credentials, or
  unverified claims.

## Canonical CLI

```bash
umem remember "Short verified fact." --scope project --tag architecture --format json
umem remember "Shared project fact." --scope project --visibility shared --tag architecture --format json
umem remember "Private project note." --scope project --visibility private --tag private --format json
umem remember "Durable user preference." --scope global --tag preference --format json
umem facts list --scope project --visibility all --format json
umem facts list --scope global --format json
umem facts purge --id <fact-id> --format json
```

If host instructions should reflect the change, sync after the mutation:

```bash
umem host sync --apply --yes --format json
```

## Parameters

- `"Short verified fact."`: one concise sentence; prefer specific, reusable knowledge.
- `--scope project|global`: project for repository-specific knowledge, global for
  cross-project user preferences.
- `--visibility shared|private`: project-only visibility. In shared-layout
  projects, shared facts write to `umem/memory/facts.jsonl`; private facts write
  under `.umem/memory`.
- `--tag <tag>`: use curated tags such as `architecture`, `workflow`, `bug`, `testing`,
  `docs`, `preference`, or `security`.
- `--id <fact-id>`: exact fact ID returned by `facts list`.
- `--format json`: canonical machine-readable output.

## MCP Equivalents

- `remember_fact(content="Short verified fact.", scope="project", tags=["architecture"])`
- `remember_fact(content="Shared project fact.", scope="project", visibility="shared", tags=["architecture"])`
- `remember_fact(content="Private project note.", scope="project", visibility="private", tags=["private"])`
- `remember_fact(content="Durable user preference.", scope="global", tags=["preference"])`
- `list_facts(scope="project", visibility="all")`
- `list_facts(scope="global")`
- `purge_fact(id="<fact-id>", confirm=true)`
- `sync_instructions(apply=true)`

## Expected Behavior

- Mutations should use the safe write pipeline: secret scan, snapshot, atomic write, and
  audit event.
- If a fact is uncertain, verify or ask before recording it.
- If a fact is obsolete, purge the old fact instead of adding a contradictory one.
- Do not place operational state, raw logs, secrets, local-only investigations,
  or private customer context in shared project facts.
- In shared-layout projects, review `storage_path` and `visibility` before
  committing `umem/memory` changes.
