# Agent Instruction Files

Universal Memory treats instruction files as bootstrap documents, not as the
memory database itself.

Instruction files should stay compact and point agents to the right operating
surface. They should not accumulate raw facts, long history, or duplicated
provider-specific rules.

## Shared Manifest

`AGENTS.md` is the shared cross-host manifesto. It should contain stable
operational rules, memory bootstrap instructions, and pointers to specialized
documentation.

For hosts that understand `AGENTS.md`, this is the preferred shared target.

## Provider Deltas

Provider-specific files should hold only the rules that cannot fit in the
shared manifest:

| Host | Typical Target |
| --- | --- |
| Claude Code | `CLAUDE.md`, `.claude/` |
| OpenCode | `AGENTS.md`, `.opencode/` |
| Codex | `AGENTS.md` |
| Cursor | `.cursor/rules/` |
| Gemini or Antigravity | `GEMINI.md`, `.gemini/` |

The product architecture classifies instruction updates as shared policy,
provider delta, scoped rule, or canonical documentation. That classification
prevents accidental drift between hosts.

## Agent Rule

Agents should not edit instruction files directly as the normal memory workflow.
They should use the Universal Memory CLI or MCP surface so mutations can pass
through validation, secret scanning, snapshots, audit logging, and rollback.
