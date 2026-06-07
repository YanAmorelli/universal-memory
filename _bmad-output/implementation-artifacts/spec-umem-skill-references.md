---
title: 'Make use-universal-memory a guide skill with progressive references'
type: 'docs'
created: '2026-06-07'
status: 'done'
route: 'one-shot'
---

# Make use-universal-memory a guide skill with progressive references

## Intent

**Problem:** UMEM host instructions require agents to bootstrap memory, inspect active
skills, use durable memory safely, and sync host instruction files. Keeping all of that
procedural detail directly in host files or a single long `SKILL.md` increases context
load and makes the guidance harder to maintain. Splitting UMEM into many separate skills
would also make the workflow harder to discover because UMEM is one operational domain,
not a collection of unrelated user intents.

**Approach:** Model `.umem/skills/use-universal-memory/` as one guide-style Agent Skill.
The root `SKILL.md` acts as the routing guide, similar in purpose to `bmad-help`, while
focused reference files under `references/` provide deeper details on startup, facts,
host sync, skills lifecycle, CLI/MCP parity, and final-response guardrails.

This follows the Agent Skills progressive disclosure pattern: advertise only the skill
metadata at startup, load the concise `SKILL.md` when relevant, and read specific
reference files only when the task needs them.

## Boundaries & Constraints

**Always:**
- Keep `use-universal-memory` as a single guide skill for UMEM operating behavior.
- Use `references/` for deeper topic-specific guidance instead of creating many UMEM
  skills for closely related memory operations.
- Keep host instruction files compact; they should point to UMEM and the skill, not embed
  raw memory dumps or long procedural catalogs.
- Use relative paths in specs, code, and docs.
- Treat the CLI as the canonical behavior contract and MCP tools as equivalent automation
  surfaces.

**Ask First:**
- Before splitting UMEM guidance into additional skills.
- Before changing host instruction bootstrap semantics.
- Before changing durable memory recording rules or final response footer requirements.

**Never:**
- Do not store secrets, raw logs, stack traces, credentials, or transient task progress in
  UMEM facts or skill references.
- Do not repeat the full UMEM bootstrap on every user message in the same conversation.
- Do not make `references/` a deep chain of nested documents; the guide should route
  directly to focused files.

## Design Notes

The intended structure is:

```text
.umem/skills/use-universal-memory/
├── SKILL.md
└── references/
    ├── startup-and-context.md
    ├── memory-facts.md
    ├── skills-lifecycle.md
    ├── host-instructions-sync.md
    ├── cli-mcp-parity.md
    └── guardrails-and-recording.md
```

`SKILL.md` should behave as an operational guide:

- Explain when the skill is used.
- State the expected outcomes for the agent and user.
- Identify the data sources to inspect.
- Tell the agent how to interpret UMEM state.
- Route to the right reference file for deeper instructions.
- Define the response and recording constraints.

The `references/` files should remain focused and task-specific:

- `startup-and-context.md` -- session preflight, status, context, and skill discovery.
- `memory-facts.md` -- remembering, listing, and purging durable facts.
- `skills-lifecycle.md` -- latent skill tracking, proposal, generation, activation,
  deactivation, and update.
- `host-instructions-sync.md` -- host setup, validation, previews, and sync.
- `cli-mcp-parity.md` -- canonical CLI commands and MCP equivalents.
- `guardrails-and-recording.md` -- what to record, what not to record, sync behavior, and
  final response footer.

## Code Map

- `.umem/skills/use-universal-memory/SKILL.md` -- Root guide skill that routes agents to
  the appropriate UMEM operation and reference.
- `.umem/skills/use-universal-memory/references/startup-and-context.md` -- Startup and
  context-loading reference.
- `.umem/skills/use-universal-memory/references/memory-facts.md` -- Durable fact
  reference.
- `.umem/skills/use-universal-memory/references/skills-lifecycle.md` -- Skills lifecycle
  reference.
- `.umem/skills/use-universal-memory/references/host-instructions-sync.md` -- Host
  instruction sync reference.
