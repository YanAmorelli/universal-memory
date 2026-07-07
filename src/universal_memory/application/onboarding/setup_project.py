# ruff: noqa: E501

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from universal_memory.domain import ConfigValidationPort, InvalidConfigError, ProjectLayoutPort
from universal_memory.domain.entities.runtime import RuntimeId, default_runtime_registry
from universal_memory.infrastructure.config.toml_loader import load_config, update_project_config

DEFAULT_ENABLED_RUNTIME_IDS = [
    runtime_id.value for runtime_id in default_runtime_registry().runtime_ids
]
DEFAULT_ENABLED_HOST_IDS = DEFAULT_ENABLED_RUNTIME_IDS
DEFAULT_UMEM_SKILL_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_UMEM_SKILL_NAME = "use-universal-memory"
DEFAULT_UMEM_SKILL_RELATIVE_PATH = ".umem/skills/use-universal-memory/SKILL.md"
DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH = ".umem/memory/latent_skills.jsonl"
DEFAULT_UMEM_SKILL_MARKDOWN = """---
name: "use-universal-memory"
description: "Operational hub for using Universal Memory context, facts, host sync, and skills lifecycle."
triggers:
  - "at the start of a work session or conversation"
  - "before implementing, investigating, reviewing, or planning in a repository with .umem"
  - "when the user mentions memory, facts, context, skills, AGENTS.md, CLAUDE.md, host sync, or learned preferences"
  - "before recording durable project or global knowledge"
  - "before creating, updating, activating, or deactivating a UMEM skill"
---

# Use Universal Memory

## Purpose

Universal Memory (`umem`) is the repository memory and skill layer. This skill is the
single UMEM guide and router: use it to load current memory context, interpret UMEM
state, decide whether deeper instructions are needed, and route directly to the focused
reference for the task.

Keep this as one guide-style skill. Do not split UMEM into separate skills for startup,
facts, host sync, or skill lifecycle work unless the user explicitly approves that design
change.

## Desired Outcomes

- Agents begin repository work with current UMEM context and relevant active skills.
- Users get behavior informed by durable project facts and global preferences without
  host files becoming memory dumps.
- Memory mutations are deliberate, safe, scoped correctly, and synced when they should
  affect future host instructions.
- References are loaded only on demand, preserving Agent Skills progressive disclosure.

## Data Sources

- `.umem/` project storage and generated project skills.
- `AGENTS.md` and `CLAUDE.md` managed UMEM bootstrap instructions.
- CLI output from `umem status`, `umem context`, `umem skills list`, and targeted read or
  mutation commands.
- MCP tool results when available; treat them as equivalent automation surfaces over the
  CLI behavior contract.
- `references/` files in this skill for deeper task-specific procedures.

## Mandatory Startup

At the start of a conversation, session, or new task, load UMEM context before planning,
editing, investigating, reviewing, or activating another workflow:

```bash
umem status --format json
umem context --scope project --format json
umem skills list --format json
```

Then inspect any relevant active skill:

```bash
umem skills detail <skill-id-or-name> --format json
```

Prefer the equivalent MCP tools when they are available. Use the CLI examples in the
references as the canonical behavior contract.

## Workflow And State Interpretation

- If `status` reports UMEM unavailable or uninitialized, say so explicitly and continue
  without external memory instead of inventing context.
- Treat `context --scope project` output as active repository guidance for the current
  work session.
- Treat global context as cross-project user preference; do not let it override explicit
  project constraints or user instructions for the current task.
- Treat `skills list` as discovery metadata. Inspect only relevant active skills with
  `skills detail`, and load deeper skill files only when the current task calls for them.
- Do not repeat the full startup sequence on every user message in the same conversation;
  query only the specific UMEM state needed after the initial preflight.
- Preserve relative paths in specs, docs, code, and reports.

## Latent Skill Decision Loop

- During substantial work and before the final response, consider whether you observed a
  repeated, durable workflow that would help future agents.
- If a reusable methodology, checklist, transformation, review pattern, or domain workflow
  recurs, call `track_latent_skill` or `umem skills track` with a short name,
  description, tags, and a sanitized evidence summary.
- If the user explicitly asks to create a new skill from scratch, use direct
  `create_skill` or `umem skills create`; do not create a latent candidate first.
- If the user points to an existing local or native skill directory, use
  `import_skill` or `umem skills import <path>`; do not recreate it with `create`,
  `track`, `promote`, or `generate`.
- If no durable repeated workflow was observed, do not call `track_latent_skill` just to
  satisfy a checklist.
- Never track secrets, raw logs, raw prompts, private customer data, uncertain patterns, or
  one-off preferences as latent skill evidence. Route durable preferences to memory facts.

## Reference Routing

- For startup, health, context loading, and active-skill discovery, read
  `references/startup-and-context.md`.
- For remembering, listing, and purging facts, read `references/memory-facts.md`.
- For skill creation, import, sync, latent tracking, proposal, generation, listing,
  detail, activation, deactivation, and update, read `references/skills-lifecycle.md`.
- For host instruction setup, validation, and sync, read
  `references/host-instructions-sync.md`.
- For CLI/MCP payload parity and error behavior, read `references/cli-mcp-parity.md`.
- For durable recording rules, security guardrails, and final response footer behavior,
  read `references/guardrails-and-recording.md`.

## Response And Recording Constraints

- Keep host instruction files compact; they should point to UMEM, not store memory dumps.
- Record only curated, durable facts or skills. Do not persist raw logs, secrets,
  credentials, transient steps, or uncertain information.
- Use project scope for repository-specific knowledge and global scope for cross-project
  user preferences.
- After any memory mutation that should affect host instructions, run host sync with
  apply enabled.
- Before the final response, decide whether a durable fact, skill pattern, architectural
  decision, or obsolete memory should be recorded or cleaned up.
- End the final response with either `[UMEM: Remembered "..."]` or
  `[UMEM: No new facts/skills to record]`.
"""
DEFAULT_UMEM_SKILL_REFERENCES = {
    ".umem/skills/use-universal-memory/references/startup-and-context.md": """# Startup And Context

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
""",
    ".umem/skills/use-universal-memory/references/memory-facts.md": """# Memory Facts

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
""",
    ".umem/skills/use-universal-memory/references/skills-lifecycle.md": """# Skills Lifecycle

Use this reference for UMEM skill discovery, direct creation, importing existing local
or native skills, syncing canonical skills to native runtimes, latent skill tracking,
approval, generation, activation, deactivation, and updates.

## Mental Model

- Canonical skill: the `SKILL.md` under the active UMEM skill root is the source
  of truth after `create`, `import`, `publish`, `promote`, or `generate`.
- Shared-layout user-facing project skills use `umem/skills/<slug>/SKILL.md`;
  private and operational project skills use `.umem/skills/<slug>/SKILL.md`.
- Legacy project skills continue to use `.umem/skills/<slug>/SKILL.md`.
- Native skill target: `.agents/skills/<slug>/`, `.opencode/skills/<slug>/`, or another
  runtime directory is a synchronized copy for a specific agent host.
- AGENTS.md/Codex/OpenAI-class hosts that support Agent Skills should use
  `.agents/skills/<slug>/SKILL.md` as a native runtime target managed by UMEM.
- Edit direction: change the canonical skill first, then run `skills sync` to refresh
  native runtime copies.
- Import direction: use `skills import` when an existing native skill should become
  canonical. Import copies the source into the appropriate UMEM skill root; it
  does not make every runtime copy current until `skills sync` runs.
- Share direction: use `skills share` when an existing project skill should move
  into reviewable `umem/skills/`. Operational skills require explicit
  confirmation and an allowlist entry in `umem/project.toml`.
- Wrapper direction: wrapper stubs are a local exception only. The default UMEM model is
  canonical source plus complete synchronized native copies.

## Use Cases

- Track a recurring workflow or methodology as a latent skill candidate.
- Draft a skill when content may need validation before publish.
- Create a skill directly when the user already knows the desired skill.
- Adopt existing canonical work in place when it already lives under a UMEM skill
  root such as `.umem/skills/<slug>/` or `umem/skills/<slug>/`.
- Import an existing local or native skill directory into the canonical UMEM
  skill registry.
- Share a project skill into `umem/skills/` only when repository-visible skill
  content is intentional.
- Sync canonical skills into supported native runtime targets after import or changes.
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
umem skills draft create --name "Skill name" --description "What the skill does." --scope project --trigger "when to use it" --format json
umem skills draft validate <draft-or-path> --format json
umem skills publish <draft-or-path> --format summary
umem skills create --name "Skill name" --description "What the skill does." --scope project --visibility shared --category user-facing --trigger "when to use it" --format summary
umem skills create --name "Local bootstrap" --description "Local-only operational behavior." --scope project --category operational --format summary
umem skills adopt .umem/skills/<skill-name> --scope project --format summary
umem skills import .agents/skills/<skill-name> --scope project --visibility shared --category user-facing --sync --format json
umem skills share use-universal-memory --category operational --yes --format summary
umem skills validate <skill-id-or-name-or-path> --format json
umem skills canonical update <skill-id-or-name> --file <relative-markdown-path> --format json
umem skills rename <skill-id-or-name> --slug <new-slug> --format json
umem skills cleanup <skill-id-or-name> --targets --format summary
umem skills cleanup <skill-id-or-name> --targets --apply --format summary
umem skills repair --remove-orphan-targets --format summary
umem skills repair --remove-orphan-targets --apply --format summary
umem skills sync <skill-id-or-name> --check-gitignore --format summary
umem skills import .agents/skills/<skill-name>/SKILL.md --scope project --replace-native --sync --format json
umem skills sync <skill-id-or-name> --format json
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

Use `umem skills sync <skill-id-or-name>` when validating or refreshing one skill. A bare
`umem skills sync` is project-wide and may report unrelated native targets. `umem update
--skills` is also project-wide maintenance; it preserves managed native drift with `keep`
and does not prompt for overwrite. Use explicit `umem skills sync <skill-id-or-name>
--drift-decision overwrite` when overwriting drift is intentional.

## Parameters

- `<skill-id-or-name>`: identifier or unique name for read-only detail.
- `<latent-skill-id>`: exact latent skill ID for proposal and mutations.
- `.agents/skills/<skill-name>` or `<path>/SKILL.md`: existing Agent Skills directory
  or its `SKILL.md`; import copies it into the canonical UMEM skill root.
- `--name <text>`: skill display name.
- `--description <text>`: concise purpose and behavior.
- `--scope project|global`: project is default; global is for cross-project agent
  workflows.
- `--visibility shared|private`: project-only placement. Shared user-facing
  skills use `umem/skills`; private skills use `.umem/skills`.
- `--category user-facing|operational`: project skill category. Operational
  skills default private and require `skills share ... --category operational
  --yes` before they become repository-visible.
- `--evidence-summary <text>`: curated reason this recurring pattern should be tracked.
- `--tag <tag>`: repeatable trigger or classification.
- `--min-recurrence <count>`: optional read-only recommendation threshold; default is 2.
- `--decision yes|always|no`: explicit proposal decision for non-interactive use.
- `--yes`: required for non-interactive generation.
- `--update-existing`: update an existing generated skill directory instead of choosing
  an alternate slug.
- `--replace-native`: after import, rewrite the matching managed native source target
  from the canonical copy. Omit it when you only want UMEM to adopt the source without
  rewriting the original native directory during import.
- `--trigger <text>`: repeatable trigger used in generated skill frontmatter.
- `--file <relative-markdown-path>`: complete replacement markdown for `SKILL.md`.
- `--format json`: canonical automation output.
- `--format summary`: concise human and agent-facing output with status, paths, warnings,
  dry-run/apply status, and next steps.
- `--check-gitignore`: sync diagnostic that warns when generated native runtime targets
  are tracked by git or not covered by ignore rules. The check runs after target planning/writes
  and is diagnostic only: do not edit `.gitignore` or untrack files from this warning alone.
  In automation, report the warning and let repository policy decide whether ignore rules should change.

## MCP Equivalents

- `list_skills()`
- `get_skill_detail(name_or_id="<skill-id-or-name>")`
- `create_skill_draft(name="Skill name", description="What the skill does.", scope="project")`
- `validate_skill(skill_or_path="<skill-id-or-name-or-path>")`
- `publish_skill(draft_or_path="<draft-or-path>", sync=false)`
- `create_skill(name="Skill name", description="What the skill does.", scope="project", raw_markdown="<complete SKILL.md content>", sync=false)`
- `create_skill(name="Skill name", description="What the skill does.", scope="project", visibility="shared", category="user-facing", raw_markdown="<complete SKILL.md content>", sync=false)`
- `adopt_skill(path=".umem/skills/<skill-name>", scope="project", sync_after_adopt=false)`
- `import_skill(path=".agents/skills/<skill-name>", scope="project", replace_native=false, sync_after_import=true)`
- `share_skill(skill_id_or_name="use-universal-memory", category="operational", confirm_operational=true)`
- `update_canonical_skill(skill_id_or_name="<skill-id-or-name>", raw_markdown="<complete SKILL.md content>", sync=false)`
- `rename_skill(skill_id_or_name="<skill-id-or-name>", slug="<new-slug>")`
- `cleanup_skill(skill_id_or_name="<skill-id-or-name>", targets=true, dry_run=true)`
- `repair_skills(remove_orphan_targets=true, dry_run=true)`
- `sync_skills(skill_id_or_name="<skill-id-or-name>", targets=null, drift_decision="keep")`
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
- `skills draft create` writes editable draft content only; validate and publish before sync.
- `skills create` writes a requested canonical skill directly and does not sync native
  targets unless `--sync` is present.
- `skills publish` converts a draft to canonical and does not sync native targets unless
  `--sync` is present.
- `skills adopt` registers existing UMEM skill-root work in place without
  creating a suffixed duplicate.
- Use `skills import`, not `skills adopt`, for existing native runtime directories such
  as `.agents/skills/<slug>` or `.opencode/skills/<slug>`.
- `skills validate`, `skills canonical update`, `skills rename`, `skills cleanup`, and
  `skills repair` are the supported maintenance path for canonical skills.
- `skills import` is the normal path for an existing `.agents/skills/...`, `.opencode/skills/...`,
  or other local Agent Skills directory. It registers a canonical UMEM skill and copies
  the source directory into the appropriate UMEM skill root.
- In shared-layout projects, user-facing project skills default to shared
  `umem/skills`; operational skills default to private `.umem/skills`.
- `skills share` is the explicit path for moving an existing project skill into
  `umem/skills`. For operational skills, require human approval or an explicit
  non-interactive `--yes`/`confirm_operational=true`.
- `skills sync` materializes canonical skills into configured native runtime targets;
  importing a skill does not necessarily make it available to every runtime until sync
  runs.
- `skills sync --check-gitignore --format summary` is the preferred interactive safety
  check when a user wants actionable warnings about tracked or unignored runtime targets.
  It warns after sync planning/writes and never edits `.gitignore` or untracks files.
- `skills sync` can create or update runtime directories such as `.opencode/skills/...`,
  `.agents/skills/...`, or `.antigravity/...` depending on configured runtimes. Treat these
  as intentional worktree changes and review whether repository ignore rules should include
  generated runtime targets.
- `skills sync` reports removed managed files separately from written paths when a file was
  present in the previous UMEM manifest but is no longer present in the canonical skill.
- For enabled AGENTS.md/Codex/OpenAI-class hosts with Agent Skills support,
  `.agents/skills/...` is the expected native target for complete synchronized copies.
- `--replace-native` on import only rewrites the matching managed native source target when
  UMEM can identify one. It is not a global sync and does not install every runtime copy.
  Prefer plain `import` followed by explicit `sync` unless you intentionally want the
  source native directory rewritten immediately.
- `skills track` explicitly creates or increments a proposed latent skill from curated observed evidence; it does not automatically scan history.
- `skills recommend` is read-only candidate review over explicit latent skill records; promotion, import, generation, and sync are separate explicit workflows.
- `skills generate` creates canonical files under the active UMEM skill root for
  project skills.
- `skills deactivate` preserves files and changes status to disabled.
- `skills activate` requires a readable, valid `SKILL.md`.
- `skills update`, `activate`, and `deactivate` operate on latent/generated skill IDs.
  For canonical Agent Skills, use `skills canonical update`, `skills rename`, `skills cleanup`,
  `skills repair`, and `skills sync`.
- `skills cleanup` previews cleanup for one canonical skill by default; add `--apply`
  only after reviewing removable and blocked paths.
- `skills repair` previews project-wide orphan target cleanup by default; add
  `--remove-orphan-targets --apply` only after reviewing the summary.
- `host sync --apply` should be non-interactive in agent automation: use
  `umem host sync --apply --yes --format json`.

## Official Workflows

- Adopt an existing local skill as canonical and distribute it: run `umem skills import .agents/skills/<skill-name> --scope project --visibility shared --category user-facing --sync --format json`, then inspect the returned `skill_file` and `native_installations`.
- Edit an imported canonical skill: modify the returned `skill_file`, run `umem skills detail <slug> --format json` to verify metadata, then run `umem skills sync <slug> --format json`.
- Avoid the common trap: do not pass a canonical `skill_id` from `skills list` or `skills detail` to `skills update` unless the payload identifies it as a latent/generated mutation target.

## Playbook: Adopt Existing Native Skill Into UMEM

Use this when the user has an existing native skill such as `.agents/skills/foo` and
wants UMEM to own it as the canonical source while preserving local agent compatibility
through managed native sync.

1. Confirm the target repository before mutating anything. If the user names a path, run
   commands from that repository root and keep all report paths relative.
2. Load current UMEM state in the target repository:

   ```bash
   umem status --format json
   umem context --scope project --format json
   umem skills list --format json
   ```

3. Validate the native source exists and contains `SKILL.md`.
4. Import it into the canonical registry and synchronize configured native targets:

   ```bash
   umem skills import .agents/skills/foo --scope project --sync --format json
   ```

5. Validate the canonical record and metadata:

   ```bash
   umem skills detail foo --format json
   ```

6. If import was run without `--sync`, synchronize configured native runtime copies from canonical:

   ```bash
   umem skills sync foo --format json
   ```

   For enabled AGENTS.md/Codex/OpenAI-class hosts with Agent Skills support, this should
   manage `.agents/skills/foo/` as a complete native copy. Use `--replace-native` during
   import only when intentionally rewriting the matching managed native source immediately.
7. Remember that `native_installations` or `targets` may be empty after import. That means
   UMEM adopted the source into a UMEM skill root, but no enabled runtime target
   was written or adopted during that command. Use `--sync` during import for the
   complete adoption flow, or run `skills sync` afterward.
8. Check the real UMEM inventory with `umem skills detail foo --format json`. Normal
   `git status` can hide `.umem/`, `.agents/`, `.opencode/`, or other runtime directories
   when repository ignore rules exclude them.
9. If adopting the skill records a durable project decision, save a memory fact, then sync
   host instructions:

   ```bash
   umem remember "Adopted <skill> as a UMEM canonical skill." --scope project --tag skills
   umem host sync --apply --yes --format json
   ```

Treat the returned canonical `skill_file` as the editable source from this point
on. For shared user-facing skills that may be `umem/skills/foo/SKILL.md`; for
private or operational skills that remains `.umem/skills/foo/SKILL.md`. Native
wrappers are a repository policy choice, not UMEM's default product behavior.
UMEM's default runtime model is canonical source plus synchronized complete
native copies, because host runtimes expect complete native skill directories.

When runtime directories should reflect the canonical version, run:

```bash
umem skills sync foo --format json
```

Future `skills migrate` behavior should follow the same product direction: discover native
skills, import or adopt them into the appropriate UMEM skill root, validate
targets, and synchronize complete managed copies to configured native runtime
directories. A `wrap-source` option may exist only for explicit local policy; it
should not be the default migration outcome.

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

## Decision Guide For Agents

- User wants a new skill written from scratch: use `skills create`.
- User points to an existing skill directory or `SKILL.md`: use `skills import`.
- User wants an existing canonical skill available in native runtimes: use `skills sync`.
- User wants to change an imported canonical skill: edit the returned canonical
  `skill_file`, then run `skills sync`; do not assume `skills update` accepts
  canonical skill IDs.
- User reports a recurring workflow but has not asked for a concrete skill yet: use
  `skills track`, then `skills recommend`, then ask before promotion/generation.
- Do not use `skills update`, `activate`, or `deactivate` on an ID returned by `skills detail`
  unless the help or payload clearly identifies that ID as a supported mutation target.
""",
    ".umem/skills/use-universal-memory/references/host-instructions-sync.md": """# Host Instructions Sync

Use this reference when UMEM needs to install, validate, or refresh host instruction
targets such as shared agent instructions and runtime-specific files.

## Use Cases

- Initialize host instruction files for supported runtimes.
- Validate that host files still contain the managed UMEM block.
- Preview host instruction changes without applying them.
- Apply a sync after recording or purging durable memory.
- Keep host files compact and prevent raw memory dumps in instruction targets.

## Canonical CLI

```bash
umem host setup codex --yes --format json
umem host setup claude_code --yes --format json
umem host check codex --format json
umem host check claude_code --format json
umem host sync --no-apply --format json
umem host sync --apply --yes --format json
```

## Parameters

- `codex`: host that consumes `AGENTS.md`.
- `claude_code`: host that consumes `CLAUDE.md`.
- `--yes`: non-interactive confirmation for writes.
- `--no-apply`: preview sync output without writing files.
- `--apply`: apply the generated host instruction update.
- `--format json`: canonical automation output.

## MCP Equivalents

- `host_setup(host_id="codex", force=true)`
- `host_setup(host_id="claude_code", force=true)`
- `host_check(host_id="codex")`
- `host_check(host_id="claude_code")`
- `sync_instructions(apply=false)`
- `sync_instructions(apply=true)`

## Expected Behavior

- Host setup and sync should only write managed instruction sections.
- Host files should point to UMEM and its startup commands; they should not embed raw
  memory dumps.
- After memory mutations that should affect future agent behavior, run sync with
  `--apply`.
- If host validation fails, inspect the reported relative path and restore the managed
  UMEM block instead of duplicating instructions manually.
""",
    ".umem/skills/use-universal-memory/references/cli-mcp-parity.md": """# CLI MCP Parity

Use this reference when documenting, testing, or implementing UMEM behavior across CLI
and MCP surfaces.

## Principle

The CLI is the canonical contract. MCP tools are equivalent automation surfaces over the
same application use cases. Do not document MCP-only behavior unless the capability is
explicitly MCP-only.

## Success Envelope

CLI commands with `--format json` and MCP tools should return equivalent payloads:

```json
{
  "ok": true,
  "operation": "skills.track",
  "scope": "project",
  "data": {},
  "warnings": []
}
```

## Core Capability Map

| Capability | Canonical CLI | MCP equivalent |
| --- | --- | --- |
| Initialize project | `umem init --yes --format json` | `initialize_project()` |
| Status | `umem status --format json` | `status()` |
| Inspect project layout | `umem layout status --format json` | `inspect_project_layout()` |
| Migrate project layout | `umem layout migrate --to shared --dry-run --format json` | `migrate_project_layout(target_layout="shared", dry_run=true)` |
| Context | `umem context --scope project --format json` | `context(scope="project")` |
| Remember fact | `umem remember "..." --scope project --visibility shared --tag workflow --format json` | `remember_fact(content="...", scope="project", visibility="shared", tags=["workflow"])` |
| List facts | `umem facts list --scope project --visibility all --format json` | `list_facts(scope="project", visibility="all")` |
| Purge fact | `umem facts purge --id <fact-id> --format json` | `purge_fact(id="<fact-id>", confirm=true)` |
| Audit list | `umem audit list --scope project --format json` | `list_audit_events(scope="project")` |
| Snapshots list | `umem snapshots list --scope project --format json` | `list_snapshots(scope="project")` |
| Rollback | `umem rollback --scope project --yes --format json` | `rollback_scope(scope="project")` |
| Host setup | `umem host setup codex --yes --format json` | `host_setup(host_id="codex", force=true)` |
| Host check | `umem host check codex --format json` | `host_check(host_id="codex")` |
| Host sync | `umem host sync --apply --yes --format json` | `sync_instructions(apply=true)` |
| Skills list | `umem skills list --format json` | `list_skills()` |
| Skill detail | `umem skills detail <skill-id-or-name> --format json` | `get_skill_detail(name_or_id="<skill-id-or-name>")` |
| Skill draft create | `umem skills draft create ... --format json` | `create_skill_draft(...)` |
| Skill validate | `umem skills validate <skill-or-path> --format json` | `validate_skill(skill_or_path="<skill-or-path>")` |
| Skill publish | `umem skills publish <draft-or-path> --format json` | `publish_skill(draft_or_path="<draft-or-path>")` |
| Skill create | `umem skills create ... --format json` | `create_skill(...)` |
| Skill adopt | `umem skills adopt <path> --format json` | `adopt_skill(path="<path>")` |
| Skill import | `umem skills import <path> --format json` | `import_skill(path="<path>")` |
| Skill share | `umem skills share <skill> --yes --format json` | `share_skill(skill_id_or_name="<skill>", confirm_operational=true)` |
| Skill canonical update | `umem skills canonical update <skill> --file <path> --format json` | `update_canonical_skill(...)` |
| Skill rename | `umem skills rename <skill> --slug <slug> --format json` | `rename_skill(...)` |
| Skill cleanup | `umem skills cleanup <skill> --targets --format json` | `cleanup_skill(...)` |
| Skill repair | `umem skills repair --remove-orphan-targets --format json` | `repair_skills(...)` |
| Track skill | `umem skills track ... --format json` | `track_latent_skill(...)` |
| Recommend skills | `umem skills recommend --scope project --format json` | `recommend_skills(scope="project", dry_run=true)` |
| Propose skill | `umem skills propose <latent-skill-id> --decision yes --format json` | `propose_skill(latent_skill_id="<latent-skill-id>", decision="yes")` |
| Promote skill recommendation | `umem skills promote <recommendation-id> --yes --format json` | `promote_skill_recommendation(recommendation_id="<recommendation-id>", confirm=true)` |
| Generate skill | `umem skills generate <latent-skill-id> --yes --format json` | `generate_skill(latent_skill_id="<latent-skill-id>")` |
| Activate skill | `umem skills activate <latent-skill-id> --format json` | `activate_skill(latent_skill_id="<latent-skill-id>")` |
| Deactivate skill | `umem skills deactivate <latent-skill-id> --format json` | `deactivate_skill(latent_skill_id="<latent-skill-id>")` |
| Update latent/generated skill | `umem skills update <latent-skill-id> ... --format json` | `update_skill(...)` |

## Error Mapping

| Domain error | MCP JSON-RPC code |
| --- | --- |
| `SecretDetectedError` | `-32010` |
| `SnapshotFailedError` | `-32020` |
| `ValidationFailedError` | `-32602` |
| `FactNotFoundError` | `-32040` |
| `InvalidConfigError` | `-32050` |
| `StorageError` | `-32060` |

## Expected Behavior

- CLI adapters and MCP tools should stay thin: translate inputs, call use cases, and
  format outputs.
- New public capabilities should include both CLI and MCP coverage unless explicitly
  marked internal.
- Error output must not leak secrets, stack traces, or absolute local paths.
- Shared-layout JSON payloads should expose project-relative paths. Layout status
  should include `shared_root`, `operational_root`, `ignored_shared_paths`,
  `tracked_operational_paths`, and `overlaps`.
- Project fact and skill payloads should preserve `visibility` and `storage_path`
  or canonical path metadata across CLI and MCP.
- Operational skill sharing must be explicit on both surfaces: CLI uses
  `--category operational --yes`; MCP uses `category="operational"` and
  `confirm_operational=true`.
""",
    ".umem/skills/use-universal-memory/references/guardrails-and-recording.md": """# Guardrails And Recording

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
""",
}


