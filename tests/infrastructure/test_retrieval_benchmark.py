from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "benchmarks" / "retrieval.py"
SPEC = importlib.util.spec_from_file_location("retrieval_benchmark", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
retrieval_benchmark = importlib.util.module_from_spec(SPEC)
sys.modules["retrieval_benchmark"] = retrieval_benchmark
SPEC.loader.exec_module(retrieval_benchmark)

build_representative_queries = retrieval_benchmark.build_representative_queries
generate_synthetic_facts = retrieval_benchmark.generate_synthetic_facts
run_benchmark = retrieval_benchmark.run_benchmark

MIN_FACT_COUNT = 1000
MIN_QUERY_COUNT = 30
TARGET_P95_MS = 150
MIN_QUALITY_SCORE = 1
MAX_QUALITY_SCORE = 5


def test_synthetic_fact_generation_is_large_varied_and_isolated() -> None:
    facts = generate_synthetic_facts(MIN_FACT_COUNT)

    assert len(facts) == MIN_FACT_COUNT
    assert {fact.scope.value for fact in facts} == {"global", "project"}
    assert any("segredos" in fact.content for fact in facts)
    assert any("Arquitetura" in fact.content for fact in facts)
    assert any("MCP" in fact.content for fact in facts)
    assert all(fact.source == "benchmark_synthetic" for fact in facts)
    assert all(fact.tags for fact in facts)


def test_representative_queries_have_quality_expectations() -> None:
    queries = build_representative_queries()

    assert len(queries) >= MIN_QUERY_COUNT
    assert all(query.expected_fact_ids for query in queries)
    assert {"segredos", "arquitetura", "global"} <= {query.category for query in queries}


def test_retrieval_benchmark_writes_expected_json_without_real_memory_side_effects(
    tmp_path: Path,
) -> None:
    result = run_benchmark(project_root=tmp_path, fact_count=MIN_FACT_COUNT)

    result_path = tmp_path / ".umem" / "benchmarks" / "retrieval-results.json"
    real_memory_path = tmp_path / ".umem" / "memory" / "facts.jsonl"

    assert result_path.exists()
    assert not real_memory_path.exists()

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload == result
    assert payload["fact_count"] >= MIN_FACT_COUNT
    assert payload["query_count"] >= MIN_QUERY_COUNT
    assert payload["selected_default_strategy"] == "local_text"
    assert "150ms" in payload["default_strategy_justification"]
    assert "strategies" in payload

    text_metrics = payload["strategies"]["local_text"]
    semantic_metrics = payload["strategies"]["semantic_stub"]

    assert text_metrics["p95_latency_ms"] < TARGET_P95_MS
    assert MIN_QUALITY_SCORE <= text_metrics["quality_score"] <= MAX_QUALITY_SCORE
    assert MIN_QUALITY_SCORE <= semantic_metrics["quality_score"] <= MAX_QUALITY_SCORE
    assert text_metrics["offline_compatibility"] == "100% offline"
    assert semantic_metrics["operational_complexity"] > text_metrics["operational_complexity"]
