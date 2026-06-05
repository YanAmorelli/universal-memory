---
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

Universal Memory (`umem`) is the repository memory and skill layer. This skill is a
hub: load only the reference file needed for the current task, then use the CLI as the
canonical contract and the MCP tool as its equivalent automation surface.

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

## Reference Routing

- For startup, health, context loading, and active-skill discovery, read
  `references/startup-and-context.md`.
- For remembering, listing, and purging facts, read `references/memory-facts.md`.
- For latent skill tracking, proposal, generation, listing, detail, activation,
  deactivation, and update, read `references/skills-lifecycle.md`.
- For host instruction setup, validation, and sync, read
  `references/host-instructions-sync.md`.
- For CLI/MCP payload parity and error behavior, read `references/cli-mcp-parity.md`.
- For durable recording rules, security guardrails, and final response footer behavior,
  read `references/guardrails-and-recording.md`.

## Operating Rules

- Keep host instruction files compact; they should point to UMEM, not store memory dumps.
- Record only curated, durable facts or skills. Do not persist raw logs, secrets,
  credentials, transient steps, or uncertain information.
- Use project scope for repository-specific knowledge and global scope for cross-project
  user preferences.
- After any memory mutation that should affect host instructions, run host sync.
- Before the final response, decide whether a durable fact, skill pattern, architectural
  decision, or obsolete memory should be recorded or cleaned up.
- End the final response with either `[UMEM: Remembered "..."]` or
  `[UMEM: No new facts/skills to record]`.
