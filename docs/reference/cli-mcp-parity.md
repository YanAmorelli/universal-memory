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
| Track skill | `umem skills track` | `track_latent_skill` |
| Propose skill | `umem skills propose` | `propose_skill` |
| Generate skill | `umem skills generate` | `generate_skill` |
| List skills | `umem skills list` | `list_skills` |
| Skill detail | `umem skills detail` | `get_skill_detail` |
| Activate skill | `umem skills activate` | `activate_skill` |
| Deactivate skill | `umem skills deactivate` | `deactivate_skill` |
| Update skill | `umem skills update` | `update_skill` |

Parity does not mean identical UX. The CLI may use Rich human output and
interactive confirmation. MCP should return structured envelopes suitable for
agent tool calls.
