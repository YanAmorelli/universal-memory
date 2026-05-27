from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from universal_memory.application.security import (
    SafeWriteCommand,
    SafeWriteResult,
    SafeWriteUseCase,
)
from universal_memory.domain import FactNotFoundError, StorageError
from universal_memory.domain.entities import AuditEventScope, Fact, FactScope, FactStatus
from universal_memory.domain.ports import FactRepository

STALE_LOCK_SECONDS = 10.0
MIN_REGEX_QUERY_LENGTH = 2


class LocalFactRepository(FactRepository):
    def __init__(
        self,
        *,
        project_root: Path,
        data_root: Path | None = None,
        facts_path: Path | None = None,
        safe_write_use_case: SafeWriteUseCase | None = None,
        global_home: Path | None = None,
    ) -> None:
        self.project_root = project_root
        self.data_root = data_root or project_root / ".umem"
        self.memory_root = self.data_root / "memory"
        self.facts_path = facts_path or self.memory_root / "facts.jsonl"

        # Determine global home safely with complete test isolation
        is_test = (
            "pytest" in sys.modules
            or os.environ.get("PYTEST_CURRENT_TEST")
            or "unittest" in sys.modules
        )
        if global_home is not None:
            self.global_home = global_home
        elif is_test:
            self.global_home = project_root / ".umem_global_test_home"
        else:
            self.global_home = Path.home()

        self.global_data_root = self.global_home / ".umem"
        self.global_memory_root = self.global_data_root / "memory"
        self.global_facts_path = self.global_memory_root / "facts.jsonl"

        # SafeWriteUseCase integration
        self.safe_write_use_case = safe_write_use_case
        self.global_safe_write_use_case = None
        if safe_write_use_case is not None:
            self.global_safe_write_use_case = SafeWriteUseCase(
                project_root=self.global_home,
                secret_scanner=safe_write_use_case.secret_scanner,
                snapshot_repository=safe_write_use_case.snapshot_repository,
                audit_log_repository=safe_write_use_case.audit_log_repository,
            )

    @contextmanager
    def _lock(self, scope: FactScope) -> Generator[None, None, None]:
        facts_path = self.global_facts_path if scope == FactScope.global_ else self.facts_path
        lock_path = facts_path.with_suffix(".jsonl.lock")
        facts_path.parent.mkdir(parents=True, exist_ok=True)

        lock_id = str(uuid4())

        # Safe stale lock verification
        if lock_path.exists():
            try:
                mtime = os.path.getmtime(lock_path)
                if time.time() - mtime > STALE_LOCK_SECONDS:
                    lock_path.unlink(missing_ok=True)
            except OSError:
                pass

        max_attempts = 20
        delay = 0.1
        acquired = False
        fd: int | None = None
        try:
            for _ in range(max_attempts):
                try:
                    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.write(fd, lock_id.encode("utf-8"))
                    acquired = True
                    break
                except FileExistsError:
                    time.sleep(delay)
            if not acquired:
                err_msg = f"Failed to acquire lock on facts storage for scope {scope.value}"
                raise StorageError(err_msg)
            yield
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if acquired:
                try:
                    # TOCTOU guard: only delete if the lock still belongs to us!
                    lock_content = lock_path.read_text(encoding="utf-8").strip()
                    if lock_path.exists() and lock_content == lock_id:
                        lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def read(self, id: str) -> Fact:
        for fact in self.list():
            if fact.id == id:
                return fact
        raise FactNotFoundError(f"Fact not found: {id}")

    def list(self, scope: FactScope | None = None, status: FactStatus | None = None) -> list[Fact]:
        if scope is not None:
            facts = self._load_facts(scope)
        else:
            facts = self._load_facts(FactScope.global_) + self._load_facts(FactScope.project)

        if status is not None:
            facts = [fact for fact in facts if fact.status == status]

        return sorted(facts, key=lambda fact: self._normalize_datetime(fact.created_at))

    def search(self, query: str, include_inactive: bool = False) -> list[Fact]:
        if not isinstance(query, str) or not query.strip():
            return []

        # Optimization: Filter by status at the list I/O layer instead of loading all in memory
        status_filter = FactStatus.active if not include_inactive else None
        facts = self.list(status=status_filter)

        is_regex = (
            query.startswith("/") and query.endswith("/") and len(query) > MIN_REGEX_QUERY_LENGTH
        )
        clean_query = query[1:-1] if is_regex else query

        normalized_query = self._normalize_search_text(clean_query)
        if not normalized_query:
            return []

        matches = []
        for fact in facts:
            if fact.content is None:
                continue

            normalized_content = self._normalize_search_text(fact.content)

            if is_regex:
                try:
                    if re.search(normalized_query, normalized_content) is not None:
                        matches.append(fact)
                except re.error:
                    pass
            elif normalized_query in normalized_content:
                matches.append(fact)

        return sorted(
            matches,
            key=lambda fact: self._normalize_datetime(fact.created_at),
            reverse=True,
        )

    def write(self, entity: Fact) -> SafeWriteResult | None:
        try:
            with self._lock(entity.scope):
                unlocked_facts = self._load_facts_unlocked(entity.scope, raise_on_corrupt=True)
                facts = [fact for fact in unlocked_facts if fact.id != entity.id]
                facts.append(entity)
                return self._write_facts_unlocked(facts, entity.scope)
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to write facts") from exc

    def delete(self, id: str) -> None:
        # Read to find scope first, then update under transactional lock
        fact = self.read(id)
        scope = fact.scope
        try:
            with self._lock(scope):
                facts = self._load_facts_unlocked(scope, raise_on_corrupt=True)
                found = False
                updated_facts = []
                for f in facts:
                    if f.id == id:
                        updated_facts.append(
                            f.model_copy(
                                update={
                                    "status": FactStatus.archived,
                                    "updated_at": datetime.now(UTC),
                                }
                            )
                        )
                        found = True
                    else:
                        updated_facts.append(f)

                if not found:
                    raise FactNotFoundError(f"Fact not found: {id}")

                self._write_facts_unlocked(updated_facts, scope)
        except (FactNotFoundError, StorageError):
            raise
        except OSError as exc:
            raise StorageError("Failed to delete fact") from exc

    def purge(self, id: str) -> None:
        fact = self.read(id)
        scope = fact.scope
        try:
            with self._lock(scope):
                facts = self._load_facts_unlocked(scope, raise_on_corrupt=True)
                if not any(f.id == id for f in facts):
                    raise FactNotFoundError(f"Fact not found: {id}")
                self._write_facts_unlocked([f for f in facts if f.id != id], scope)
        except (FactNotFoundError, StorageError):
            raise
        except OSError as exc:
            raise StorageError("Failed to purge fact") from exc

    def write_batch(self, entities: list[Fact]) -> SafeWriteResult | None:
        if not entities:
            return None
        by_scope = defaultdict(list)
        for entity in entities:
            by_scope[entity.scope].append(entity)

        last_result = None
        for scope, scope_entities in by_scope.items():
            try:
                with self._lock(scope):
                    unlocked_facts = self._load_facts_unlocked(scope, raise_on_corrupt=True)
                    facts_dict = {fact.id: fact for fact in unlocked_facts}
                    for entity in scope_entities:
                        facts_dict[entity.id] = entity
                    last_result = self._write_facts_unlocked(list(facts_dict.values()), scope)
            except StorageError:
                raise
            except OSError as exc:
                raise StorageError("Failed to write batch of facts") from exc
        return last_result

    def purge_batch(self, ids: list[str]) -> None:
        if not ids:
            return
        facts_to_purge = [f for f in self.list() if f.id in ids]
        if not facts_to_purge:
            return

        by_scope = defaultdict(list)
        for fact in facts_to_purge:
            by_scope[fact.scope].append(fact.id)

        for scope, scope_ids in by_scope.items():
            try:
                with self._lock(scope):
                    facts = self._load_facts_unlocked(scope, raise_on_corrupt=True)
                    updated_facts = [f for f in facts if f.id not in scope_ids]
                    self._write_facts_unlocked(updated_facts, scope)
            except StorageError:
                raise
            except OSError as exc:
                raise StorageError("Failed to purge batch of facts") from exc

    def migrate(self, target_version: int) -> None:
        if target_version != 1:
            raise StorageError(f"Unsupported fact repository schema version: {target_version}")

    def _load_facts(self, scope: FactScope) -> list[Fact]:
        try:
            with self._lock(scope):
                return self._load_facts_unlocked(scope, raise_on_corrupt=False)
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to read facts") from exc

    def _load_facts_unlocked(self, scope: FactScope, raise_on_corrupt: bool = False) -> list[Fact]:
        facts_path = self.global_facts_path if scope == FactScope.global_ else self.facts_path
        if not facts_path.exists():
            return []
        try:
            facts: list[Fact] = []
            for line in facts_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    facts.append(Fact.model_validate(json.loads(line)))
                except (json.JSONDecodeError, ValidationError) as line_exc:
                    if raise_on_corrupt:
                        raise StorageError(f"Corrupt fact line detected: {line_exc}") from line_exc
                    else:
                        print(f"Skipping corrupt fact line: {line_exc}", file=sys.stderr)
            return facts
        except OSError as exc:
            raise StorageError("Failed to read facts") from exc

    def _write_facts_unlocked(self, facts: list[Fact], scope: FactScope) -> SafeWriteResult | None:
        content = self._render_facts(facts)

        is_global = scope == FactScope.global_
        safe_write = self.global_safe_write_use_case if is_global else self.safe_write_use_case
        if safe_write is not None:
            relative_path = ".umem/memory/facts.jsonl"
            return safe_write.execute(
                SafeWriteCommand(
                    relative_path=relative_path,
                    content=content,
                    scope=self._audit_scope_for(scope),
                    origin="repository",
                    action="write_fact",
                )
            )
        else:
            facts_path = self.global_facts_path if scope == FactScope.global_ else self.facts_path
            facts_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = facts_path.with_name(f"{facts_path.name}.{uuid4()}.tmp")
            try:
                temp_path.write_text(content, encoding="utf-8")
                os.replace(temp_path, facts_path)
                return None
            except OSError as exc:
                temp_path.unlink(missing_ok=True)
                raise StorageError("Failed to write facts") from exc

    @staticmethod
    def _audit_scope_for(scope: FactScope) -> AuditEventScope:
        if scope == FactScope.global_:
            return AuditEventScope.global_
        return AuditEventScope.project

    @classmethod
    def _render_facts(cls, facts: list[Fact]) -> str:
        lines = [cls._render_fact(fact) for fact in facts]
        return f"{'\n'.join(lines)}\n" if lines else ""

    @classmethod
    def _render_fact(cls, entity: Fact) -> str:
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
            clean_val = value.replace("Z", "+00:00")
            datetime.fromisoformat(clean_val)
            return True
        except ValueError:
            return False

    @staticmethod
    def _normalize_datetime(dt: datetime | None) -> datetime:
        if dt is None:
            return datetime.min.replace(tzinfo=UTC)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=UTC)
        return dt

    @staticmethod
    def _normalize_search_text(value: str | None) -> str:
        if value is None:
            return ""
        decomposed = unicodedata.normalize("NFKD", value)
        without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
        return without_accents.casefold()

    @classmethod
    def _matches_search_query(cls, content: str | None, normalized_query: str) -> bool:
        if content is None:
            return False
        normalized_content = cls._normalize_search_text(content)

        # Check if query is explicitly regex (wrapped in /)
        is_regex = (
            normalized_query.startswith("/")
            and normalized_query.endswith("/")
            and len(normalized_query) > MIN_REGEX_QUERY_LENGTH
        )
        clean_query = normalized_query[1:-1] if is_regex else normalized_query

        if is_regex:
            try:
                return re.search(clean_query, normalized_content) is not None
            except re.error:
                return False
        else:
            return clean_query in normalized_content
