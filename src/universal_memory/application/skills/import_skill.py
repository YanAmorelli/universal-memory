from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.application.skills.create_skill import _hash_text
from universal_memory.application.skills.native_skill_sync import (
    MANIFEST_TREE_HASH_ALGORITHM,
    NativeSkillSync,
    NativeSkillSyncResult,
)
from universal_memory.application.skills.update_skill import _parse_skill_markdown, _slug
from universal_memory.application.skills.validate_skill import (
    assert_validation_passes,
    validate_skill_tree,
)
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    AuditEventScope,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    RuntimeRegistry,
    default_runtime_registry,
)
from universal_memory.domain.ports import AgentSkillRepository

NO_NATIVE_INSTALLATIONS_NOTE = (
    "Import copied/adopted the source into the canonical .umem/skills registry. "
    "No native runtime target was recorded for this import. Supported compatible native targets "
    "can be adopted during import and refreshed with `umem skills sync <skill-id-or-name> "
    "--format json`, which distributes complete synchronized copies as native runtime copies "
    "to configured runtimes."
)


@dataclass(frozen=True, slots=True)
class ImportSkillCommand:
    path: str | Path
    scope: LatentSkillScope
    origin: str
    replace_native: bool = False
    sync_after_import: bool = False
    slug: str | None = None


@dataclass(frozen=True, slots=True)
class ImportSkillResult:
    agent_skill: AgentSkill
    slug: str
    skill_dir: str
    skill_file: str
    created_paths: list[str]
    affected_paths: list[str]
    audit_reference: str
    snapshot_reference: str
    native_installations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def latent_skill(self) -> LatentSkill:
        return LatentSkill(
            id=self.agent_skill.id,
            created_at=self.agent_skill.created_at,
            updated_at=self.agent_skill.updated_at,
            name=self.agent_skill.name,
            description=self.agent_skill.description,
            scope=self.agent_skill.scope,
            status=LatentSkillStatus.active,
            recurrence_count=1,
            metadata={
                **self.agent_skill.metadata,
                "origin": self.agent_skill.origin,
                "audit_reference": self.agent_skill.audit_reference,
                "canonical_path": self.agent_skill.canonical_path,
                "native_installations": self.agent_skill.native_installations,
            },
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "skill_id": self.agent_skill.id,
            "name": self.agent_skill.name,
            "slug": self.slug,
            "skill_dir": self.skill_dir,
            "skill_file": self.skill_file,
            "created_paths": self.created_paths,
            "affected_paths": self.affected_paths,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "native_installations": self.native_installations,
            "canonical_skill": {
                "id": self.agent_skill.id,
                "name": self.agent_skill.name,
                "description": self.agent_skill.description,
                "scope": self.agent_skill.scope.value,
                "status": self.agent_skill.status.value,
                "canonical_path": self.agent_skill.canonical_path,
                "origin": self.agent_skill.origin,
                "content_hash": self.agent_skill.content_hash,
            },
        }
        if not self.native_installations:
            payload["native_installations_note"] = NO_NATIVE_INSTALLATIONS_NOTE
        return payload


class _ImportSkillSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    path: str | Path
    scope: LatentSkillScope
    origin: str = Field(min_length=1)
    replace_native: bool = False
    sync_after_import: bool = False
    slug: str | None = None


@dataclass(frozen=True, slots=True)
class _NativeImportOutcome:
    result: NativeSkillSyncResult
    warnings: list[str]
    backup: _NativeTreeBackup | None


@dataclass(frozen=True, slots=True)
class _NativeImportRequest:
    agent_skill: AgentSkill
    source_dir: Path
    slug: str
    files: list[tuple[str, str]]
    canonical_skill_file: str
    origin: str
    replace_native: bool
    canonical_base_path: Path


class ImportSkillUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        repository: AgentSkillRepository,
        safe_write_use_case: SafeWriteUseCase,
        global_safe_write_use_case: SafeWriteUseCase | None = None,
        runtime_registry: RuntimeRegistry | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository
        self.safe_write_use_case = safe_write_use_case
        self.global_safe_write_use_case = global_safe_write_use_case or safe_write_use_case
        self.runtime_registry = runtime_registry or default_runtime_registry()
        self.native_skill_sync = NativeSkillSync(
            project_root=self.project_root,
            safe_write_use_case=safe_write_use_case,
            runtime_registry=self.runtime_registry,
        )

    def execute(self, command: ImportSkillCommand) -> ImportSkillResult:
        validated = _ImportSkillSchema.model_validate(command)
        source_dir = self._source_dir(Path(validated.path))
        skill_file = source_dir / "SKILL.md"
        try:
            markdown = skill_file.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"Failed to read SKILL.md: {source_dir.as_posix()}"
            raise ValidationFailedError(msg) from exc

        parsed = _parse_skill_markdown(markdown)
        slug = _slug(validated.slug) if validated.slug else _slug(parsed.name)
        skill_dir = self._skill_dir_for(validated.scope, slug)
        canonical_skill_file = f"{skill_dir}/SKILL.md"
        self._validate_no_conflict(validated.scope, slug)
        validation_report = validate_skill_tree(
            skill_file,
            project_root=self.project_root,
            subject=slug,
        )
        assert_validation_passes(validation_report)

        files = self._source_files(source_dir)
        write = self._safe_write_for(validated.scope)
        audit_scope = _audit_scope_for(validated.scope)
        write_results = []
        native_backup: _NativeTreeBackup | None = None
        try:
            for relative_file, content in files:
                write_results.append(
                    write.execute(
                        SafeWriteCommand(
                            relative_path=f"{skill_dir}/{relative_file}",
                            content=content,
                            scope=audit_scope,
                            origin=validated.origin,
                            action="import_skill",
                        )
                    )
                )

            now = datetime.now(UTC)
            content_hash = _hash_text(markdown)
            import_source = self._safe_relative_source(source_dir, validated.scope)
            metadata: dict[str, Any] = {
                "triggers": parsed.triggers,
                "creation_flow": "import",
                "recommendation_flow": False,
                "import_source": import_source,
                "validation": validation_report.to_payload(),
            }
            agent_skill = AgentSkill(
                id=str(uuid4()),
                created_at=now,
                updated_at=now,
                name=parsed.name,
                slug=slug,
                description=parsed.description,
                scope=validated.scope,
                status=AgentSkillStatus.active,
                canonical_path=canonical_skill_file,
                origin=validated.origin,
                audit_reference=", ".join(result.audit_reference for result in write_results),
                content_hash=content_hash,
                metadata=metadata,
            )

            native_outcome = self._handle_native_source(
                _NativeImportRequest(
                    agent_skill=agent_skill,
                    source_dir=source_dir,
                    slug=slug,
                    files=files,
                    canonical_skill_file=canonical_skill_file,
                    origin=validated.origin,
                    replace_native=validated.replace_native,
                    canonical_base_path=write.project_root,
                )
            )
            native_result = native_outcome.result
            warnings = [*validation_report.warnings, *native_outcome.warnings]
            native_backup = native_outcome.backup
            warnings.extend(native_result.warnings)
            agent_skill = agent_skill.model_copy(
                update={
                    "native_installations": native_result.installations,
                    "audit_reference": ", ".join(
                        ref
                        for ref in [agent_skill.audit_reference, *native_result.audit_references]
                        if ref
                    ),
                    "metadata": {**metadata, "native_installations": native_result.installations},
                }
            )
            if validated.sync_after_import:
                native_result = self.native_skill_sync.sync(
                    skill=agent_skill,  # type: ignore[arg-type]
                    slug=slug,
                    canonical_skill_file=canonical_skill_file,
                    origin=validated.origin,
                    drift_decision="keep",
                    canonical_base_path=write.project_root,
                    allow_unmanaged_overwrite=False,
                )
                warnings.extend(native_result.warnings)
                agent_skill = agent_skill.model_copy(
                    update={
                        "native_installations": native_result.installations,
                        "audit_reference": ", ".join(
                            ref
                            for ref in [
                                agent_skill.audit_reference,
                                *native_result.audit_references,
                            ]
                            if ref
                        ),
                        "metadata": {
                            **metadata,
                            "native_installations": native_result.installations,
                            "sync_after_import": True,
                        },
                    }
                )
            registry_write = self.repository.write(agent_skill, origin=validated.origin)
            audit_references = [agent_skill.audit_reference]
            snapshot_references = [
                *(result.snapshot_reference for result in write_results),
                *native_result.snapshot_references,
            ]
            if registry_write is not None:
                audit_references.append(registry_write.audit_reference)
                snapshot_references.append(registry_write.snapshot_reference)

            return ImportSkillResult(
                agent_skill=agent_skill,
                slug=slug,
                skill_dir=skill_dir,
                skill_file=canonical_skill_file,
                created_paths=[result.relative_path for result in write_results],
                affected_paths=[
                    *(result.relative_path for result in write_results),
                    *native_result.affected_paths,
                ],
                audit_reference=", ".join(ref for ref in audit_references if ref),
                snapshot_reference=", ".join(ref for ref in snapshot_references if ref),
                native_installations=native_result.installations,
                warnings=warnings,
            )
        except Exception:
            for result in write_results:
                _cleanup_created_path(write.project_root / result.relative_path)
            if native_backup is not None:
                native_backup.restore()
            raise

    def _source_dir(self, path: Path) -> Path:
        source = path.expanduser()
        if not source.is_absolute():
            source = self.project_root / source
        if source.is_symlink():
            raise ValidationFailedError("Import source must not be a symlink.")
        if source.name == "SKILL.md" and source.parent.is_symlink():
            raise ValidationFailedError("Import source must not be a symlink.")
        source = source.resolve()
        if source.is_file():
            if source.name != "SKILL.md":
                raise ValidationFailedError(
                    "Import path must be a skill directory or SKILL.md file."
                )
            source = source.parent
            if source.is_symlink():
                raise ValidationFailedError("Import source must not be a symlink.")
        if not source.exists():
            raise ValidationFailedError(f"Import source not found: {path.as_posix()}")
        if not source.is_dir():
            raise ValidationFailedError("Import source must be a directory or SKILL.md file.")
        if not (source / "SKILL.md").is_file():
            raise ValidationFailedError("Import source directory must contain SKILL.md.")
        return source

    def _source_files(self, source_dir: Path) -> list[tuple[str, str]]:
        files: list[tuple[str, str]] = []
        for path in sorted(source_dir.rglob("*")):
            if path.is_symlink():
                raise ValidationFailedError("Import source must not contain symlinks.")
            if not path.is_file():
                continue
            resolved = path.resolve()
            try:
                resolved.relative_to(source_dir)
            except ValueError as exc:
                raise ValidationFailedError(
                    "Import source contains files outside its directory."
                ) from exc
            relative_path = resolved.relative_to(source_dir).as_posix()
            try:
                files.append((relative_path, resolved.read_text(encoding="utf-8")))
            except UnicodeDecodeError as exc:
                msg = f"Imported file must be UTF-8 text: {relative_path}"
                raise ValidationFailedError(msg) from exc
            except OSError as exc:
                raise StorageError(f"Failed to read imported file: {relative_path}") from exc
        return files

    def _validate_no_conflict(self, scope: LatentSkillScope, slug: str) -> None:
        canonical_dir = self._safe_write_for(scope).project_root / self._skill_dir_for(scope, slug)
        if canonical_dir.exists():
            raise ValidationFailedError(
                f"Skill import conflict: canonical skill already exists for slug '{slug}'."
            )
        for skill in self.repository.list(scope=scope):
            if skill.slug == slug or Path(skill.canonical_path).parent.name == slug:
                raise ValidationFailedError(
                    f"Skill import conflict: registry already contains slug '{slug}'."
                )

    def _supported_native_source(self, source_dir: Path, slug: str) -> tuple[str, str] | None:
        for runtime in self.runtime_registry.runtimes:
            for target in runtime.native_skill_targets:
                native_path = f"{target.relative_path}/{slug}"
                if source_dir == (self.project_root / native_path).resolve():
                    return runtime.runtime_id.value, native_path
        return None

    def _handle_native_source(self, request: _NativeImportRequest) -> _NativeImportOutcome:
        native_source = self._supported_native_source(request.source_dir, request.slug)
        if native_source is None:
            return _NativeImportOutcome(NativeSkillSyncResult(), [], None)

        runtime_id, native_path = native_source
        if request.replace_native:
            backup = _NativeTreeBackup.capture(self.project_root / native_path)
            result = self.native_skill_sync.sync(
                skill=request.agent_skill,  # type: ignore[arg-type]
                slug=request.slug,
                canonical_skill_file=request.canonical_skill_file,
                origin=request.origin,
                drift_decision="overwrite",
                canonical_base_path=request.canonical_base_path,
                targets=[runtime_id],
            )
            return _NativeImportOutcome(result, [], backup)

        if _hash_target_tree(request.source_dir) == _hash_tree(request.files):
            installation = self._native_installation(
                agent_skill=request.agent_skill,
                runtime=runtime_id,
                path=native_path,
                files=request.files,
            )
            return _NativeImportOutcome(
                NativeSkillSyncResult(installations=[installation]), [], None
            )

        return _NativeImportOutcome(
            NativeSkillSyncResult(),
            [
                "Warning: Native source target content does not match canonical import: "
                f"{native_path}"
            ],
            None,
        )

    @staticmethod
    def _native_installation(
        *, agent_skill: AgentSkill, runtime: str, path: str, files: list[tuple[str, str]]
    ) -> dict[str, Any]:
        tree_hash = _hash_tree(files)
        return {
            "source_skill_id": agent_skill.id,
            "runtime": runtime,
            "path": path,
            "canonical_hash": tree_hash,
            "target_hash": tree_hash,
            "hash_algorithm": MANIFEST_TREE_HASH_ALGORITHM,
            "manifest": [relative_path for relative_path, _content in files],
            "timestamp": datetime.now(UTC).isoformat(),
            "audit_reference": "",
        }

    def _safe_relative_source(self, source_dir: Path, scope: LatentSkillScope) -> str:
        roots = [self.project_root]
        if scope == LatentSkillScope.global_:
            roots.append(self._safe_write_for(scope).project_root)
        for root in roots:
            try:
                return source_dir.relative_to(root.resolve()).as_posix()
            except ValueError:
                continue
        return source_dir.as_posix()

    def _safe_write_for(self, scope: LatentSkillScope) -> SafeWriteUseCase:
        if scope == LatentSkillScope.global_:
            return self.global_safe_write_use_case
        return self.safe_write_use_case

    @staticmethod
    def _skill_dir_for(scope: LatentSkillScope, slug: str) -> str:
        if scope == LatentSkillScope.global_:
            return f"skills/{slug}"
        return f".umem/skills/{slug}"


