from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from universal_memory.domain import SecretDetectedError
from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    ContextSummary,
    ContextSummaryScope,
    Fact,
    FactScope,
    FactStatus,
    Rule,
    RuleScope,
    RuleStatus,
)
from universal_memory.domain.ports import (
    AuditLogRepository,
    ContextSummaryRepository,
    FactRepository,
    RuleRepository,
    SecretScannerPort,
)

HIGH_PRIORITY_TAGS = {"preferences", "core-behavior"}
MINIMUM_TEMPLATE_SIZE = 110


@dataclass(frozen=True, slots=True)
class AssembleContextSummaryCommand:
    scope: ContextSummaryScope
    max_size_chars: int
    agent_session_key: str | None = None


@dataclass(frozen=True, slots=True)
class AssembleContextSummaryResult:
    context_summary: ContextSummary
    context_markdown: str
    included_fact_ids: list[str] = field(default_factory=list)
    audit_event: AuditEvent | None = None


@dataclass(frozen=True, slots=True)
class _SummaryItem:
    content: str
    source_id: str
    section: str
    priority: tuple[int, int, int, datetime]


@dataclass(frozen=True, slots=True)
class _AuditEventPayload:
    audit_reference: str
    timestamp: datetime
    scope: ContextSummaryScope
    result: str
    status: str
    details: dict[str, object]


