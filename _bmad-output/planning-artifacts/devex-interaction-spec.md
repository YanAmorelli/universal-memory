# DevEx Interaction Specification - universal-memory

**Date:** 2026-05-22
**Status:** Planning artifact
**Scope:** CLI, MCP, confirmations, structured output, and actionable errors

## Purpose

This document defines the user experience contract for `universal-memory` as a developer tool. It is not a visual UX specification. The primary interaction surfaces are CLI commands, MCP tools/resources, local files, confirmations before mutation, and machine-readable outputs consumed by agents.

## Interaction Principles

1. **Predictable commands:** Command names, options, and outputs must stay stable across CLI and MCP surfaces.
2. **Safe by default:** Read-only commands must not create, update, delete, or normalize files.
3. **Explicit mutation:** Commands that mutate memory, rules, skills, snapshots, host files, or instruction files must show scope and impact before writing when user confirmation is required.
4. **Parseable automation:** `--format json` must return JSON only, with no Rich markup, log lines, progress text, or prose outside the JSON payload.
5. **Human-readable default:** Default CLI output should be concise Rich-formatted text optimized for agent-mediated terminal use and human inspection.
6. **Actionable errors:** Expected domain errors must explain what failed, why it matters, and the next safe action.
7. **No secret exposure:** Errors, audit events, summaries, and confirmation prompts must never echo detected secret values.
8. **Relative project paths:** Specs, command examples, and user-facing local project paths should use relative paths when possible.

## Output Contract

### Human CLI Output

Default CLI output should include:
- Operation result: success, no-op, warning, or failure.
- Scope: project, global, host, skill, rule, snapshot, or audit.
- Affected relative paths when applicable.
- Audit reference for mutations.
- Next action only when useful.

Human output must not be the source of truth for automation. Tests should assert semantic content without overfitting to Rich styling.

### JSON CLI Output

All `--format json` responses must:
- Emit valid JSON to stdout and nothing else.
- Use `snake_case` keys.
- Use ISO 8601 UTC timestamps for time fields.
- Use relative paths for project-local paths when possible.
- Include `audit_reference` for successful mutations.
- Include `warnings[]` when the operation succeeds with caveats.
- Include `errors[]` only for multi-item partial failures; single failures should use the standard error envelope.

Standard success envelope:

```json
{
  "ok": true,
  "operation": "status",
  "scope": "project",
  "data": {},
  "warnings": []
}
```

Standard error envelope:

```json
{
  "ok": false,
  "error": {
    "code": "validation_failed",
    "message": "Configuration is invalid.",
    "detail": "Missing project memory path.",
    "recovery_hint": "Run umem init from the project root.",
    "audit_reference": null
  }
}
```

## Confirmation Contract

Confirmations are required before:
- Writing or modifying instruction files such as `AGENTS.md` or `CLAUDE.md`.
- Promoting recurring facts into persistent rules.
- Creating, activating, deactivating, or editing skills.
- Purging facts or memory bases.
- Rolling back snapshots.
- Applying host setup changes that alter files.

Confirmation prompts must show:
- Operation summary.
- Scope.
- Affected relative paths.
- Whether a snapshot will be created.
- Expected audit event.
- Choices and default behavior.

Rule and skill learning flows must support the PRD options `Sim`, `Sempre`, and `Não`. Destructive or irreversible operations must not default to confirmation.

## Error Contract

CLI errors should show:
- Short failure title.
- Safe detail without secrets.
- Recovery hint.
- Audit/log reference when available.

MCP errors should map domain exceptions to JSON-RPC error codes defined by the architecture and include safe `data.detail` plus `data.recovery_hint`.

Domain error mapping:

| Domain error | JSON-RPC code | CLI behavior |
| --- | ---: | --- |
| `SecretDetectedError` | `-32010` | Explain that secret-like content was blocked; do not print the secret |
| `SnapshotFailedError` | `-32020` | Explain mutation was aborted before write |
| `ValidationFailedError` | `-32602` | Show invalid field or input reason |
| `FactNotFoundError` | `-32040` | Show missing identifier/scope |
| `InvalidConfigError` | `-32050` | Show config path and recovery command |
| `StorageError` | `-32060` | Show safe storage failure and retry guidance |

## Command Contracts

### `umem init`

Human output:
- Indicates whether `.umem/` was created or already existed.
- Lists created or reused relative paths.
- Shows next command suggestion.

JSON `data` keys:
- `project_path`
- `config_path`
- `memory_path`
- `audit_path`
- `snapshots_path`
- `created`
- `already_initialized`
- `audit_reference`

### `umem status`

Human output:
- Shows initialization state, fact counts, active rules, registered skills, approximate size, host validation status, and last health check.

JSON `data` keys:
- `initialized`
- `project_path`
- `fact_counts`
- `active_rules_count`
- `registered_skills_count`
- `approximate_size_bytes`
- `last_health_check`
- `host_validation`
- `recommended_action` when uninitialized

### `umem context`

Human output:
- Shows compact project summary, universal preferences, active rules, and source references.

JSON `data` keys:
- `project_summary`
- `universal_preferences`
- `active_rules`
- `source_fact_ids`
- `truncated`
- `token_estimate`
- `last_read_at`

### `umem remember`

Human output:
- Shows saved fact id, scope, status, tags, and audit reference.

JSON `data` keys:
- `fact_id`
- `scope`
- `status`
- `tags`
- `created_at`
- `audit_reference`

### `umem audit list`

JSON `data` keys:
- `events[]` with `timestamp`, `action`, `scope`, `origin`, `result`, `snapshot_reference`, and `audit_reference`.

### `umem snapshots list`

JSON `data` keys:
- `snapshots[]` with `timestamp`, `scope`, `origin`, `action`, `relative_path`, `hash`, and `manifest_path`.

### `umem rollback`

Human output:
- Shows target scope, snapshot selected, affected path, and confirmation prompt before restore.

JSON `data` keys:
- `scope`
- `snapshot_reference`
- `restored_paths`
- `audit_reference`

### `umem host setup/check`

Human output:
- Shows host id, instruction target, mutation plan, manual steps, and validation result.

JSON `data` keys:
- `host_id`
- `instruction_targets`
- `planned_changes`
- `manual_steps`
- `validation_status`
- `audit_reference`

### `umem skills list/detail/propose`

JSON `data` keys for list:
- `skills[]` with `name`, `scope`, `status`, `relative_path`, `created_at`, `updated_at`, `origin`, and `audit_reference`.

JSON `data` keys for detail:
- `name`
- `scope`
- `status`
- `relative_path`
- `triggers`
- `audit_reference`
- `references_loaded`

Skill proposal prompts must show suggested name, scope, purpose, summarized evidence, and choices `Sim`, `Sempre`, and `Não`.

## MCP Parity

Every public CLI capability should have an equivalent MCP tool/resource unless explicitly marked internal. MCP responses should use the same semantic fields as CLI JSON responses even when transport-specific wrappers differ.

Parity tests should verify:
- Same use case is invoked by CLI and MCP adapters.
- Same success fields are present.
- Same domain errors map to expected CLI and MCP forms.
- Read-only operations remain side-effect free.

## Story Integration

Implementation stories that expose CLI or MCP behavior must reference this document and include tests for:
- Human output semantic content.
- JSON parseability and required keys.
- Error envelope for expected domain errors.
- Confirmation behavior for mutations.
- CLI/MCP parity when both surfaces exist.
