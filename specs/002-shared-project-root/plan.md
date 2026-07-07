# Implementation Plan: Shared Project Root

**Branch**: `spec/shared-project-root` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-shared-project-root/spec.md`

## Summary

Add an opt-in shared project layout that stores curated project memories, repository rules, and user-facing project skills under a visible `umem/` root while keeping `.umem/` for operational state, private project content, audit events, snapshots, locks, drafts, and local bootstrap guidance. The implementation extends the existing layout, repository, CLI, MCP, and doctor paths with a layout resolver, idempotent migration flow, visibility metadata, and repository visibility diagnostics.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: Existing project dependencies only: Pydantic, Typer, Rich, FastMCP, tomli-w

**Storage**: File-backed local storage. Legacy project content remains under `.umem/`; shared project content uses `umem/project.toml`, `umem/memory/facts.jsonl`, `umem/memory/rules.jsonl`, and `umem/skills/<slug>/`. Operational audit, snapshots, locks, drafts, summaries, generated runtime guidance, and private project content remain under `.umem/`. Global memory and global skills remain in the existing user data roots.

**Testing**: pytest, CLI tests, MCP tests, interface parity tests, storage repository tests, doctor diagnostics tests, docs content tests

**Target Platform**: Local developer CLI and MCP server for agent host runtimes in Git and non-Git project directories

**Project Type**: Python package exposing CLI commands and MCP tools

**Performance Goals**: Normal project fact and skill operations should stay under 1 second for dozens of records. Migration and doctor layout checks should finish in under 30 seconds for repositories with hundreds of facts/skills and normal Git status sizes.

**Constraints**: Preserve legacy `.umem` behavior until a project explicitly opts into the shared layout; keep user-facing paths project-relative; keep operational state private by default; never migrate global records into project content; make migration idempotent; preserve safe-write, snapshot, and audit behavior; maintain CLI/MCP JSON parity.

**Scale/Scope**: Project/global fact storage, project/global canonical skills, runtime target manifests, repository ignore/tracking diagnostics, and mixed legacy/shared project states during migration.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file is still a template and defines no enforceable project-specific gates. This plan applies the active repository conventions instead:

- PASS: Python 3.12+ and existing dependencies only.
- PASS: CLI and MCP capabilities remain parity-tested.
- PASS: Mutations use existing safe-write, snapshot, and audit patterns.
- PASS: User-facing output and generated docs use project-relative paths.
- PASS: Existing projects keep legacy `.umem` semantics until explicit opt-in.
- PASS: Operational skills such as `use-universal-memory` remain private by default.

Post-design re-check: PASS. The design artifacts preserve these constraints and introduce no justified violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-shared-project-root/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── mcp.md
└── tasks.md
```

### Source Code (repository root)

```text
src/universal_memory/
├── application/
│   ├── diagnostics/
│   │   └── doctor_use_case.py
│   ├── host/
│   │   └── sync_instructions_use_case.py
│   ├── layout/
│   │   ├── inspect_project_layout.py
│   │   └── migrate_project_layout.py
│   ├── memory/
│   │   ├── remember_fact_use_case.py
│   │   ├── list_facts_use_case.py
│   │   └── assemble_context_summary_use_case.py
│   ├── onboarding/
│   │   └── setup_project.py
│   └── skills/
│       ├── create_skill.py
│       ├── import_skill.py
│       ├── list_skills.py
│       └── sync_skills.py
├── bootstrap/
│   ├── cli.py
│   └── mcp.py
├── domain/
│   ├── entities/
│   │   ├── agent_skill.py
│   │   ├── fact.py
│   │   └── rule.py
│   ├── ports/
│   │   ├── agent_skill_repository.py
│   │   ├── fact_repository.py
│   │   └── project_layout_port.py
│   └── project_layout.py
├── infrastructure/
│   ├── config/
│   │   ├── project_layout.py
│   │   └── toml_loader.py
│   └── storage/
│       ├── local_agent_skill_repository.py
│       ├── local_fact_repository.py
│       └── local_rule_repository.py
└── interfaces/
    ├── cli/init_command.py
    └── mcp/server.py

tests/
├── application/
│   ├── diagnostics/
│   ├── layout/
│   ├── memory/
│   └── skills/
├── infrastructure/
│   ├── storage/
│   └── test_project_layout.py
├── interfaces/
│   ├── cli/
│   ├── mcp/
│   └── test_parity.py
└── docs/
```

**Structure Decision**: Add a focused layout application layer for inspection and migration, but keep routine reads/writes inside the existing fact, rule, and agent skill repositories through a shared layout resolver. Extend current CLI/MCP bootstrap wiring and doctor diagnostics rather than creating a second health-check surface.

## Complexity Tracking

No constitution violations require complexity justification.
