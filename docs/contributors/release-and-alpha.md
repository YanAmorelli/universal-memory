# Release And Alpha Testing

Universal Memory is an alpha-stage developer tool. A feature-complete MVP still
needs packaging, onboarding, and environment hardening before broad use.

## Release Path

1. Pre-alpha internal validation.
2. Private alpha with a small tester group.
3. Initial PyPI alpha release.

The release process should keep expectations explicit: alpha means real usage is
welcome, but bugs and edge cases are expected.

## Minimum Pre-Alpha Checks

Run the normal engineering checks before distributing a build:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv build
```

Then validate the package in a clean environment:

```bash
python -m venv .venv-alpha
source .venv-alpha/bin/activate
pip install dist/*.whl
umem --help
umem-mcp --help
```

Also validate the published-package MCP launch path from a directory without a local
`pyproject.toml`:

```bash
uvx --from universal-memory umem-mcp --help
```

## Tester Focus

Ask testers to focus on:

- installation friction;
- `umem init` in clean and existing projects;
- CLI output clarity;
- JSON output shape for automation;
- MCP startup and tool behavior;
- host setup and instruction synchronization;
- snapshots, audit events, and rollback behavior;
- skill lifecycle operations.

## Bug Reports

Useful alpha reports include:

- the exact command or MCP tool call;
- the output format used, especially `--format json`;
- expected behavior;
- actual behavior;
- whether `.umem/` already existed;
- host/runtime involved.
