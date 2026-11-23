"""Subprocess-only harness using unmodified released storage implementations."""
# ruff: noqa: PLC0415, N806

import hashlib
import importlib.machinery
import importlib.util
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def load_legacy(name: str):
    path = Path(__file__).parents[1] / "fixtures/legacy_0_6_x" / (name + ".py.txt")
    loader = importlib.machinery.SourceFileLoader("released_" + name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def main() -> int:
    version, kind, directory, label, pause = sys.argv[1:]
    # An optional full source tree exercises a real tag/archive or the installed
    # distribution in addition to the frozen byte-for-byte release modules.
    import os

    if version == "old" and os.environ.get("UMEM_REAL_LEGACY_SRC"):
        sys.path.insert(0, os.environ["UMEM_REAL_LEGACY_SRC"])
    from universal_memory.application.security import SafeWriteUseCase
    from universal_memory.domain import SnapshotFailedError, StorageError
    from universal_memory.domain.entities import (
        AuditEvent,
        AuditEventScope,
        Fact,
        FactScope,
        FactStatus,
        Snapshot,
        SnapshotScope,
        SnapshotStatus,
    )
    from universal_memory.infrastructure.security import (
        EntropySecretScanner,
        LocalAuditLogRepository,
        LocalSnapshotRepository,
    )
    from universal_memory.infrastructure.storage import LocalFactRepository

    if version == "old" and not os.environ.get("UMEM_REAL_LEGACY_SRC"):
        LocalAuditLogRepository = load_legacy("local_audit_log_repository").LocalAuditLogRepository
        LocalSnapshotRepository = load_legacy("local_snapshot_repository").LocalSnapshotRepository
        LocalFactRepository = load_legacy("local_fact_repository").LocalFactRepository
    root = Path(directory)
    audit = LocalAuditLogRepository(
        project_root=root,
        data_root=root / ".umem",
        lock_acquire_timeout_seconds=2,
    )
    snapshots = LocalSnapshotRepository(project_root=root, data_root=root / ".umem")
    facts = LocalFactRepository(
        project_root=root,
        safe_write_use_case=SafeWriteUseCase(
            project_root=root,
            secret_scanner=EntropySecretScanner(),
            audit_log_repository=audit,
            snapshot_repository=snapshots,
        ),
    )
    repository = {"facts": facts, "audit": audit, "snapshots": snapshots}[kind]
    if pause == "hold":
        if kind == "facts":
            write = facts._write_facts_unlocked

            def hold_write(*args, **kwargs):
                print("held", flush=True)
                sys.stdin.readline()
                return write(*args, **kwargs)

            facts._write_facts_unlocked = hold_write
        else:
            acquire = repository._lock

            @contextmanager
            def hold_lock(*args, **kwargs):
                with acquire(*args, **kwargs):
                    print("held", flush=True)
                    sys.stdin.readline()
                    yield

            repository._lock = hold_lock
    now = datetime.now(UTC)
    identifier = str(uuid4())
    try:
        if kind == "facts":
            facts.write(
                Fact(
                    id=identifier,
                    created_at=now,
                    updated_at=now,
                    content=label,
                    scope=FactScope.project,
                    source="mixed-version-test",
                    status=FactStatus.active,
                )
            )
        elif kind == "audit":
            audit.write(
                AuditEvent(
                    id=identifier,
                    created_at=now,
                    updated_at=now,
                    timestamp=now,
                    action=label,
                    scope=AuditEventScope.project,
                    origin="test",
                    result="success",
                    snapshot_reference=str(uuid4()),
                    audit_reference=identifier,
                    status="logged",
                )
            )
        else:
            snapshots.write(
                Snapshot(
                    id=identifier,
                    created_at=now,
                    updated_at=now,
                    timestamp=now,
                    scope=SnapshotScope.project,
                    origin="test",
                    action=label,
                    relative_path=".umem/memory/facts.jsonl",
                    hash=hashlib.sha256(b"").hexdigest(),
                    status=SnapshotStatus.created,
                    previous_file_existed=False,
                )
            )
    except (StorageError, SnapshotFailedError):
        print("blocked", flush=True)
        return 23
    print("written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
