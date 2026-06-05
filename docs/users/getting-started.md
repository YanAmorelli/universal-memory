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

## Check Health

```bash
umem status
umem doctor
```
