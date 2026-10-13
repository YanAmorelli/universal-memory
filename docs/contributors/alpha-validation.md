# Alpha Validation

Use this guide to test Universal Memory as a real user without relying on
`pytest`. Validate behavior by command output, JSON payloads, exit codes, and
generated files.

Run these commands with an installed `umem` executable. When testing directly
from a source checkout instead, replace `umem` with `uv --project
<source-checkout> run umem` and `umem-mcp` with `uv --project
<source-checkout> run umem-mcp`.

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
umem --help
umem-mcp --help
umem status --format json
umem init --yes --runtime codex --runtime claude_code --format json
umem init --yes --runtime codex --runtime claude_code --format json
umem status --format json
umem bootstrap --format json
```

Expected results:

- help output lists the main commands;
- initial status is either uninitialized or gives a clear setup action;
- initialization creates `.umem/`;
- repeated initialization is idempotent;
- JSON output uses the standard success envelope.

## Memory Smoke

```bash
umem remember "The project uses clean architecture." --scope project --tag architecture --format json
umem facts list --scope project --format json
umem context --scope project --max-size-chars 4000 --format json
```

Expected results:

- the fact is listed under project scope;
- context includes the expected fact;
- payloads include `ok`, `operation`, `scope`, `data`, and `warnings`.

## Host Sync Smoke

```bash
umem host setup codex --yes --format json
umem host check codex --format json
umem host sync --apply --yes --format json
```

Expected results:

- host setup reports configured instruction targets or clear manual steps;
- host check reports validation status;
- host sync uses snapshots and audit events for managed writes.

## Skill Smoke

Create a canonical skill:

```bash
umem skills create --name "Review Protocol" --description "Reusable review workflow" --format json
umem skills list --format json
umem skills detail review-protocol --format json
umem skills sync review-protocol --format json
```

Import an existing native-style skill:

```bash
mkdir -p .agents/skills/imported-review
cat > .agents/skills/imported-review/SKILL.md <<'EOF'
---
name: imported-review
description: Review code changes for behavioral regressions.
---

# Imported Review

Use this skill when reviewing code changes.
EOF

umem skills import .agents/skills/imported-review --scope project --sync --format json
umem skills detail imported-review --format json
umem skills sync imported-review --format json
```

Expected results:

- canonical skills are stored under `.umem/skills/<slug>/SKILL.md`;
- native runtime folders are synchronized copies;
- import and sync report affected paths, warnings, and target metadata.

## Safety Smoke

```bash
umem snapshots list --scope project --format json
umem audit list --scope project --format json
umem rollback --scope project --yes --format json
```

Expected results:

- safe mutations create snapshots and audit events;
- rollback uses the most recent snapshot for the requested scope;
- errors do not leak secrets or unrelated absolute machine details.

## MCP Parity Smoke

Use a separate project directory for MCP validation so pre-initialization
behavior is still exercised:

```bash
MCP_PROJECT="$SANDBOX/mcp-project"
mkdir -p "$MCP_PROJECT"
cd "$MCP_PROJECT"
HOME="$HOME_SANDBOX" umem-mcp
```

Call equivalent tools from an MCP client. Use concrete arguments rather than
only checking that tools exist:

```text
initialize_project
status
context(scope="project")
remember_fact(content="The project uses clean architecture.", scope="project", tags=["architecture"])
list_facts(scope="project")
host_setup(host_id="codex", force=true)
host_check(host_id="codex")
sync_instructions(apply=true)
create_skill(name="Review Protocol", description="Reusable review workflow", scope="project")
import_skill(path=".agents/skills/imported-review", scope="project", sync_after_import=true)
sync_skills(skill_id_or_name="review-protocol")
bootstrap()
list_skills()
get_skill_detail(name_or_id="review-protocol")
list_audit_events(scope="project")
list_snapshots(scope="project")
rollback_scope(scope="project", confirm=true)
```

Expected results:

- MCP tools return structured payloads equivalent to CLI JSON output;
- destructive mutations require explicit confirmation arguments where defined;
- project mutations fail clearly before initialization and succeed after
  `initialize_project`;
- CLI and MCP payloads expose the same key operational data.
