# Quickstart: Skill Authoring Flow

This guide describes validation scenarios for the implemented feature.

## Prerequisites

- Project initialized with UMEM.
- Development dependencies installed.
- Commands run from the repository root.

## Static Checks

```bash
uv run pytest tests/application/skills tests/interfaces/cli tests/interfaces/mcp tests/interfaces/test_parity.py tests/docs
```

Expected outcome:

- Application skill lifecycle tests pass.
- CLI and MCP tests pass.
- CLI/MCP parity tests include the new capabilities.
- Docs content tests reflect the updated lifecycle guidance.

## Scenario 1: Draft Does Not Sync Native Targets

```bash
umem skills draft create --name "Review Helper" --description "Guides repeatable reviews." --format summary
umem skills draft validate review-helper --format summary
umem skills publish review-helper --format summary
```

Expected outcome:

- Draft creation reports a draft path.
- Validation reports pass or actionable blocking issues.
- Publish reports a canonical path.
- No native runtime target is created until sync is requested.

## Scenario 2: Explicit Sync Preserves One-Step Workflow

```bash
umem skills create --name "Release Helper" --description "Guides release checks." --sync --format summary
```

Expected outcome:

- Summary output shows canonical creation and native target sync.
- JSON output for the same command still includes full audit and native installation details.

## Scenario 3: Adopt Existing Skill Work

Create a valid local skill directory, then run:

```bash
umem skills adopt .umem/skills/review-helper --slug review-helper --format summary
umem skills detail review-helper --format json
```

Expected outcome:

- Adoption registers the existing directory without creating a suffixed duplicate.
- Detail output resolves the adopted canonical skill.

## Scenario 4: Validate Before Publish Or Update

```bash
umem skills validate .umem/skills/review-helper --format summary
umem skills canonical update review-helper --file .umem/skills/review-helper/SKILL.md --format summary
```

Expected outcome:

- Validation reports required frontmatter, placeholder, path, link, and risky-command checks.
- Canonical update uses the same validation rules and gives the correct next step for sync.

## Scenario 5: Rename And Cleanup Safely

```bash
umem skills rename review-helper --slug review-protocol --format summary
umem skills cleanup review-protocol --targets --dry-run --format summary
umem skills repair --remove-orphan-targets --dry-run --format summary
```

Expected outcome:

- Rename reports old and new canonical paths.
- Cleanup and repair dry-runs list removable and blocked paths without deleting files.
- Apply mode removes only UMEM-managed paths.

## Scenario 6: Git Ignore Warnings

```bash
umem skills sync review-protocol --check-gitignore --format summary
```

Expected outcome:

- The command warns for runtime roots that are not ignored or contain tracked generated files.
- The warning uses relative paths and does not modify ignore rules automatically.
