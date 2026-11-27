# Mixed-version storage locks

Project memory sharing makes mixed-version sessions a practical risk. The way to
eliminate that risk is a quiescent upgrade: stop old CLI commands and all old MCP
processes, update every installation and integration pin, and start new sessions.
Do not run archived old versions against the shared store during that cutover.
Upgrading a binary leaves an already-running MCP process on its loaded old code.

## Evidence from released code

The fact, audit and snapshot repositories in tags `v0.6.1` and `v0.6.4` are byte
identical to the installed 0.6.1 distribution examined for this change. Unmodified
copies and SHA-256 digests are in `tests/fixtures/legacy_0_6_x/`. Regression tests
load those released modules in separate processes; they do not mock their lock
algorithms. The same worker can use a complete old source tree through the
test-only `UMEM_REAL_LEGACY_SRC` environment variable.

- Facts read the legacy lock's mtime, unlink it if `time.time() - mtime > 10`,
  then acquire with `O_CREAT | O_EXCL`. They write a UUID, not a PID, and check
  that UUID on release. The acquisition timeout is approximately two seconds.
- Audit and snapshot locks also expire after ten seconds. Their release unlinks
  the path without checking ownership. Audit has a configurable acquisition
  timeout; snapshots use approximately two seconds.
- Rules and skill registries have the same age-based expiry. Context summaries
  already use a stable `flock` and have no age-based eviction.
- Repository locks do not encompass arbitrary SafeWrite targets, initialization,
  configuration read/merge/write, rollback or native host/skill files. In particular,
  old rollback can replace a fact file without acquiring its repository lock.

An old writer could therefore evict the first implementation's live new UUID
lock after ten seconds. The new writer could also evict a live old UUID lock,
since the old process did not acquire the new kernel lease. Two old writers can
still evict one another; no change confined to the new executable can repair that.

## Chosen compatibility fence

The persisted fact, config, audit and snapshot formats remain unchanged, and the
legacy `.lock` still contains only its original UUID. No data migration is needed.
The already-stable operational `.guard` sidecar now records the UUID and the lock
file's device/inode while holding its kernel lease. It is not a memory record.

Before entering a mutation, the new owner prepares a private inode with lock mtime
`9000000000000000000` nanoseconds since epoch (2255). It verifies that the filesystem
preserved that timestamp and that the named inode still belongs to it. The old
expiry expression then sees a negative age under ordinary clock changes. This
requires no heartbeat thread and continues to protect a `SIGSTOP`'ed owner. The
already-pinned inode is published at the legacy path with an atomic hard link:
old readers never see an initial normal mtime that they could cache before a
suspension. Filesystems without hard links fail before entering the mutation.

This does **not** fence a cached timestamp from a previous legacy owner. A real
released reader can read that owner's old mtime, pause, and resume after the
previous owner exits and a new updated writer acquires its pinned lock. The old
reader unlinks the path using its cached value without checking the inode. It can
then write concurrently with the updated owner and lose a record. This was
reproduced with complete 0.6.1 and 0.6.4 packages, three real processes, and an old
owner held for more than ten real seconds: all writers returned success, but the
cached reader's committed fact was overwritten by the updated writer. The pause
was inserted after the real getmtime call; the released lock algorithm was unchanged.

The future timestamp therefore mitigates ordinary expiry of a new owner's inode;
it does not establish general mixed-version safety, even for repository writes.
A heartbeat, shorter lock duration, PID checks or a marker ignored by old code
cannot repair an old reader's unchecked unlink. A quiescent upgrade is required
for data-integrity guarantees across this cutover.

The new implementation never expires an unknown UUID-only lock. It recovers a
previous updated lock only while owning the kernel lease and only when its UUID,
device and inode match the operational ownership record. The kernel releases a
dead process's lease, so crash recovery does not depend on a PID, PID reuse,
process-start timestamps or wall-clock age. A partial ownership record fails
closed; it may need manual recovery after all writers have stopped.

The `.guard` inode must not be unlinked or replaced while writers may exist. Old
versions ignore it, so older installations do not need to understand a new schema.
Versions of this branch predating this fence may leave an empty sidecar; their
unrecognized leftover locks are also treated conservatively.

### Recovering an unknown legacy lock

CLI and MCP errors include `lock_path`, `lock_age_seconds` and recovery guidance.
The age is diagnostic only: a negative age may be the compatibility timestamp,
and an old timestamp does not prove that a process is dead. Do not run `umem init`
to repair a lock.

1. Stop all CLI and MCP writers using that storage, including old installations
   and suspended sessions. Restarting only the client does not stop an MCP server.
2. Back up the storage and confirm that no remaining process owns the indicated
   lock. If ownership remains uncertain, leave it in place.
3. Quarantine only the exact `.lock` file reported by the error, preserving a copy.
   Never remove, replace or move its `.guard` sidecar.
4. Retry with the updated executable and restart updated sessions. Preserve the
   quarantined file until recovery and data integrity have been verified.

Crashes before publication can leave private `*.pending` files. They are not
active locks and are not automatically deleted by another process; inspect them
only during the same quiescent maintenance procedure. Publication and recovery
are tested at both sides of guard persistence, hard-link publication and pending
unlink, without changing memory records or replacing the guard inode.

## Alternatives considered

| Option | Limit |
| --- | --- |
| Renew mtime periodically | Stops during suspension, starvation or a long runtime pause; a forward clock jump can expire the lock before renewal. |
| Shorten critical sections | Reduces probability; storage stalls and suspension still exceed ten seconds. |
| Evict only when the PID is dead | Old UUID locks contain no PID; PID reuse and permission errors make guessed ownership unsafe. A PID in new locks would not change old readers. |
| Add an incompatible-version marker | Old writers do not check it. A marker only the new executable obeys cannot fence a running old process. Enforced schema rejection would require a separately approved format/migration change. |
| Kernel lease alone | Old versions never acquire it and still unlink the legacy lock. |
| Future mtime plus proven kernel ownership | Mitigates ordinary expiry through suspension; unknown old owners are never expelled. Does not fence cached stale checks from a previous old owner or paths that ignore locks. |

## Validation and remaining boundaries

The mixed-process test holds actual read/modify/write operations across more than
ten real seconds, suspends their processes with `SIGSTOP`, and runs contenders in
both directions for facts, audit and snapshots. Contenders must return a typed
timeout without writing; after the holder resumes and completes, retry succeeds
and both records remain. Updated-process crashes are tested separately, as are
unknown ancient locks and clocks beyond the fence horizon.

There is no claim of universal zero risk: the cached-old-owner race, old unlocked
write paths and old/old concurrency remain outside this protocol. External modification of lock files,
filesystems without reliable POSIX locking or nanosecond timestamps, or an OS
clock jumping beyond the 2255 fence can invalidate the assumptions of old readers.
The new executable fails before mutation when its initial clock/filesystem checks
detect those problems, but it cannot control a later clock jump observed by old
code. The quiescent upgrade described above removes the mixed-version dependency;
all updated writers must still share a filesystem that honors kernel leases.

FAT32 and exFAT are explicitly unsupported. The lock implementation rejects a
filesystem that cannot retain the exact timestamp or publish a hard link, before
entering the protected mutation, with an actionable unsupported-filesystem error.
APFS and HFS+ passed the earlier filesystem reproduction; no general support is
claimed for network filesystems or configurations that lack these capabilities.
The regression tests emulate missing timestamp and hard-link capabilities; they
do not mount or provision filesystems.
