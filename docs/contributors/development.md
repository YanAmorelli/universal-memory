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
