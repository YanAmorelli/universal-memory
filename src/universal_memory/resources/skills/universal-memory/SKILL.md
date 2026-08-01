---
name: "universal-memory"
description: "Operational hub for using Universal Memory context, facts, host sync, and skills lifecycle."
---

# Universal Memory

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

At the start of a work session or conversation, load UMEM context before planning,
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
- Do not wait for the user to say "use UMEM" before loading context for the current repository.
- Treat global context as cross-project user preference; do not let it override explicit
  project constraints or user instructions for the current task.
- Explicit user instructions always override remembered context.
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
- Never persist stack traces, transient task progress, or unverified assumptions.

## Reference Routing

- For startup, health, context loading, and active-skill discovery, read
  [startup and context](references/startup-and-context.md).
- For remembering, listing, and purging facts, read
  [memory facts](references/memory-facts.md).
- For skill creation, import, sync, latent tracking, proposal, generation, listing,
  detail, activation, deactivation, and update, read
  [skills lifecycle](references/skills-lifecycle.md).
- For host instruction setup, validation, and sync, read
  [host instructions sync](references/host-instructions-sync.md).
- For CLI/MCP payload parity and error behavior, read
  [CLI/MCP parity](references/cli-mcp-parity.md).
- For durable recording rules, security guardrails, and final response footer behavior,
  read [guardrails and recording](references/guardrails-and-recording.md).

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
