# Quickstart: Shared Project Root

This guide describes validation scenarios for the implemented feature.

## Prerequisites

- Development dependencies installed.
- Commands run from the repository root.
- Use temporary repositories for migration scenarios so local `.umem` state is disposable.

## Static Checks

```bash
uv run pytest tests/infrastructure/test_project_layout.py tests/infrastructure/storage tests/application/layout tests/application/memory tests/application/skills tests/application/diagnostics tests/interfaces/cli tests/interfaces/mcp tests/interfaces/test_parity.py tests/docs
```

Expected outcome:

- Layout resolver and migration tests pass.
- Fact, rule, and skill repositories read/write the expected shared or private storage paths.
- CLI and MCP contract tests pass with matching JSON keys.
- Doctor reports layout health without stopping unrelated checks.
- Docs tests cover shared-root guidance and operational privacy.

Validation notes:

- Quickstart static check passed with 519 tests.
- `uv run pytest tests/docs` passed with 15 tests.
- `uv run --group docs mkdocs build --strict` passed; Material for MkDocs emitted
  its upstream MkDocs 2.0 compatibility warning.
- `git diff --check` passed.
- No deferred follow-up is recorded for Phase 7.

## Scenario 1: Initialize A Shared-Layout Project

```bash
umem init --layout shared --yes --format summary
umem layout status --format json
```

Expected outcome:

- `.umem/` exists for operational state.
- `umem/project.toml`, `umem/memory`, and `umem/skills` exist.
- `layout.status` reports `layout=shared`, `shared_root=umem`, and `operational_root=.umem`.
- `use-universal-memory` remains operational under `.umem/skills` unless explicitly shared.

## Scenario 2: Shared And Private Project Memories

```bash
umem remember "Project uses shared UMEM root." --scope project --tag architecture --format summary
umem remember "Local-only investigation note." --scope project --visibility private --tag private --format summary
umem facts list --scope project --visibility all --format json
```

Expected outcome:

- The shared fact writes to `umem/memory/facts.jsonl`.
- The private fact writes under `.umem/memory`.
- JSON list output includes both facts with `visibility` and `storage_path`.
- No lock, audit, or snapshot files appear under `umem/`.

## Scenario 3: User-Facing And Operational Skills

```bash
umem skills create --name "Review Helper" --description "Guides repository reviews." --format summary
umem skills create --name "Local Bootstrap Helper" --description "Local agent bootstrap." --category operational --format summary
umem skills list --format json
```

Expected outcome:

- `Review Helper` is canonical under `umem/skills/review-helper/SKILL.md`.
- `Local Bootstrap Helper` is canonical under `.umem/skills/local-bootstrap-helper/SKILL.md`.
- Both skill records include `visibility` and `category`.
- No native runtime target is written unless sync is requested.

## Scenario 4: Explicitly Share An Operational Skill

```bash
umem skills share use-universal-memory --category operational --yes --format summary
umem skills detail use-universal-memory --format json
```

Expected outcome:

- The command requires explicit confirmation for an operational skill.
- `umem/project.toml` records the allowlisted operational skill slug.
- The shared canonical path is reported as `umem/skills/use-universal-memory/SKILL.md`.

## Scenario 5: Migrate A Legacy Project

```bash
umem layout migrate --to shared --dry-run --format summary
umem layout migrate --to shared --apply --format json
umem layout migrate --to shared --apply --format json
```

Expected outcome:

- Dry run lists project facts, project rules, and user-facing project skills that would be copied.
- Apply creates or updates `umem/project.toml` and shared content.
- The second apply reports existing shared content instead of duplicating records.
- Global facts and global skills are skipped as out of scope.
- Operational skills are skipped unless explicitly selected.

## Scenario 6: Doctor Detects Visibility And Privacy Issues

```bash
umem doctor --format json
```

Expected outcome for a healthy shared-layout project:

- `project_layout_mode`, `shared_root_visibility`, `operational_root_privacy`, and `layout_overlaps` pass.
- Summary reports no failures.

Expected outcome for a misconfigured project:

- Ignored `umem/` content produces a warning with a commit/ignore-rule next step.
- Tracked `.umem/audit`, `.umem/snapshots`, `.umem/locks`, or private memory files produce an operational privacy warning.
- Overlapping legacy/shared fact IDs or skill slugs report that shared content takes precedence.

## Scenario 7: MCP Parity

Call the MCP tools equivalent to:

- `initialize_project(layout="shared")`
- `remember_fact(scope="project", visibility="shared")`
- `create_skill(scope="project", visibility="shared", category="user-facing")`
- `migrate_project_layout(target_layout="shared", dry_run=true)`
- `doctor()`

Expected outcome:

- Tool payloads expose the same operation names and top-level data keys as CLI JSON.
- Returned paths are project-relative.
- Validation errors are sanitized and match existing error envelope conventions.
