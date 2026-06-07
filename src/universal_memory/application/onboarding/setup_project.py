# ruff: noqa: E501

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from universal_memory.domain import ConfigValidationPort, InvalidConfigError, ProjectLayoutPort
from universal_memory.domain.entities.runtime import RuntimeId, default_runtime_registry
from universal_memory.infrastructure.config.toml_loader import load_config, update_project_config

DEFAULT_ENABLED_RUNTIME_IDS = [
    runtime_id.value for runtime_id in default_runtime_registry().runtime_ids
]
DEFAULT_ENABLED_HOST_IDS = DEFAULT_ENABLED_RUNTIME_IDS
DEFAULT_UMEM_SKILL_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_UMEM_SKILL_NAME = "use-universal-memory"
DEFAULT_UMEM_SKILL_RELATIVE_PATH = ".umem/skills/use-universal-memory/SKILL.md"
DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH = ".umem/memory/latent_skills.jsonl"
DEFAULT_UMEM_SKILL_MARKDOWN = """---
name: "use-universal-memory"
description: "Operational hub for using Universal Memory context, facts, host sync, and skills lifecycle."
triggers:
  - "at the start of a work session or conversation"
  - "before implementing, investigating, reviewing, or planning in a repository with .umem"
  - "when the user mentions memory, facts, context, skills, AGENTS.md, CLAUDE.md, host sync, or learned preferences"
  - "before recording durable project or global knowledge"
  - "before creating, updating, activating, or deactivating a UMEM skill"
---

# Use Universal Memory

## Purpose

Universal Memory (`umem`) is the repository memory and skill layer. This skill is the
single UMEM guide and router: use it to load current memory context, interpret UMEM
state, decide whether deeper instructions are needed, and route directly to the focused
reference for the task.

Keep this as one guide-style skill. Do not split UMEM into separate skills for startup,
facts, host sync, or skill lifecycle work unless the user explicitly approves that design
change.

## Desired Outcomes

- Agents begin repository work with current UMEM context and relevant active skills.
- Users get behavior informed by durable project facts and global preferences without
  host files becoming memory dumps.
- Memory mutations are deliberate, safe, scoped correctly, and synced when they should
  affect future host instructions.
- References are loaded only on demand, preserving Agent Skills progressive disclosure.

## Data Sources

- `.umem/` project storage and generated project skills.
- `AGENTS.md` and `CLAUDE.md` managed UMEM bootstrap instructions.
- CLI output from `umem status`, `umem context`, `umem skills list`, and targeted read or
  mutation commands.
- MCP tool results when available; treat them as equivalent automation surfaces over the
  CLI behavior contract.
- `references/` files in this skill for deeper task-specific procedures.

## Mandatory Startup

At the start of a conversation, session, or new task, load UMEM context before planning,
editing, investigating, reviewing, or activating another workflow:

```bash
umem status --format json
umem context --scope project --format json
umem skills list --format json
```

Then inspect any relevant active skill:

```bash
umem skills detail <skill-id-or-name> --format json
```

Prefer the equivalent MCP tools when they are available. Use the CLI examples in the
references as the canonical behavior contract.

## Workflow And State Interpretation

- If `status` reports UMEM unavailable or uninitialized, say so explicitly and continue
  without external memory instead of inventing context.
- Treat `context --scope project` output as active repository guidance for the current
  work session.
- Treat global context as cross-project user preference; do not let it override explicit
  project constraints or user instructions for the current task.
- Treat `skills list` as discovery metadata. Inspect only relevant active skills with
  `skills detail`, and load deeper skill files only when the current task calls for them.
- Do not repeat the full startup sequence on every user message in the same conversation;
  query only the specific UMEM state needed after the initial preflight.
- Preserve relative paths in specs, docs, code, and reports.

## Reference Routing

- For startup, health, context loading, and active-skill discovery, read
  `references/startup-and-context.md`.
- For remembering, listing, and purging facts, read `references/memory-facts.md`.
- For latent skill tracking, proposal, generation, listing, detail, activation,
  deactivation, and update, read `references/skills-lifecycle.md`.
- For host instruction setup, validation, and sync, read
  `references/host-instructions-sync.md`.
- For CLI/MCP payload parity and error behavior, read `references/cli-mcp-parity.md`.
- For durable recording rules, security guardrails, and final response footer behavior,
  read `references/guardrails-and-recording.md`.

## Response And Recording Constraints

- Keep host instruction files compact; they should point to UMEM, not store memory dumps.
- Record only curated, durable facts or skills. Do not persist raw logs, secrets,
  credentials, transient steps, or uncertain information.
- Use project scope for repository-specific knowledge and global scope for cross-project
  user preferences.
- After any memory mutation that should affect host instructions, run host sync with
  apply enabled.
- Before the final response, decide whether a durable fact, skill pattern, architectural
  decision, or obsolete memory should be recorded or cleaned up.
- End the final response with either `[UMEM: Remembered "..."]` or
  `[UMEM: No new facts/skills to record]`.
"""
DEFAULT_UMEM_SKILL_REFERENCES = {
    ".umem/skills/use-universal-memory/references/startup-and-context.md": """# Startup And Context

Use this reference when beginning a session or when an agent needs the current UMEM
state before planning, editing, investigating, reviewing, or using another workflow.

## Use Cases

- Confirm whether the current project is initialized and healthy.
- Load project context plus relevant global preferences.
- Discover active or candidate skills before acting.
- Inspect one relevant skill without loading large reference files unless needed.
- Continue without external memory only after reporting that UMEM is unavailable or not
  initialized.

## Canonical CLI

```bash
umem status --format json
umem context --scope project --format json
umem context --scope project --max-size-chars 4000 --format json
umem context --scope global --format json
umem skills list --format json
umem skills detail <skill-id-or-name> --format json
```

## Parameters

- `--format json`: use for agent automation and deterministic parsing.
- `--scope project|global`: choose project for repository context; choose global only
  when the task is explicitly cross-project.
- `--max-size-chars <number>`: cap returned context when the caller has a tight context
  budget.
- `<skill-id-or-name>`: skill identifier or unique skill name. Use the ID when a name is
  ambiguous.

## MCP Equivalents

- `status()`
- `context(scope="project", max_size_chars=<number>)`
- `context(scope="global")`
- `list_skills()`
- `get_skill_detail(name_or_id="<skill-id-or-name>")`

## Expected Behavior

- Treat `context` output as active project guidance.
- Treat `skills detail` as a lightweight metadata read; it should not force loading large
  files under a skill's `references/` directory.
- Do not repeat the full startup sequence on every user message in the same conversation.
  Query specific UMEM state only when the task requires it.
""",
    ".umem/skills/use-universal-memory/references/memory-facts.md": """# Memory Facts

Use this reference for durable facts: storing useful knowledge, inspecting stored facts,
and removing obsolete or incorrect memory.

## Use Cases

- Store a stable project decision, architecture note, workflow, bug fix, command, or
  constraint.
- Store a global user preference that should apply across repositories.
- List facts to verify current memory before updating it.
- Purge an outdated or incorrect fact by ID.
- Avoid storing transient task progress, raw command output, secrets, credentials, or
  unverified claims.

## Canonical CLI

```bash
umem remember "Short verified fact." --scope project --tag architecture --format json
umem remember "Durable user preference." --scope global --tag preference --format json
umem facts list --scope project --format json
umem facts list --scope global --format json
umem facts purge --id <fact-id> --format json
```

If host instructions should reflect the change, sync after the mutation:

```bash
umem host sync --apply --yes --format json
```

## Parameters

- `"Short verified fact."`: one concise sentence; prefer specific, reusable knowledge.
- `--scope project|global`: project for repository-specific knowledge, global for
  cross-project user preferences.
- `--tag <tag>`: use curated tags such as `architecture`, `workflow`, `bug`, `testing`,
  `docs`, `preference`, or `security`.
- `--id <fact-id>`: exact fact ID returned by `facts list`.
- `--format json`: canonical machine-readable output.

## MCP Equivalents

- `remember_fact(content="Short verified fact.", scope="project", tags=["architecture"])`
- `remember_fact(content="Durable user preference.", scope="global", tags=["preference"])`
- `list_facts(scope="project")`
- `list_facts(scope="global")`
- `purge_fact(id="<fact-id>", confirm=true)`
- `sync_instructions(apply=true)`

## Expected Behavior

- Mutations should use the safe write pipeline: secret scan, snapshot, atomic write, and
  audit event.
- If a fact is uncertain, verify or ask before recording it.
- If a fact is obsolete, purge the old fact instead of adding a contradictory one.
""",
    ".umem/skills/use-universal-memory/references/skills-lifecycle.md": """# Skills Lifecycle

Use this reference for UMEM skill discovery, latent skill tracking, approval, generation,
activation, deactivation, and updates.

## Use Cases

- Track a recurring workflow or methodology as a latent skill candidate.
- Review and approve or reject a latent skill proposal.
- Generate the canonical Agent Skills directory structure.
- List and inspect active, disabled, and candidate skills.
- Deactivate a skill without deleting its files.
- Reactivate a disabled skill after validating its `SKILL.md`.
- Update skill metadata, triggers, or full markdown content through the safe mutation
  pipeline.

## Canonical CLI

```bash
umem skills list --format json
umem skills detail <skill-id-or-name> --format json
umem skills track --name "Skill name" --description "What the skill does." --scope project --evidence-summary "Why this pattern recurred." --tag workflow --format json
umem skills propose <latent-skill-id> --decision yes --format json
umem skills propose <latent-skill-id> --decision always --format json
umem skills propose <latent-skill-id> --decision no --format json
umem skills generate <latent-skill-id> --yes --format json
umem skills generate <latent-skill-id> --yes --update-existing --format json
umem skills deactivate <latent-skill-id> --format json
umem skills activate <latent-skill-id> --format json
umem skills update <latent-skill-id> --name "New name" --description "New description." --trigger "when to use it" --format json
umem skills update <latent-skill-id> --file <relative-markdown-path> --format json
```

## Parameters

- `<skill-id-or-name>`: identifier or unique name for read-only detail.
- `<latent-skill-id>`: exact latent skill ID for proposal and mutations.
- `--name <text>`: skill display name.
- `--description <text>`: concise purpose and behavior.
- `--scope project|global`: project is default; global is for cross-project agent
  workflows.
- `--evidence-summary <text>`: curated reason this recurring pattern should be tracked.
- `--tag <tag>`: repeatable trigger or classification.
- `--decision yes|always|no`: explicit proposal decision for non-interactive use.
- `--yes`: required for non-interactive generation.
- `--update-existing`: update an existing generated skill directory instead of choosing
  an alternate slug.
- `--trigger <text>`: repeatable trigger used in generated skill frontmatter.
- `--file <relative-markdown-path>`: complete replacement markdown for `SKILL.md`.
- `--format json`: canonical automation output.

## MCP Equivalents

- `list_skills()`
- `get_skill_detail(name_or_id="<skill-id-or-name>")`
- `track_latent_skill(name="Skill name", description="What the skill does.", scope="project", evidence_summary="Why this pattern recurred.", tags=["workflow"])`
- `propose_skill(latent_skill_id="<latent-skill-id>", decision="yes")`
- `propose_skill(latent_skill_id="<latent-skill-id>", decision="always")`
- `propose_skill(latent_skill_id="<latent-skill-id>", decision="no")`
- `generate_skill(latent_skill_id="<latent-skill-id>", update_existing=false)`
- `generate_skill(latent_skill_id="<latent-skill-id>", update_existing=true)`
- `deactivate_skill(latent_skill_id="<latent-skill-id>")`
- `activate_skill(latent_skill_id="<latent-skill-id>")`
- `update_skill(latent_skill_id="<latent-skill-id>", name="New name", description="New description.", triggers=["when to use it"])`
- `update_skill(latent_skill_id="<latent-skill-id>", raw_markdown="<complete SKILL.md content>")`

## Expected Behavior

- `skills list` returns active, candidate, and disabled skills with relative paths when
  materialized.
- `skills detail` returns triggers and metadata without loading large references.
- `skills track` creates or increments a proposed latent skill and records recurrence.
- `skills generate` creates canonical files under `.umem/skills/` for project skills.
- `skills deactivate` preserves files and changes status to disabled.
- `skills activate` requires a readable, valid `SKILL.md`.
- `skills update` writes through snapshot, secret scanning, audit, and rollback-capable
  safe write behavior.
""",
    ".umem/skills/use-universal-memory/references/host-instructions-sync.md": """# Host Instructions Sync

Use this reference when UMEM needs to install, validate, or refresh host instruction
targets such as shared agent instructions and runtime-specific files.

## Use Cases

- Initialize host instruction files for supported runtimes.
- Validate that host files still contain the managed UMEM block.
- Preview host instruction changes without applying them.
- Apply a sync after recording or purging durable memory.
- Keep host files compact and prevent raw memory dumps in instruction targets.

## Canonical CLI

```bash
umem host setup codex --yes --format json
umem host setup claude_code --yes --format json
umem host check codex --format json
umem host check claude_code --format json
umem host sync --no-apply --format json
umem host sync --apply --yes --format json
```

## Parameters

- `codex`: host that consumes `AGENTS.md`.
- `claude_code`: host that consumes `CLAUDE.md`.
- `--yes`: non-interactive confirmation for writes.
- `--no-apply`: preview sync output without writing files.
- `--apply`: apply the generated host instruction update.
- `--format json`: canonical automation output.

## MCP Equivalents

- `host_setup(host_id="codex", force=true)`
- `host_setup(host_id="claude_code", force=true)`
- `host_check(host_id="codex")`
- `host_check(host_id="claude_code")`
- `sync_instructions(apply=false)`
- `sync_instructions(apply=true)`

## Expected Behavior

- Host setup and sync should only write managed instruction sections.
- Host files should point to UMEM and its startup commands; they should not embed raw
  memory dumps.
- After memory mutations that should affect future agent behavior, run sync with
  `--apply`.
- If host validation fails, inspect the reported relative path and restore the managed
  UMEM block instead of duplicating instructions manually.
""",
    ".umem/skills/use-universal-memory/references/cli-mcp-parity.md": """# CLI MCP Parity

Use this reference when documenting, testing, or implementing UMEM behavior across CLI
and MCP surfaces.

## Principle

The CLI is the canonical contract. MCP tools are equivalent automation surfaces over the
same application use cases. Do not document MCP-only behavior unless the capability is
explicitly MCP-only.

## Success Envelope

CLI commands with `--format json` and MCP tools should return equivalent payloads:

```json
{
  "ok": true,
  "operation": "skills.track",
  "scope": "project",
  "data": {},
  "warnings": []
}
```

## Core Capability Map

| Capability | Canonical CLI | MCP equivalent |
| --- | --- | --- |
| Initialize project | `umem init --yes --format json` | `initialize_project()` |
| Status | `umem status --format json` | `status()` |
| Context | `umem context --scope project --format json` | `context(scope="project")` |
| Remember fact | `umem remember "..." --scope project --tag workflow --format json` | `remember_fact(content="...", scope="project", tags=["workflow"])` |
| List facts | `umem facts list --scope project --format json` | `list_facts(scope="project")` |
| Purge fact | `umem facts purge --id <fact-id> --format json` | `purge_fact(id="<fact-id>", confirm=true)` |
| Audit list | `umem audit list --scope project --format json` | `list_audit_events(scope="project")` |
| Snapshots list | `umem snapshots list --scope project --format json` | `list_snapshots(scope="project")` |
| Rollback | `umem rollback --scope project --yes --format json` | `rollback_scope(scope="project")` |
| Host setup | `umem host setup codex --yes --format json` | `host_setup(host_id="codex", force=true)` |
| Host check | `umem host check codex --format json` | `host_check(host_id="codex")` |
| Host sync | `umem host sync --apply --yes --format json` | `sync_instructions(apply=true)` |
| Skills list | `umem skills list --format json` | `list_skills()` |
| Skill detail | `umem skills detail <skill-id-or-name> --format json` | `get_skill_detail(name_or_id="<skill-id-or-name>")` |
| Track skill | `umem skills track ... --format json` | `track_latent_skill(...)` |
| Propose skill | `umem skills propose <latent-skill-id> --decision yes --format json` | `propose_skill(latent_skill_id="<latent-skill-id>", decision="yes")` |
| Generate skill | `umem skills generate <latent-skill-id> --yes --format json` | `generate_skill(latent_skill_id="<latent-skill-id>")` |
| Activate skill | `umem skills activate <latent-skill-id> --format json` | `activate_skill(latent_skill_id="<latent-skill-id>")` |
| Deactivate skill | `umem skills deactivate <latent-skill-id> --format json` | `deactivate_skill(latent_skill_id="<latent-skill-id>")` |
| Update skill | `umem skills update <latent-skill-id> ... --format json` | `update_skill(...)` |

## Error Mapping

| Domain error | MCP JSON-RPC code |
| --- | --- |
| `SecretDetectedError` | `-32010` |
| `SnapshotFailedError` | `-32020` |
| `ValidationFailedError` | `-32602` |
| `FactNotFoundError` | `-32040` |
| `InvalidConfigError` | `-32050` |
| `StorageError` | `-32060` |

## Expected Behavior

- CLI adapters and MCP tools should stay thin: translate inputs, call use cases, and
  format outputs.
- New public capabilities should include both CLI and MCP coverage unless explicitly
  marked internal.
- Error output must not leak secrets, stack traces, or absolute local paths.
""",
    ".umem/skills/use-universal-memory/references/guardrails-and-recording.md": """# Guardrails And Recording

Use this reference before finalizing a task, changing memory, or deciding whether a
recurring workflow should become a skill.

## What To Record

Record only curated, durable information:

- Architecture decisions and repository conventions.
- Commands or workflows that future agents will need again.
- Verified bug fixes and important troubleshooting findings.
- Stable user preferences in global scope.
- Repeated methodologies that are strong candidates for a formal skill.

## What Not To Record

Do not record:

- Secrets, credentials, tokens, private keys, or environment dumps.
- Raw logs, long command output, stack traces, or large pasted files.
- Temporary task progress that will be irrelevant after the current turn.
- Unverified assumptions or guesses.
- Duplicate facts that should instead update or purge an existing fact.

## Canonical CLI

```bash
umem facts list --scope project --format json
umem facts list --scope global --format json
umem remember "Short verified fact." --scope project --tag workflow --format json
umem remember "Durable user preference." --scope global --tag preference --format json
umem facts purge --id <fact-id> --format json
umem skills track --name "Skill name" --description "Reusable workflow." --scope project --evidence-summary "Observed recurring workflow." --tag workflow --format json
umem host sync --apply --yes --format json
```

## MCP Equivalents

- `list_facts(scope="project")`
- `list_facts(scope="global")`
- `remember_fact(content="Short verified fact.", scope="project", tags=["workflow"])`
- `remember_fact(content="Durable user preference.", scope="global", tags=["preference"])`
- `purge_fact(id="<fact-id>", confirm=true)`
- `track_latent_skill(name="Skill name", description="Reusable workflow.", scope="project", evidence_summary="Observed recurring workflow.", tags=["workflow"])`
- `sync_instructions(apply=true)`

## Final Response Footer

Before completing a turn:

1. Decide whether the task produced a durable fact, skill pattern, architectural decision,
   bug fix, or obsolete memory cleanup.
2. If yes, record or purge it through UMEM and sync host instructions when needed.
3. If no, do not mutate memory.
4. End the final response with exactly one UMEM footer:

```text
[UMEM: Remembered "..."]
[UMEM: No new facts/skills to record]
```

## Safety Rules

- Use project scope unless the information clearly applies across repositories.
- Prefer one short sentence per remembered fact.
- Use tags that future agents can filter reliably.
- Do not run bulk cleanup, rollback, or destructive hygiene without explicit user
  confirmation.
- If UMEM storage is unavailable, report it and continue without external memory rather
  than inventing context.
""",
}


