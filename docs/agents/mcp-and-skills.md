# MCP And Skills

Universal Memory gives agents a controlled way to keep useful context without
editing instruction files or asking the user to repeat the same constraints.
An agent can retrieve current repository context, record durable learnings,
adopt reusable workflows as skills, synchronize host instructions, and leave an
audit trail for recovery.

Universal Memory combines three complementary surfaces:

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

## Launching MCP

For published package usage, prefer a launch command that works outside this
repository and outside any local `uv` project:

```json
{
  "command": "uvx",
  "args": ["--from", "universal-memory", "umem-mcp"]
}
```

For persistent installs created with `uv tool install universal-memory` or
`pipx install universal-memory`, use:

```json
{
  "command": "umem-mcp",
  "args": []
}
```

If a host reports that the MCP server exited before listing tools, inspect
stderr for `Universal Memory MCP startup failed:` and run `uvx --from
universal-memory umem doctor` or the installed `umem doctor` from the same
environment. GUI-launched hosts may need the absolute path to `uvx` if they do
not inherit your shell `PATH`.

## CLI And MCP Equivalence

The CLI is the canonical contract. MCP is the equivalent automation surface for
agents.

| Agent need | CLI | MCP |
| --- | --- | --- |
| Bootstrap one session | `umem bootstrap --format json` | `bootstrap()` |
| Retrieve project context | `umem context --scope project --format json` | `context(scope="project")` |
| Record a durable fact | `umem remember "..." --scope project --format json` | `remember_fact(content="...", scope="project")` |
| Adopt an existing skill | `umem skills import .agents/skills/review-protocol --scope project --sync --format json` | `import_skill(path=".agents/skills/review-protocol", scope="project", sync_after_import=true)` |
| Refresh one skill | `umem skills sync review-protocol --format json` | `sync_skills(skill_id_or_name="review-protocol")` |

### Measured Bootstrap Impact

A controlled five-sample benchmark comparing the previous three-call routine with the
single bootstrap measured:

| Metric | Three calls | Bootstrap |
| --- | ---: | ---: |
| Public round-trips | 3 | 1 |
| CLI subprocess median | 501.334 ms | 167.805 ms |
| MCP in-process median | 6.407 ms | 3.545 ms |
| CLI token proxy | 1791 | 1729 |
| MCP token proxy | 1752 | 1710 |

The token proxy divides serialized request-plus-response characters by four; it is a
comparison aid, not an exact model-billing token count. The recorded evidence lives in
`.umem/benchmarks/bootstrap-results.json`.

## Why Skills Exist

Skills are procedural guidance. They tell an agent when to query memory, when to
record a durable fact, when to propose a new skill, and when to ask for human
approval.

Skills do not replace MCP. They reduce ambiguity around tool use.

## Canonical Skill Store

UMEM owns Agent Skills from `.umem/skills/<slug>/SKILL.md`. Native runtime directories
such as `.agents/skills/<slug>/`, `.opencode/skills/<slug>/`, and
`.antigravity/rules/<slug>/` are synchronized copies for specific hosts. Agents should
evolve the canonical skill first, then call `umem skills sync <slug>` or the equivalent
MCP `sync_skills` tool.

Use this decision rule:

- new skill from scratch: `umem skills create`;
- existing native skill directory or `SKILL.md`: `umem skills import <path> --sync`;
- recurring workflow evidence, but no skill yet: `umem skills track`, then
  `umem skills recommend`, then ask before proposal or generation;
- one canonical skill changed: `umem skills sync <slug>`;
- project-wide maintenance: `umem update --skills`.

Do not evolve the native runtime copy long term. Edit the canonical UMEM skill,
then sync it back to the runtimes that need it.

## Normal Agent Flow

At the beginning of one conversation or session, prefer MCP `bootstrap()` and fall back to
`umem bootstrap --format json`. Treat `data.context` as active context, inspect
`data.skills.list`, and request details only for selected relevant skills. Do not repeat the
bootstrap on later interactions in the same session.

```text
Agent reads AGENTS.md or provider-specific bootstrap instructions
Agent follows the Universal Memory operating skill
Agent calls bootstrap once and selects relevant skills
Agent proposes or records durable changes through the safe mutation pipeline
Universal Memory writes snapshots, audit events, and managed targets
```

## Skill References

The curated operational references live in:

```text
.umem/skills/universal-memory/references/
```

Those files are the detailed agent-facing procedures for startup/context, memory facts,
host sync, skill lifecycle, CLI/MCP parity, and recording guardrails. Keep this page as
the high-level explanation and link agents to the references when they need the exact
workflow.
