# Startup And Context

Use this reference when beginning a session or when an agent needs the current UMEM
state before planning, editing, investigating, reviewing, or using another workflow.

## Use Cases

- Confirm whether the current project is initialized and healthy.
- Load project context plus relevant global preferences.
- Discover active or candidate skills before acting.
- Inspect one relevant skill without loading large reference files unless needed.
- Continue without external memory only after reporting that UMEM is unavailable or not
  initialized.

## Canonical CLI

```bash
umem bootstrap --format json
umem context --scope project --max-size-chars 4000 --format json
umem context --scope global --format json
umem skills detail <skill-id-or-name> --format json
```

## Parameters

- `--format json`: use for agent automation and deterministic parsing.
- `bootstrap` uses project scope and the default 4000-character context limit.
- `--scope project|global`: choose project for targeted repository context; choose global only
  when the task is explicitly cross-project.
- `--max-size-chars <number>`: cap returned context when the caller has a tight context
  budget.
- `<skill-id-or-name>`: skill identifier or unique skill name. Use the ID when a name is
  ambiguous.

## MCP Equivalents

- `bootstrap()`
- `context(scope="project", max_size_chars=<number>)` for a targeted refresh
- `context(scope="global")`
- `get_skill_detail(name_or_id="<skill-id-or-name>")`

## Expected Behavior

- Treat bootstrap `data.context` as active project guidance.
- Read bootstrap `data.skills.list` and select only relevant skills for detail lookup.
- Treat `skills detail` as a lightweight metadata read; it should not force loading large
  files under a skill's `references/` directory.
- Do not repeat the full startup sequence on every user message in the same conversation.
  Query specific UMEM state only when the task requires it.