@dataclass(frozen=True, slots=True)
class SetupProjectResult:
    project_path: Path
    config_path: Path
    memory_path: Path
    audit_path: Path
    snapshots_path: Path
    skills_path: Path
    benchmarks_path: Path
    created: bool
    already_initialized: bool
    created_paths: list[str]
    existing_paths: list[str]
    layout: str = "legacy"
    shared_root: Path | None = None
    operational_root: Path = Path(".umem")
    shared_paths: list[str] | None = None
    operational_paths: list[str] | None = None


def setup_project(  # noqa: PLR0913
    project_root: Path,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
    global_config_path: Path | None = None,
    enabled_runtime_ids: list[str] | None = None,
    enabled_host_ids: list[str] | None = None,
    layout: str = "legacy",
) -> SetupProjectResult:
    normalized_project_root = project_root.resolve()
    layout_result = layout_port.ensure_project_layout(normalized_project_root)
    shared_paths: list[str] = []
    if layout == "shared":
        layout_port.write_project_layout_metadata(normalized_project_root, layout="shared")
        shared_paths = ["umem/project.toml", "umem/memory", "umem/skills"]
    seeded_skill_paths = _ensure_default_umem_skill(normalized_project_root)
    loaded_config = load_config(normalized_project_root, global_config_path=global_config_path)
    requested_runtime_ids = (
        enabled_runtime_ids if enabled_runtime_ids is not None else enabled_host_ids
    )
    if requested_runtime_ids is None:
        configured_runtime_ids = _configured_runtime_ids(loaded_config.merged)
        normalized_runtime_ids = (
            configured_runtime_ids
            if configured_runtime_ids is not None
            else list(DEFAULT_ENABLED_RUNTIME_IDS)
        )
    else:
        normalized_runtime_ids = _normalize_runtime_ids(requested_runtime_ids)
    unsupported = [
        runtime_id
        for runtime_id in normalized_runtime_ids
        if runtime_id not in DEFAULT_ENABLED_RUNTIME_IDS
    ]
    if unsupported:
        raise InvalidConfigError(f"Unsupported runtimes: {', '.join(unsupported)}")

    preferences = loaded_config.project_data.get("preferences")
    updates: dict[str, Any] = {"runtimes": {"enabled": normalized_runtime_ids}}
    if not isinstance(preferences, dict) or "locale" not in preferences:
        updates["preferences"] = {"locale": "en"}

    update_project_config(
        normalized_project_root,
        updates,
        global_config_path=global_config_path,
    )

    # Validate config after materializing defaults so downstream adapters can rely on valid TOML.
    config_validation_port.validate_project_config(
        project_root=normalized_project_root,
        global_config_path=global_config_path,
    )

    umem_root = Path(".umem")
    operational_paths = [
        ".umem/config.toml",
        ".umem/memory",
        ".umem/audit/events.jsonl",
        ".umem/snapshots",
        ".umem/skills",
        ".umem/benchmarks",
    ]
    return SetupProjectResult(
        project_path=Path("."),
        config_path=umem_root / "config.toml",
        memory_path=umem_root / "memory",
        audit_path=umem_root / "audit" / "events.jsonl",
        snapshots_path=umem_root / "snapshots",
        skills_path=umem_root / "skills",
        benchmarks_path=umem_root / "benchmarks",
        created=layout_result.created,
        already_initialized=not layout_result.created,
        created_paths=[*layout_result.created_paths, *shared_paths, *seeded_skill_paths["created"]],
        existing_paths=[*layout_result.existing_paths, *seeded_skill_paths["existing"]],
        layout=layout,
        shared_root=Path("umem") if layout == "shared" else None,
        operational_root=Path(".umem"),
        shared_paths=shared_paths if layout == "shared" else [],
        operational_paths=operational_paths,
    )


