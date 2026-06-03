import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from universal_memory.domain.entities.audit_event import AuditEvent, AuditEventScope
from universal_memory.domain.entities.context_summary import ContextSummary, ContextSummaryScope
from universal_memory.domain.entities.fact import Fact, FactScope, FactStatus
from universal_memory.domain.entities.latent_skill import (
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
)
from universal_memory.domain.entities.rule import Rule, RuleScope, RuleStatus
from universal_memory.domain.entities.snapshot import Snapshot, SnapshotScope, SnapshotStatus

LATENT_SKILL_RECURRENCE_COUNT = 3
SHA256_DIGEST = "a" * 64


def utc_now() -> datetime:
    return datetime.now(UTC)


def base_entity_data() -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": 1,
        "id": str(uuid.uuid4()),
        "created_at": now,
        "updated_at": now,
    }


def fact_data() -> dict[str, Any]:
    return {
        **base_entity_data(),
        "content": "Priorizar TDD para endpoints de autenticação",
        "scope": FactScope.project,
        "source": "user_explicit",
        "status": FactStatus.active,
        "recurrence_count": 0,
        "tags": ["auth", "tdd"],
        "metadata": {"priority": "high"},
    }


def test_fact_valid_creation() -> None:
    data = fact_data()

    fact = Fact.model_validate(data)

    assert fact.schema_version == 1
    assert fact.id == data["id"]
    assert fact.content == "Priorizar TDD para endpoints de autenticação"
    assert fact.scope == FactScope.project
    assert fact.status == FactStatus.active
    assert fact.recurrence_count == 0
    assert fact.tags == ["auth", "tdd"]
    assert fact.metadata == {"priority": "high"}


def test_fact_rejects_invalid_uuid() -> None:
    data = fact_data() | {"id": "not-a-uuid"}

    with pytest.raises(ValidationError):
        Fact.model_validate(data)


def test_fact_rejects_non_canonical_schema_version() -> None:
    data = fact_data() | {"schema_version": 2}

    with pytest.raises(ValidationError):
        Fact.model_validate(data)


def test_fact_rejects_non_utc_timestamps() -> None:
    data = fact_data() | {"created_at": datetime.now()}

    with pytest.raises(ValidationError):
        Fact.model_validate(data)


def test_fact_rejects_negative_recurrence_count() -> None:
    data = fact_data() | {"recurrence_count": -1}

    with pytest.raises(ValidationError):
        Fact.model_validate(data)


def test_fact_lifecycle_states() -> None:
    for status in [FactStatus.active, FactStatus.stale, FactStatus.archived, FactStatus.purged]:
        fact = Fact.model_validate(fact_data() | {"status": status})

        assert fact.status == status


def test_rule_creation() -> None:
    rule = Rule.model_validate(
        {
            **base_entity_data(),
            "name": "Regra TOML",
            "content": "Preferir tomllib para TOML",
            "scope": RuleScope.project,
            "status": RuleStatus.active,
            "metadata": {"reason": "recorrência"},
        }
    )

    assert rule.schema_version == 1
    assert rule.scope == RuleScope.project
    assert rule.status == RuleStatus.active


def test_latent_skill_creation() -> None:
    skill = LatentSkill.model_validate(
        {
            **base_entity_data(),
            "name": "generate-sdd-spec",
            "description": "Gera especificações SDD antes do código",
            "scope": LatentSkillScope.project,
            "status": LatentSkillStatus.proposed,
            "recurrence_count": LATENT_SKILL_RECURRENCE_COUNT,
            "metadata": {"last_detected": utc_now().isoformat()},
        }
    )

    assert skill.schema_version == 1
    assert skill.name == "generate-sdd-spec"
    assert skill.recurrence_count == LATENT_SKILL_RECURRENCE_COUNT
    assert skill.status == LatentSkillStatus.proposed


def test_latent_skill_rejects_negative_recurrence_count() -> None:
    with pytest.raises(ValidationError):
        LatentSkill.model_validate(
            {
                **base_entity_data(),
                "name": "generate-sdd-spec",
                "description": "Gera especificações SDD antes do código",
                "scope": LatentSkillScope.project,
                "status": LatentSkillStatus.proposed,
                "recurrence_count": -1,
            }
        )


def snapshot_data() -> dict[str, Any]:
    return {
        **base_entity_data(),
        "timestamp": utc_now(),
        "scope": SnapshotScope.project,
        "action": "remember_fact",
        "relative_path": ".umem/memory/facts.json",
        "hash": SHA256_DIGEST,
        "status": SnapshotStatus.created,
    }


def test_snapshot_creation() -> None:
    snapshot = Snapshot.model_validate(snapshot_data())

    assert snapshot.schema_version == 1
    assert snapshot.hash == SHA256_DIGEST
    assert snapshot.action == "remember_fact"


def test_snapshot_rejects_invalid_sha256_hash() -> None:
    data = snapshot_data() | {"hash": "sha256_hash_value_here"}

    with pytest.raises(ValidationError):
        Snapshot.model_validate(data)


def test_snapshot_rejects_unsafe_relative_path() -> None:
    data = snapshot_data() | {"relative_path": "../outside.json"}

    with pytest.raises(ValidationError):
        Snapshot.model_validate(data)


def test_snapshot_rejects_non_utc_timestamp() -> None:
    non_utc = datetime.now(timezone(timedelta(hours=-3)))
    data = snapshot_data() | {"timestamp": non_utc}

    with pytest.raises(ValidationError):
        Snapshot.model_validate(data)


def test_audit_event_creation() -> None:
    event_id = str(uuid.uuid4())
    event = AuditEvent.model_validate(
        {
            **base_entity_data(),
            "timestamp": utc_now(),
            "action": "remember_fact",
            "scope": AuditEventScope.project,
            "origin": "cli",
            "result": "success",
            "snapshot_reference": str(uuid.uuid4()),
            "audit_reference": event_id,
            "status": "logged",
        }
    )

    assert event.schema_version == 1
    assert event.action == "remember_fact"
    assert event.audit_reference == event_id


def test_audit_event_rejects_invalid_references() -> None:
    with pytest.raises(ValidationError):
        AuditEvent.model_validate(
            {
                **base_entity_data(),
                "timestamp": utc_now(),
                "action": "remember_fact",
                "scope": AuditEventScope.project,
                "origin": "cli",
                "result": "success",
                "snapshot_reference": "snapshot-uuid-here",
                "audit_reference": str(uuid.uuid4()),
                "status": "logged",
            }
        )


def test_context_summary_creation() -> None:
    audit_id = str(uuid.uuid4())
    summary = ContextSummary.model_validate(
        {
            **base_entity_data(),
            "project_summary": "Yan está usando TDD",
            "universal_preferences": "Preferir tomllib",
            "active_rules": "Regra TOML ativa",
            "audit_reference": audit_id,
            "status": "generated",
            "scope": ContextSummaryScope.project,
        }
    )

    assert summary.schema_version == 1
    assert summary.project_summary == "Yan está usando TDD"
    assert summary.audit_reference == audit_id


def test_context_summary_rejects_invalid_audit_reference() -> None:
    with pytest.raises(ValidationError):
        ContextSummary.model_validate(
            {
                **base_entity_data(),
                "project_summary": "Yan está usando TDD",
                "universal_preferences": "Preferir tomllib",
                "active_rules": "Regra TOML ativa",
                "audit_reference": "audit-uuid-here",
                "status": "generated",
                "scope": ContextSummaryScope.project,
            }
        )
