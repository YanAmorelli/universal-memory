# Skills Lifecycle

Use this reference for UMEM skill discovery, latent skill tracking, approval, generation,
activation, deactivation, and updates.

## Use Cases

- Track a recurring workflow or methodology as a latent skill candidate.
- Create a skill directly when the user already knows the desired skill.
- Review and approve or reject a latent skill proposal.
- Generate the canonical Agent Skills directory structure.
- List and inspect active, disabled, and candidate skills.
- Deactivate a skill without deleting its files.
- Reactivate a disabled skill after validating its `SKILL.md`.
- Update skill metadata, triggers, or full markdown content through the safe mutation
  pipeline.

## Canonical CLI

```bash
umem skills list --format json
umem skills detail <skill-id-or-name> --format json
umem skills create --name "Skill name" --description "What the skill does." --scope project --trigger "when to use it" --format json
umem skills track --name "Skill name" --description "What the skill does." --scope project --evidence-summary "Why this pattern recurred." --tag workflow --format json
umem skills recommend --scope project --format json
umem skills propose <latent-skill-id> --decision yes --format json
umem skills propose <latent-skill-id> --decision always --format json
umem skills propose <latent-skill-id> --decision no --format json
umem skills generate <latent-skill-id> --yes --format json
umem skills generate <latent-skill-id> --yes --update-existing --format json
umem skills deactivate <latent-skill-id> --format json
umem skills activate <latent-skill-id> --format json
umem skills update <latent-skill-id> --name "New name" --description "New description." --trigger "when to use it" --format json
umem skills update <latent-skill-id> --file <relative-markdown-path> --format json
```

## Parameters

- `<skill-id-or-name>`: identifier or unique name for read-only detail.
- `<latent-skill-id>`: exact latent skill ID for proposal and mutations.
- `--name <text>`: skill display name.
- `--description <text>`: concise purpose and behavior.
- `--scope project|global`: project is default; global is for cross-project agent
  workflows.
- `--evidence-summary <text>`: curated reason this recurring pattern should be tracked.
- `--tag <tag>`: repeatable trigger or classification.
- `--min-recurrence <count>`: optional read-only recommendation threshold; default is 2.
- `--decision yes|always|no`: explicit proposal decision for non-interactive use.
- `--yes`: required for non-interactive generation.
- `--update-existing`: update an existing generated skill directory instead of choosing
  an alternate slug.
- `--trigger <text>`: repeatable trigger used in generated skill frontmatter.
- `--file <relative-markdown-path>`: complete replacement markdown for `SKILL.md`.
- `--format json`: canonical automation output.

## MCP Equivalents

- `list_skills()`
- `get_skill_detail(name_or_id="<skill-id-or-name>")`
- `create_skill(name="Skill name", description="What the skill does.", scope="project", raw_markdown="<complete SKILL.md content>")`
- `track_latent_skill(name="Skill name", description="What the skill does.", scope="project", evidence_summary="Why this pattern recurred.", tags=["workflow"])`
- `recommend_skills(scope="project", min_recurrence=null, dry_run=true)`
- `propose_skill(latent_skill_id="<latent-skill-id>", decision="yes")`
- `propose_skill(latent_skill_id="<latent-skill-id>", decision="always")`
- `propose_skill(latent_skill_id="<latent-skill-id>", decision="no")`
- `generate_skill(latent_skill_id="<latent-skill-id>", update_existing=false)`
- `generate_skill(latent_skill_id="<latent-skill-id>", update_existing=true)`
- `deactivate_skill(latent_skill_id="<latent-skill-id>")`
- `activate_skill(latent_skill_id="<latent-skill-id>")`
- `update_skill(latent_skill_id="<latent-skill-id>", name="New name", description="New description.", triggers=["when to use it"])`
- `update_skill(latent_skill_id="<latent-skill-id>", raw_markdown="<complete SKILL.md content>")`

## Expected Behavior

- `skills list` returns active, candidate, and disabled skills with relative paths when
  materialized.
- `skills detail` returns triggers and metadata without loading large references.
- `skills create` writes a requested canonical skill directly; use it when the user asks
  for a known skill instead of routing through latent tracking.
- `skills track` explicitly creates or increments a proposed latent skill from curated observed evidence; it does not automatically scan history.
- `skills recommend` is read-only candidate review over explicit latent skill records; promotion, import, generation, and sync are separate explicit workflows.
- `skills generate` creates canonical files under `.umem/skills/` for project skills.
- `skills deactivate` preserves files and changes status to disabled.
- `skills activate` requires a readable, valid `SKILL.md`.
- `skills update` writes through snapshot, secret scanning, audit, and rollback-capable
  safe write behavior.

## Latent Tracking Criteria

Track a latent skill only when the observed pattern is durable, reusable, and operational:

- A methodology the agent followed repeatedly across similar tasks.
- A review pattern with a stable checklist or triage structure.
- A transformation that maps one artifact shape to another in repeatable steps.
- A domain process with recurring inputs, decisions, and outputs.
- A multi-step operating procedure future agents could follow safely.

Do not track a latent skill for:

- A one-off task or transient implementation detail.
- A vague preference; record durable preferences as memory facts instead.
- Secrets, credentials, raw logs, raw prompts, environment dumps, or private customer data.
- Speculative, uncertain, or weakly observed patterns.
- Checklist-only compliance when no reusable workflow was actually observed.

## Safe Evidence Summaries

Evidence summaries must be curated and minimal. Prefer relative paths and short behavioral
summaries over raw artifacts.

Good examples:

- `Repeated BMAD story implementation flow observed: load story, update sprint status,
  implement tasks in order, validate, and update Dev Agent Record.`
- `Review checklist recurred across src/application/host and tests/application/host:
  compact host manifest, pointer-based guidance, no raw memory dumps.`

Bad examples:

- Raw command output, stack traces, logs, prompts, or pasted user data.
- Secret-containing examples or private customer details.
- Absolute local paths when a relative path would identify the evidence.

## Promotion And Approval

- Surface why a latent candidate is useful and ask the user before promotion.
- Never auto-promote or generate a skill without explicit approval.
- If the user already requested a specific skill, skip latent tracking and use direct
  `create_skill` or `umem skills create`.
