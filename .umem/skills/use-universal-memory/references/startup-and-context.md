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
umem status --format json
umem context --scope project --format json
umem context --scope project --max-size-chars 4000 --format json
umem context --scope global --format json
umem skills list --format json
umem skills detail <skill-id-or-name> --format json
```

## Parameters

- `--format json`: use for agent automation and deterministic parsing.
- `--scope project|global`: choose project for repository context; choose global only
  when the task is explicitly cross-project.
- `--max-size-chars <number>`: cap returned context when the caller has a tight context
  budget.
- `<skill-id-or-name>`: skill identifier or unique skill name. Use the ID when a name is
  ambiguous.

## MCP Equivalents

- `status()`
- `context(scope="project", max_size_chars=<number>)`
- `context(scope="global")`
- `list_skills()`
- `get_skill_detail(name_or_id="<skill-id-or-name>")`

## Expected Behavior

- Treat `context` output as active project guidance.
- Treat `skills detail` as a lightweight metadata read; it should not force loading large
  files under a skill's `references/` directory.
- Do not repeat the full startup sequence on every user message in the same conversation.
  Query specific UMEM state only when the task requires it.
