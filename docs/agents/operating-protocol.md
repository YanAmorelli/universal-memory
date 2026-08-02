# Operating Protocol For Agents

Agents should use Universal Memory as a controlled context and mutation surface.

## Session Start

1. Read the host instruction file that applies to the workspace.
2. Check whether Universal Memory is initialized.
3. Retrieve active project context before planning or editing.

Preferred CLI form:

```bash
umem status --format json
umem layout status --format json
umem context --scope project --format json
umem skills list --format json
```

Equivalent MCP tools:

```text
status
inspect_project_layout
context
list_skills
```

After `list_skills`, inspect any relevant skill with `umem skills detail
<skill-id-or-name> --format json` or MCP `get_skill_detail`.

## During Work

Use facts only for durable information:

- stable project constraints;
- durable user preferences;
- architectural decisions;
- fixed bugs or important operational learnings;
- obsolete fact cleanup when prior memory is no longer true;
- recurring workflow evidence that may become a skill.

Do not record transient logs, raw command output, secrets, or uncertain
inferences. Do not record raw prompts, private customer data, or one-off task
progress.

In shared-layout projects, treat `umem/` as reviewable project content and
`.umem/` as private operational state. Project facts, rules, and user-facing
skills that collaborators should inherit belong under `umem/`; local notes,
private facts, audit logs, snapshots, locks, and operational skills stay under
`.umem/`.

Ask before publishing context that could expose local operating details,
private investigations, customer data, credentials, or an operational skill.
Sharing an operational skill such as `universal-memory` requires explicit
approval through `umem skills share ... --category operational --yes` or MCP
`share_skill(..., category="operational", confirm_operational=true)`.

## Before Persisting Changes

Prefer the CLI or MCP tool over direct file edits for memory, instruction, and
skill mutations. This preserves snapshots, audit events, and secret scanning.

## Skills During Work

Treat the current canonical `SKILL.md` as the source of truth. In legacy
projects that usually means `.umem/skills/<slug>/SKILL.md`. In shared-layout
projects, user-facing shared skills live at `umem/skills/<slug>/SKILL.md`, while
private and operational skills remain under `.umem/skills/<slug>/SKILL.md`.
Native runtime folders are synchronized copies for the host that consumes them.

Use the narrowest command for the task:

- `umem skills create` for a new skill;
- `umem skills import <path> --sync` for an existing `.agents/skills/...`,
  `.opencode/skills/...`, or `SKILL.md`;
- `umem skills share <skill>` when a project skill should become reviewable
  shared content;
- `umem skills sync <slug>` after editing one canonical skill;
- `umem update --skills` for project-wide maintenance.

Do not use `skills update`, `activate`, or `deactivate` on imported canonical skill IDs
unless the command payload identifies the target as a latent/generated skill.

## Skill References

The operational skill reference location is:

```text
.umem/skills/universal-memory/references/
```

Agents should rely on the installed `universal-memory` skill instructions when
available, then open the focused reference file for the current task.
