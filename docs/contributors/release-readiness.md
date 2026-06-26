# Release Readiness

Universal Memory is an alpha-stage developer tool. Release readiness means the
package, docs, CLI, MCP server, and real-user sandbox flow have all been checked
against the current product contract.

## Runtime

Universal Memory currently requires Python 3.12 or newer. Do not advertise
Python 3.11 support unless package metadata, classifiers, Ruff, Pyright, CI,
dependencies, and the full test suite have been updated and validated for it.

## Release Path

1. Run local engineering checks.
2. Build the documentation and run docs content tests.
3. Build the package.
4. Validate the wheel in a clean virtual environment.
5. Validate the published-package MCP launch path.
6. Run the isolated alpha validation flow.
7. Collect tester reports with exact commands, payloads, and environments.

Alpha means real usage is welcome, but bugs and edge cases are expected.

## Required Checks

Run the normal engineering checks before distributing a build:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run --group docs mkdocs build --strict
uv build
```

If docs content tests exist, include them explicitly during focused validation:

```bash
uv run pytest tests/docs
```

For public CLI or MCP capability changes, also run:

```bash
uv run pytest tests/interfaces/test_parity.py tests/interfaces/mcp/test_compliance.py
```

## Clean Package Validation

Validate the built package in a clean virtual environment. Keep the wheel path
explicit so the commands can run from a temporary directory:

```bash
WHEEL="$(pwd)/dist/$(ls dist | grep '\.whl$' | tail -1)"
SANDBOX="$(mktemp -d /tmp/umem-release.XXXXXX)"
cd "$SANDBOX"

python3.12 -m venv .venv-alpha
source .venv-alpha/bin/activate
pip install "$WHEEL"
umem --help
umem doctor --format json
umem-mcp --help
```

Also validate the published-package MCP launch path from a directory without a
local `pyproject.toml`:

```bash
SANDBOX="$(mktemp -d /tmp/umem-uvx.XXXXXX)"
cd "$SANDBOX"
uvx --from universal-memory umem-mcp --help
```

## Tester Focus

Ask testers to focus on:

- installation friction;
- `umem init --runtime ...` in clean and existing projects;
- CLI output clarity;
- JSON output shape for automation;
- MCP startup and CLI/MCP parity;
- host setup, check, and instruction synchronization;
- snapshots, audit events, and rollback behavior;
- skill create, import, sync, list, and detail operations;
- docs examples matching real commands.

## Bug Reports

Useful alpha reports include:

- the exact command or MCP tool call;
- the output format used, especially `--format json`;
- expected behavior;
- actual behavior;
- whether `.umem/` already existed;
- host/runtime involved;
- package version and installation method.
