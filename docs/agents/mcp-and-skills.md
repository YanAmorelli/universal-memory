# MCP And Skills

Universal Memory combines two complementary surfaces:

- The CLI is the canonical human and automation surface.
- MCP exposes equivalent capabilities to agents and MCP hosts.
- Skills teach agents when and how to use those capabilities.

This combination avoids direct, inconsistent edits to critical instruction
files while still letting agents evolve memory and workflow behavior.

## Why MCP Exists

MCP is the controlled operational surface. It lets an agent retrieve context,
record facts, manage skills, inspect audit events, and synchronize instruction
targets without bypassing product guardrails.

MCP operations should reuse the same application use cases as CLI commands.
That parity keeps behavior consistent for humans and agents.

## Why Skills Exist

Skills are procedural guidance. They tell an agent when to query memory, when to
record a durable fact, when to propose a new skill, and when to ask for human
approval.

Skills do not replace MCP. They reduce ambiguity around tool use.

## Normal Agent Flow

```text
Agent reads AGENTS.md or provider-specific bootstrap instructions
Agent follows the Universal Memory operating skill
Agent calls CLI or MCP to retrieve context
Agent proposes or records durable changes through the safe mutation pipeline
Universal Memory writes snapshots, audit events, and managed targets
```

## SKILLS Front Integration

The future curated reference location is expected to be:

```text
.umem/skills/use-universal-memory/references/
```

That directory does not exist in this worktree yet. When the SKILLS front creates
it, this page should link to those reference files and keep this page as the
high-level explanation.
