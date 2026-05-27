from __future__ import annotations

import fcntl
import json
import os
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from universal_memory.domain import StorageError
from universal_memory.domain.entities import ContextSummary, ContextSummaryScope
from universal_memory.domain.ports import ContextSummaryRepository

STALE_LOCK_SECONDS = 10.0
RETENTION_LIMIT = 100


class LocalContextSummaryRepository(ContextSummaryRepository):
    def __init__(
        self,
        *,
        project_root: Path,
        data_root: Path | None = None,
        summaries_path: Path | None = None,
    ) -> None:
        self.project_root = project_root
        self.data_root = data_root or project_root / ".umem"
        self.memory_root = self.data_root / "memory"
        self.summaries_path = summaries_path or self.memory_root / "context_summaries.jsonl"

    @contextmanager
    def _lock(self) -> Generator[None, None, None]:
        lock_path = self.summaries_path.with_suffix(".jsonl.lock")
        self.summaries_path.parent.mkdir(parents=True, exist_ok=True)

        max_attempts = 20
        delay = 0.1
        acquired = False
        fd: int | None = None
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
            for _ in range(max_attempts):
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError:
                    time.sleep(delay)
            if not acquired:
                raise StorageError("Failed to acquire lock on context summaries storage")
            yield
        finally:
            if fd is not None:
                if acquired:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except OSError:
                        pass
                try:
                    os.close(fd)
                except OSError:
                    pass

    def read(self, id: str) -> ContextSummary:
        try:
            with self._lock():
                summaries = self._load_summaries_unlocked(raise_on_corrupt=True)
        except (StorageError, OSError) as exc:
            raise StorageError(f"Database corruption or access failure: {exc}") from exc

        for summary in summaries:
            if summary.id == id:
                return summary
        raise StorageError(f"Context summary not found: {id}")

    def list(self, scope: ContextSummaryScope | None = None) -> list[ContextSummary]:
        try:
            summaries = self._load_summaries_unlocked(raise_on_corrupt=False)
        except OSError as exc:
            raise StorageError("Failed to read context summaries") from exc

        if scope is not None:
            summaries = [summary for summary in summaries if summary.scope == scope]

        return sorted(summaries, key=lambda summary: self._normalize_datetime(summary.created_at))

    def write(self, entity: ContextSummary) -> None:
        try:
            with self._lock():
                summaries = self._load_summaries_unlocked(raise_on_corrupt=True)
                updated = [summary for summary in summaries if summary.id != entity.id]
                updated.append(entity)
                
                # Implement retention policy: keep only the last N historical summaries
                updated = sorted(updated, key=lambda s: self._normalize_datetime(s.created_at))
                if len(updated) > RETENTION_LIMIT:
                    updated = updated[-RETENTION_LIMIT:]
                    
                self._write_summaries_unlocked(updated)
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to write context summaries") from exc

    def migrate(self, target_version: int) -> None:
        if target_version != 1:
            raise StorageError(
                f"Unsupported context summary repository schema version: {target_version}"
            )

    def _load_summaries_unlocked(self, raise_on_corrupt: bool) -> list[ContextSummary]:
        if not self.summaries_path.exists():
            return []
        try:
            summaries: list[ContextSummary] = []
            for line in self.summaries_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    summaries.append(ContextSummary.model_validate(json.loads(line)))
                except (json.JSONDecodeError, ValidationError) as line_exc:
                    if raise_on_corrupt:
                        raise StorageError(
                            f"Corrupt context summary line detected: {line_exc}"
                        ) from line_exc
                    print(f"Skipping corrupt context summary line: {line_exc}", file=sys.stderr)
            return summaries
        except OSError as exc:
            raise StorageError("Failed to read context summaries") from exc

    def _write_summaries_unlocked(self, summaries: list[ContextSummary]) -> None:
        content = self._render_summaries(summaries)
        self.summaries_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.summaries_path.with_name(f"{self.summaries_path.name}.{uuid4()}.tmp")
        try:
            temp_path.write_text(content, encoding="utf-8")
            os.replace(temp_path, self.summaries_path)
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            raise StorageError("Failed to write context summaries") from exc

    @classmethod
    def _render_summaries(cls, summaries: list[ContextSummary]) -> str:
        lines = [cls._render_summary(summary) for summary in summaries]
        return f"{'\n'.join(lines)}\n" if lines else ""

    @classmethod
    def _render_summary(cls, entity: ContextSummary) -> str:
        payload = entity.model_dump(mode="json")
        normalized = cls._normalize_payload(payload)
        return json.dumps(normalized, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _normalize_payload(cls, data: object) -> object:
        if isinstance(data, dict):
            return {key: cls._normalize_payload(value) for key, value in data.items()}
        if isinstance(data, list):
            return [cls._normalize_payload(item) for item in data]
        if isinstance(data, str) and data.endswith("+00:00") and cls._is_iso_datetime(data):
            return data.removesuffix("+00:00") + "Z"
        return data

    @staticmethod
    def _is_iso_datetime(value: str) -> bool:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime:
        if value is None:
            return datetime.min.replace(tzinfo=UTC)
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value
