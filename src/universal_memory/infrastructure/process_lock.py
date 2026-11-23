"""Protect legacy expiring locks with a stable kernel-owned lease.

The guard inode must never be removed: unlinking an advisory lock permits two
processes to own different inodes at the same path. Kernel leases survive long
operations and are released automatically on process exit. No stored data changes.
"""

import fcntl
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from universal_memory.domain import StorageError


class LockAcquisitionError(StorageError):
    pass


@contextmanager
def process_lock(
    path: Path,
    *,
    timeout: float = 2.0,
    message: str = "Failed to acquire lock on shared storage",
) -> Iterator[None]:
    guard = path.with_name(path.name + ".guard")
    guard.parent.mkdir(parents=True, exist_ok=True)
    with guard.open("a") as stream:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LockAcquisitionError(message) from None
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def legacy_file_lock(
    path: Path,
    *,
    timeout: float = 2.0,
    stale_after: float = 10.0,
    message: str = "Failed to acquire lock on shared storage",
) -> Iterator[None]:
    deadline = time.monotonic() + timeout
    with process_lock(path, timeout=timeout, message=message):
        # Only the lease owner may recover an abandoned legacy lock. Age alone
        # can no longer evict a live process, even during operations over 10s.
        try:
            if time.time() - path.stat().st_mtime > stale_after:
                path.unlink()
        except FileNotFoundError:
            pass
        token = str(uuid4())
        while True:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                break
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise LockAcquisitionError(message) from None
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        try:
            os.write(fd, token.encode())
            yield
        finally:
            os.close(fd)
            try:
                if path.read_text() == token:
                    path.unlink()
            except FileNotFoundError:
                pass
