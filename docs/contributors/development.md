# Development Guide

## Tooling

The project uses:

- Python 3.12+;
- `uv` for environment and build operations;
- Typer and Rich for the CLI;
- FastMCP for MCP integration;
- Pydantic for typed data contracts;
- Ruff for linting and formatting;
- Pyright for static type checking;
- pytest for tests.

## Common Commands

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv build
```

## Testing Contract

Run focused checks while iterating, then broaden validation based on the blast
radius of the change:

- full test suite: `uv run pytest`;
- lint: `uv run ruff check .`;
- formatting check: `uv run ruff format --check .`;
- type check: `uv run pyright`;
- docs build: `uv run --group docs mkdocs build --strict`;
- package build, when packaging metadata or entrypoints change: `uv build`.

## What To Test By Change Type

- Domain or application use cases: add or update `tests/domain/` or
  `tests/application/` coverage.
- CLI behavior: add or update `tests/interfaces/cli/` coverage.
- MCP behavior: add or update `tests/interfaces/mcp/` coverage.
- Public CLI/MCP capability parity: update `tests/interfaces/test_parity.py`.
- Documentation examples or content guarantees: add or update `tests/docs/`.
- Dependency and packaging contracts: add or update `tests/packaging/` when that
  directory is present.

## CLI/MCP Parity Rule

The CLI is the canonical contract. MCP is the equivalent automation surface for
agents and hosts. New public CLI capabilities should have an MCP equivalent or
an explicit documented exclusion.

For public capability changes, keep these together:

- CLI command behavior and JSON output;
- MCP tool behavior and structured payload;
- `docs/reference/cli-mcp-parity.md`;
- `tests/interfaces/test_parity.py`.

CLI JSON and MCP tool responses should use the same success envelope:
`ok`, `operation`, `scope`, `data`, and `warnings`.

## Design Rules

- Keep CLI and MCP adapters thin.
- Add use cases in the application layer.
- Keep domain models independent from infrastructure and interfaces.
- Use `tomllib` for TOML reads and `tomli-w` for TOML writes.
- Return relative paths in user-facing output where possible.
- Keep `AGENTS.md` compact and use it as a pointer, not a knowledge dump.

## Documentation Changes

Curated MkDocs pages live under `docs/`. Use `_bmad-output/` as planning and
implementation source material, but do not publish raw BMad artifacts directly
in the navigation.

Build the documentation with:

```bash
uv run --group docs mkdocs build --strict
```