def _normalize_runtime_ids(runtime_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    for runtime_id in runtime_ids:
        cleaned = runtime_id.strip().lower().replace("-", "_")
        try:
            resolved = RuntimeId(cleaned).value
        except ValueError:
            resolved = cleaned
        if resolved not in normalized:
            normalized.append(resolved)
    return normalized


def _configured_runtime_ids(config_data: dict[str, Any]) -> list[str] | None:
    raw_runtimes = config_data.get("runtimes")
    if not isinstance(raw_runtimes, dict):
        return None
    raw_enabled = raw_runtimes.get("enabled")
    if not isinstance(raw_enabled, list):
        return None
    return _normalize_runtime_ids([str(runtime_id) for runtime_id in raw_enabled])


def _ensure_default_umem_skill(project_root: Path) -> dict[str, list[str]]:
    created: list[str] = []
    existing: list[str] = []

    skill_path = project_root / DEFAULT_UMEM_SKILL_RELATIVE_PATH
    if skill_path.exists():
        existing.append(DEFAULT_UMEM_SKILL_RELATIVE_PATH)
    else:
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(DEFAULT_UMEM_SKILL_MARKDOWN, encoding="utf-8")
        created.append(DEFAULT_UMEM_SKILL_RELATIVE_PATH)

    for relative_path, content in DEFAULT_UMEM_SKILL_REFERENCES.items():
        reference_path = project_root / relative_path
        if reference_path.exists():
            existing.append(relative_path)
        else:
            reference_path.parent.mkdir(parents=True, exist_ok=True)
            reference_path.write_text(content, encoding="utf-8")
            created.append(relative_path)

    latent_skills_path = project_root / DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH
    if _default_umem_skill_is_registered(latent_skills_path):
        existing.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)
    else:
        latent_skills_path.parent.mkdir(parents=True, exist_ok=True)
        with latent_skills_path.open("a", encoding="utf-8") as file:
            file.write(_default_umem_skill_jsonl_line())
        created.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)

    return {"created": created, "existing": existing}


