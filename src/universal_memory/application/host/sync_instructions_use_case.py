from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from universal_memory.application.host.setup_host_use_case import (
    ConfigureHostCommand,
    ConfigureHostResult,
    ConfigureHostUseCase,
    InstructionBlock,
    _safe_relative_path,
)
from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.domain import InvalidConfigError, StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AuditEventScope,
    InstructionClassification,
    Rule,
    RuleStatus,
    FactStatus,
)
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.domain.ports import RuleRepository, FactRepository
from universal_memory.infrastructure.config.toml_loader import load_config, update_project_config

DEFAULT_SYNC_HOSTS = ("codex", "claude_code")
CLAUDE_SUPPORTED_CLASSIFICATIONS = {
    InstructionClassification.provider_delta,
    InstructionClassification.scoped_rule,
}


@dataclass(frozen=True, slots=True)
class SyncInstructionsCommand:
    host_ids: list[str] = field(default_factory=lambda: list(DEFAULT_SYNC_HOSTS))
    apply: bool = False
    max_managed_lines: int = 100
    max_managed_chars: int = 4000
    origin: str = "host_sync"


@dataclass(frozen=True, slots=True)
class SyncInstructionsResult:
    host_ids: list[str]
    instruction_targets: list[str]
    planned_changes: list[dict[str, str]]
    manual_steps: list[str]
    validation_status: str
    audit_reference: str
    snapshot_reference: str
    timestamp: str
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "host_ids": self.host_ids,
            "instruction_targets": self.instruction_targets,
            "planned_changes": self.planned_changes,
            "manual_steps": self.manual_steps,
            "validation_status": self.validation_status,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "timestamp": self.timestamp,
        }


class SyncInstructionsUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        safe_write_use_case: SafeWriteUseCase,
        rule_repository: RuleRepository,
        fact_repository: FactRepository | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.rule_repository = rule_repository
        self.fact_repository = fact_repository
        self.configure_host_use_case = ConfigureHostUseCase(
            project_root=project_root,
            safe_write_use_case=safe_write_use_case,
            fact_repository=fact_repository,
        )

    def execute(self, command: SyncInstructionsCommand) -> SyncInstructionsResult:
        host_ids, config_warnings = self._host_ids_for_command(command.host_ids)
        all_blocks = self._active_rule_blocks()
        plans = self._plan_commands(host_ids, all_blocks, command)

        results = []
        for host_id, blocks, shared_manifest_available in plans:
            results.append(
                self._execute_host_plan(
                    host_id,
                    blocks,
                    command,
                    shared_manifest_available=shared_manifest_available,
                )
            )

        planned_changes = self._unique_changes(
            change for result in results for change in result.planned_changes
        )
        instruction_targets = self._instruction_targets(planned_changes)
        warnings = config_warnings + [warning for result in results for warning in result.warnings]
        manual_steps = self._manual_steps(results, command.apply)
        return SyncInstructionsResult(
            host_ids=host_ids,
            instruction_targets=instruction_targets,
            planned_changes=planned_changes,
            manual_steps=manual_steps,
            validation_status="success" if command.apply else "planned",
            audit_reference=self._join_refs(
                [result.audit_reference for result in results],
                default_val="not-applied",
            ),
            snapshot_reference=self._join_refs(
                [result.snapshot_reference for result in results],
                default_val="planned",
            ),
            timestamp=format_utc_iso(datetime.now(UTC)),
            warnings=warnings,
        )

    def _execute_host_plan(
        self,
        host_id: str,
        blocks: list[InstructionBlock],
        command: SyncInstructionsCommand,
        *,
        shared_manifest_available: bool | None,
    ) -> ConfigureHostResult:
        host = self.configure_host_use_case.host_for(host_id)
        target = self.configure_host_use_case.primary_target_for(host)
        host_command = ConfigureHostCommand(
            host_id=host_id,
            apply=command.apply,
            instruction_blocks=blocks,
            shared_manifest_available=shared_manifest_available,
            max_managed_lines=command.max_managed_lines,
            max_managed_chars=command.max_managed_chars,
            origin=command.origin,
        )
        existing_content = self.configure_host_use_case.read_existing(target.relative_path)
        self.configure_host_use_case.validate_existing_managed_content(
            existing_content,
            target_path=target.relative_path,
            command=host_command,
        )
        prepared = self.configure_host_use_case.prepare_target_content(
            target,
            existing_content=existing_content,
            instruction_blocks=blocks,
            command=host_command,
        )
        planned_changes = self.configure_host_use_case.planned_changes(
            target,
            existing_content=existing_content,
            final_content=prepared.final_content,
            canonical_documents=prepared.canonical_documents,
        )

        drift = self.configure_host_use_case.drift_content(
            existing_content, prepared.final_content, command.apply
        )
        drift_warnings = self.configure_host_use_case.drift_warnings(host, target, drift)
        warnings = list(prepared.warnings) + drift_warnings

        audit_reference = "not-applied"
        snapshot_reference = "planned"
        if command.apply:
            audit_reference, snapshot_reference = self._write_prepared_target(
                target_path=target.relative_path,
                final_content=prepared.final_content,
                canonical_documents=prepared.canonical_documents,
                origin=command.origin,
            )
        return ConfigureHostResult(
            host_id=host_id,
            instruction_targets=[target.name.value],
            planned_changes=planned_changes,
            manual_steps=[],
            validation_status="success" if command.apply else "planned",
            audit_reference=audit_reference,
            snapshot_reference=snapshot_reference,
            timestamp=format_utc_iso(datetime.now(UTC)),
            warnings=warnings,
        )

    def _write_prepared_target(
        self,
        *,
        target_path: str,
        final_content: str,
        canonical_documents: list[Any],
        origin: str,
    ) -> tuple[str, str]:
        audit_refs: list[str] = []
        snapshot_refs: list[str] = []
        successful_writes: list[tuple[str, str]] = []
        try:
            for document in canonical_documents:
                # Keep original content for rollback if exists
                prev_content = ""
                full_path = self.project_root / document.relative_path
                if full_path.exists():
                    prev_content = full_path.read_text(encoding="utf-8")

                result = self.configure_host_use_case.safe_write_use_case.execute(
                    SafeWriteCommand(
                        relative_path=document.relative_path,
                        content=self.configure_host_use_case.render_canonical_document(document),
                        scope=AuditEventScope.project,
                        origin=origin,
                        action="host_sync.canonical_doc",
                    )
                )
                audit_refs.append(result.audit_reference)
                snapshot_refs.append(result.snapshot_reference)
                successful_writes.append((document.relative_path, prev_content))

            prev_content = ""
            full_path = self.project_root / target_path
            if full_path.exists():
                prev_content = full_path.read_text(encoding="utf-8")

            result = self.configure_host_use_case.safe_write_use_case.execute(
                SafeWriteCommand(
                    relative_path=target_path,
                    content=final_content,
                    scope=AuditEventScope.project,
                    origin=origin,
                    action=f"host_sync.{target_path}",
                )
            )
            audit_refs.append(result.audit_reference)
            snapshot_refs.append(result.snapshot_reference)
            successful_writes.append((target_path, prev_content))

            clean_audit = [ref for ref in audit_refs if ref not in ("not-applied", "planned")]
            clean_snap = [ref for ref in snapshot_refs if ref not in ("not-applied", "planned")]
            return (
                ", ".join(clean_audit) if clean_audit else "not-applied",
                ", ".join(clean_snap) if clean_snap else "planned",
            )
        except Exception as error:
            # Coordinated Transaction Rollback
            for path, prev_content in reversed(successful_writes):
                try:
                    self.configure_host_use_case.safe_write_use_case.execute(
                        SafeWriteCommand(
                            relative_path=path,
                            content=prev_content,
                            scope=AuditEventScope.project,
                            origin=origin,
                            action="host_sync.rollback",
                        )
                    )
                except Exception as rollback_error:
                    print(f"Error during rollback of {path}: {rollback_error}", file=sys.stderr)
            raise error

    def _plan_commands(
        self,
        host_ids: list[str],
        blocks: list[InstructionBlock],
        command: SyncInstructionsCommand,
    ) -> list[tuple[str, list[InstructionBlock], bool | None]]:
        plans: list[tuple[str, list[InstructionBlock], bool | None]] = []
        should_write_agents = "codex" in host_ids and any(
            block.resolved_classification
            in {
                InstructionClassification.shared_policy,
                InstructionClassification.provider_delta,
                InstructionClassification.scoped_rule,
                InstructionClassification.canonical_doc,
            }
            for block in blocks
        )
        if should_write_agents:
            plans.append(("codex", blocks, None))
        if "claude_code" in host_ids:
            claude_classifications = set(CLAUDE_SUPPORTED_CLASSIFICATIONS)
            if not should_write_agents:
                claude_classifications.add(InstructionClassification.shared_policy)
            plans.append(
                (
                    "claude_code",
                    [
                        block
                        for block in blocks
                        if block.resolved_classification in claude_classifications
                    ],
                    should_write_agents,
                )
            )
        if not plans and host_ids:
            raise ValidationFailedError("Nenhum host suportado informado para sincronizacao.")
        return plans

    def _active_rule_blocks(self) -> list[InstructionBlock]:
        blocks = []
        rules = self.rule_repository.list(status=RuleStatus.active)
        for rule in rules:
            blocks.append(self._rule_to_block(rule))

        if self.fact_repository is not None:
            for fact in self.fact_repository.list(status=FactStatus.active):
                classification = InstructionClassification.shared_policy
                tags = fact.tags or []
                for candidate in InstructionClassification:
                    if candidate.value in tags or candidate.value.replace("_", "-") in tags:
                        classification = candidate
                        break
                title = fact.metadata.get("title") if fact.metadata else None
                blocks.append(
                    InstructionBlock(
                        title=title or f"Fato {fact.id[:8]}",
                        content=fact.content,
                        classification=classification,
                    )
                )
        return blocks

    def _rule_to_block(self, rule: Rule) -> InstructionBlock:
        classification = self._classification_for(rule)
        metadata = rule.metadata or {}
        relative_path = (
            metadata.get("relative_path") or metadata.get("canonical_path") or metadata.get("path")
        )
        if relative_path:
            relative_path = _safe_relative_path(str(relative_path))
        return InstructionBlock(
            title=metadata.get("title") or rule.name,
            content=rule.content,
            classification=classification,
            relative_path=relative_path,
        )

    def _classification_for(self, rule: Rule) -> InstructionClassification:
        metadata = rule.metadata or {}
        raw = (
            metadata.get("classification")
            or metadata.get("category")
            or metadata.get("instruction_classification")
        )
        if raw is None:
            raw = "shared_policy"
        try:
            return InstructionClassification(str(raw))
        except ValueError as exc:
            raise ValidationFailedError(
                f"Classificacao de regra nao suportada para '{rule.name}': {raw}"
            ) from exc

    def _normalized_host_ids(self, host_ids: list[str] | None) -> list[str]:
        normalized: list[str] = []
        resolved = host_ids if host_ids is not None else list(DEFAULT_SYNC_HOSTS)
        for host_id in resolved:
            if host_id not in normalized:
                normalized.append(host_id)
        unsupported = [host_id for host_id in normalized if host_id not in DEFAULT_SYNC_HOSTS]
        if unsupported:
            raise ValidationFailedError(f"Hosts nao suportados: {', '.join(unsupported)}")
        return normalized

    def _host_ids_for_command(self, host_ids: list[str] | None) -> tuple[list[str], list[str]]:
        normalized = self._normalized_host_ids(host_ids)
        enabled_hosts = self._enabled_hosts_from_config()
        if enabled_hosts is None:
            return normalized, []

        if not host_ids or set(normalized) == set(DEFAULT_SYNC_HOSTS):
            return [host_id for host_id in DEFAULT_SYNC_HOSTS if host_id in enabled_hosts], []

        warnings = []
        to_enable = []
        for host_id in normalized:
            if host_id not in enabled_hosts:
                warnings.append(
                    f"Host '{host_id}' nao esta habilitado em .umem/config.toml; "
                    "ativando automaticamente."
                )
                to_enable.append(host_id)

        if to_enable:
            new_enabled = list(enabled_hosts)
            for h in to_enable:
                if h not in new_enabled:
                    new_enabled.append(h)
            update_project_config(self.project_root, {"runtimes": {"enabled": new_enabled}})

        return normalized, warnings

    def _enabled_hosts_from_config(self) -> list[str] | None:
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
        enabled = [str(host_id) for host_id in raw_enabled]
        return [host_id for host_id in enabled if host_id in DEFAULT_SYNC_HOSTS]

    def _instruction_targets(self, planned_changes: list[dict[str, str]]) -> list[str]:
        targets: list[str] = []
        for change in planned_changes:
            path = change["path"]
            if path not in targets:
                targets.append(path)
        priority = {"AGENTS.md": 0, "CLAUDE.md": 1}
        return sorted(targets, key=lambda path: (priority.get(path, 2), path))

    def _manual_steps(self, results: list[Any], apply: bool) -> list[str]:
        steps: list[str] = []
        if not apply:
            steps.append("Revise os caminhos afetados antes de aplicar.")
        for result in results:
            for step in result.manual_steps:
                if step not in steps:
                    steps.append(step)
        return steps

    def _unique_changes(self, changes: Any) -> list[dict[str, str]]:
        unique: list[dict[str, str]] = []
        seen: dict[str, dict[str, str]] = {}
        for change in changes:
            path = change["path"]
            if path in seen:
                existing = seen[path]
                if existing["action"] != change["action"]:
                    # Action conflict on the same file! Preserve to show in CLI.
                    unique.append(change)
                continue
            seen[path] = change
            unique.append(change)
        return unique

    def _join_refs(self, refs: list[str], default_val: str = "not-applied") -> str:
        unique = []
        for ref in refs:
            for part in ref.split(", "):
                part_clean = part.strip()
                if (
                    part_clean
                    and part_clean not in ("not-applied", "planned")
                    and part_clean not in unique
                ):
                    unique.append(part_clean)
        return ", ".join(unique) if unique else default_val
