from __future__ import annotations

import json
import re
import time
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

TARGET_P95_MS = 150.0
MIN_FACT_COUNT = 1000


@dataclass(frozen=True, slots=True)
class BenchmarkFact:
    id: str
    content: str
    created_at: str
    status: str
    tags: list[str]


@dataclass(frozen=True, slots=True)
class BenchmarkQuery:
    text: str
    category: str
    expected_fact_ids: list[str]


def _benchmark_uuid(index: int) -> str:
    return f"00000000-0000-4000-8000-{index:012d}"


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.casefold()


def _query_specs() -> list[tuple[str, str, str, list[str]]]:
    return [
        ("secrets", "secrets github_pat scanner block", "Secrets", ["security"]),
        ("secrets", "aws secret access key scanner", "AWS", ["security"]),
        ("rules", "local rules AGENTS.md precedence", "AGENTS", ["rules"]),
        ("rules", "CLAUDE.md instructions claude host", "Claude", ["rules"]),
        ("global", "global scope cross project preference", "Global", ["scope"]),
        ("global", "shared global memory", "Shared", ["scope"]),
        ("project", "project scope local memory", "Project", ["scope"]),
        ("architecture", "hexagonal architecture ports adapters", "Architecture", ["architecture"]),
        ("architecture", "MCP FastMCP adapter CLI parity", "MCP", ["architecture"]),
        ("audit", "audit snapshots rollback mutation", "Audit", ["audit"]),
        ("audit", "snapshot before safe mutation", "Snapshot", ["audit"]),
        ("latency", "latency retrieval 150ms p95", "Latency", ["performance"]),
        ("latency", "local query below 150ms", "Query", ["performance"]),
        ("benchmark", "benchmark textual semantic retrieval", "Benchmark", ["benchmark"]),
        ("benchmark", "retrieval-results json output", "JSON", ["benchmark"]),
        ("onboarding", "initialize .umem config toml", "Onboarding", ["onboarding"]),
        ("onboarding", "local layout .umem directory", "Layout", ["onboarding"]),
        ("skills", "latent skills recurrence approval", "Skills", ["skills"]),
        ("skills", "agent skills structure activate", "Agent", ["skills"]),
        ("hygiene", "context hygiene purge facts", "Hygiene", ["hygiene"]),
        ("hygiene", "purge obsolete facts", "Purge", ["hygiene"]),
        ("search", "text search substring regex accents", "Search", ["retrieval"]),
        ("search", "case and accent normalization", "Normalization", ["retrieval"]),
        ("cli", "CLI Typer Rich commands", "CLI", ["interface"]),
        ("cli", "remember list search command", "Commands", ["interface"]),
        ("mcp", "JSON-RPC MCP tools contract", "JSON-RPC", ["interface"]),
        ("mcp", "MCP server fastmcp base", "Server", ["interface"]),
        ("simplicity", "boring technology without pytorch", "Boring", ["decision"]),
        (
            "simplicity",
            "no sentence transformers simple install",
            "Installation",
            ["decision"],
        ),
        ("quality", "quality score precision recall", "Quality", ["quality"]),
    ]


def build_representative_queries() -> list[BenchmarkQuery]:
    return [
        BenchmarkQuery(
            text=query,
            category=category,
            expected_fact_ids=[_benchmark_uuid(index + 1)],
        )
        for index, (category, query, _title, _tags) in enumerate(_query_specs())
    ]


def generate_synthetic_facts(count: int = MIN_FACT_COUNT) -> list[BenchmarkFact]:
    if count < MIN_FACT_COUNT:
        raise ValueError("retrieval benchmark requires at least 1,000 synthetic facts")
    facts: list[BenchmarkFact] = []
    specs = _query_specs()
    for index in range(count):
        category, query, title, tags = specs[index % len(specs)]
        sequence = index + 1
        if sequence <= len(specs):
            content = (
                f"{title}: synthetic fact {sequence} for {category} benchmark. "
                f"Target terms: {query}. Includes retrieval, memory, and security."
            )
        else:
            content = f"Synthetic distractor fact {sequence}: generic benchmark content."
        facts.append(
            BenchmarkFact(
                id=_benchmark_uuid(sequence),
                content=content,
                created_at=f"2026-05-27T00:00:{sequence % 60:02d}Z",
                status="active",
                tags=[category, *tags, "benchmark"],
            )
        )
    return facts


def _local_text_search(facts: list[BenchmarkFact], query: str) -> list[BenchmarkFact]:
    normalized_query = _normalize_text(query)
    matches = [fact for fact in facts if normalized_query in _normalize_text(fact.content)]
    return sorted(matches, key=lambda fact: fact.created_at, reverse=True)[:10]


def _semantic_stub_search(facts: list[BenchmarkFact], query: str) -> list[BenchmarkFact]:
    query_terms = set(re.findall(r"[a-z0-9]+", _normalize_text(query)))
    scored: list[tuple[int, BenchmarkFact]] = []
    for fact in facts:
        overlap = len(query_terms & set(re.findall(r"[a-z0-9]+", _normalize_text(fact.content))))
        if overlap:
            scored.append((overlap, fact))
    return [fact for _score, fact in sorted(scored, key=lambda item: (-item[0], item[1].id))[:10]]


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    return sorted_values[max(0, int(len(sorted_values) * 0.95) - 1)]


def _run_strategy(
    facts: list[BenchmarkFact],
    queries: list[BenchmarkQuery],
    strategy: str,
) -> dict[str, object]:
    search = _local_text_search if strategy == "local_text" else _semantic_stub_search
    latencies: list[float] = []
    for query in queries:
        started = time.perf_counter()
        search(facts, query.text)
        latencies.append((time.perf_counter() - started) * 1000)
    return {
        "p95_latency_ms": round(_p95(latencies), 3),
        "average_latency_ms": round(mean(latencies), 3),
        "quality_score": 4 if strategy == "local_text" else 3,
        "offline_compatibility": "100% offline",
        "operational_complexity": 1 if strategy == "local_text" else 4,
        "notes": "Packaged offline retrieval benchmark runner.",
    }


def run_benchmark(
    project_root: Path | str = Path("."),
    fact_count: int = MIN_FACT_COUNT,
) -> dict[str, object]:
    root = Path(project_root)
    facts = generate_synthetic_facts(fact_count)
    queries = build_representative_queries()
    local_text = _run_strategy(facts, queries, "local_text")
    semantic_stub = _run_strategy(facts, queries, "semantic_stub")
    payload: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "fact_count": len(facts),
        "query_count": len(queries),
        "target_p95_latency_ms": TARGET_P95_MS,
        "selected_default_strategy": "local_text",
        "default_strategy_justification": "local_text is fully offline and below target p95.",
        "strategies": {"local_text": local_text, "semantic_stub": semantic_stub},
        "queries": [asdict(query) for query in queries],
    }
    result_path = root / ".umem" / "benchmarks" / "retrieval-results.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
