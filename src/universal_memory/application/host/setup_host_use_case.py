from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal
from uuid import uuid4

from universal_memory.application.host.drift_detector import InstructionDriftDetector
from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    FactStatus,
    Host,
    HostName,
    InstructionClassification,
    InstructionTarget,
    InstructionTargetOwnership,
    InstructionTargetType,
)
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.domain.ports import FactRepository

UMEM_START = "<!-- UMEM: START -->"
UMEM_END = "<!-- UMEM: END -->"
DEFAULT_MAX_MANAGED_LINES = 100
DEFAULT_MAX_MANAGED_CHARS = 4000
LONG_CONTENT_THRESHOLD = 800
RAW_MEMORY_DUMP_HIT_THRESHOLD = 3

InstructionClassificationValue = Literal[
    "shared_policy", "provider_delta", "scoped_rule", "canonical_doc"
]


@dataclass(frozen=True, slots=True)
class InstructionBlock:
    title: str
    content: str
    classification: InstructionClassification | InstructionClassificationValue
    relative_path: str | None = None

    @property
    def resolved_classification(self) -> InstructionClassification:
        if isinstance(self.classification, InstructionClassification):
            return self.classification
        return InstructionClassification(self.classification)


@dataclass(frozen=True, slots=True)
class CanonicalDocument:
    title: str
    content: str
    relative_path: str


@dataclass(frozen=True, slots=True)
class ManifestInstruction:
    title: str
    content: str
    classification: InstructionClassification


@dataclass(frozen=True, slots=True)
class InstructionPartition:
    manifest_blocks: list[ManifestInstruction]
    canonical_documents: list[CanonicalDocument]
    pointer_lines: list[str]


@dataclass(frozen=True, slots=True)
class ConfigureHostCommand:
    host_id: str
    apply: bool = False
    check: bool = False
    instruction_blocks: list[InstructionBlock] = field(default_factory=list)
    shared_manifest_available: bool | None = None
    max_managed_lines: int = DEFAULT_MAX_MANAGED_LINES
    max_managed_chars: int = DEFAULT_MAX_MANAGED_CHARS
    origin: str = "host_setup"


@dataclass(frozen=True, slots=True)
class ConfigureHostResult:
    host_id: str
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
            "host_id": self.host_id,
            "instruction_targets": self.instruction_targets,
            "planned_changes": self.planned_changes,
            "manual_steps": self.manual_steps,
            "validation_status": self.validation_status,
            "audit_reference": self.audit_reference,
            "snapshot_reference": self.snapshot_reference,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True, slots=True)
class PreparedInstructionTarget:
    final_content: str
    canonical_documents: list[CanonicalDocument]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class HostReadValidationResult:
    status: str
    method: str
    checks: dict[str, bool]
    failures: list[str]
    warnings: list[str]


def partition_instruction_blocks(
    blocks: list[InstructionBlock],
    *,
    docs_directory: str = "docs",
) -> InstructionPartition:
    manifest_blocks: list[ManifestInstruction] = []
    canonical_documents: list[CanonicalDocument] = []
    pointer_lines: list[str] = []
    seen_paths: set[str] = set()

    for block in blocks:
        if UMEM_START in block.content or UMEM_END in block.content:
            raise ValidationFailedError(
                f"O conteudo do bloco '{block.title}' nao pode conter os delimitadores UMEM."
            )

        classification = block.resolved_classification
        if classification == InstructionClassification.canonical_doc:
            relative_path = block.relative_path or _canonical_doc_path(block.title, docs_directory)
            _safe_relative_path(relative_path)
            if relative_path in seen_paths:
                raise ValidationFailedError(
                    f"Caminho canonico duplicado detectado: {relative_path}"
                )
            seen_paths.add(relative_path)
            document = CanonicalDocument(
                title=block.title.strip() or "Documento canônico",
                content=block.content.strip(),
                relative_path=relative_path,
            )
            canonical_documents.append(document)
            pointer_lines.append(f"- [{relative_path}](file:///{relative_path})")
            continue

        if block.relative_path:
            _safe_relative_path(block.relative_path)

        manifest_blocks.append(
            ManifestInstruction(
                title=block.title.strip() or classification.value,
                content=block.content.strip(),
                classification=classification,
            )
        )

    return InstructionPartition(
        manifest_blocks=manifest_blocks,
        canonical_documents=canonical_documents,
        pointer_lines=pointer_lines,
    )


class ConfigureHostUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        safe_write_use_case: SafeWriteUseCase,
        fact_repository: FactRepository | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.safe_write_use_case = safe_write_use_case
        self.fact_repository = fact_repository

    def execute(self, command: ConfigureHostCommand) -> ConfigureHostResult:
        host = self._host_for(command.host_id)
        target = self._primary_target_for(host)

        if command.check:
            validation = self._validate_host_read(host, target)
            audit_reference = self._record_host_validation(command, host, validation)
            return ConfigureHostResult(
                host_id=host.name.value,
                instruction_targets=[target.name.value],
                planned_changes=[],
                manual_steps=[],
                validation_status=validation.status,
                audit_reference=audit_reference,
                snapshot_reference="planned",
                timestamp=format_utc_iso(datetime.now(UTC)),
                warnings=validation.warnings,
            )

        existing_content = self._read_existing(target.relative_path)
        self._validate_existing_managed_content(
            existing_content,
            target_path=target.relative_path,
            command=command,
        )
        prepared = self._prepare_target_content(
            target,
            existing_content=existing_content,
            instruction_blocks=self._instruction_blocks_for(command),
            command=command,
        )
        drift_content = self._drift_content(
            existing_content=existing_content,
            final_content=prepared.final_content,
            apply=command.apply,
        )
        drift_warnings = self._drift_warnings(host, target, drift_content)
        warnings = prepared.warnings + drift_warnings

        include_agents_ref = False
        instruction_targets = [target.name.value]
        if host.name == HostName.claude_code and any("AGENTS.md" in w for w in warnings):
            include_agents_ref = True
            instruction_targets.append(InstructionTargetType.agents_md.value)

        planned_changes = self._planned_changes(
            target,
            existing_content=existing_content,
            final_content=prepared.final_content,
            canonical_documents=prepared.canonical_documents,
            include_agents_ref=include_agents_ref,
        )

        audit_reference, snapshot_reference = self._audit_and_snapshot_references(
            command,
            target=target,
            prepared=prepared,
            include_agents_ref=include_agents_ref,
        )

        manual_steps = []
        if warnings:
            manual_steps.append("Remova a duplicacao manualmente antes de aplicar setup.")

        return ConfigureHostResult(
            host_id=host.name.value,
            instruction_targets=instruction_targets,
            planned_changes=planned_changes,
            manual_steps=manual_steps,
            validation_status="success",
            audit_reference=audit_reference,
            snapshot_reference=snapshot_reference,
            timestamp=format_utc_iso(datetime.now(UTC)),
            warnings=warnings,
        )

    def _validate_host_read(
        self,
        host: Host,
        target: InstructionTarget,
    ) -> HostReadValidationResult:
        method = host.read_validation_method
        checks = {
            "instruction_file_exists": False,
            "instruction_file_readable": False,
            "managed_block_has_valid_delimiters": False,
            "managed_block_has_content": False,
            "managed_block_has_mcp_reference": False,
            "mcp_configuration_documented_or_active": False,
        }
        failures: list[str] = []

        path = (self.project_root / target.relative_path).resolve()
        project_root_resolved = self.project_root.resolve()
        try:
            path.relative_to(project_root_resolved)
        except ValueError:
            failures.append("Falha de Arquivo de Instrução: caminho fora do projeto.")
            return self._host_read_validation_result(method, checks, failures)

        if not path.exists() or not path.is_file():
            failures.append(f"Falha de Arquivo de Instrução: {target.relative_path} ausente.")
            return self._host_read_validation_result(method, checks, failures)

        checks["instruction_file_exists"] = True

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(
                f"Falha de Permissão de Leitura ou Escrita: não foi possível ler "
                f"{target.relative_path}: {exc}"
            )
            return self._host_read_validation_result(method, checks, failures)

        checks["instruction_file_readable"] = True

        try:
            managed_block = self._extract_managed_block(
                content,
                target_path=target.relative_path,
            )
        except ValidationFailedError:
            failures.append(
                f"Falha de Arquivo de Instrução: {target.relative_path} deve conter "
                "delimitadores UMEM válidos."
            )
            return self._host_read_validation_result(method, checks, failures)

        checks["managed_block_has_valid_delimiters"] = True
        try:
            self._validate_compact_manifest(
                managed_block,
                target_path=target.relative_path,
                max_lines=DEFAULT_MAX_MANAGED_LINES,
                max_chars=DEFAULT_MAX_MANAGED_CHARS,
            )
            self._validate_no_raw_memory_dump(content, target_path=target.relative_path)
        except ValidationFailedError as exc:
            failures.append(f"Falha de Arquivo de Instrução: {exc}")

        inner_content = self._managed_block_inner_content(managed_block).strip()
        if inner_content:
            checks["managed_block_has_content"] = True
        else:
            failures.append(
                f"Falha de Arquivo de Instrução: bloco UMEM em {target.relative_path} está vazio."
            )

        if self._has_mcp_reference(inner_content):
            checks["managed_block_has_mcp_reference"] = True
            checks["mcp_configuration_documented_or_active"] = True
        else:
            failures.append(
                "Falha de Configuração MCP: bloco UMEM não referencia universal-memory, "
                "MCP/FastMCP ou comandos como umem context/status."
            )

        result = self._host_read_validation_result(method, checks, failures)

        # Combine failures and drift warnings if readable
        all_warnings = failures.copy()
        if checks["instruction_file_readable"] and host.name == HostName.claude_code:
            drift_warnings = self._drift_warnings(host, target, content)
            all_warnings.extend(drift_warnings)

        return HostReadValidationResult(
            status=result.status,
            method=result.method,
            checks=result.checks,
            failures=result.failures,
            warnings=all_warnings,
        )

    def _host_read_validation_result(
        self,
        method: str,
        checks: dict[str, bool],
        failures: list[str],
    ) -> HostReadValidationResult:
        return HostReadValidationResult(
            status="failure" if failures else "success",
            method=method,
            checks=checks,
            failures=failures,
            warnings=failures.copy(),
        )

    def _record_host_validation(
        self,
        command: ConfigureHostCommand,
        host: Host,
        validation: HostReadValidationResult,
    ) -> str:
        timestamp = datetime.now(UTC)
        audit_reference = str(uuid4())
        details = {
            "method": validation.method,
            "checks": validation.checks,
            "failures": validation.failures,
        }
        event = AuditEvent(
            id=audit_reference,
            created_at=timestamp,
            updated_at=timestamp,
            timestamp=timestamp,
            action=f"host_validation.{host.name.value}",
            scope=AuditEventScope.project,
            origin=command.origin,
            result=validation.status,
            snapshot_reference=str(uuid4()),
            audit_reference=audit_reference,
            status="logged" if validation.status == "success" else "failed",
            details=json.dumps(details, sort_keys=True),
        )
        try:
            self.safe_write_use_case.audit_log_repository.write(event)
        except (OSError, KeyError, ValueError):
            pass
        return audit_reference

    def _managed_block_inner_content(self, managed_block: str) -> str:
        start = managed_block.find(UMEM_START) + len(UMEM_START)
        end = managed_block.rfind(UMEM_END)
        return managed_block[start:end]

    def _has_mcp_reference(self, content: str) -> bool:
        normalized = content.lower()
        references = (
            "universal-memory",
            "umem context",
            "umem status",
            "mcp",
            "fastmcp",
        )
        return any(reference in normalized for reference in references)

    def _validate_existing_managed_content(
        self,
        existing_content: str,
        *,
        target_path: str,
        command: ConfigureHostCommand,
    ) -> None:
        if not existing_content:
            return
        has_managed_block = UMEM_START in existing_content and UMEM_END in existing_content
        if not has_managed_block:
            return
        try:
            self._validate_compact_manifest(
                self._extract_managed_block(existing_content, target_path=target_path),
                target_path=target_path,
                max_lines=command.max_managed_lines,
                max_chars=command.max_managed_chars,
            )
            self._validate_no_raw_memory_dump(existing_content, target_path=target_path)
        except ValidationFailedError:
            if not command.apply:
                raise

    def _instruction_blocks_for(self, command: ConfigureHostCommand) -> list[InstructionBlock]:
        if command.instruction_blocks or self.fact_repository is None:
            return command.instruction_blocks

        instruction_blocks: list[InstructionBlock] = []
        for fact in self.fact_repository.list(status=FactStatus.active):
            classification = InstructionClassification.shared_policy
            tags = fact.tags or []
            for candidate in InstructionClassification:
                if candidate.value in tags or candidate.value.replace("_", "-") in tags:
                    classification = candidate
                    break
            title = fact.metadata.get("title") if fact.metadata else None
            instruction_blocks.append(
                InstructionBlock(
                    title=title or f"Fato {fact.id[:8]}",
                    content=fact.content,
                    classification=classification,
                )
            )
        return instruction_blocks

    def _prepare_target_content(
        self,
        target: InstructionTarget,
        *,
        existing_content: str,
        instruction_blocks: list[InstructionBlock],
        command: ConfigureHostCommand,
    ) -> PreparedInstructionTarget:
        partition = partition_instruction_blocks(instruction_blocks)
        shared_manifest_available = True
        if target.name == InstructionTargetType.claude_md:
            shared_manifest_available = self._shared_manifest_available(command)

        supported = set(getattr(c, "value", c) for c in target.supported_classifications)
        if target.name == InstructionTargetType.claude_md and not shared_manifest_available:
            supported.add(InstructionClassification.shared_policy.value)
        warnings = []
        for block in instruction_blocks:
            classification_val = getattr(block.classification, "value", block.classification)
            target_name_val = getattr(target.name, "value", target.name)
            if classification_val not in supported:
                warnings.append(
                    f"Instrucao '{block.title}' com classificacao '{classification_val}' "
                    f"foi ignorada pois nao e suportada pelo target {target_name_val}."
                )

        canonical_documents: list[CanonicalDocument] = []
        if target.name == InstructionTargetType.claude_md:
            if partition.canonical_documents:
                raise ValidationFailedError("Host Claude Code nao suporta documentos canonicos.")
            managed_content = self._render_claude_managed_block(
                self._target_manifest_blocks(
                    partition,
                    target,
                    include_shared_policy=not shared_manifest_available,
                ),
                shared_manifest_available=shared_manifest_available,
            )
        else:
            canonical_documents = partition.canonical_documents
            managed_content = self._render_managed_block(partition)

        self._validate_compact_manifest(
            managed_content,
            target_path=target.relative_path,
            max_lines=command.max_managed_lines,
            max_chars=command.max_managed_chars,
        )
        final_content = self._merge_managed_block(existing_content, managed_content)
        self._validate_compact_manifest(
            self._extract_managed_block(final_content, target_path=target.relative_path),
            target_path=target.relative_path,
            max_lines=command.max_managed_lines,
            max_chars=command.max_managed_chars,
        )
        self._validate_no_raw_memory_dump(final_content, target_path=target.relative_path)
        return PreparedInstructionTarget(
            final_content=final_content,
            canonical_documents=canonical_documents,
            warnings=warnings,
        )

    def _shared_manifest_available(self, command: ConfigureHostCommand) -> bool:
        if command.shared_manifest_available is not None:
            return command.shared_manifest_available
        return bool(self._read_existing("AGENTS.md"))

    def _drift_content(
        self,
        *,
        existing_content: str,
        final_content: str,
        apply: bool,
    ) -> str:
        if not apply and "- (" not in final_content and existing_content:
            return existing_content
        return final_content

    def _audit_and_snapshot_references(
        self,
        command: ConfigureHostCommand,
        *,
        target: InstructionTarget,
        prepared: PreparedInstructionTarget,
        include_agents_ref: bool = False,
    ) -> tuple[str, str]:
        if not command.apply:
            return "not-applied", "planned"

        audit_refs: list[str] = []
        snapshot_refs: list[str] = []
        for document in prepared.canonical_documents:
            result = self.safe_write_use_case.execute(
                SafeWriteCommand(
                    relative_path=document.relative_path,
                    content=self._render_canonical_document(document),
                    scope=AuditEventScope.project,
                    origin=command.origin,
                    action="host_setup.canonical_doc",
                )
            )
            audit_refs.append(result.audit_reference)
            snapshot_refs.append(result.snapshot_reference)

        if include_agents_ref:
            agents_target = self._instruction_target_for(None, InstructionTargetType.agents_md)
            result = self.safe_write_use_case.execute(
                SafeWriteCommand(
                    relative_path=agents_target.relative_path,
                    content=self._read_existing(agents_target.relative_path),
                    scope=AuditEventScope.project,
                    origin=command.origin,
                    action="host_setup.agents_md_reference",
                )
            )
            audit_refs.append(result.audit_reference)
            snapshot_refs.append(result.snapshot_reference)

        result = self.safe_write_use_case.execute(
            SafeWriteCommand(
                relative_path=target.relative_path,
                content=prepared.final_content,
                scope=AuditEventScope.project,
                origin=command.origin,
                action=f"host_setup.{target.name.value}",
            )
        )
        audit_refs.append(result.audit_reference)
        snapshot_refs.append(result.snapshot_reference)
        return ", ".join(audit_refs), ", ".join(snapshot_refs)

    def _drift_warnings(
        self,
        host: Host,
        target: InstructionTarget,
        final_content: str,
    ) -> list[str]:
        if host.name != HostName.claude_code or target.name != InstructionTargetType.claude_md:
            return []
        agents_target = self._instruction_target_for(None, InstructionTargetType.agents_md)
        try:
            agents_content = self._read_existing(agents_target.relative_path)
        except (OSError, UnicodeDecodeError, ValueError, ValidationFailedError):
            return []
        if not agents_content:
            return []
        return InstructionDriftDetector().detect(
            agents_content=agents_content,
            claude_content=final_content,
        )

    def _primary_target_for(self, host: Host) -> InstructionTarget:
        return self._instruction_target_for(host, host.supported_targets[0])

    def _host_for(self, host_id: str) -> Host:
        try:
            host_name = HostName(host_id)
        except ValueError as exc:
            raise ValidationFailedError(f"Host nao suportado: {host_id}") from exc
        timestamp = datetime.now(UTC)
        if host_name == HostName.claude_code:
            return Host(
                id=str(uuid4()),
                created_at=timestamp,
                updated_at=timestamp,
                name=HostName.claude_code,
                supported_targets=[InstructionTargetType.claude_md],
                mcp_config_method="fastmcp",
                read_validation_method="claude_md_delta_validator",
                write_validation_method="safe_write_use_case",
                rollback_behavior="snapshot_rollback",
                audit_event_type="host_setup",
            )
        elif host_name == HostName.codex:
            return Host(
                id=str(uuid4()),
                created_at=timestamp,
                updated_at=timestamp,
                name=HostName.codex,
                supported_targets=[InstructionTargetType.agents_md],
                mcp_config_method="fastmcp",
                read_validation_method="agents_md_compact_validator",
                write_validation_method="safe_write_use_case",
                rollback_behavior="snapshot_rollback",
                audit_event_type="host_setup",
            )
        else:
            raise ValidationFailedError(f"Host ainda nao suportado para setup: {host_id}")

    def _agents_md_target(self, host: Host) -> InstructionTarget:
        return self._instruction_target_for(host, InstructionTargetType.agents_md)

    def _instruction_target_for(
        self,
        host: Host | None,
        target_type: InstructionTargetType,
    ) -> InstructionTarget:
        if host is not None and target_type not in host.supported_targets:
            raise ValidationFailedError(f"Host {host.name.value} nao suporta {target_type.value}")
        timestamp = datetime.now(UTC)
        if target_type == InstructionTargetType.claude_md:
            return InstructionTarget(
                id=str(uuid4()),
                created_at=timestamp,
                updated_at=timestamp,
                name=InstructionTargetType.claude_md,
                relative_path="CLAUDE.md",
                ownership=InstructionTargetOwnership.delta_consumer,
                supported_classifications=[
                    InstructionClassification.provider_delta,
                    InstructionClassification.scoped_rule,
                ],
            )
        elif target_type == InstructionTargetType.agents_md:
            return InstructionTarget(
                id=str(uuid4()),
                created_at=timestamp,
                updated_at=timestamp,
                name=InstructionTargetType.agents_md,
                relative_path="AGENTS.md",
                ownership=InstructionTargetOwnership.single_writer,
                supported_classifications=[
                    InstructionClassification.shared_policy,
                    InstructionClassification.provider_delta,
                    InstructionClassification.scoped_rule,
                    InstructionClassification.canonical_doc,
                ],
            )
        else:
            raise ValidationFailedError(f"Target nao suportado: {target_type.value}")

    def _read_existing(self, relative_path: str) -> str:
        path = (self.project_root / relative_path).resolve()
        if not path.exists():
            return ""
        if not path.is_file():
            raise ValidationFailedError(f"Caminho alvo nao e arquivo: {relative_path}")
        try:
            path.relative_to(self.project_root)
        except ValueError as exc:
            raise ValidationFailedError(
                "Caminho fora do diretorio do projeto nao permitido."
            ) from exc
        return path.read_text(encoding="utf-8")

    def _render_managed_block(self, partition: InstructionPartition) -> str:
        lines = [
            UMEM_START,
            "# Universal Memory Active Policy",
            "> [!IMPORTANT]",
            "> `umem` is this project's operational memory. Before planning, editing, "
            "investigating, or reviewing, load memory with `umem status --format json`, "
            "`umem context --scope project --format json`, and "
            "`umem skills list --format json`, or use the equivalent MCP/FastMCP tools.",
            "> Read and follow `.umem/skills/use-universal-memory/SKILL.md`. If a relevant "
            "active skill exists, inspect it with "
            "`umem skills detail <skill-id-or-name> --format json` before acting.",
            "> When recording learnings, use `--scope global` for durable user preferences "
            "across projects and `--scope project` for decisions, commands, and context for "
            "this repository. Never record secrets, large dumps, or uncertain facts.",
            "",
            "## Required Bootstrap",
            "- Run `umem status --format json` to validate the integration.",
            "- Run `umem context --scope project --format json` and treat the result as "
            "active context.",
            "- Run `umem skills list --format json`; for each relevant skill, run "
            "`umem skills detail <skill-id-or-name> --format json`.",
            "- If MCP/FastMCP is available, prefer the equivalent tools; otherwise, use the "
            "CLI commands above.",
            "- Keep `AGENTS.md` and `CLAUDE.md` compact: they should point to `umem`, not "
            "store memory dumps.",
            "",
            "## Consolidated Operational Rules",
        ]
        if partition.manifest_blocks:
            for block in partition.manifest_blocks:
                lines_content = block.content.splitlines()
                if lines_content:
                    lines.append(f"- ({block.classification.value}) {lines_content[0]}")
                    for subline in lines_content[1:]:
                        lines.append(f"  {subline}")
        else:
            lines.append("- Use `umem context` to retrieve active rules on demand.")

        lines.extend(["", "## Canonical Pointers"])
        if partition.pointer_lines:
            lines.extend(partition.pointer_lines)
        else:
            lines.append("- No additional canonical document registered.")
        lines.append(UMEM_END)
        return "\n".join(lines) + "\n"

    def _render_claude_managed_block(
        self,
        blocks: list[ManifestInstruction],
        *,
        shared_manifest_available: bool,
    ) -> str:
        if shared_manifest_available:
            title = "# Claude Delta Instructions"
            scope_line = (
                "> Read `AGENTS.md` as the shared manifest. This file contains only "
                "Claude Code-specific deltas, but `umem` usage remains required."
            )
            memory_line = (
                "> Before planning, editing, investigating, or reviewing, load `umem` with "
                "`umem status --format json`, `umem context --scope project --format json` "
                "and `umem skills list --format json`, or use the equivalent MCP/FastMCP "
                "tools."
            )
            policy_line = (
                "> Read and follow `.umem/skills/use-universal-memory/SKILL.md`. If a "
                "relevant active skill exists, inspect it with "
                "`umem skills detail <skill-id-or-name> --format json` before acting."
            )
            section_title = "## Provider Deltas"
            empty_line = "- No Claude Code-specific delta registered."
        else:
            title = "# Claude Code Universal Memory Instructions"
            scope_line = (
                "> Use this file as Claude Code's operational reference for this project. "
                "It consolidates how to retrieve context, apply active rules, and record "
                "learnings when `AGENTS.md` does not exist yet."
            )
            memory_line = (
                "> Before planning, editing, investigating, or reviewing, load `umem` with "
                "`umem status --format json`, `umem context --scope project --format json` "
                "and `umem skills list --format json`, or use the equivalent MCP/FastMCP "
                "tools."
            )
            policy_line = (
                "> Read and follow `.umem/skills/use-universal-memory/SKILL.md`. If a "
                "relevant active skill exists, inspect it with "
                "`umem skills detail <skill-id-or-name> --format json` before acting."
            )
            section_title = "## Operational Rules"
            empty_line = (
                "- No consolidated rule registered; use `umem context --scope project` to "
                "retrieve context on demand."
            )
        lines = [
            UMEM_START,
            title,
            scope_line,
            memory_line,
            policy_line,
            "",
        ]

        if not shared_manifest_available:
            lines.extend(
                [
                    "## Standard Flow",
                    "- Run `umem status --format json` to validate the integration.",
                    "- Run `umem context --scope project --format json` and treat the result "
                    "as active context.",
                    "- Run `umem skills list --format json`; for each relevant skill, run "
                    "`umem skills detail <skill-id-or-name> --format json`.",
                    "- When you find a durable user preference, record it as global memory; "
                    "when you find a repository decision or detail, record it as project "
                    "memory.",
                    "- Preserve manual content outside the UMEM block and keep this block "
                    "compact, pointing to external documents when guidance grows long.",
                    "",
                ]
            )

        lines.append(section_title)

        if blocks:
            for block in blocks:
                lines_content = block.content.splitlines()
                if lines_content:
                    lines.append(f"- ({block.classification.value}) {lines_content[0]}")
                    for subline in lines_content[1:]:
                        lines.append(f"  {subline}")
        else:
            lines.append(empty_line)
        lines.append(UMEM_END)
        return "\n".join(lines) + "\n"

    def _target_manifest_blocks(
        self,
        partition: InstructionPartition,
        target: InstructionTarget,
        *,
        include_shared_policy: bool = False,
    ) -> list[ManifestInstruction]:
        supported = set(target.supported_classifications)
        if include_shared_policy:
            supported.add(InstructionClassification.shared_policy)
        return [block for block in partition.manifest_blocks if block.classification in supported]

    def _render_canonical_document(self, document: CanonicalDocument) -> str:
        return f"# {document.title}\n\n{document.content}\n"

    def _merge_managed_block(self, existing_content: str, managed_content: str) -> str:
        if not existing_content.strip():
            return managed_content
        start = existing_content.find(UMEM_START)
        end = existing_content.find(UMEM_END)
        if start != -1:
            if end != -1 and end > start:
                end += len(UMEM_END)
                suffix_start = end
                if existing_content[end : end + 2] == "\r\n":
                    suffix_start = end + 2
                elif existing_content[end : end + 1] == "\n":
                    suffix_start = end + 1
                return existing_content[:start] + managed_content + existing_content[suffix_start:]
            else:
                return existing_content[:start] + managed_content

        separator = "" if existing_content.endswith("\n") else "\n"
        return f"{existing_content}{separator}\n{managed_content}"

    def _extract_managed_block(self, content: str, target_path: str = "AGENTS.md") -> str:
        start = content.find(UMEM_START)
        end = content.find(UMEM_END)
        if start == -1 or end == -1 or end <= start:
            raise ValidationFailedError(f"{target_path} deve conter delimitadores UMEM validos.")
        return content[start : end + len(UMEM_END)]

    def _validate_compact_manifest(
        self,
        content: str,
        *,
        target_path: str = "AGENTS.md",
        max_lines: int,
        max_chars: int,
    ) -> None:
        lines_count = len(content.splitlines())
        chars_count = len(content)
        if chars_count > max_chars or lines_count > max_lines:
            raise ValidationFailedError(
                f"Manifesto {target_path} deve permanecer compacto; mova conteudo longo para docs/."
            )

    def _validate_no_raw_memory_dump(self, content: str, *, target_path: str = "AGENTS.md") -> None:
        managed = self._extract_managed_block(content, target_path=target_path)

        # Avoid false positives by targeting JSON-like formatting of fact attributes
        json_fact_hits = len(re.findall(r'"fact_id"\s*:', managed)) + len(
            re.findall(r'"source_fact_ids"\s*:', managed)
        )
        if json_fact_hits >= 2:  # noqa: PLR2004
            raise ValidationFailedError(
                f"Manifesto {target_path} deve permanecer compacto e nao pode conter dump bruto "
                "de fatos ou memorias."
            )

        raw_fact_hits = len(re.findall(r"\b(?:raw memory fact|fact_id|source_fact_ids)\b", managed))
        if raw_fact_hits >= 5:  # noqa: PLR2004
            raise ValidationFailedError(
                f"Manifesto {target_path} deve permanecer compacto e nao pode conter dump bruto "
                "de fatos ou memorias."
            )

    def _planned_changes(
        self,
        target: InstructionTarget,
        *,
        existing_content: str,
        final_content: str,
        canonical_documents: list[CanonicalDocument],
        include_agents_ref: bool = False,
    ) -> list[dict[str, str]]:
        changes: list[dict[str, str]] = []
        for document in canonical_documents:
            document_path = self.project_root / document.relative_path
            changes.append(
                {
                    "target": "canonical_doc",
                    "action": "update" if document_path.exists() else "create",
                    "path": document.relative_path,
                }
            )
        if existing_content != final_content:
            target_name_val = getattr(target.name, "value", target.name)
            changes.append(
                {
                    "target": target_name_val,
                    "action": "update" if existing_content else "create",
                    "path": target.relative_path,
                }
            )
        if include_agents_ref:
            changes.append(
                {
                    "target": "agents_md",
                    "action": "reference",
                    "path": "AGENTS.md",
                }
            )
        return changes

    # --- Public API wrappers to avoid private coupling ---
    def host_for(self, host_id: str) -> Host:
        return self._host_for(host_id)

    def primary_target_for(self, host: Host) -> InstructionTarget:
        return self._primary_target_for(host)

    def read_existing(self, relative_path: str) -> str:
        return self._read_existing(relative_path)

    def validate_existing_managed_content(
        self, content: str, target_path: str, command: ConfigureHostCommand
    ) -> None:
        return self._validate_existing_managed_content(
            content,
            target_path=target_path,
            command=command,
        )

    def prepare_target_content(
        self,
        target: InstructionTarget,
        existing_content: str,
        instruction_blocks: list[InstructionBlock],
        command: ConfigureHostCommand,
    ) -> PreparedInstructionTarget:
        return self._prepare_target_content(
            target,
            existing_content=existing_content,
            instruction_blocks=instruction_blocks,
            command=command,
        )

    def planned_changes(
        self,
        target: InstructionTarget,
        existing_content: str,
        final_content: str,
        canonical_documents: list[CanonicalDocument],
    ) -> list[dict[str, str]]:
        return self._planned_changes(
            target,
            existing_content=existing_content,
            final_content=final_content,
            canonical_documents=canonical_documents,
        )

    def render_canonical_document(self, document: CanonicalDocument) -> str:
        return self._render_canonical_document(document)

    def drift_content(self, existing: str, final: str, apply: bool) -> str | None:
        return self._drift_content(
            existing_content=existing,
            final_content=final,
            apply=apply,
        )

    def drift_warnings(
        self,
        host: Host,
        target: InstructionTarget,
        drift_content: str | None,
    ) -> list[str]:
        return self._drift_warnings(host, target, drift_content or "")


def _canonical_doc_path(title: str, docs_directory: str) -> str:
    directory = _safe_relative_path(docs_directory)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "canonical-doc"
    return f"{directory}/{slug}.md"


def _safe_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    if ":" in normalized or normalized.startswith("/") or not normalized:
        raise ValidationFailedError("Caminho relativo invalido.")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValidationFailedError("Caminho relativo invalido.")
    return path.as_posix()
