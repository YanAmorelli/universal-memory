# CLI And MCP Parity

The CLI is the canonical surface. MCP exposes equivalent behavior for agents and
hosts by calling the same application use cases.

| Capability | CLI | MCP |
| --- | --- | --- |
| Initialize project | `umem init` | `initialize_project` |
| Status | `umem status` | `status` |
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
umem skills import .agents/skills/review-protocol --scope project --sync --format json
umem skills sync review-protocol --format json
```

`skills import --sync` and MCP `import_skill(..., sync_after_import=true)` are the
recommended adoption path for existing native skills. Both surfaces should report the
canonical skill path, native installations, removed managed paths, warnings, and target
hash metadata consistently.
