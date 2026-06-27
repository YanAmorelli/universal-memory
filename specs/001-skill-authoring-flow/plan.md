# Implementation Plan: Skill Authoring Flow

**Branch**: `001-skill-authoring-flow` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-skill-authoring-flow/spec.md`

## Summary

Improve the UMEM skill lifecycle so authors can draft, validate, adopt, publish, update, rename, sync, and clean up skills through explicit safe flows. The implementation extends the existing skill application layer, CLI, MCP tools, and docs while preserving JSON automation output, safe-write snapshots/audit, and CLI/MCP parity.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: Existing project dependencies only: Pydantic, Typer, Rich, FastMCP, tomli-w

**Storage**: File-backed `.umem` storage, `.umem/memory/skills.jsonl`, canonical skill directories, native runtime target manifests, snapshots, and audit events

**Testing**: pytest, existing interface parity tests, CLI tests, MCP tests, docs content tests

**Target Platform**: Local developer CLI and MCP server for agent host runtimes

**Project Type**: Python package exposing CLI commands and MCP tools

**Performance Goals**: Single-skill draft, validate, adopt, update, rename, and summary operations should complete in under 1 second on a typical local repository with dozens of skills and runtime targets

**Constraints**: Preserve relative paths in user-facing output, avoid implicit native runtime sync, protect unmanaged files, keep machine-readable JSON stable, maintain CLI/MCP parity, use existing safe write, audit, and snapshot patterns

**Scale/Scope**: Project/global skill storage, dozens of canonical skills, configured runtime targets for Codex, Claude Code, OpenCode, Cursor, and Antigravity

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file is still a template and defines no enforceable project-specific gates. This plan applies the active repository conventions instead:

- PASS: Python 3.12+ and existing dependencies only.
- PASS: CLI and MCP capabilities remain parity-tested.
- PASS: Skill mutations use safe-write, snapshot, and audit behavior.
- PASS: User-facing paths remain project-relative.
- PASS: Native runtime writes require explicit sync intent.

Post-design re-check: PASS. The design artifacts preserve the same constraints and introduce no justified violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-skill-authoring-flow/
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
├── application/skills/
│   ├── create_skill.py
│   ├── import_skill.py
│   ├── list_skills.py
│   ├── sync_skills.py
│   ├── update_skill.py
│   ├── validate_skill.py
│   ├── draft_skill.py
│   ├── rename_skill.py
│   └── cleanup_skill.py
├── bootstrap/
│   ├── cli.py
│   └── mcp.py
├── domain/entities/
│   └── agent_skill.py
├── infrastructure/storage/
│   └── local_agent_skill_repository.py
└── interfaces/
    ├── cli/init_command.py
    └── mcp/server.py

tests/
├── application/skills/
├── interfaces/cli/
├── interfaces/mcp/
├── interfaces/test_parity.py
└── docs/

docs/reference/
└── skill-lifecycle.md
```

**Structure Decision**: Keep the feature inside the existing skill lifecycle subsystem. Add focused use case modules only where behavior is new enough to avoid overloading current create/import/update modules. Update CLI/MCP bootstrap wiring and docs alongside use cases.

## Complexity Tracking

No constitution violations require complexity justification.
