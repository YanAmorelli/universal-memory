# Operating Protocol For Agents

Agents should use Universal Memory as a controlled context and mutation surface.

## Session Start

1. Read the host instruction file that applies to the workspace.
2. Check whether Universal Memory is initialized.
3. Retrieve active project context before planning or editing.

Preferred CLI form:

```bash
umem status --format json
umem context --scope project --format json
umem skills list --format json
```

Equivalent MCP tools:

```text
status
context
list_skills
```

## During Work

Use facts only for durable information:

- stable project constraints;
- durable user preferences;
- architectural decisions;
- fixed bugs or important operational learnings.

Do not record transient logs, raw command output, secrets, or uncertain
inferences.

## Before Persisting Changes

Prefer the CLI or MCP tool over direct file edits for memory, instruction, and
skill mutations. This preserves snapshots, audit events, and secret scanning.

## Skill References

The expected future skill reference location is:

```text
.umem/skills/use-universal-memory/references/
```

That directory is not present in this worktree. Until the SKILLS front creates
it, agents should rely on the installed `use-universal-memory` skill instructions
when available and this curated protocol page for public documentation.
