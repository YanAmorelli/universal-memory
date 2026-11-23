"""Protect legacy expiring locks with a stable kernel-owned lease.

The guard inode must never be removed: unlinking an advisory lock permits two
processes to own different inodes at the same path. Kernel leases survive long
operations and are released automatically on process exit. No stored data changes.
"""

import fcntl
import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO
from uuid import uuid4

from universal_memory.domain.exceptions import LockAcquisitionError

# A finite filesystem timestamp, deliberately outside normal wall-clock changes.
# Legacy 0.6.1/0.6.4 treat a lock as stale solely by time.time() - st_mtime > 10.
# Pinning instead of heartbeating also protects a SIGSTOP'ed process. Do not
# interpret this marker as ownership: only the kernel lease plus token/inode do.
LEGACY_LOCK_MTIME_NS = 9_000_000_000_000_000_000


@contextmanager
def process_lock(
    path: Path,
    *,
    timeout: float = 2.0,
    message: str = "Failed to acquire lock on shared storage",
) -> Iterator[TextIO]:
    guard = path.with_name(path.name + ".guard")
    try:
        guard.parent.mkdir(parents=True, exist_ok=True)
        stream = guard.open("a+")
    except OSError as error:
        raise LockAcquisitionError(message, path=path) from error
    with stream:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LockAcquisitionError(message, path=path) from None
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
            except OSError as error:
                raise LockAcquisitionError(message, path=path) from error
        try:
            yield stream
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def legacy_file_lock(  # noqa: PLR0912, PLR0915
    path: Path,
    *,
    timeout: float = 2.0,
    stale_after: float = 10.0,
    message: str = "Failed to acquire lock on shared storage",
) -> Iterator[None]:
    deadline = time.monotonic() + timeout
    with process_lock(path, timeout=timeout, message=message) as guard:
        # Never evict an unknown UUID-only lock by age: it can belong to a live
        # old process that neither knows our kernel lease nor records its PID.
        # Recover only a previous updated owner whose kernel lease has ended.
        try:
            guard.seek(0)
            previous = json.load(guard)
            stat = path.stat()
            if previous == {"token": path.read_text(), "device": stat.st_dev, "inode": stat.st_ino}:
                path.unlink()
        except (FileNotFoundError, ValueError, TypeError):
            pass
        except OSError as error:
            raise LockAcquisitionError(message, path=path) from error
        token = str(uuid4())
        pending = path.with_name(path.name + "." + token + ".pending")
        try:
            fd = os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except OSError as error:
            raise LockAcquisitionError(message, path=path) from error
        identity = os.fstat(fd)
        acquired = False
        try:
            os.write(fd, token.encode())
            os.utime(fd, ns=(identity.st_atime_ns, LEGACY_LOCK_MTIME_NS))
            prepared = os.fstat(fd)
            if prepared.st_mtime_ns != LEGACY_LOCK_MTIME_NS:
                raise LockAcquisitionError(
                    "Filesystem cannot preserve the legacy lock timestamp", path=path
                )
            if prepared.st_mtime - time.time() <= stale_after:
                raise LockAcquisitionError(
                    "Filesystem clock cannot safely fence legacy writers", path=path
                )
            guard.seek(0)
            guard.truncate()
            json.dump({"token": token, "device": identity.st_dev, "inode": identity.st_ino}, guard)
            guard.flush()
            os.fsync(guard.fileno())
            # Publish an already-pinned inode atomically. Otherwise an old
            # reader could cache the initial mtime before utime, get suspended,
            # then evict our live lock using that cached value after ten seconds.
            while True:
                try:
                    os.link(pending, path)
                    break
                except FileExistsError:
                    if time.monotonic() >= deadline:
                        raise LockAcquisitionError(message, path=path, unknown_owner=True) from None
                    time.sleep(min(0.05, max(0, deadline - time.monotonic())))
            pending.unlink()
            current = path.stat()
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
                raise LockAcquisitionError(
                    "Legacy lock ownership changed before acquisition", path=path
                )
            acquired = True
            yield
        except OSError as error:
            if not acquired:
                raise LockAcquisitionError(message, path=path) from error
            raise
        finally:
            os.close(fd)
            try:
                current = path.stat()
                if (current.st_dev, current.st_ino) == (
                    identity.st_dev,
                    identity.st_ino,
                ) and path.read_text() == token:
                    path.unlink()
            except FileNotFoundError:
                pass
            pending.unlink(missing_ok=True)