@dataclass(frozen=True, slots=True)
class SetupProjectResult:
    project_path: Path
    config_path: Path
    memory_path: Path
    audit_path: Path
    snapshots_path: Path
    skills_path: Path
    benchmarks_path: Path
    created: bool
    already_initialized: bool
    created_paths: list[str]
    existing_paths: list[str]


def setup_project(  # noqa: PLR0913
    project_root: Path,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
    global_config_path: Path | None = None,
    enabled_runtime_ids: list[str] | None = None,
    enabled_host_ids: list[str] | None = None,
) -> SetupProjectResult:
    normalized_project_root = project_root.resolve()
    layout_result = layout_port.ensure_project_layout(normalized_project_root)
    seeded_skill_paths = _ensure_default_umem_skill(normalized_project_root)
    loaded_config = load_config(normalized_project_root, global_config_path=global_config_path)
    requested_runtime_ids = (
        enabled_runtime_ids if enabled_runtime_ids is not None else enabled_host_ids
    )
    if requested_runtime_ids is None:
        configured_runtime_ids = _configured_runtime_ids(loaded_config.merged)
        normalized_runtime_ids = (
            configured_runtime_ids
            if configured_runtime_ids is not None
            else list(DEFAULT_ENABLED_RUNTIME_IDS)
        )
    else:
        normalized_runtime_ids = _normalize_runtime_ids(requested_runtime_ids)
    unsupported = [
        runtime_id
        for runtime_id in normalized_runtime_ids
        if runtime_id not in DEFAULT_ENABLED_RUNTIME_IDS
    ]
    if unsupported:
        raise InvalidConfigError(f"Unsupported runtimes: {', '.join(unsupported)}")

    preferences = loaded_config.project_data.get("preferences")
    updates: dict[str, Any] = {"runtimes": {"enabled": normalized_runtime_ids}}
    if not isinstance(preferences, dict) or "locale" not in preferences:
        updates["preferences"] = {"locale": "en"}

    update_project_config(
        normalized_project_root,
        updates,
        global_config_path=global_config_path,
    )

    # Validate config after materializing defaults so downstream adapters can rely on valid TOML.
    config_validation_port.validate_project_config(
        project_root=normalized_project_root,
        global_config_path=global_config_path,
    )

    umem_root = Path(".umem")
    return SetupProjectResult(
        project_path=Path("."),
        config_path=umem_root / "config.toml",
        memory_path=umem_root / "memory",
        audit_path=umem_root / "audit" / "events.jsonl",
        snapshots_path=umem_root / "snapshots",
        skills_path=umem_root / "skills",
        benchmarks_path=umem_root / "benchmarks",
        created=layout_result.created,
        already_initialized=not layout_result.created,
        created_paths=[*layout_result.created_paths, *seeded_skill_paths["created"]],
        existing_paths=[*layout_result.existing_paths, *seeded_skill_paths["existing"]],
    )


