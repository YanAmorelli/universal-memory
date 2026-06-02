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
description: "Use umem to inspect project memory, skills, and durable learnings."
triggers:
  - "at the start of a work session"
  - "before implementing, investigating, or reviewing code"
  - "when project memory, facts, or skills are needed"
---

# Use Universal Memory

## When To Use

- At the start of a relevant work session.
- Before implementing, investigating, reviewing code, or answering questions about project
  decisions.
- When the user asks to inspect memory, context, facts, rules, or skills.
- After discovering a durable decision that should be remembered for future work.

## Procedure

1. Run `umem status` to confirm the project is initialized.
2. Run `umem context --scope project` to load relevant facts and preferences.
3. Run `umem skills list` to inspect registered or candidate skills.
4. If a skill looks relevant, run `umem skills detail <name-or-id>` before acting.
5. Use `umem facts list --scope project` when individual facts need to be audited.
6. During or at the end of the activity, review durable learnings and record only short,
   verifiable, non-sensitive facts.

## Global Memory Vs Project Memory

- Use `--scope global` for personal preferences, communication style, durable user
  information, recurring habits, and behavior that should apply across projects.
- Use `--scope project` for decisions, architecture, commands, constraints, tasks, bugs,
  domain knowledge, and learnings specific to the current repository.
- `umem context --scope project` loads project memory together with relevant global
  preferences.

## Examples

```bash
umem remember "Prefer concise responses in English." --scope global --tag preference
umem remember "Project uses Firebase Admin/ADC backend-only." --scope project --tag architecture
```

## Criteria For Recording Memory

- Record architecture decisions, recurring conventions, and user preferences in the
  correct scope.
- Do not record transient steps, huge outputs, raw logs, secrets, credentials,
  sensitive personal data, or uncertain information.
- Prefer short, verifiable facts with tags such as `architecture`, `workflow`, or `bug`.

## Guardrails

- Do not run `purge`, `rollback`, or `hygiene` without explicit user confirmation.
- Do not paste full memory dumps into host instruction files.
- Do not persist tokens, keys, env dumps, sensitive data, or facts you have not verified.
- If `umem status` reports an initialization problem, report it before continuing.
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
    requested_runtime_ids = (
        enabled_runtime_ids if enabled_runtime_ids is not None else enabled_host_ids
    )
    if requested_runtime_ids is not None:
        normalized_runtime_ids = _normalize_runtime_ids(requested_runtime_ids)
        unsupported = [
            runtime_id
            for runtime_id in normalized_runtime_ids
            if runtime_id not in DEFAULT_ENABLED_RUNTIME_IDS
        ]
        if unsupported:
            raise InvalidConfigError(f"Unsupported runtimes: {', '.join(unsupported)}")
    else:
        normalized_runtime_ids = list(DEFAULT_ENABLED_RUNTIME_IDS)

    loaded_config = load_config(normalized_project_root, global_config_path=global_config_path)
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