class AssembleContextSummaryUseCase:
    def __init__(
        self,
        *,
        fact_repository: FactRepository,
        rule_repository: RuleRepository,
        secret_scanner: SecretScannerPort,
        audit_log_repository: AuditLogRepository,
        context_summary_repository: ContextSummaryRepository,
    ) -> None:
        self.fact_repository = fact_repository
        self.rule_repository = rule_repository
        self.secret_scanner = secret_scanner
        self.audit_log_repository = audit_log_repository
        self.context_summary_repository = context_summary_repository

    def execute(self, command: AssembleContextSummaryCommand) -> AssembleContextSummaryResult:
        if command.max_size_chars < MINIMUM_TEMPLATE_SIZE:
            raise ValueError(
                f"max_size_chars ({command.max_size_chars}) must be at least "
                f"{MINIMUM_TEMPLATE_SIZE} to accommodate the required markdown template structure."
            )

        timestamp = datetime.now(UTC)
        audit_reference = str(uuid4())
        included_fact_ids: list[str] = []
        blocked_fact_ids: list[str] = []
        blocked_rule_ids: list[str] = []

        try:
            fact_items, blocked_fact_ids = self._collect_fact_items(command.scope)
            rule_items, blocked_rule_ids = self._collect_rule_items(command.scope)
            selected_facts, selected_rules = self._select_items_within_limit(
                command.max_size_chars,
                fact_items,
                rule_items,
            )
            included_fact_ids = [item.source_id for item in selected_facts]

            project_summary = self._render_section_body(
                [item for item in selected_facts if item.section == "project_summary"]
            )
            universal_preferences = self._render_section_body(
                [item for item in selected_facts if item.section == "universal_preferences"]
            )
            active_rules = self._render_section_body(selected_rules)
            context_markdown = self._render_markdown(
                project_summary=project_summary,
                universal_preferences=universal_preferences,
                active_rules=active_rules,
            )

            audit_event = self._build_audit_event(
                _AuditEventPayload(
                    audit_reference=audit_reference,
                    timestamp=timestamp,
                    scope=command.scope,
                    result="success",
                    status="logged",
                    details={
                        "included_fact_ids": included_fact_ids,
                        "blocked_fact_ids": blocked_fact_ids,
                        "blocked_rule_ids": blocked_rule_ids,
                        "summary_origin": command.scope.value,
                        "agent_session_key": command.agent_session_key,
                        "max_size_chars": command.max_size_chars,
                        "context_size_chars": len(context_markdown),
                    },
                )
            )
            context_summary = ContextSummary(
                id=str(uuid4()),
                created_at=timestamp,
                updated_at=timestamp,
                project_summary=project_summary,
                universal_preferences=universal_preferences,
                active_rules=active_rules,
                audit_reference=audit_reference,
                status="generated",
                scope=command.scope,
            )

            self.context_summary_repository.write(context_summary)
            self.audit_log_repository.write(audit_event)
            return AssembleContextSummaryResult(
                context_summary=context_summary,
                context_markdown=context_markdown,
                included_fact_ids=included_fact_ids,
                audit_event=audit_event,
            )
        except Exception as exc:
            failure_event = self._build_audit_event(
                _AuditEventPayload(
                    audit_reference=audit_reference,
                    timestamp=timestamp,
                    scope=command.scope,
                    result="failure",
                    status="failed",
                    details={
                        "included_fact_ids": included_fact_ids,
                        "blocked_fact_ids": blocked_fact_ids,
                        "blocked_rule_ids": blocked_rule_ids,
                        "summary_origin": command.scope.value,
                        "agent_session_key": command.agent_session_key,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
            )
            self.audit_log_repository.write(failure_event)
            raise

    def _collect_fact_items(
        self,
        scope: ContextSummaryScope,
    ) -> tuple[list[_SummaryItem], list[str]]:
        active_facts = self.fact_repository.list(status=FactStatus.active)
        fact_items: list[_SummaryItem] = []
        blocked_fact_ids: list[str] = []

        for fact in active_facts:
            if not self._fact_is_relevant(fact, scope):
                continue
            try:
                self.secret_scanner.scan(fact.content, origin="assemble_context_summary.fact")
            except SecretDetectedError:
                blocked_fact_ids.append(fact.id)
                continue

            fact_items.append(
                _SummaryItem(
                    content=fact.content,
                    source_id=fact.id,
                    section=self._fact_section(fact),
                    priority=self._fact_priority(fact, scope),
                )
            )

        return sorted(fact_items, key=lambda item: item.priority, reverse=True), blocked_fact_ids

    def _collect_rule_items(
        self,
        scope: ContextSummaryScope,
    ) -> tuple[list[_SummaryItem], list[str]]:
        active_rules = self.rule_repository.list(status=RuleStatus.active)
        rule_items: list[_SummaryItem] = []
        blocked_rule_ids: list[str] = []

        for rule in active_rules:
            if not self._rule_is_relevant(rule, scope):
                continue
            try:
                self.secret_scanner.scan(rule.content, origin="assemble_context_summary.rule")
            except SecretDetectedError:
                blocked_rule_ids.append(rule.id)
                continue
            rule_items.append(
                _SummaryItem(
                    content=rule.content,
                    source_id=rule.id,
                    section="active_rules",
                    priority=self._rule_priority(rule, scope),
                )
            )

        return sorted(rule_items, key=lambda item: item.priority, reverse=True), blocked_rule_ids

    def _select_items_within_limit(
        self,
        max_size_chars: int,
        fact_items: list[_SummaryItem],
        rule_items: list[_SummaryItem],
    ) -> tuple[list[_SummaryItem], list[_SummaryItem]]:
        selected_facts: list[_SummaryItem] = []
        selected_rules: list[_SummaryItem] = []

        combined_items = sorted(
            [*fact_items, *rule_items],
            key=lambda x: x.priority,
            reverse=True,
        )

        for item in combined_items:
            candidate_facts = selected_facts.copy()
            candidate_rules = selected_rules.copy()
            if item.section == "active_rules":
                candidate_rules.append(item)
            else:
                candidate_facts.append(item)

            markdown = self._render_markdown(
                project_summary=self._render_section_body(
                    [fact for fact in candidate_facts if fact.section == "project_summary"]
                ),
                universal_preferences=self._render_section_body(
                    [fact for fact in candidate_facts if fact.section == "universal_preferences"]
                ),
                active_rules=self._render_section_body(candidate_rules),
            )
            if len(markdown) <= max_size_chars:
                selected_facts = candidate_facts
                selected_rules = candidate_rules

        return selected_facts, selected_rules

    @staticmethod
    def _fact_is_relevant(fact: Fact, scope: ContextSummaryScope) -> bool:
        if scope == ContextSummaryScope.global_:
            return fact.scope == FactScope.global_
        return fact.scope in {FactScope.project, FactScope.global_}

    @staticmethod
    def _rule_is_relevant(rule: Rule, scope: ContextSummaryScope) -> bool:
        if scope == ContextSummaryScope.global_:
            return rule.scope == RuleScope.global_
        return rule.scope in {RuleScope.project, RuleScope.global_}

    @staticmethod
    def _fact_section(fact: Fact) -> str:
        if fact.scope == FactScope.global_:
            return "universal_preferences"
        return "project_summary"

    @staticmethod
    def _fact_priority(fact: Fact, scope: ContextSummaryScope) -> tuple[int, int, int, datetime]:
        scope_score = 1 if (
            scope == ContextSummaryScope.project and fact.scope == FactScope.project
        ) else 0
        tag_score = 1 if HIGH_PRIORITY_TAGS.intersection(fact.tags) else 0
        created_at = AssembleContextSummaryUseCase._normalize_datetime(fact.created_at)
        return (scope_score, tag_score, fact.recurrence_count, created_at)

    @staticmethod
    def _rule_priority(rule: Rule, scope: ContextSummaryScope) -> tuple[int, int, int, datetime]:
        scope_score = 1 if (
            scope == ContextSummaryScope.project and rule.scope == RuleScope.project
        ) else 0
        created_at = AssembleContextSummaryUseCase._normalize_datetime(rule.created_at)
        return (scope_score, 0, 0, created_at)

    @staticmethod
    def _render_section_body(items: list[_SummaryItem]) -> str:
        return "\n".join(f"- {item.content}" for item in items)

    @staticmethod
    def _render_markdown(
        *,
        project_summary: str,
        universal_preferences: str,
        active_rules: str,
    ) -> str:
        return "\n".join(
            [
                "# MEMORY CONTEXT SUMMARY",
                "",
                "## Project Summary",
                project_summary or "- None",
                "",
                "## Universal Preferences",
                universal_preferences or "- None",
                "",
                "## Active Rules",
                active_rules or "- None",
            ]
        )

    @staticmethod
    def _build_audit_event(payload: _AuditEventPayload) -> AuditEvent:
        event_scope = (
            AuditEventScope.global_
            if payload.scope == ContextSummaryScope.global_
            else AuditEventScope.project
        )
        return AuditEvent(
            id=payload.audit_reference,
            created_at=payload.timestamp,
            updated_at=payload.timestamp,
            timestamp=payload.timestamp,
            action="assemble_context_summary",
            scope=event_scope,
            origin="application",
            result=payload.result,
            snapshot_reference=str(uuid4()),
            audit_reference=payload.audit_reference,
            status=payload.status,
            details=json.dumps(payload.details, sort_keys=True, separators=(",", ":")),
        )

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime:
        if value is None:
            return datetime.min.replace(tzinfo=UTC)
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value
