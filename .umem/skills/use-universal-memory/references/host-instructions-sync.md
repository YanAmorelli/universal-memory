# Host Instructions Sync

Use this reference when UMEM needs to install, validate, or refresh host instruction
targets such as shared agent instructions and runtime-specific files.

## Use Cases

- Initialize host instruction files for supported runtimes.
- Validate that host files still contain the managed UMEM block.
- Preview host instruction changes without applying them.
- Apply a sync after recording or purging durable memory.
- Keep host files compact and prevent raw memory dumps in instruction targets.

## Canonical CLI

```bash
umem host setup codex --yes --format json
umem host setup claude_code --yes --format json
umem host check codex --format json
umem host check claude_code --format json
umem host sync --no-apply --format json
umem host sync --apply --yes --format json
```

## Parameters

- `codex`: host that consumes `AGENTS.md`.
- `claude_code`: host that consumes `CLAUDE.md`.
- `--yes`: non-interactive confirmation for writes.
- `--no-apply`: preview sync output without writing files.
- `--apply`: apply the generated host instruction update.
- `--format json`: canonical automation output.

## MCP Equivalents

- `host_setup(host_id="codex", force=true)`
- `host_setup(host_id="claude_code", force=true)`
- `host_check(host_id="codex")`
- `host_check(host_id="claude_code")`
- `sync_instructions(apply=false)`
- `sync_instructions(apply=true)`

## Expected Behavior

- Host setup and sync should only write managed instruction sections.
- Host files should point to UMEM and its startup commands; they should not embed raw
  memory dumps.
- After memory mutations that should affect future agent behavior, run sync with
  `--apply`.
- If host validation fails, inspect the reported relative path and restore the managed
  UMEM block instead of duplicating instructions manually.