- `.umem/skills/use-universal-memory/references/cli-mcp-parity.md` -- CLI/MCP parity
  reference.
- `.umem/skills/use-universal-memory/references/guardrails-and-recording.md` -- Guardrails
  and final-response recording reference.
- `.gitignore` -- Allows the project-owned UMEM skill files to be versioned while keeping
  local UMEM storage ignored.

## Tasks & Acceptance

**Execution:**
- [x] `.gitignore` -- Allow `.umem/skills/use-universal-memory/**` to be tracked while
  preserving ignores for local UMEM runtime data.
- [x] `.umem/skills/use-universal-memory/SKILL.md` -- Add the guide skill entry point,
  mandatory startup instructions, reference routing, and operating rules.
- [x] `.umem/skills/use-universal-memory/references/startup-and-context.md` -- Document
  startup and context preflight commands and MCP equivalents.
- [x] `.umem/skills/use-universal-memory/references/memory-facts.md` -- Document durable
  memory commands, MCP equivalents, and mutation expectations.
- [x] `.umem/skills/use-universal-memory/references/skills-lifecycle.md` -- Document skill
  discovery, tracking, proposal, generation, activation, deactivation, and update.
- [x] `.umem/skills/use-universal-memory/references/host-instructions-sync.md` -- Document
  host setup, validation, preview, and sync behavior.
- [x] `.umem/skills/use-universal-memory/references/cli-mcp-parity.md` -- Document CLI as
  canonical contract and MCP equivalents.
- [x] `.umem/skills/use-universal-memory/references/guardrails-and-recording.md` --
  Document final recording decisions, safe memory rules, and UMEM footer behavior.

**Acceptance Criteria:**
- Given an agent begins a session in this repository, when `use-universal-memory` is
  relevant, then the root `SKILL.md` guides the agent through startup and routes to
  focused references instead of requiring a large monolithic instruction file.
- Given a user asks for UMEM help, state, next steps, memory recording, host sync, or
  skill lifecycle guidance, then the agent can use one guide skill and read only the
  matching reference file.
- Given future maintainers review the skill structure, then they can see that the single
  guide skill plus `references/` design is intentional and aligned with Agent Skills
  progressive disclosure.
- Given `.umem/*` remains ignored for local storage, then the project-owned guide skill
  remains explicitly unignored and versionable.

## Out Of Scope

- Changing the UMEM CLI behavior.
- Changing MCP tool behavior.
- Bumping package versions.
- Documenting Python package upgrade behavior for `umem update`.
- Creating additional UMEM skills for individual memory operations.

## Suggested Review Order

- [Skill guide](../../.umem/skills/use-universal-memory/SKILL.md) -- confirm it reads as
  an operational guide and not only a technical index.
- [Startup reference](../../.umem/skills/use-universal-memory/references/startup-and-context.md)
  -- confirm bootstrap guidance matches host instructions.
- [Recording guardrails](../../.umem/skills/use-universal-memory/references/guardrails-and-recording.md)
  -- confirm durable memory and footer rules are explicit.
- [CLI/MCP parity reference](../../.umem/skills/use-universal-memory/references/cli-mcp-parity.md)
  -- confirm command and tool names match the implemented public surface.
- [Git ignore rules](../../.gitignore) -- confirm only the project-owned skill is
  unignored from `.umem/`.

## Verification

**Commands:**
- `umem status --format json` -- expected: `ok: true` and initialized project status.
- `umem context --scope project --format json` -- expected: active project guidance loads.
- `umem skills list --format json` -- expected: `use-universal-memory` appears as an
  active project skill.
- `umem skills detail use-universal-memory --format json` -- expected: guide skill
  metadata and triggers are returned.
- `git diff --check dev...docs/umem-skill-references` -- expected: no whitespace errors.
- `uv run pyright` -- expected: `0 errors`.
- `uv run pytest` -- expected: all tests pass.

## Review Findings

- [ ] [Review][Scope] Confirm unrelated package version and `umem update` documentation
  changes are either removed from this branch or covered by a separate spec.
