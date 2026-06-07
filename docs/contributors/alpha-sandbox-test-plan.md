# Alpha Sandbox Test Plan

Use this plan to test Universal Memory as a real user without relying on
`pytest`. Validate behavior by command output, JSON payloads, exit codes, and
generated files.

## Prepare A Sandbox

```bash
SANDBOX="$(mktemp -d /tmp/umem-smoke.XXXXXX)"
PROJECT="$SANDBOX/project"
HOME_SANDBOX="$SANDBOX/home"

mkdir -p "$PROJECT" "$HOME_SANDBOX"
cd "$PROJECT"

export HOME="$HOME_SANDBOX"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
```

## Basic CLI Smoke

```bash
uv run umem --help
uv run umem-mcp --help
uv run umem status --format json
uv run umem init --yes --hosts codex --hosts claude_code --format json
uv run umem status --format json
```

Expected results:

- help output lists the main commands;
- initial status is either uninitialized or gives a clear setup action;
- initialization creates `.umem/`;
- repeated initialization is idempotent.

## Memory Smoke

```bash
uv run umem remember "The project uses hexagonal architecture." --scope project --tag architecture --format json
uv run umem facts list --scope project --format json
uv run umem context --scope project --max-size-chars 4000 --format json
```

Expected results:

- the fact is listed under project scope;
- context includes the expected fact;
- JSON output uses the standard success envelope.

## Safety Smoke

```bash
uv run umem snapshots list --scope project --format json
uv run umem audit list --scope project --format json
uv run umem rollback --scope project --yes --format json
```

Expected results:

- safe mutations create snapshots and audit events;
- rollback uses the most recent snapshot for the requested scope;
- errors do not leak secrets or unrelated absolute machine details.

## MCP Smoke

Start the MCP server from the sandbox and call equivalent tools from an MCP
client:

```bash
HOME="$HOME_SANDBOX" uv run umem-mcp
```

Recommended tool sequence:

```text
initialize_project
status
remember_fact
list_facts
context
list_audit_events
list_snapshots
host_setup
host_check
list_skills
get_skill_detail
```
