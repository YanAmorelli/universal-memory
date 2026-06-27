# Skills Lifecycle

Use this reference for UMEM skill discovery, direct creation, importing existing local
or native skills, syncing canonical skills to native runtimes, latent skill tracking,
approval, generation, activation, deactivation, and updates.

## Mental Model

- Canonical skill: `.umem/skills/<slug>/SKILL.md` is the source of truth after
  `create`, `import`, `promote`, or `generate`.
- Native skill target: `.agents/skills/<slug>/`, `.opencode/skills/<slug>/`, or another
  runtime directory is a synchronized copy for a specific agent host.
- AGENTS.md/Codex/OpenAI-class hosts that support Agent Skills should use
  `.agents/skills/<slug>/SKILL.md` as a native runtime target managed by UMEM.
- Edit direction: change the canonical skill first, then run `skills sync` to refresh
  native runtime copies.
- Import direction: use `skills import` when an existing native skill should become
  canonical. Import copies the source into `.umem/skills/<slug>/`; it does not make every
  runtime copy current until `skills sync` runs.
- Wrapper direction: wrapper stubs are a local exception only. The default UMEM model is
  canonical source plus complete synchronized native copies.

## Use Cases

- Track a recurring workflow or methodology as a latent skill candidate.
- Draft a skill when content may need validation before publish.
- Create a skill directly when the user already knows the desired skill.
- Adopt existing canonical work in place when it already lives under `.umem/skills/<slug>/`.
- Import an existing local or native skill directory into the canonical `.umem/skills`
  registry.
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
umem skills create --name "Skill name" --description "What the skill does." --scope project --trigger "when to use it" --format summary
umem skills adopt .umem/skills/<skill-name> --scope project --format summary
umem skills import .agents/skills/<skill-name> --scope project --sync --format json
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
  or its `SKILL.md`; import copies it into canonical `.umem/skills/<slug>/`.
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
- `adopt_skill(path=".umem/skills/<skill-name>", scope="project", sync_after_adopt=false)`
- `import_skill(path=".agents/skills/<skill-name>", scope="project", replace_native=false, sync_after_import=true)`
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
- `skills adopt` registers existing `.umem/skills/<slug>` work in place without creating a suffixed duplicate.
- Use `skills import`, not `skills adopt`, for existing native runtime directories such
  as `.agents/skills/<slug>` or `.opencode/skills/<slug>`.
- `skills validate`, `skills canonical update`, `skills rename`, `skills cleanup`, and
  `skills repair` are the supported maintenance path for canonical skills.
- `skills import` is the normal path for an existing `.agents/skills/...`, `.opencode/skills/...`,
  or other local Agent Skills directory. It registers a canonical UMEM skill and copies
  the source directory into `.umem/skills/<slug>/`.
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
- `skills generate` creates canonical files under `.umem/skills/` for project skills.
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

- Adopt an existing local skill as canonical and distribute it: run `umem skills import .agents/skills/<skill-name> --scope project --sync --format json`, then inspect the returned `skill_file` and `native_installations`.
- Edit an imported canonical skill: modify `.umem/skills/<slug>/SKILL.md`, run `umem skills detail <slug> --format json` to verify metadata, then run `umem skills sync <slug> --format json`.
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
   UMEM adopted the source into `.umem/skills/`, but no enabled runtime target was written
   or adopted during that command. Use `--sync` during import for the complete adoption flow,
   or run `skills sync` afterward.
8. Check the real UMEM inventory with `umem skills detail foo --format json`. Normal
   `git status` can hide `.umem/`, `.agents/`, `.opencode/`, or other runtime directories
   when repository ignore rules exclude them.
9. If adopting the skill records a durable project decision, save a memory fact, then sync
   host instructions:

   ```bash
   umem remember "Adopted <skill> as a UMEM canonical skill." --scope project --tag skills
   umem host sync --apply --yes --format json
   ```

Treat `.umem/skills/foo/SKILL.md` as the editable source from this point on. Native
wrappers are a repository policy choice, not UMEM's default 0.1.4 product behavior. UMEM's
default runtime model is canonical source plus synchronized complete native copies, because
host runtimes expect complete native skill directories.

When runtime directories should reflect the canonical version, run:

```bash
umem skills sync foo --format json
```

Future `skills migrate` behavior should follow the same product direction: discover native
skills, import or adopt them into `.umem/skills/`, validate targets, and synchronize
complete managed copies to configured native runtime directories. A `wrap-source` option
may exist only for explicit local policy; it should not be the default migration outcome.

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
- User wants to change an imported canonical skill: edit `.umem/skills/<slug>/SKILL.md`, then
  run `skills sync`; do not assume `skills update` accepts canonical skill IDs.
- User reports a recurring workflow but has not asked for a concrete skill yet: use
  `skills track`, then `skills recommend`, then ask before promotion/generation.
- Do not use `skills update`, `activate`, or `deactivate` on an ID returned by `skills detail`
  unless the help or payload clearly identifies that ID as a supported mutation target.
