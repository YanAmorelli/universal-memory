# Documentation Sources

This MkDocs site is curated from project source material. It does not publish
raw planning or implementation artifacts directly.

## Public Entry Points

- `README.md` remains the repository and package entrypoint.
- `docs/` contains the curated documentation site.
- `mkdocs.yml` defines the published navigation.

## Source Material

The following sources informed the curated pages:

- `README.md`;
- `docs/`;
- `pyproject.toml`;
- `_bmad-output/planning-artifacts/prd.md`;
- `_bmad-output/planning-artifacts/architecture.md`;
- `_bmad-output/planning-artifacts/epics.md`;
- selected implementation artifacts under `_bmad-output/implementation-artifacts/`.

## Curation Rule

Use BMad artifacts to extract stable decisions, requirements, and validated
behavior. Do not expose raw story files in the public navigation unless a future
documentation decision explicitly creates an implementation archive.

## Skill References

The Universal Memory operating skill references are:

```text
.umem/skills/use-universal-memory/references/
```

Those files contain the agent-facing procedures for startup/context, memory facts, host
sync, skill lifecycle, CLI/MCP parity, and recording guardrails. Public docs should
summarize those procedures without copying every operational detail into the site.
