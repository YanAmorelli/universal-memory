# Guardrails And Recording

Use this reference before finalizing a task, changing memory, or deciding whether a
recurring workflow should become a skill.

## What To Record

Record only curated, durable information:

- Architecture decisions and repository conventions.
- Commands or workflows that future agents will need again.
- Verified bug fixes and important troubleshooting findings.
- Stable user preferences in global scope.
- Repeated methodologies that are strong candidates for a formal skill.

## What Not To Record

Do not record:

- Secrets, credentials, tokens, private keys, or environment dumps.
- Raw logs, long command output, stack traces, or large pasted files.
- Temporary task progress that will be irrelevant after the current turn.
- Unverified assumptions or guesses.
- Duplicate facts that should instead update or purge an existing fact.

## Canonical CLI

```bash
umem facts list --scope project --format json
umem facts list --scope global --format json
umem remember "Short verified fact." --scope project --tag workflow --format json
umem remember "Durable user preference." --scope global --tag preference --format json
umem facts purge --id <fact-id> --format json
umem skills track --name "Skill name" --description "Reusable workflow." --scope project --evidence-summary "Observed recurring workflow." --tag workflow --format json
umem host sync --apply --yes --format json
```

## MCP Equivalents

- `list_facts(scope="project")`
- `list_facts(scope="global")`
- `remember_fact(content="Short verified fact.", scope="project", tags=["workflow"])`
- `remember_fact(content="Durable user preference.", scope="global", tags=["preference"])`
- `purge_fact(id="<fact-id>", confirm=true)`
- `track_latent_skill(name="Skill name", description="Reusable workflow.", scope="project", evidence_summary="Observed recurring workflow.", tags=["workflow"])`
- `sync_instructions(apply=true)`

## Final Response Footer

Before completing a turn:

1. Decide whether the task produced a durable fact, skill pattern, architectural decision,
   bug fix, or obsolete memory cleanup.
2. If yes, record or purge it through UMEM and sync host instructions when needed.
3. If no, do not mutate memory.
4. End the final response with exactly one UMEM footer:

```text
[UMEM: Remembered "..."]
[UMEM: No new facts/skills to record]
```

## Safety Rules

- Use project scope unless the information clearly applies across repositories.
- Prefer one short sentence per remembered fact.
- Use tags that future agents can filter reliably.
- Do not run bulk cleanup, rollback, or destructive hygiene without explicit user
  confirmation.
- If UMEM storage is unavailable, report it and continue without external memory rather
  than inventing context.

