---
title: "MkDocs documentation structure"
type: "feature"
created: "2026-06-05"
status: "ready-for-dev"
context:
  - "README.md"
  - "docs/"
  - "pyproject.toml"
  - "_bmad-output/planning-artifacts/architecture.md"
  - "_bmad-output/planning-artifacts/prd.md"
---

<frozen-after-approval reason="human-owned intent">

## Intent

Create a curated MkDocs documentation structure for `universal-memory` in English.
The site must serve three audiences: end users, contributors/developers, and
agents/LLMs. `README.md` remains the package and repository entrypoint; MkDocs
becomes the curated documentation surface.

## Boundaries

- Publish curated content only.
- Use `_bmad-output/` as source material, not as raw navigation content.
- Treat the CLI as canonical and MCP as equivalent automation surface.
- Use relative paths in documentation.
- Do not depend on `.umem/skills/use-universal-memory/references/` until the
  SKILLS front creates it.

</frozen-after-approval>

## Tasks

- [x] Add `mkdocs.yml` with a pragmatic built-in theme and persona-oriented navigation.
- [x] Add curated English documentation pages under `docs/`.
- [x] Keep existing assets and reuse README concepts without duplicating the README verbatim.
- [x] Add a reproducible docs dependency group.
- [x] Run a MkDocs build check.
- [x] Add CI/CD workflow to validate MkDocs and deploy the site with GitHub Pages.
