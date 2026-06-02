from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.domain import InvalidConfigError, StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEventScope,
    LatentSkill,
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

    def sync(
        self,
        *,
        skill: LatentSkill,
        slug: str,
        canonical_skill_file: str,
        origin: str,
        drift_decision: NativeDriftDecision | None,
    ) -> NativeSkillSyncResult:
        canonical_path = self.project_root / canonical_skill_file
        canonical_content = canonical_path.read_text(encoding="utf-8")
        canonical_hash = _hash_text(canonical_content)
        previous_by_path = _previous_installations_by_path(skill.metadata)

        affected_paths: list[str] = []
        audit_refs: list[str] = []
        snapshot_refs: list[str] = []
        installations: list[dict[str, Any]] = []
        warnings: list[str] = []

        for runtime in self._enabled_runtimes():
            for target in runtime.native_skill_targets:
                relative_path = self._native_skill_file_path(
                    target_base=target.relative_path,
                    target_format=target.format,
                    slug=slug,
                )
                content = canonical_content
                current_path = self.project_root / relative_path
                previous = previous_by_path.get(relative_path)
                current_hash = (
                    _hash_text(current_path.read_text(encoding="utf-8"))
                    if current_path.is_file()
                    else None
                )
                has_drift = (
                    previous is not None
                    and current_hash is not None
                    and current_hash != previous.get("target_hash")
                )
                if has_drift and drift_decision != "overwrite":
                    warnings.append(DRIFT_WARNING)
                    installations.append({**previous, "drift_detected": True})
                    continue

                write_result = self.safe_write_use_case.execute(
                    SafeWriteCommand(
                        relative_path=relative_path,
                        content=content,
                        scope=AuditEventScope.project,
                        origin=origin,
                        action="sync_native_skill",
                    )
                )
                affected_paths.append(write_result.relative_path)
                audit_refs.append(write_result.audit_reference)
                snapshot_refs.append(write_result.snapshot_reference)
                if has_drift:
                    warnings.append(
                        f"Native target overwritten after manual drift: {relative_path}"
                    )
                installations.append(
                    {
                        "source_skill_id": skill.id,
                        "runtime": runtime.runtime_id.value,
                        "path": write_result.relative_path,
                        "canonical_hash": canonical_hash,
                        "target_hash": _hash_text(content),
                        "timestamp": datetime.now(UTC).isoformat(),
                        "audit_reference": write_result.audit_reference,
                    }
                )

        return NativeSkillSyncResult(
            affected_paths=affected_paths,
            audit_references=audit_refs,
            snapshot_references=snapshot_refs,
            installations=installations,
            warnings=warnings,
        )

    def disable(
        self,
        *,
        skill: LatentSkill,
        origin: str,
    ) -> NativeSkillSyncResult:
        affected_paths: list[str] = []
        audit_refs: list[str] = []
        snapshot_refs: list[str] = []
        for installation in _previous_installations_by_path(skill.metadata).values():
            relative_path = str(installation.get("path", ""))
            if not relative_path:
                continue
            result = self.safe_write_use_case.execute(
                SafeWriteCommand(
                    relative_path=relative_path,
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
        return NativeSkillSyncResult(
            affected_paths=affected_paths,
            audit_references=audit_refs,
            snapshot_references=snapshot_refs,
        )

    def _enabled_runtimes(self) -> list[RuntimeAdapter]:
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
            raise ValidationFailedError(f"Falha ao ler configuracao do projeto: {exc}") from exc
        raw_runtimes = loaded.merged.get("runtimes")
        if raw_runtimes is None:
            return None
        if not isinstance(raw_runtimes, dict):
            raise ValidationFailedError("Configuracao invalida: runtimes deve ser uma tabela.")
        raw_enabled = raw_runtimes.get("enabled")
        if raw_enabled is None:
            return None
        if not isinstance(raw_enabled, list):
            raise ValidationFailedError(
                "Configuracao invalida: runtimes.enabled deve ser uma lista."
            )
        enabled = [str(runtime_id) for runtime_id in raw_enabled]
        unsupported = [
            runtime_id
            for runtime_id in enabled
            if runtime_id not in {item.value for item in RuntimeId}
        ]
        if unsupported:
            raise ValidationFailedError(f"Runtimes nao suportados: {', '.join(unsupported)}")
        return enabled

    @staticmethod
    def _native_skill_file_path(*, target_base: str, target_format: str, slug: str) -> str:
        filename = "SKILL.mdc" if target_format == "mdc-directory" else "SKILL.md"
        return f"{target_base}/{slug}/{filename}"


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


def _hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
