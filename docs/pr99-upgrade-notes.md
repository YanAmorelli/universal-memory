# PR 99 upgrade notes

This change requires a quiescent upgrade. Close every old CLI command and every
old MCP server that uses the memory, including suspended sessions. Update every
installation and integration pin, then restart sessions with the updated code
before writing memory. Updating an executable does not replace the old code in
an already-open MCP process. Published 0.6.4 predates this lock protocol; verify
the installed commit rather than relying on the unchanged version number.

Do not keep old and new writers running together. The compatibility timestamp
does not prevent every mixed-version lost update; append alone cannot repair an
old writer that replaces the file afterward. See
[mixed-version storage locks](mixed-version-locks.md) for the demonstrated race
and manual recovery instructions. No release or version bump is part of this PR.

Memory ownership follows the current worktree's index:

- If the active layout's facts file is tracked, project memory uses this worktree.
  The main checkout does not need initialization. This includes a staged facts
  file; a tracked file missing from disk is still tracked until removed from the
  index. Existing local records are not treated as orphaned in this mode.
- If facts are untracked here, memory stays shared with the main checkout even
  when another branch tracks facts or this branch tracks only config. The main
  memory must be initialized before a shared project mutation.
- Legacy layout checks `.umem/memory/facts.jsonl`; shared layout checks
  `umem/memory/facts.jsonl`, or its configured shared root. Tracking an inactive
  layout's file does not select branch-local memory.
- `UMEM_MEMORY_ROOT` explicitly overrides automatic memory selection. Git access
  errors still stop resolution rather than silently choosing another store.
- A completely initialized nested subproject keeps its own memory, as before.

This changes ownership only: it neither moves existing records nor changes their
format, deletion semantics or Git merge behavior. Review branch-specific records
before removing a worktree. Merge-driver installation, operational-file untracking
and deletion retention are separate decisions and are not performed by this PR.
