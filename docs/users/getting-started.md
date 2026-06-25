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
umem init --hosts codex --hosts claude_code
```

Initialization creates the local `.umem/` layout and prepares selected host
instruction targets.

## Record Your First Fact

```bash
umem remember "This project prefers typed Python and clean architecture." --scope project --tag architecture
```

Use project scope for repository-specific facts. Use global scope for durable
preferences that should apply across projects.

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

## Check Health

```bash
umem status
umem doctor
```

## Run The MCP Server

For Claude Desktop or another MCP host, use a launch command that does not require a
local `pyproject.toml`:

```json
{
  "command": "uvx",
  "args": ["--from", "universal-memory", "umem-mcp"]
}
```

If you installed Universal Memory persistently with `uv tool install universal-memory` or
`pipx install universal-memory`, use the installed entrypoint:

```json
{
  "command": "umem-mcp",
  "args": []
}
```

If startup fails, run `uvx --from universal-memory umem doctor` or the installed
`umem doctor`, then check the stderr line that starts with
`Universal Memory MCP startup failed:`. GUI-launched MCP hosts may need the absolute
path to `uvx` if they do not inherit your shell `PATH`.
