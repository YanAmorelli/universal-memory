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
description: "Operational guide for using umem memory, skills, and durable learnings."
triggers:
  - "at the start of a work session or conversation"
  - "before implementing, investigating, or reviewing code in a new session"
  - "when project memory, facts, or skills are needed"
  - "when instructions mention AGENTS.md, CLAUDE.md, memory, context, or learned preferences"
  - "before changing project conventions, architecture, workflows, or documentation"
---

# Use Universal Memory

`umem` is the project memory layer. It stores short, curated facts and skills outside
agent-specific instruction files so Codex, Claude Code, and other agents can recover the
same context without duplicating or rewriting `AGENTS.md` and `CLAUDE.md`.

## When To Use

- At the start of a relevant work session or conversation.
- Before implementing, investigating, reviewing code, or answering questions about project
  decisions in a new session.
- When the user asks to inspect memory, context, facts, rules, or skills.
- After discovering a durable decision that should be remembered for future work.
- Before editing instructions, specs, docs, tests, or source files when the repository has
  `.umem/`.

## Required Startup / Session Procedure

This procedure is a mandatory preflight at the start of a conversation, session, or new task.
Run it before planning, editing, investigating, reviewing, using a skill, running a slash command,
or following any structured agent workflow in a new session. If `umem` is unavailable or not initialized,
report that explicitly before continuing without external memory.
Do not repeat the full bootstrap on every interaction.

1. Run `umem status --format json` to confirm the project is initialized and to inspect
   memory health.
2. Run `umem context --scope project --format json` before planning or editing. Treat the
   returned context as active project guidance.
3. Run `umem skills list --format json` to inspect active and candidate skills.
4. For every relevant active skill, run `umem skills detail <skill-id-or-name> --format json`
   and follow that skill before acting.
5. If a skill, slash command, or workflow has its own activation steps, run steps 1-4 before
   that activation. Do not let the workflow replace this preflight.
6. If no skill applies, continue with the loaded context. Do not skip steps 1-3 just because
   the task looks small.

Use the MCP/FastMCP tools with equivalent names when they are available. If the MCP tools
are unavailable, use the CLI commands above.

## Command Reference

```bash
umem status --format json
umem context --scope project --format json
umem skills list --format json
umem skills detail <skill-id-or-name> --format json
umem facts list --scope project --format json
umem facts list --scope global --format json
umem remember "Short verified fact." --scope project --tag workflow --format json
umem remember "Durable user preference." --scope global --tag preference --format json
umem facts purge --id <fact-id> --format json
```

## Global Memory Vs Project Memory

- Use `--scope global` for personal preferences, communication style, durable user
  information, recurring habits, and behavior that should apply across projects.
- Use `--scope project` for decisions, architecture, commands, constraints, tasks, bugs,
  domain knowledge, and learnings specific to the current repository.
- `umem context --scope project` loads project memory together with relevant global
  preferences.

## Recording & Cleanup Procedure

1. Record only stable facts that will help a future session.
2. Prefer one short sentence per fact.
3. Use `--scope global` only for cross-project user preferences.
4. Use `--scope project` for repository-specific decisions, commands, bugs, architecture,
   workflows, and documentation conventions.
5. Add a tag such as `preference`, `architecture`, `workflow`, `bug`, `testing`, or `docs`.
6. If the fact is uncertain, ask or verify before recording.
7. To permanently delete/remove an outdated or incorrect fact (memória defasada), use:
   `umem facts purge --id <fact-id>`
   After purging, run `umem host sync --apply` to update the host files (`AGENTS.md` / `CLAUDE.md`).

## Criteria For Recording Memory

- Record architecture decisions, recurring conventions, and user preferences in the
  correct scope.
- Do not record transient steps, huge outputs, raw logs, secrets, credentials,
  sensitive personal data, or uncertain information.
- Prefer short, verifiable facts with tags such as `architecture`, `workflow`, or `bug`.

## Examples

```bash
umem remember "Prefer concise responses in English." --scope global --tag preference
umem remember "Project uses Firebase Admin/ADC backend-only." --scope project --tag architecture
umem facts purge --id 9a5baa11-60a5-4532-b56a-5e9773c9116b
```

## Guardrails

- Do not run bulk `purge` (without `--id`), `rollback`, or `hygiene` without explicit user confirmation.
- Do not paste full memory dumps into host instruction files.
- Do not persist tokens, keys, env dumps, sensitive data, or facts you have not verified.
- If `umem status` reports an initialization problem, report it before continuing.
- Keep `AGENTS.md` and `CLAUDE.md` compact. They should point to `umem`, not contain raw
  memory dumps.
"""


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
            "Use umem to inspect project memory, available skills, and durable learnings "
            "before and after substantial work."
        ),
        "scope": "project",
        "status": "active",
        "recurrence_count": 1,
        "metadata": {
            "origin": "umem-init",
            "audit_reference": "seeded-by-init",
            "triggers": [
                "at the start of a work session",
                "before implementing, investigating, or reviewing code",
                "when project memory, facts, or skills are needed",
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