def _audit_scope_for(scope: LatentSkillScope) -> AuditEventScope:
    if scope == LatentSkillScope.global_:
        return AuditEventScope.global_
    return AuditEventScope.project


def _hash_tree(files: list[tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for relative_path, content in files:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_hash_text(content).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _hash_target_tree(path: Path) -> str | None:
    if not path.is_dir():
        return None
    files: list[tuple[str, str]] = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink() or not item.is_file():
            continue
        files.append((item.relative_to(path).as_posix(), item.read_text(encoding="utf-8")))
    return _hash_tree(files)


def _cleanup_created_path(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
            parent = path.parent
            while parent.name and not any(parent.iterdir()):
                parent.rmdir()
                if parent.name == "skills":
                    break
                parent = parent.parent
    except OSError:
        pass


@dataclass(frozen=True, slots=True)
class _NativeTreeBackup:
    root: Path
    existed: bool
    files: tuple[tuple[str, str], ...]

    @classmethod
    def capture(cls, root: Path) -> _NativeTreeBackup:
        if not root.exists():
            return cls(root=root, existed=False, files=())
        files: list[tuple[str, str]] = []
        if root.is_file():
            files.append(("", root.read_text(encoding="utf-8")))
            return cls(root=root, existed=True, files=tuple(files))
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                files.append((path.relative_to(root).as_posix(), path.read_text(encoding="utf-8")))
        return cls(root=root, existed=True, files=tuple(files))

    def restore(self) -> None:
        if self.root.is_dir():
            shutil.rmtree(self.root)
        elif self.root.exists():
            self.root.unlink()
        if not self.existed:
            return
        if len(self.files) == 1 and self.files[0][0] == "":
            self.root.parent.mkdir(parents=True, exist_ok=True)
            self.root.write_text(self.files[0][1], encoding="utf-8")
            return
        for relative_path, content in self.files:
            target = self.root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
