from __future__ import annotations

from typing import Any

from universal_memory.application.memory import (
    DEFAULT_CONTEXT_MAX_SIZE_CHARS,
    AssembleContextSummaryResult,
    GetMemoryStatusResult,
)
from universal_memory.application.onboarding import SessionBootstrapResult
from universal_memory.domain.entities.base import format_utc_iso

TOKEN_ESTIMATE_CHARS = 4


def status_payload(result: GetMemoryStatusResult) -> dict[str, Any]:
    if not result.initialized:
        return {
            "initialized": False,
            "project_path": result.project_path,
            "installed_version": result.installed_version,
            "recommended_action": result.recommended_action,
            "layout": result.layout,
            "shared_root": result.shared_root,
            "operational_root": result.operational_root,
            "path_counts": result.path_counts or {},
        }

    return {
        "initialized": True,
        "project_path": result.project_path,
        "installed_version": result.installed_version,
        "fact_counts": result.fact_counts,
        "active_rules_count": result.active_rules_count,
        "registered_skills_count": result.registered_skills_count,
        "approximate_size_bytes": result.approximate_size_bytes,
        "last_health_check": result.last_health_check,
        "host_validation": result.host_validation,
        "layout": result.layout,
        "shared_root": result.shared_root,
        "operational_root": result.operational_root,
        "path_counts": result.path_counts or {},
    }


def context_payload(
    result: AssembleContextSummaryResult,
    *,
    max_size_chars: int,
) -> dict[str, Any]:
    summary = result.context_summary
    markdown_size = len(result.context_markdown)
    return {
        "project_summary": summary.project_summary,
        "universal_preferences": summary.universal_preferences,
        "active_rules": summary.active_rules,
        "source_fact_ids": result.included_fact_ids,
        "truncated": markdown_size >= max_size_chars,
        "token_estimate": max(1, round(markdown_size / TOKEN_ESTIMATE_CHARS)),
        "last_read_at": format_utc_iso(summary.created_at),
    }


def session_bootstrap_payload(result: SessionBootstrapResult) -> dict[str, Any]:
    return {
        "status": status_payload(result.status),
        "context": context_payload(
            result.context,
            max_size_chars=DEFAULT_CONTEXT_MAX_SIZE_CHARS,
        ),
        "skills": {"list": result.skills_list.to_payload()},
    }
