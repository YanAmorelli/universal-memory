from __future__ import annotations

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

from universal_memory.application.security import (
    SafeWriteCommand,
    SafeWriteUseCase,
)
from universal_memory.domain import StorageError
from universal_memory.domain.entities import AuditEventScope, Rule, RuleScope, RuleStatus
from universal_memory.domain.ports import RuleRepository
from universal_memory.domain.project_layout import ResolvedProjectLayout
from universal_memory.infrastructure.config.project_layout import resolve_project_layout
from universal_memory.infrastructure.security import (
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)

STALE_LOCK_SECONDS = 10.0


class RuleNotFoundError(StorageError):
    pass


class LocalRuleRepository(RuleRepository):
    def __init__(
        self,
        *,
        project_root: Path,
        data_root: Path | None = None,
        rules_path: Path | None = None,
        safe_write_use_case: SafeWriteUseCase | None = None,
        global_home: Path | None = None,
    ) -> None:
        self.project_root = project_root
        self.data_root = data_root or project_root / ".umem"
        self.memory_root = self.data_root / "memory"
        self.layout = resolve_project_layout(project_root)
        self.rules_path = rules_path or self._default_project_rules_path(self.layout)
        self.legacy_rules_path = self.layout.legacy_rules_path
        self.private_rules_path = self.layout.private_rules_path

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

        self.global_data_root = self._global_data_root(self.global_home)
        self.global_memory_root = self.global_data_root / "memory"
        self.global_rules_path = self.global_memory_root / "rules.jsonl"

        self.safe_write_use_case = safe_write_use_case
        self.global_safe_write_use_case = None
        if safe_write_use_case is not None:
            self.global_safe_write_use_case = SafeWriteUseCase(
                project_root=self.global_data_root,
                secret_scanner=safe_write_use_case.secret_scanner,
                snapshot_repository=LocalSnapshotRepository(
                    project_root=self.global_data_root,
                    data_root=self.global_data_root,
                ),
                audit_log_repository=LocalAuditLogRepository(
                    project_root=self.global_data_root,
                    data_root=self.global_data_root,
                ),
            )

    @contextmanager
    def _lock(  # noqa: PLR0912
        self,
        scope: RuleScope,
        *,
        path: Path | None = None,
    ) -> Generator[None, None, None]:
        rules_path = path or (
            self.global_rules_path if scope == RuleScope.global_ else self.rules_path
        )
        lock_path = rules_path.with_suffix(".jsonl.lock")
        if scope == RuleScope.project and self.layout.is_shared:
            lock_path = self.layout.operational_locks_root / "rules.jsonl.lock"
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        lock_id = str(uuid4())

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
                err_msg = f"Failed to acquire lock on rules storage for scope {scope.value}"
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
                    lock_content = lock_path.read_text(encoding="utf-8").strip()
                    if lock_path.exists() and lock_content == lock_id:
                        lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def read(self, id: str) -> Rule:
        for rule in self.list():
            if rule.id == id:
                return rule
        raise RuleNotFoundError(f"Rule not found: {id}")

    def list(self, scope: RuleScope | None = None, status: RuleStatus | None = None) -> list[Rule]:
        if scope is not None:
            rules = self._load_rules(scope)
        else:
            rules = self._load_rules(RuleScope.global_) + self._load_rules(RuleScope.project)

        if status is not None:
            rules = [rule for rule in rules if rule.status == status]

        return sorted(rules, key=lambda rule: rule.created_at)

    def write(self, entity: Rule) -> None:
        try:
            path = self._path_for_existing_id(entity.scope, entity.id)
            if path is None:
                path = self._path_for_write(entity)
            with self._lock(entity.scope, path=path):
                rules = self._load_rules_unlocked(
                    entity.scope,
                    raise_on_corrupt=True,
                    path=path,
                )
                rules_dict = {r.id: r for r in rules}
                rules_dict[entity.id] = entity
                self._write_rules_unlocked(list(rules_dict.values()), entity.scope, path=path)
        except OSError as exc:
            raise StorageError("Failed to write rule") from exc

    def delete(self, id: str) -> None:
        rule = self.read(id)
        scope = rule.scope
        path = self._path_for_existing_id(scope, id) or self._path_for_write(rule)
        try:
            with self._lock(scope, path=path):
                rules = self._load_rules_unlocked(scope, raise_on_corrupt=True, path=path)
                updated_rules = []
                found = False
                for r in rules:
                    if r.id == id:
                        updated_rules.append(
                            r.model_copy(
                                update={
                                    "status": RuleStatus.inactive,
                                    "updated_at": datetime.now(UTC),
                                }
                            )
                        )
                        found = True
                    else:
                        updated_rules.append(r)

                if not found:
                    raise RuleNotFoundError(f"Rule not found: {id}")

                self._write_rules_unlocked(updated_rules, scope, path=path)
        except (RuleNotFoundError, StorageError):
            raise
        except OSError as exc:
            raise StorageError("Failed to delete rule") from exc

    def migrate(self, target_version: int) -> None:
        if target_version != 1:
            raise StorageError(f"Unsupported rule repository schema version: {target_version}")

    def _load_rules(self, scope: RuleScope) -> list[Rule]:
        try:
            return self._load_rules_unlocked(scope, raise_on_corrupt=False)
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to read rules") from exc

    def _load_rules_unlocked(
        self,
        scope: RuleScope,
        raise_on_corrupt: bool = False,
        *,
        path: Path | None = None,
    ) -> list[Rule]:
        if path is not None:
            return self._load_rules_file(path, raise_on_corrupt)
        return self._load_rules_from_paths(self._paths_for_read(scope), raise_on_corrupt)

    def _load_rules_from_paths(self, paths: list[Path], raise_on_corrupt: bool) -> list[Rule]:
        by_id: dict[str, Rule] = {}
        for rules_path in paths:
            for rule in self._load_rules_file(rules_path, raise_on_corrupt):
                by_id.setdefault(rule.id, rule)
        return list(by_id.values())

    def _load_rules_file(self, rules_path: Path, raise_on_corrupt: bool) -> list[Rule]:
        if not rules_path.exists():
            return []
        try:
            rules: list[Rule] = []
            for line in rules_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rules.append(Rule.model_validate(json.loads(line)))
                except (json.JSONDecodeError, ValidationError) as line_exc:
                    if raise_on_corrupt:
                        raise StorageError(f"Corrupt rule line detected: {line_exc}") from line_exc
                    else:
                        print(f"Skipping corrupt rule line: {line_exc}", file=sys.stderr)
            return rules
        except OSError as exc:
            raise StorageError("Failed to read rules") from exc

    def _write_rules_unlocked(
        self,
        rules: list[Rule],
        scope: RuleScope,
        *,
        path: Path | None = None,
    ) -> None:
        content = "".join(json.dumps(r.model_dump(mode="json")) + "\n" for r in rules)

        is_global = scope == RuleScope.global_
        safe_write = self.global_safe_write_use_case if is_global else self.safe_write_use_case
        if safe_write is not None:
            relative_path = (
                "memory/rules.jsonl" if is_global else self._relative_path(path or self.rules_path)
            )
            safe_write.execute(
                SafeWriteCommand(
                    relative_path=relative_path,
                    content=content,
                    scope=self._audit_scope_for(scope),
                    origin="repository",
                    action="write_rule",
                )
            )
        else:
            rules_path = path or (
                self.global_rules_path if scope == RuleScope.global_ else self.rules_path
            )
            rules_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = rules_path.with_name(f"{rules_path.name}.{uuid4()}.tmp")
            try:
                temp_path.write_text(content, encoding="utf-8")
                os.replace(temp_path, rules_path)
            except OSError as exc:
                temp_path.unlink(missing_ok=True)
                raise StorageError("Failed to write rules") from exc

    def _audit_scope_for(self, scope: RuleScope) -> AuditEventScope:
        return AuditEventScope.global_ if scope == RuleScope.global_ else AuditEventScope.project

    def _paths_for_read(self, scope: RuleScope) -> list[Path]:
        if scope == RuleScope.global_:
            return [self.global_rules_path]
        if not self.layout.is_shared:
            return [self.rules_path]
        return [
            self.layout.shared_rules_path,
            self.layout.private_rules_path,
            self.layout.legacy_rules_path,
        ]

    def _path_for_write(self, entity: Rule) -> Path:
        if entity.scope == RuleScope.global_:
            return self.global_rules_path
        if entity.metadata.get("visibility") == "private" and self.layout.is_shared:
            return self.layout.private_rules_path
        return self.rules_path

    def _path_for_existing_id(self, scope: RuleScope, id: str) -> Path | None:
        for path in self._paths_for_read(scope):
            if any(rule.id == id for rule in self._load_rules_file(path, raise_on_corrupt=False)):
                return path
        return None

    def _default_project_rules_path(self, layout: ResolvedProjectLayout) -> Path:
        return layout.shared_rules_path if layout.is_shared else self.memory_root / "rules.jsonl"

    def _relative_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.project_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    @staticmethod
    def _global_data_root(global_home: Path) -> Path:
        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                return Path(local_appdata) / "umem"
            return global_home / "AppData" / "Local" / "umem"
        return global_home / ".local" / "share" / "umem"
