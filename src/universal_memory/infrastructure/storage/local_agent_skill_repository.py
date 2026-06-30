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
    SafeWriteResult,
    SafeWriteUseCase,
)
from universal_memory.domain import StorageError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    AuditEventScope,
    LatentSkillScope,
)
from universal_memory.domain.ports import AgentSkillRepository
from universal_memory.domain.project_layout import ResolvedProjectLayout
from universal_memory.infrastructure.config.project_layout import resolve_project_layout
from universal_memory.infrastructure.security import (
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)

STALE_LOCK_SECONDS = 10.0


class LocalAgentSkillRepository(AgentSkillRepository):
    def __init__(
        self,
        *,
        project_root: Path,
        data_root: Path | None = None,
        skills_path: Path | None = None,
        safe_write_use_case: SafeWriteUseCase | None = None,
        global_home: Path | None = None,
    ) -> None:
        if safe_write_use_case is None:
            raise StorageError(
                "safe_write_use_case is strictly required for LocalAgentSkillRepository"
            )

        self.project_root = project_root
        self.data_root = data_root or project_root / ".umem"
        self.memory_root = self.data_root / "memory"
        self.layout = resolve_project_layout(project_root)
        self.skills_path = skills_path or self._default_project_skills_path(self.layout)
        self.legacy_skills_path = self.layout.legacy_skills_registry_path

        is_test = "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST")
        if global_home is not None:
            self.global_home = global_home
        elif is_test:
            self.global_home = project_root / ".umem_global_test_home"
        else:
            self.global_home = Path.home()

        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA")
            self.global_data_root = (
                Path(local_appdata) / "umem"
                if local_appdata
                else self.global_home / "AppData" / "Local" / "umem"
            )
        else:
            self.global_data_root = self.global_home / ".local" / "share" / "umem"

        self.global_memory_root = self.global_data_root / "memory"
        self.global_skills_path = self.global_memory_root / "skills.jsonl"
        self.safe_write_use_case = safe_write_use_case
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

    def read(self, id: str) -> AgentSkill:
        for skill in self.list():
            if skill.id == id:
                return skill
        raise StorageError(f"Agent skill not found: {id}")

    def read_by_slug(
        self,
        slug: str,
        *,
        scope: LatentSkillScope | None = None,
        status: AgentSkillStatus | None = None,
    ) -> AgentSkill:
        for skill in self.list(scope=scope, status=status):
            if skill.slug == slug:
                return skill
        raise StorageError(f"Agent skill not found for slug: {slug}")

    def list(
        self, scope: LatentSkillScope | None = None, status: AgentSkillStatus | None = None
    ) -> list[AgentSkill]:
        if scope is not None:
            skills = self._load_skills(scope)
        else:
            skills = self._load_skills(LatentSkillScope.global_) + self._load_skills(
                LatentSkillScope.project
            )
        if status is not None:
            skills = [skill for skill in skills if skill.status == status]
        return sorted(skills, key=lambda skill: self._normalize_datetime(skill.created_at))

    def write(self, entity: AgentSkill, *, origin: str = "repository") -> SafeWriteResult | None:
        try:
            storage_path = self._path_for_existing_id(entity.scope, entity.id) or (
                self._path_for_write(entity)
            )
            with self._lock(entity.scope, path=storage_path):
                skills = self._load_skills_unlocked(
                    entity.scope,
                    raise_on_corrupt=True,
                    path=storage_path,
                )
                by_id = {skill.id: skill for skill in skills}
                previous = by_id.get(entity.id)
                by_id[entity.id] = entity
                return self._write_skills_unlocked(
                    list(by_id.values()),
                    entity.scope,
                    path=storage_path,
                    action="update_agent_skill" if previous else "write_agent_skill",
                    origin=origin,
                )
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to write agent skills") from exc

    def replace(self, entity: AgentSkill, *, origin: str = "repository") -> SafeWriteResult | None:
        return self.write(entity, origin=origin)

    def remove(
        self,
        id: str,
        *,
        scope: LatentSkillScope,
        origin: str = "repository",
    ) -> SafeWriteResult | None:
        try:
            storage_path = self._path_for_existing_id(scope, id) or self._path_for(scope)
            with self._lock(scope, path=storage_path):
                skills = self._load_skills_unlocked(
                    scope,
                    raise_on_corrupt=True,
                    path=storage_path,
                )
                remaining = [skill for skill in skills if skill.id != id]
                if len(remaining) == len(skills):
                    raise StorageError(f"Agent skill not found: {id}")
                return self._write_skills_unlocked(
                    remaining,
                    scope,
                    path=storage_path,
                    action="remove_agent_skill",
                    origin=origin,
                )
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to remove agent skill") from exc

    @contextmanager
    def _lock(  # noqa: PLR0912
        self,
        scope: LatentSkillScope,
        *,
        path: Path | None = None,
    ) -> Generator[None, None, None]:
        storage_path = path or self._path_for(scope)
        lock_path = storage_path.with_suffix(".jsonl.lock")
        if scope == LatentSkillScope.project and self.layout.is_shared:
            lock_path = self.layout.operational_locks_root / "skills.jsonl.lock"
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_id = str(uuid4())
        if lock_path.exists():
            try:
                if time.time() - os.path.getmtime(lock_path) > STALE_LOCK_SECONDS:
                    lock_path.unlink(missing_ok=True)
            except OSError:
                pass
        fd: int | None = None
        acquired = False
        try:
            for _ in range(20):
                try:
                    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.write(fd, lock_id.encode("utf-8"))
                    acquired = True
                    break
                except FileExistsError:
                    time.sleep(0.1)
            if not acquired:
                raise StorageError(
                    f"Failed to acquire lock on agent skills storage for {scope.value}"
                )
            yield
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if acquired:
                try:
                    if lock_path.read_text(encoding="utf-8").strip() == lock_id:
                        lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _load_skills(self, scope: LatentSkillScope) -> list[AgentSkill]:
        return self._load_skills_unlocked(scope, raise_on_corrupt=True)

    def _load_skills_unlocked(
        self,
        scope: LatentSkillScope,
        *,
        raise_on_corrupt: bool = False,
        path: Path | None = None,
    ) -> list[AgentSkill]:
        if path is not None:
            return self._load_skills_file(path, raise_on_corrupt=raise_on_corrupt)
        return self._load_skills_from_paths(self._paths_for_read(scope), raise_on_corrupt)

    def _load_skills_from_paths(
        self,
        paths: list[Path],
        raise_on_corrupt: bool,
    ) -> list[AgentSkill]:
        by_slug: dict[str, AgentSkill] = {}
        for storage_path in paths:
            for skill in self._load_skills_file(storage_path, raise_on_corrupt=raise_on_corrupt):
                by_slug.setdefault(skill.slug, skill)
        return list(by_slug.values())

    def _load_skills_file(
        self,
        storage_path: Path,
        *,
        raise_on_corrupt: bool,
    ) -> list[AgentSkill]:
        if not storage_path.exists():
            return []
        try:
            skills: list[AgentSkill] = []
            for line in storage_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    skills.append(AgentSkill.model_validate(json.loads(line)))
                except (json.JSONDecodeError, ValidationError) as line_exc:
                    if raise_on_corrupt:
                        raise StorageError(
                            f"Corrupt agent skill line detected: {line_exc}"
                        ) from line_exc
                    print(f"Skipping corrupt agent skill line: {line_exc}", file=sys.stderr)
            return skills
        except OSError as exc:
            raise StorageError("Failed to read agent skills") from exc

    def _write_skills_unlocked(
        self,
        skills: list[AgentSkill],
        scope: LatentSkillScope,
        *,
        path: Path | None = None,
        action: str,
        origin: str,
    ) -> SafeWriteResult | None:
        content = self._render_skills(skills)
        is_global = scope == LatentSkillScope.global_
        safe_write = self.global_safe_write_use_case if is_global else self.safe_write_use_case
        relative_path = "memory/skills.jsonl"
        if not is_global:
            relative_path = self._relative_path(path or self._path_for(scope))
        return safe_write.execute(
            SafeWriteCommand(
                relative_path=relative_path,
                content=content,
                scope=AuditEventScope.global_ if is_global else AuditEventScope.project,
                origin=origin,
                action=action,
            )
        )

    def _path_for(self, scope: LatentSkillScope) -> Path:
        if scope == LatentSkillScope.global_:
            return self.global_skills_path
        return self.skills_path

    def _paths_for_read(self, scope: LatentSkillScope) -> list[Path]:
        if scope == LatentSkillScope.global_:
            return [self.global_skills_path]
        if not self.layout.is_shared:
            return [self.skills_path]
        return [self.layout.shared_skills_registry_path, self.layout.legacy_skills_registry_path]

    def _path_for_write(self, entity: AgentSkill) -> Path:
        if entity.scope == LatentSkillScope.global_:
            return self.global_skills_path
        if not self.layout.is_shared:
            return self.skills_path
        visibility = entity.metadata.get("visibility")
        category = entity.metadata.get("category")
        canonical_path = entity.canonical_path.replace("\\", "/")
        if (
            visibility == "private"
            or category == "operational"
            or canonical_path.startswith(".umem/")
        ):
            return self.layout.legacy_skills_registry_path
        return self.layout.shared_skills_registry_path

    def _path_for_existing_id(self, scope: LatentSkillScope, id: str) -> Path | None:
        for path in self._paths_for_read(scope):
            skills = self._load_skills_file(path, raise_on_corrupt=False)
            if any(skill.id == id for skill in skills):
                return path
        return None

    def _default_project_skills_path(self, layout: ResolvedProjectLayout) -> Path:
        if layout.is_shared:
            return layout.shared_skills_registry_path
        return self.memory_root / "skills.jsonl"

    def _relative_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.project_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    @classmethod
    def _render_skills(cls, skills: list[AgentSkill]) -> str:
        lines = [cls._render_skill(skill) for skill in skills]
        return f"{'\n'.join(lines)}\n" if lines else ""

    @classmethod
    def _render_skill(cls, entity: AgentSkill) -> str:
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