def _normalize_runtime_ids(runtime_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    for runtime_id in runtime_ids:
        cleaned = runtime_id.strip().lower().replace("-", "_")
        try:
            resolved = RuntimeId(cleaned).value
        except ValueError:
            resolved = cleaned
        if resolved not in normalized:
            normalized.append(resolved)
    return normalized


def _configured_runtime_ids(config_data: dict[str, Any]) -> list[str] | None:
    raw_runtimes = config_data.get("runtimes")
    if not isinstance(raw_runtimes, dict):
        return None
    raw_enabled = raw_runtimes.get("enabled")
    if not isinstance(raw_enabled, list):
        return None
    return _normalize_runtime_ids([str(runtime_id) for runtime_id in raw_enabled])


def _ensure_default_umem_skill(project_root: Path) -> dict[str, list[str]]:
    created: list[str] = []
    existing: list[str] = []

    skill_path = project_root / DEFAULT_UMEM_SKILL_RELATIVE_PATH
    if skill_path.exists():
        existing.append(DEFAULT_UMEM_SKILL_RELATIVE_PATH)
    else:
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(DEFAULT_UMEM_SKILL_MARKDOWN, encoding="utf-8")
        created.append(DEFAULT_UMEM_SKILL_RELATIVE_PATH)

    for relative_path, content in DEFAULT_UMEM_SKILL_REFERENCES.items():
        reference_path = project_root / relative_path
        if reference_path.exists():
            existing.append(relative_path)
        else:
            reference_path.parent.mkdir(parents=True, exist_ok=True)
            reference_path.write_text(content, encoding="utf-8")
            created.append(relative_path)

    latent_skills_path = project_root / DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH
    if _default_umem_skill_is_registered(latent_skills_path):
        existing.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)
    else:
        latent_skills_path.parent.mkdir(parents=True, exist_ok=True)
        with latent_skills_path.open("a", encoding="utf-8") as file:
            file.write(_default_umem_skill_jsonl_line())
        created.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)

    return {"created": created, "existing": existing}


