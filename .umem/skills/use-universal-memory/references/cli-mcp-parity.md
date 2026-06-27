# CLI MCP Parity

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
| Skill draft create | `umem skills draft create ... --format json` | `create_skill_draft(...)` |
| Skill validate | `umem skills validate <skill-or-path> --format json` | `validate_skill(skill_or_path="<skill-or-path>")` |
| Skill publish | `umem skills publish <draft-or-path> --format json` | `publish_skill(draft_or_path="<draft-or-path>")` |
| Skill create | `umem skills create ... --format json` | `create_skill(...)` |
| Skill adopt | `umem skills adopt <path> --format json` | `adopt_skill(path="<path>")` |
| Skill canonical update | `umem skills canonical update <skill> --file <path> --format json` | `update_canonical_skill(...)` |
| Skill rename | `umem skills rename <skill> --slug <slug> --format json` | `rename_skill(...)` |
| Skill cleanup | `umem skills cleanup <skill> --targets --format json` | `cleanup_skill(...)` |
| Skill repair | `umem skills repair --remove-orphan-targets --format json` | `repair_skills(...)` |
| Track skill | `umem skills track ... --format json` | `track_latent_skill(...)` |
| Recommend skills | `umem skills recommend --scope project --format json` | `recommend_skills(scope="project", dry_run=true)` |
| Propose skill | `umem skills propose <latent-skill-id> --decision yes --format json` | `propose_skill(latent_skill_id="<latent-skill-id>", decision="yes")` |
| Promote skill recommendation | `umem skills promote <recommendation-id> --yes --format json` | `promote_skill_recommendation(recommendation_id="<recommendation-id>", confirm=true)` |
| Generate skill | `umem skills generate <latent-skill-id> --yes --format json` | `generate_skill(latent_skill_id="<latent-skill-id>")` |
| Activate skill | `umem skills activate <latent-skill-id> --format json` | `activate_skill(latent_skill_id="<latent-skill-id>")` |
| Deactivate skill | `umem skills deactivate <latent-skill-id> --format json` | `deactivate_skill(latent_skill_id="<latent-skill-id>")` |
| Update latent/generated skill | `umem skills update <latent-skill-id> ... --format json` | `update_skill(...)` |

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
