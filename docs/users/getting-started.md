# Getting Started

Universal Memory requires Python 3.12 or newer.

## Try Without Installing Permanently

```bash
uvx --from universal-memory umem --help
```

Use this for quick trials. For ongoing usage, install Universal Memory as a
persistent tool so the `umem` command is always available.

## Install

```bash
uv tool install universal-memory
```

Alternative:

```bash
pip install universal-memory
```

## Initialize A Project

Run initialization from the project directory where agents should read project
memory:

```bash
umem init
```

Initialization creates the local `.umem/` layout, detects agents available in or for
the project, presents one combined confirmation, configures the best available
project integration, and verifies a real project-context read.

You do not need to select runtimes or understand the integration mechanism for
the normal path. If a compatible agent needs the portable Agent Skill, UMEM
discloses network use and the external project-scoped copy before confirmation,
disables anonymous installer telemetry, and falls back gracefully when an
optional prerequisite is unavailable.

For a portable Tier 2 agent, UMEM resolves the project skill directory from a
catalog pinned to the installed `skills` CLI version, checks that destination,
runs one project-scoped `npx skills add`, and validates every file in the complete
skill tree. It does not install into a second project and copy the result back.
The temporary directory is used only to isolate the external process home and npm
cache. Unknown agent IDs do not execute `npx`; they receive a managed or manual
fallback.

### Existing Legacy Projects

If a project already contains only `.umem/skills/use-universal-memory/`, UMEM
preserves that tree and keeps host instructions pointed to it. It does not create
a second canonical tree or overwrite customizations. If both the legacy and
`.umem/skills/universal-memory/` roots exist, initialization, skill updates, and
host setup stop with an explicit conflict. Review both trees and choose an
explicit migration before continuing; UMEM will not delete or merge either one
automatically. An incomplete legacy root without `SKILL.md` is also reported for
review instead of being treated as a valid installation.

Connect another agent later with:

```bash
umem connect
```

Explicit `--runtime` selection remains available for automation and unusual
setups. `--hosts` is still accepted as a legacy alias.

## Hand It To Your Agent

The best day-to-day workflow is to initialize the project once, then let the
agent use Universal Memory through MCP or the configured host instructions.
Ask the agent to run the UMEM bootstrap before planning or editing, retrieve
project context, inspect relevant skills, and record only durable learnings.

Use manual CLI commands for inspection, review, and recovery. Let the agent
handle routine context loading and safe memory updates so it does not need to
ask you to repeat project constraints every session.

## Understand Memory Scopes

Project memory is repository-specific working memory. It is stored under
`.umem/` and should contain facts, rules, task context, and constraints that
belong to this project:

```bash
umem remember "This project prefers typed Python and clean architecture." --scope project --tag architecture
```

Global memory is long-lived user context. Use it for preferences that should
apply across projects:

```bash
umem remember "Prefer concise engineering answers." --scope global --tag preference
```

## Retrieve Context

```bash
umem context --scope project
```

For automation, prefer JSON:

```bash
umem context --scope project --format json
```

## Adopt An Existing Skill

If you already have an Agent Skill under a native runtime folder, import it into UMEM and
sync complete managed copies back to configured hosts:

```bash
umem skills import .agents/skills/review-protocol --scope project --sync
umem skills detail review-protocol
```

From then on, edit `.umem/skills/review-protocol/SKILL.md` and refresh the native copies:

```bash
umem skills sync review-protocol
```

`.umem/skills/<slug>/SKILL.md` is the source of truth after creation or import.
Native runtime folders such as `.agents/skills/`, `.opencode/skills/`, and
`.antigravity/rules/` are synchronized copies for the hosts that consume them.

## Check Health

```bash
umem status
umem doctor
```

## Run The MCP Server

For Claude Desktop or another MCP host, use a launch command that does not
require a local `pyproject.toml`:

```json
{
  "command": "uvx",
  "args": ["--from", "universal-memory", "umem-mcp"]
}
```

If you installed Universal Memory persistently with `uv tool install
universal-memory` or `pipx install universal-memory`, use the installed
entrypoint:

```json
{
  "command": "umem-mcp",
  "args": []
}
```

If startup fails, run `uvx --from universal-memory umem doctor` or the installed
`umem doctor`, then inspect the stderr line that starts with `Universal Memory
MCP startup failed:`. GUI-launched MCP hosts may need the absolute path to
`uvx` if they do not inherit your shell `PATH`.