def _default_umem_skill_is_registered(latent_skills_path: Path) -> bool:
    if not latent_skills_path.exists():
        return False
    try:
        content = latent_skills_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return DEFAULT_UMEM_SKILL_ID in content or DEFAULT_UMEM_SKILL_NAME in content


def _default_umem_skill_jsonl_line() -> str:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = {
        "schema_version": 1,
        "id": DEFAULT_UMEM_SKILL_ID,
        "created_at": timestamp,
        "updated_at": timestamp,
        "name": DEFAULT_UMEM_SKILL_NAME,
        "description": (
            "Operational hub for using Universal Memory context, facts, host sync, "
            "and skills lifecycle."
        ),
        "scope": "project",
        "status": "active",
        "recurrence_count": 1,
        "metadata": {
            "origin": "umem-init",
            "audit_reference": "seeded-by-init",
            "triggers": [
                "at the start of a work session or conversation",
                "before implementing, investigating, reviewing, or planning in a repository with .umem",
                "when the user mentions memory, facts, context, skills, AGENTS.md, CLAUDE.md, host sync, or learned preferences",
                "before recording durable project or global knowledge",
                "before creating, updating, activating, or deactivating a UMEM skill",
            ],
            "evidence": [
                {
                    "origin": "umem-init",
                    "summary": "Default operational skill installed during project initialization.",
                }
            ],
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
