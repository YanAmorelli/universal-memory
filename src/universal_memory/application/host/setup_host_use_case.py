from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal
from uuid import uuid4

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import (
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
    instruction_blocks: list[InstructionBlock] = field(default_factory=list)
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

    def to_payload(self) -> dict[str, Any]:
        return {
            "host_id": self.host_id,
            "instruction_targets": self.instruction_targets,
            "planned_changes": self.planned_changes,
            "manual_steps": self.manual_steps,
            "validation_status": self.validation_status,
            "audit_reference": self.audit_reference,
        }


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
        target = self._agents_md_target(host)
        existing_content = self._read_existing(target.relative_path)
        if existing_content and UMEM_START in existing_content and UMEM_END in existing_content:
            if not command.apply:
                self._validate_compact_manifest(
                    self._extract_managed_block(existing_content),
                    max_lines=command.max_managed_lines,
                    max_chars=command.max_managed_chars,
                )
                self._validate_no_raw_memory_dump(existing_content)
            else:
                try:
                    self._validate_compact_manifest(
                        self._extract_managed_block(existing_content),
                        max_lines=command.max_managed_lines,
                        max_chars=command.max_managed_chars,
                    )
                    self._validate_no_raw_memory_dump(existing_content)
                except ValidationFailedError:
                    pass

        instruction_blocks = command.instruction_blocks
        if not instruction_blocks and self.fact_repository is not None:
            active_facts = self.fact_repository.list(status=FactStatus.active)
            instruction_blocks = []
            for fact in active_facts:
                classification = "shared_policy"
                for c in ["shared_policy", "provider_delta", "scoped_rule", "canonical_doc"]:
                    if c in fact.tags or c.replace("_", "-") in fact.tags:
                        classification = c
                        break
                title = fact.metadata.get("title") if fact.metadata else None
                if not title:
                    title = f"Fato {fact.id[:8]}"
                instruction_blocks.append(
                    InstructionBlock(
                        title=title,
                        content=fact.content,
                        classification=classification,
                    )
                )

        partition = partition_instruction_blocks(instruction_blocks)
        managed_content = self._render_managed_block(partition)
        self._validate_compact_manifest(
            managed_content,
            max_lines=command.max_managed_lines,
            max_chars=command.max_managed_chars,
        )
        final_content = self._merge_managed_block(existing_content, managed_content)
        self._validate_compact_manifest(
            self._extract_managed_block(final_content),
            max_lines=command.max_managed_lines,
            max_chars=command.max_managed_chars,
        )
        self._validate_no_raw_memory_dump(final_content)

        planned_changes = self._planned_changes(
            target.relative_path,
            existing_content=existing_content,
            final_content=final_content,
            canonical_documents=partition.canonical_documents,
        )

        audit_reference = "not-applied"
        snapshot_reference = "planned"
        if command.apply:
            audit_refs = []
            snapshot_refs = []
            for document in partition.canonical_documents:
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

            result = self.safe_write_use_case.execute(
                SafeWriteCommand(
                    relative_path=target.relative_path,
                    content=final_content,
                    scope=AuditEventScope.project,
                    origin=command.origin,
                    action="host_setup.agents_md",
                )
            )
            audit_refs.append(result.audit_reference)
            snapshot_refs.append(result.snapshot_reference)
            audit_reference = ", ".join(audit_refs)
            snapshot_reference = ", ".join(snapshot_refs)

        return ConfigureHostResult(
            host_id=host.name.value,
            instruction_targets=[target.name.value],
            planned_changes=planned_changes,
            manual_steps=[],
            validation_status="success",
            audit_reference=audit_reference,
            snapshot_reference=snapshot_reference,
            timestamp=format_utc_iso(datetime.now(UTC)),
        )

    def _host_for(self, host_id: str) -> Host:
        try:
            host_name = HostName(host_id)
        except ValueError as exc:
            raise ValidationFailedError(f"Host nao suportado: {host_id}") from exc
        if host_name != HostName.codex:
            raise ValidationFailedError(f"Host ainda nao suportado para setup: {host_id}")
        timestamp = datetime.now(UTC)
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

    def _agents_md_target(self, host: Host) -> InstructionTarget:
        if InstructionTargetType.agents_md not in host.supported_targets:
            raise ValidationFailedError("Host codex nao suporta AGENTS.md")
        timestamp = datetime.now(UTC)
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
            "> Antes de iniciar qualquer tarefa de codificação, consulte a Short Term Memory "
            "deste repositório executando a CLI `umem context` ou usando as ferramentas MCP "
            "correspondentes.",
            "",
            "## Regras Operacionais Consolidadas",
        ]
        if partition.manifest_blocks:
            for block in partition.manifest_blocks:
                lines_content = block.content.splitlines()
                if lines_content:
                    lines.append(f"- ({block.classification.value}) {lines_content[0]}")
                    for subline in lines_content[1:]:
                        lines.append(f"  {subline}")
        else:
            lines.append("- Consulte `umem context` para recuperar regras ativas sob demanda.")

        lines.extend(["", "## Ponteiros Canônicos"])
        if partition.pointer_lines:
            lines.extend(partition.pointer_lines)
        else:
            lines.append("- Nenhum documento canônico adicional registrado.")
        lines.append(UMEM_END)
        return "\n".join(lines) + "\n"

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

    def _extract_managed_block(self, content: str) -> str:
        start = content.find(UMEM_START)
        end = content.find(UMEM_END)
        if start == -1 or end == -1 or end <= start:
            raise ValidationFailedError("AGENTS.md deve conter delimitadores UMEM validos.")
        return content[start : end + len(UMEM_END)]

    def _validate_compact_manifest(self, content: str, *, max_lines: int, max_chars: int) -> None:
        if len(content) > max_chars or len(content.splitlines()) > max_lines:
            raise ValidationFailedError(
                "Manifesto AGENTS.md deve permanecer compacto; mova conteudo longo para docs/."
            )

    def _validate_no_raw_memory_dump(self, content: str) -> None:
        managed = self._extract_managed_block(content)

        # Avoid false positives by targeting JSON-like formatting of fact attributes
        json_fact_hits = len(re.findall(r'"fact_id"\s*:', managed)) + len(
            re.findall(r'"source_fact_ids"\s*:', managed)
        )
        if json_fact_hits >= 2:  # noqa: PLR2004
            raise ValidationFailedError(
                "Manifesto AGENTS.md deve permanecer compacto e nao pode conter dump bruto "
                "de fatos ou memorias."
            )

        raw_fact_hits = len(re.findall(r"\b(?:raw memory fact|fact_id|source_fact_ids)\b", managed))
        if raw_fact_hits >= 5:  # noqa: PLR2004
            raise ValidationFailedError(
                "Manifesto AGENTS.md deve permanecer compacto e nao pode conter dump bruto "
                "de fatos ou memorias."
            )

    def _planned_changes(
        self,
        target_path: str,
        *,
        existing_content: str,
        final_content: str,
        canonical_documents: list[CanonicalDocument],
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
            changes.append(
                {
                    "target": "agents_md",
                    "action": "update" if existing_content else "create",
                    "path": target_path,
                }
            )
        return changes


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
