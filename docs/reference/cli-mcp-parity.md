# CLI And MCP Parity

The CLI is the canonical surface. MCP exposes equivalent behavior for agents and
hosts by calling the same application use cases.

| Capability | CLI | MCP |
| --- | --- | --- |
| Initialize project | `umem init` | `initialize_project` |
| Status | `umem status` | `status` |
| Inspect project layout | `umem layout status` | `inspect_project_layout` |
| Migrate project layout | `umem layout migrate` | `migrate_project_layout` |
| Diagnostics | `umem doctor` | `doctor` |
| Context | `umem context` | `context` |
| Remember fact | `umem remember` | `remember_fact` |
| List facts | `umem facts list` | `list_facts` |
| Purge fact | `umem facts purge` | `purge_fact` |
| Audit events | `umem audit list` | `list_audit_events` |
| Snapshots | `umem snapshots list` | `list_snapshots` |
| Rollback | `umem rollback` | `rollback_scope` |
| Host setup | `umem host setup` | `host_setup` |
| Host check | `umem host check` | `host_check` |
| Instruction sync | `umem host sync` | `sync_instructions` |
| Create skill | `umem skills create` | `create_skill` |
| Import skill | `umem skills import` | `import_skill` |
| Share skill | `umem skills share` | `share_skill` |
| Sync skills | `umem skills sync` | `sync_skills` |
| Track skill | `umem skills track` | `track_latent_skill` |
| Recommend skills | `umem skills recommend` | `recommend_skills` |
| Propose skill | `umem skills propose` | `propose_skill` |
| Promote skill recommendation | `umem skills promote` | `promote_skill_recommendation` |
| Generate skill | `umem skills generate` | `generate_skill` |
| List skills | `umem skills list` | `list_skills` |
| Skill detail | `umem skills detail` | `get_skill_detail` |
| Activate skill | `umem skills activate` | `activate_skill` |
| Deactivate skill | `umem skills deactivate` | `deactivate_skill` |
| Update skill | `umem skills update` | `update_skill` |

Parity does not mean identical UX. The CLI may use Rich human output and interactive
confirmation. MCP should return structured envelopes suitable for agent tool calls.

For automation, prefer JSON CLI output and non-interactive confirmation flags:

```bash
umem host sync --apply --yes --format json
umem layout status --format json
umem layout migrate --to shared --dry-run --format json
umem remember "Project uses shared UMEM root." --scope project --visibility shared --format json
umem facts list --scope project --visibility all --format json
umem skills import .agents/skills/review-protocol --scope project --sync --format json
umem skills share use-universal-memory --category operational --yes --format json
umem skills sync review-protocol --format json
```

Shared-layout payloads should keep path and visibility fields aligned across
surfaces:

| Data | CLI JSON | MCP |
| --- | --- | --- |
| Layout status | `operation=layout.status`, `shared_root`, `operational_root`, `ignored_shared_paths`, `tracked_operational_paths` | `inspect_project_layout()` |
| Migration | `operation=layout.migrate`, `copied`, `skipped`, `conflicts`, `remaining_local`, `next_steps` | `migrate_project_layout(target_layout="shared", dry_run=true)` |
| Project fact visibility | `visibility`, `storage_path` | `remember_fact(..., visibility="shared")`, `list_facts(..., visibility="all")` |
| Project skill visibility | `visibility`, `category`, `skill_file`, `canonical_skill.canonical_path` | `create_skill(..., visibility="shared", category="user-facing")` |
| Explicit skill sharing | `operation=skills.share`, shared canonical path, warnings | `share_skill(..., confirm_operational=true)` |

`skills import --sync` and MCP `import_skill(..., sync_after_import=true)` are the
recommended adoption path for existing native skills. Both surfaces should report the
canonical skill path, native installations, removed managed paths, warnings, and target
hash metadata consistently.
