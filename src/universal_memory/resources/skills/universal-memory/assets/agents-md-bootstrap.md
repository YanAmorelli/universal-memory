## Universal Memory

Before durable planning, implementation, investigation, or review, prefer MCP
`bootstrap()` when available; otherwise run `umem bootstrap --format json` once at the
start of the conversation or session.
Reconcile `data.context` with the current repository and the user's instructions. Inspect
`data.skills.list` and request details only for selected relevant skills. Follow the
`universal-memory` Agent Skill when available. Persist only stable, reusable, and safe
information. If UMEM is unavailable, say so and continue without inventing context.
