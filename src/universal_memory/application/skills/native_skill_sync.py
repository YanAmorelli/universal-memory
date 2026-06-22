from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.domain import InvalidConfigError, StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEventScope,
    LatentSkill,
    NativeSkillTarget,
    RuntimeAdapter,
    RuntimeId,
    RuntimeRegistry,
    default_runtime_registry,
)
from universal_memory.infrastructure.config.toml_loader import load_config

NativeDriftDecision = Literal["keep", "overwrite"]

DRIFT_WARNING = (
    "Warning: Native target has manual changes. Overwriting it might break your current "
    "agent workflow. Keep local version or Overwrite with canonical library version? "
    "[Keep/Overwrite]"
)


@dataclass(frozen=True, slots=True)
class NativeSkillSyncResult:
    affected_paths: list[str] = field(default_factory=list)
    audit_references: list[str] = field(default_factory=list)
    snapshot_references: list[str] = field(default_factory=list)
    installations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class NativeSkillSync:
    def __init__(
        self,
        *,
        project_root: Path,
        safe_write_use_case: SafeWriteUseCase,
        runtime_registry: RuntimeRegistry | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.safe_write_use_case = safe_write_use_case
        self.runtime_registry = runtime_registry or default_runtime_registry()

    def sync(  # noqa: PLR0913
        self,
        *,
        skill: LatentSkill,
        slug: str,
        canonical_skill_file: str,
        origin: str,
        drift_decision: NativeDriftDecision | None,
        canonical_base_path: Path | None = None,
        targets: list[str] | None = None,
        allow_unmanaged_overwrite: bool = True,
    ) -> NativeSkillSyncResult:
        canonical_path = (canonical_base_path or self.project_root) / canonical_skill_file
        canonical_dir = canonical_path.parent
        canonical_files = _directory_files(canonical_dir)
        canonical_hash = _hash_tree(canonical_files)
        previous_by_path = _previous_installations_by_path(skill.metadata)

        affected_paths: list[str] = []
        audit_refs: list[str] = []
        snapshot_refs: list[str] = []
        installations: list[dict[str, Any]] = []
        warnings: list[str] = []

        for runtime in self._enabled_runtimes(targets=targets):
            for target in runtime.native_skill_targets:
                relative_path = self._native_skill_dir_path(
                    target_base=target.relative_path,
                    slug=slug,
                )
                current_path = self.project_root / relative_path
                previous = previous_by_path.get(relative_path)
                current_hash = self._target_hash_for_previous_installation(current_path, previous)
                has_drift = (
                    previous is not None
                    and current_hash is not None
                    and current_hash != previous.get("target_hash")
                )
                has_unmanaged_target = previous is None and current_hash is not None
                if has_unmanaged_target and (
                    not allow_unmanaged_overwrite or drift_decision != "overwrite"
                ):
                    warnings.append(
                        "Warning: Native target already exists and is not managed by UMEM: "
                        f"{relative_path}"
                    )
                    installations.append(
                        {
                            "source_skill_id": skill.id,
                            "runtime": runtime.runtime_id.value,
                            "path": relative_path,
                            "canonical_hash": canonical_hash,
                            "target_hash": current_hash,
                            "manifest": [],
                            "timestamp": datetime.now(UTC).isoformat(),
                            "audit_reference": "",
                            "snapshot_reference": "",
                            "drift_detected": True,
                            "managed": False,
                            "status": "unmanaged_native",
                        }
                    )
                    continue
                if has_drift and drift_decision != "overwrite":
                    warnings.append(DRIFT_WARNING)
                    previous_installation = cast(dict[str, Any], previous)
                    installations.append({**previous_installation, "drift_detected": True})
                    continue

                write_results = []
                target_files = _target_files_for(canonical_files, target)
                target_manifest = [path for path, _content in target_files]
                for target_relative_file, content in target_files:
                    write_results.append(
                        self.safe_write_use_case.execute(
                            SafeWriteCommand(
                                relative_path=f"{relative_path}/{target_relative_file}",
                                content=content,
                                scope=AuditEventScope.project,
                                origin=origin,
                                action="sync_native_skill",
                            )
                        )
                    )
                obsolete_paths = self._remove_obsolete_managed_files(
                    target_root=current_path,
                    previous_manifest=_manifest_for(previous),
                    target_manifest=target_manifest,
                )
                affected_paths.extend(result.relative_path for result in write_results)
                affected_paths.extend(f"{relative_path}/{path}" for path in obsolete_paths)
                audit_refs.extend(result.audit_reference for result in write_results)
                snapshot_refs.extend(result.snapshot_reference for result in write_results)
                if has_drift:
                    warnings.append(
                        f"Native target overwritten after manual drift: {relative_path}"
                    )
                installations.append(
                    {
                        "source_skill_id": skill.id,
                        "runtime": runtime.runtime_id.value,
                        "path": relative_path,
                        "canonical_hash": canonical_hash,
                        "target_hash": _hash_tree(target_files),
                        "manifest": target_manifest,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "audit_reference": ", ".join(
                            result.audit_reference for result in write_results
                        ),
                        "snapshot_reference": ", ".join(
                            result.snapshot_reference for result in write_results
                        ),
                        "drift_detected": False,
                        "status": "overwritten" if has_drift else "synced",
                    }
                )

        return NativeSkillSyncResult(
            affected_paths=affected_paths,
            audit_references=audit_refs,
            snapshot_references=snapshot_refs,
            installations=installations,
            warnings=warnings,
        )

    def _target_hash_for_previous_installation(
        self, current_path: Path, previous: dict[str, Any] | None
    ) -> str | None:
        if previous is None:
            return _hash_target_tree(current_path)
        manifest = _manifest_for(previous)
        if not manifest:
            return _hash_target_tree(current_path)
        return _hash_target_manifest_tree(current_path, manifest)

    def _remove_obsolete_managed_files(
        self,
        *,
        target_root: Path,
        previous_manifest: list[str],
        target_manifest: list[str],
    ) -> list[str]:
        obsolete = sorted(set(previous_manifest) - set(target_manifest))
        removed: list[str] = []
        for relative_path in obsolete:
            path = _safe_manifest_path(target_root, relative_path)
            if path is None or not path.is_file():
                continue
            path.unlink()
            removed.append(relative_path)
            _prune_empty_directories(path.parent, target_root)
        return removed

    def disable(
        self,
        *,
        skill: LatentSkill,
        origin: str,
    ) -> NativeSkillSyncResult:
        affected_paths: list[str] = []
        audit_refs: list[str] = []
        snapshot_refs: list[str] = []
        policies_by_runtime = self._disable_policies_by_runtime()
        for installation in _previous_installations_by_path(skill.metadata).values():
            relative_path = str(installation.get("path", ""))
            if not relative_path:
                continue
            runtime_id = str(installation.get("runtime", ""))
            policy = policies_by_runtime.get(runtime_id, "remove")
            if policy == "preserve":
                continue
            if policy == "disable_stub":
                result = self.safe_write_use_case.execute(
                    SafeWriteCommand(
                        relative_path=f"{relative_path}/SKILL.md",
                        content=(
                            "# Universal Memory skill disabled\n\n"
                            "This native runtime target was disabled by Universal Memory.\n"
                            "The canonical skill under .umem/skills remains preserved.\n"
                        ),
                        scope=AuditEventScope.project,
                        origin=origin,
                        action="disable_native_skill",
                    )
                )
                affected_paths.append(result.relative_path)
                audit_refs.append(result.audit_reference)
                snapshot_refs.append(result.snapshot_reference)
                continue
            self._remove_native_target(relative_path)
            affected_paths.append(relative_path)
        return NativeSkillSyncResult(
            affected_paths=affected_paths,
            audit_references=audit_refs,
            snapshot_references=snapshot_refs,
        )

    def _enabled_runtimes(self, *, targets: list[str] | None = None) -> list[RuntimeAdapter]:
        if targets is not None:
            unsupported = [
                runtime_id
                for runtime_id in targets
                if runtime_id not in {item.value for item in RuntimeId}
            ]
            if unsupported:
                raise ValidationFailedError(f"Unsupported runtimes: {', '.join(unsupported)}")
            target_set = set(targets)
            return [
                runtime
                for runtime in self.runtime_registry.runtimes
                if runtime.runtime_id.value in target_set and runtime.native_skill_targets
            ]
        enabled = self._enabled_runtime_ids_from_config()
        runtimes = self.runtime_registry.runtimes
        if enabled is None:
            return [runtime for runtime in runtimes if runtime.native_skill_targets]
        enabled_set = set(enabled)
        return [
            runtime
            for runtime in runtimes
            if runtime.runtime_id.value in enabled_set and runtime.native_skill_targets
        ]

    def _enabled_runtime_ids_from_config(self) -> list[str] | None:
        try:
            loaded = load_config(self.project_root)
        except (OSError, InvalidConfigError, StorageError) as exc:
            raise ValidationFailedError(f"Failed to read project configuration: {exc}") from exc
        raw_runtimes = loaded.merged.get("runtimes")
        if raw_runtimes is None:
            return None
        if not isinstance(raw_runtimes, dict):
            raise ValidationFailedError("Invalid configuration: runtimes must be a table.")
        raw_enabled = raw_runtimes.get("enabled")
        if raw_enabled is None:
            return None
        if not isinstance(raw_enabled, list):
            raise ValidationFailedError("Invalid configuration: runtimes.enabled must be a list.")
        enabled = [str(runtime_id) for runtime_id in raw_enabled]
        unsupported = [
            runtime_id
            for runtime_id in enabled
            if runtime_id not in {item.value for item in RuntimeId}
        ]
        if unsupported:
            raise ValidationFailedError(f"Unsupported runtimes: {', '.join(unsupported)}")
        return enabled

    @staticmethod
    def _native_skill_dir_path(*, target_base: str, slug: str) -> str:
        return f"{target_base}/{slug}"

    def _disable_policies_by_runtime(self) -> dict[str, str]:
        return {
            runtime.runtime_id.value: target.disable_policy
            for runtime in self.runtime_registry.runtimes
            for target in runtime.native_skill_targets
        }

    def _remove_native_target(self, relative_path: str) -> None:
        target_path = (self.project_root / relative_path).resolve()
        try:
            target_path.relative_to(self.project_root)
        except ValueError as exc:
            raise ValidationFailedError("Native target resolves outside the project.") from exc
        if target_path.is_dir():
            shutil.rmtree(target_path)
        elif target_path.is_file():
            target_path.unlink()


def merge_native_installations(
    metadata: dict[str, Any] | None,
    installations: list[dict[str, Any]],
) -> dict[str, Any]:
    merged = dict(metadata or {})
    current = _previous_installations_by_path(merged)
    for installation in installations:
        path = str(installation.get("path", ""))
        if path:
            current[path] = installation
    merged["native_installations"] = list(current.values())
    return merged


def _previous_installations_by_path(metadata: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    raw = (metadata or {}).get("native_installations", [])
    if not isinstance(raw, list):
        return {}
    result = {}
    for item in raw:
        if isinstance(item, dict) and item.get("path"):
            result[str(item["path"])] = dict(item)
    return result


def _manifest_for(installation: dict[str, Any] | None) -> list[str]:
    raw_manifest = (installation or {}).get("manifest", [])
    if not isinstance(raw_manifest, list):
        return []
    manifest: list[str] = []
    for item in raw_manifest:
        if isinstance(item, str) and _safe_manifest_relative_path(item):
            manifest.append(item)
    return manifest


def _directory_files(directory: Path) -> list[tuple[str, str]]:
    if not directory.is_dir():
        raise ValidationFailedError(f"Diretorio canonico de skill ausente: {directory}")
    files: list[tuple[str, str]] = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        relative_path = path.relative_to(directory).as_posix()
        files.append((relative_path, path.read_text(encoding="utf-8")))
    return files


def _target_files_for(
    canonical_files: list[tuple[str, str]], target: NativeSkillTarget
) -> list[tuple[str, str]]:
    files = []
    for relative_path, content in canonical_files:
        target_relative_path = relative_path
        if target.format == "mdc-directory" and relative_path == "SKILL.md":
            target_relative_path = "SKILL.mdc"
        files.append((target_relative_path, content))
    return files


def _hash_target_tree(path: Path) -> str | None:
    if not path.exists():
        return None
    if path.is_file():
        return _hash_text(path.read_text(encoding="utf-8"))
    if not path.is_dir():
        return None
    return _hash_tree(_directory_files(path))


def _hash_target_manifest_tree(path: Path, manifest: list[str]) -> str | None:
    if not path.is_dir():
        return None
    files: list[tuple[str, str]] = []
    for relative_path in sorted(manifest):
        target_file = _safe_manifest_path(path, relative_path)
        if target_file is None or not target_file.is_file():
            return None
        files.append((relative_path, target_file.read_text(encoding="utf-8")))
    return _hash_tree(files)


def _safe_manifest_relative_path(relative_path: str) -> bool:
    if "\\" in relative_path:
        return False
    path = PurePosixPath(relative_path)
    return relative_path != "" and not path.is_absolute() and ".." not in path.parts


def _safe_manifest_path(root: Path, relative_path: str) -> Path | None:
    if not _safe_manifest_relative_path(relative_path):
        return None
    resolved = (root / relative_path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def _prune_empty_directories(path: Path, root: Path) -> None:
    root = root.resolve()
    current = path.resolve()
    while current != root:
        try:
            current.relative_to(root)
        except ValueError:
            return
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _hash_tree(files: list[tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for relative_path, content in files:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_hash_text(content).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