def _default_umem_skill_is_registered(latent_skills_path: Path) -> bool:
    if not latent_skills_path.exists():
        return False
    try:
        content = latent_skills_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return DEFAULT_UMEM_SKILL_ID in content or DEFAULT_UMEM_SKILL_NAME in content


def _default_umem_skill_jsonl_line() -> str:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = {
        "schema_version": 1,
        "id": DEFAULT_UMEM_SKILL_ID,
        "created_at": timestamp,
        "updated_at": timestamp,
        "name": DEFAULT_UMEM_SKILL_NAME,
        "description": (
            "Operational hub for using Universal Memory context, facts, host sync, "
            "and skills lifecycle."
        ),
        "scope": "project",
        "status": "active",
        "recurrence_count": 1,
        "metadata": {
            "origin": "umem-init",
            "audit_reference": "seeded-by-init",
            "triggers": [
                "at the start of a work session or conversation",
                "before implementing, investigating, reviewing, or planning in a repository with .umem",
                "when the user mentions memory, facts, context, skills, AGENTS.md, CLAUDE.md, host sync, or learned preferences",
                "before recording durable project or global knowledge",
                "before creating, updating, activating, or deactivating a UMEM skill",
            ],
            "evidence": [
                {
                    "origin": "umem-init",
                    "summary": "Default operational skill installed during project initialization.",
                }
            ],
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
