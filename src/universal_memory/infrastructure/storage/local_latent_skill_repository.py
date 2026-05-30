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
    AuditEventScope,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
)
from universal_memory.domain.ports import LatentSkillRepository
from universal_memory.infrastructure.security import (
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)

STALE_LOCK_SECONDS = 10.0


class LocalLatentSkillRepository(LatentSkillRepository):
    def __init__(
        self,
        *,
        project_root: Path,
        data_root: Path | None = None,
        latent_skills_path: Path | None = None,
        safe_write_use_case: SafeWriteUseCase | None = None,
        global_home: Path | None = None,
    ) -> None:
        if safe_write_use_case is None:
            raise StorageError(
                "safe_write_use_case is strictly required for LocalLatentSkillRepository"
            )

        self.project_root = project_root
        self.data_root = data_root or project_root / ".umem"
        self.memory_root = self.data_root / "memory"
        self.latent_skills_path = latent_skills_path or self.memory_root / "latent_skills.jsonl"

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

        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                self.global_data_root = Path(local_appdata) / "umem"
            else:
                self.global_data_root = self.global_home / "AppData" / "Local" / "umem"
        else:
            self.global_data_root = self.global_home / ".local" / "share" / "umem"

        self.global_memory_root = self.global_data_root / "memory"
        self.global_latent_skills_path = self.global_memory_root / "latent_skills.jsonl"

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

    @contextmanager
    def _lock(self, scope: LatentSkillScope) -> Generator[None, None, None]:  # noqa: PLR0912
        storage_path = self._path_for(scope)
        lock_path = storage_path.with_suffix(".jsonl.lock")
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        lock_id = str(uuid4())

        if lock_path.exists():
            try:
                mtime = os.path.getmtime(lock_path)
                if time.time() - mtime > STALE_LOCK_SECONDS:
                    mtime_now = os.path.getmtime(lock_path)
                    if time.time() - mtime_now > STALE_LOCK_SECONDS:
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
                    acquired = True
                    os.write(fd, lock_id.encode("utf-8"))
                    break
                except FileExistsError:
                    time.sleep(delay)
            if not acquired:
                raise StorageError(
                    f"Failed to acquire lock on latent skills storage for scope {scope.value}"
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
                    lock_content = lock_path.read_text(encoding="utf-8").strip()
                    if lock_path.exists() and lock_content == lock_id:
                        lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def read(self, id: str) -> LatentSkill:
        for skill in self.list():
            if skill.id == id:
                return skill
        raise StorageError(f"Latent skill not found: {id}")

    def list(
        self, scope: LatentSkillScope | None = None, status: LatentSkillStatus | None = None
    ) -> list[LatentSkill]:
        if scope is not None:
            skills = self._load_latent_skills(scope)
        else:
            skills = self._load_latent_skills(LatentSkillScope.global_) + self._load_latent_skills(
                LatentSkillScope.project
            )

        if status is not None:
            skills = [skill for skill in skills if skill.status == status]

        return sorted(skills, key=lambda skill: self._normalize_datetime(skill.created_at))

    def write(self, entity: LatentSkill, *, origin: str = "repository") -> SafeWriteResult | None:
        try:
            with self._lock(entity.scope):
                skills = self._load_latent_skills_unlocked(entity.scope, raise_on_corrupt=True)
                skills_by_id = {skill.id: skill for skill in skills}
                previous = skills_by_id.get(entity.id)
                skills_by_id[entity.id] = entity
                action = self._audit_action_for(previous, entity)
                return self._write_latent_skills_unlocked(
                    list(skills_by_id.values()), entity.scope, action=action, origin=origin
                )
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to write latent skills") from exc

    def delete(self, id: str) -> None:
        skill = self.read(id)
        try:
            with self._lock(skill.scope):
                skills = self._load_latent_skills_unlocked(skill.scope, raise_on_corrupt=True)
                found = False
                updated_skills = []
                for current in skills:
                    if current.id == id:
                        updated_skills.append(
                            current.model_copy(
                                update={
                                    "status": LatentSkillStatus.ignored,
                                    "updated_at": datetime.now(UTC),
                                }
                            )
                        )
                        found = True
                    else:
                        updated_skills.append(current)
                if not found:
                    raise StorageError(f"Latent skill not found: {id}")
                self._write_latent_skills_unlocked(
                    updated_skills, skill.scope, action="delete_latent_skill"
                )
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to delete latent skill") from exc

    def migrate(self, target_version: int) -> None:
        if target_version != 1:
            raise StorageError(
                f"Unsupported latent skill repository schema version: {target_version}"
            )

    def _load_latent_skills(self, scope: LatentSkillScope) -> list[LatentSkill]:
        try:
            with self._lock(scope):
                return self._load_latent_skills_unlocked(scope, raise_on_corrupt=True)
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("Failed to read latent skills") from exc

    def _load_latent_skills_unlocked(
        self, scope: LatentSkillScope, raise_on_corrupt: bool = False
    ) -> list[LatentSkill]:
        storage_path = self._path_for(scope)
        if not storage_path.exists():
            return []

        try:
            skills: list[LatentSkill] = []
            for line in storage_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    skills.append(LatentSkill.model_validate(json.loads(line)))
                except (json.JSONDecodeError, ValidationError) as line_exc:
                    if raise_on_corrupt:
                        raise StorageError(
                            f"Corrupt latent skill line detected: {line_exc}"
                        ) from line_exc
                    print(f"Skipping corrupt latent skill line: {line_exc}", file=sys.stderr)
            return skills
        except OSError as exc:
            raise StorageError("Failed to read latent skills") from exc

    def _write_latent_skills_unlocked(
        self,
        skills: list[LatentSkill],
        scope: LatentSkillScope,
        action: str = "write_latent_skill",
        origin: str = "repository",
    ) -> SafeWriteResult | None:
        content = self._render_latent_skills(skills)
        is_global = scope == LatentSkillScope.global_
        safe_write = self.global_safe_write_use_case if is_global else self.safe_write_use_case
        if safe_write is not None:
            relative_path = (
                "memory/latent_skills.jsonl" if is_global else ".umem/memory/latent_skills.jsonl"
            )
            return safe_write.execute(
                SafeWriteCommand(
                    relative_path=relative_path,
                    content=content,
                    scope=self._audit_scope_for(scope),
                    origin=origin,
                    action=action,
                )
            )

        storage_path = self._path_for(scope)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = storage_path.with_name(f"{storage_path.name}.{uuid4()}.tmp")
        try:
            temp_path.write_text(content, encoding="utf-8")
            os.replace(temp_path, storage_path)
            return None
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            raise StorageError("Failed to write latent skills") from exc

    def _path_for(self, scope: LatentSkillScope) -> Path:
        if scope == LatentSkillScope.global_:
            return self.global_latent_skills_path
        return self.latent_skills_path

    @staticmethod
    def _audit_action_for(previous: LatentSkill | None, entity: LatentSkill) -> str:
        if previous is not None:
            if (
                previous.status == LatentSkillStatus.active
                and entity.status == LatentSkillStatus.ignored
            ):
                return "deactivate_skill"
            if (
                previous.status == LatentSkillStatus.ignored
                and entity.status == LatentSkillStatus.active
            ):
                return "activate_skill"
        if "approval" in entity.metadata:
            return "propose_skill_decision"
        return "write_latent_skill"

    @staticmethod
    def _audit_scope_for(scope: LatentSkillScope) -> AuditEventScope:
        if scope == LatentSkillScope.global_:
            return AuditEventScope.global_
        return AuditEventScope.project

    @classmethod
    def _render_latent_skills(cls, skills: list[LatentSkill]) -> str:
        lines = [cls._render_latent_skill(skill) for skill in skills]
        return f"{'\n'.join(lines)}\n" if lines else ""

    @classmethod
    def _render_latent_skill(cls, entity: LatentSkill) -> str:
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
