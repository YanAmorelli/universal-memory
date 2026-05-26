from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from universal_memory.domain import SnapshotFailedError, StorageError
from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
from universal_memory.domain.ports import SnapshotRepository


class LocalSnapshotRepository(SnapshotRepository):
    def __init__(
        self,
        *,
        project_root: Path,
        data_root: Path,
        retention_limit: int = 5,
    ) -> None:
        if retention_limit < 1:
            raise ValueError("retention_limit must be at least 1")
        self.project_root = project_root
        self.data_root = data_root
        self.retention_limit = retention_limit
        self.snapshots_root = self.data_root / "snapshots"
        self.files_root = self.snapshots_root / "files"
        self.manifest_path = self.snapshots_root / "manifest.json"

    @contextmanager
    def _lock(self) -> Generator[None, None, None]:
        lock_path = self.manifest_path.with_suffix(".json.lock")
        self.snapshots_root.mkdir(parents=True, exist_ok=True)
        
        # Break stale locks older than 10 seconds
        if lock_path.exists():
            try:
                mtime = os.path.getmtime(lock_path)
                if time.time() - mtime > 10.0:
                    lock_path.unlink(missing_ok=True)
            except OSError:
                pass

        max_attempts = 20
        delay = 0.1
        acquired = False
        fd = None
        try:
            for _ in range(max_attempts):
                try:
                    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    acquired = True
                    break
                except FileExistsError:
                    time.sleep(delay)
            if not acquired:
                raise SnapshotFailedError("Failed to acquire lock on snapshot manifest")
            yield
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if acquired:
                try:
                    os.unlink(lock_path)
                except OSError:
                    pass

    def read(self, id: str) -> Snapshot:
        for snapshot in self._load_snapshots():
            if snapshot.id == id:
                return snapshot
        raise StorageError(f"Snapshot not found: {id}")

    def list(
        self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None
    ) -> list[Snapshot]:
        snapshots = self._load_snapshots()
        if scope is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.scope == scope]
        if status is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.status == status]
        return sorted(snapshots, key=lambda snapshot: self._normalize_datetime(snapshot.timestamp))

    def write(self, entity: Snapshot) -> None:
        copied_file: Path | None = None
        retired_snapshots: list[Snapshot] = []
        try:
            self.snapshots_root.mkdir(parents=True, exist_ok=True)
            self.files_root.mkdir(parents=True, exist_ok=True)
            copied_file = self._copy_current_file(entity)
            
            with self._lock():
                snapshots = [
                    snapshot for snapshot in self._load_snapshots() if snapshot.id != entity.id
                ]
                snapshots.append(entity)
                retained_snapshots, retired_snapshots = self._apply_retention(snapshots)
                self._write_manifest(retained_snapshots)
        except (SnapshotFailedError, StorageError) as exc:
            self._remove_file(copied_file)
            if isinstance(exc, StorageError):
                raise SnapshotFailedError("Failed to create snapshot") from exc
            raise
        except OSError as exc:
            self._remove_file(copied_file)
            raise SnapshotFailedError("Failed to create snapshot") from exc

        try:
            self._remove_retired_files(retired_snapshots)
        except OSError:
            # Resiliently handle post-confirmation cleanup errors without aborting
            pass

    def migrate(self, target_version: int) -> None:
        if target_version != 1:
            raise StorageError(f"Unsupported snapshot repository schema version: {target_version}")

    def _copy_current_file(self, entity: Snapshot) -> Path | None:
        source = self.project_root / entity.relative_path
        if not source.exists():
            return None
        if not source.is_file():
            raise SnapshotFailedError("Failed to create snapshot: source path is not a file")

        try:
            resolved_source = source.resolve()
            resolved_root = self.project_root.resolve()
            resolved_source.relative_to(resolved_root)
        except ValueError as exc:
            raise SnapshotFailedError("Failed to create snapshot: path traversal detected") from exc

        content = source.read_bytes()
        actual_hash = sha256(content).hexdigest()
        if actual_hash != entity.hash:
            raise SnapshotFailedError("Failed to create snapshot: source hash mismatch")

        destination = self.files_root / entity.id
        temp_destination = destination.with_name(f"{destination.name}.{uuid4()}.tmp")
        try:
            temp_destination.write_bytes(content)
            os.replace(temp_destination, destination)
            return destination
        except OSError as exc:
            self._remove_file(temp_destination)
            raise SnapshotFailedError(
                "Failed to create snapshot: failed to write backup file"
            ) from exc

    def _load_snapshots(self) -> list[Snapshot]:
        if not self.manifest_path.exists():
            return []
        try:
            raw_manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            schema_version = raw_manifest.get("schema_version", 1)
            if schema_version != 1:
                raise StorageError(
                    f"Unsupported snapshot repository schema version: {schema_version}"
                )
            raw_snapshots = raw_manifest.get("snapshots", [])
            if not isinstance(raw_snapshots, list):
                raise StorageError("Snapshot manifest is invalid")
            return [Snapshot.model_validate(raw_snapshot) for raw_snapshot in raw_snapshots]
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            if isinstance(exc, StorageError):
                raise
            raise StorageError("Failed to read snapshot manifest") from exc

    def _write_manifest(self, snapshots: list[Snapshot]) -> None:
        rendered = json.dumps(
            {
                "schema_version": 1,
                "snapshots": [snapshot.model_dump(mode="json") for snapshot in snapshots],
            },
            indent=2,
            sort_keys=True,
        )
        temp_manifest = self.manifest_path.with_name(f"{self.manifest_path.name}.{uuid4()}.tmp")
        try:
            temp_manifest.write_text(f"{rendered}\n", encoding="utf-8")
            os.replace(temp_manifest, self.manifest_path)
        except OSError as exc:
            self._remove_file(temp_manifest)
            raise StorageError("Failed to write snapshot manifest") from exc

    def _apply_retention(
        self, snapshots: list[Snapshot]
    ) -> tuple[list[Snapshot], list[Snapshot]]:
        by_scope: dict[SnapshotScope, list[Snapshot]] = defaultdict(list)
        for snapshot in snapshots:
            by_scope[snapshot.scope].append(snapshot)

        retained: list[Snapshot] = []
        retired: list[Snapshot] = []
        for _scope, scope_snapshots in by_scope.items():
            ordered = sorted(
                scope_snapshots,
                key=lambda snapshot: self._normalize_datetime(snapshot.timestamp),
            )
            retired.extend(ordered[:-self.retention_limit])
            retained.extend(ordered[-self.retention_limit :])

        return (
            sorted(
                retained,
                key=lambda snapshot: self._normalize_datetime(snapshot.timestamp),
            ),
            retired,
        )

    def _remove_retired_files(self, retired_snapshots: list[Snapshot]) -> None:
        for snapshot in retired_snapshots:
            self._remove_file(self.files_root / snapshot.id)

    @staticmethod
    def _normalize_datetime(dt: datetime) -> datetime:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=UTC)
        return dt

    @staticmethod
    def _remove_file(path: Path | None) -> None:
        if path is not None:
            path.unlink(missing_ok=True)
