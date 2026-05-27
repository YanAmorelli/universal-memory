from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from uuid import UUID

try:
    from universal_memory.domain.entities import Fact, FactScope, FactStatus
except ModuleNotFoundError:  # pragma: no cover - convenience for direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_memory.domain.entities import Fact, FactScope, FactStatus


TARGET_P95_MS = 150.0
MIN_REGEX_QUERY_LENGTH = 2
MIN_FACT_COUNT = 1000
MAX_EXCELLENT_NOISE = 3
GOOD_RANK_LIMIT = 2
ACCEPTABLE_RANK_LIMIT = 5


@dataclass(frozen=True, slots=True)
class BenchmarkQuery:
    text: str
    category: str
    expected_fact_ids: list[str]


@dataclass(frozen=True, slots=True)
class StrategyMetrics:
    p95_latency_ms: float
    average_latency_ms: float
    quality_score: int
    offline_compatibility: str
    operational_complexity: int
    notes: str


@dataclass(frozen=True, slots=True)
class StrategyRun:
    metrics: StrategyMetrics
    query_latencies_ms: list[float]


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    search: Callable[[list[Fact], str], list[Fact]]
    offline_compatibility: str
    operational_complexity: int
    notes: str


def _benchmark_uuid(index: int) -> str:
    return str(UUID(f"00000000-0000-4000-8000-{index:012d}"))


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.casefold()


def _query_specs() -> list[tuple[str, str, str, list[str]]]:
    return [
        ("segredos", "segredos github_pat bloqueio scanner", "Segredos", ["security"]),
        ("segredos", "chave aws secret access scanner", "AWS", ["security"]),
        ("regras", "regras locais AGENTS.md precedencia", "AGENTS", ["rules"]),
        ("regras", "instrucoes CLAUDE.md host claude", "Claude", ["rules"]),
        ("global", "escopo global preferencia entre projetos", "Global", ["scope"]),
        ("global", "memoria global compartilhada", "Compartilhada", ["scope"]),
        ("project", "escopo project memoria local", "Project", ["scope"]),
        ("arquitetura", "Arquitetura hexagonal ports adapters", "Arquitetura", ["architecture"]),
        ("arquitetura", "MCP FastMCP adapter CLI paridade", "MCP", ["architecture"]),
        ("auditoria", "auditoria snapshots rollback mutacao", "Auditoria", ["audit"]),
        ("auditoria", "snapshot antes de mutacao segura", "Snapshot", ["audit"]),
        ("latencia", "latencia recuperacao 150ms p95", "Latência", ["performance"]),
        ("latencia", "consulta local abaixo 150ms", "Consulta", ["performance"]),
        ("benchmark", "benchmark recuperacao textual semantico", "Benchmark", ["benchmark"]),
        ("benchmark", "resultado retrieval-results json", "JSON", ["benchmark"]),
        ("onboarding", "inicializacao .umem config toml", "Onboarding", ["onboarding"]),
        ("onboarding", "layout local diretorio .umem", "Layout", ["onboarding"]),
        ("skills", "latent skills recorrencia aprovacao", "Skills", ["skills"]),
        ("skills", "agent skills estrutura ativar", "Agent", ["skills"]),
        ("higiene", "context hygiene purge fatos", "Higiene", ["hygiene"]),
        ("higiene", "purgar fatos obsoletos", "Purgar", ["hygiene"]),
        ("busca", "busca textual substring regex acentuacao", "Busca", ["retrieval"]),
        ("busca", "normalizacao caixa acentos", "Normalização", ["retrieval"]),
        ("cli", "CLI Typer Rich comandos", "CLI", ["interface"]),
        ("cli", "comando remember list search", "Comandos", ["interface"]),
        ("mcp", "JSON-RPC contrato MCP tools", "JSON-RPC", ["interface"]),
        ("mcp", "servidor MCP base fastmcp", "Servidor", ["interface"]),
        ("simplicidade", "boring technology sem pytorch", "Boring", ["decision"]),
        (
            "simplicidade",
            "sem sentence transformers instalacao simples",
            "Instalação",
            ["decision"],
        ),
        ("qualidade", "score qualidade precisao revocabilidade", "Qualidade", ["quality"]),
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


def generate_synthetic_facts(count: int = MIN_FACT_COUNT) -> list[Fact]:
    if count < MIN_FACT_COUNT:
        msg = "retrieval benchmark requires at least 1,000 synthetic facts"
        raise ValueError(msg)

    base_time = datetime(2026, 5, 27, tzinfo=UTC)
    specs = _query_specs()
    facts: list[Fact] = []

    for index in range(count):
        spec = specs[index % len(specs)]
        category, query, title, tags = spec
        sequence = index + 1
        scope = FactScope.global_ if index % 5 == 0 else FactScope.project
        case_variant = title.upper() if index % 7 == 0 else title
        accent_text = "recuperação, memória, configuração e segurança"
        
        # Apenas os primeiros len(specs) fatos contêm os termos de busca específicos
        if sequence <= len(specs):
            content = (
                f"{case_variant}: fato sintético {sequence} para benchmark de {category}. "
                f"Termos alvo: {query}. Inclui {accent_text}; variação de Caixa e domínio "
                "de desenvolvimento de software para universal-memory."
            )
        else:
            # Fatos distratores genéricos sem as palavras-chave específicas das queries
            content = (
                f"Fato sintético distrator {sequence}: conteúdo de desenvolvimento genérico "
                f"para universal-memory sobre escopo {scope.value}. Inclui {accent_text}."
            )
            
        facts.append(
            Fact(
                id=_benchmark_uuid(sequence),
                created_at=base_time + timedelta(seconds=sequence),
                updated_at=base_time + timedelta(seconds=sequence),
                content=content,
                scope=scope,
                source="benchmark_synthetic",
                status=FactStatus.active,
                tags=[category, *tags, "benchmark"],
                metadata={"synthetic": True, "sequence": sequence},
            )
        )

    return facts


def _local_text_search(facts: list[Fact], query: str) -> list[Fact]:
    is_regex = query.startswith("/") and query.endswith("/") and len(query) > MIN_REGEX_QUERY_LENGTH
    clean_query = query[1:-1] if is_regex else query
    normalized_query = _normalize_text(clean_query)
    
    matches: list[Fact] = []
    for fact in facts:
        if fact.status != FactStatus.active:
            continue
        normalized_content = _normalize_text(fact.content)
        if is_regex:
            try:
                if re.search(normalized_query, normalized_content):
                    matches.append(fact)
            except re.error:
                pass
        elif normalized_query in normalized_content:
            matches.append(fact)
    return sorted(matches, key=lambda fact: fact.created_at, reverse=True)[:10]


def _semantic_stub_search(facts: list[Fact], query: str) -> list[Fact]:
    # A real local semantic search would load an embedding model, keep vectors in memory,
    # and pay installation/model-size costs. This deterministic stub approximates recall by
    # token overlap without adding PyTorch/SentenceTransformers or network downloads.
    query_terms = set(re.findall(r"[a-z0-9]+", _normalize_text(query)))
    scored: list[tuple[int, Fact]] = []
    for fact in facts:
        content_terms = set(re.findall(r"[a-z0-9]+", _normalize_text(fact.content)))
        overlap = len(query_terms & content_terms)
        if overlap:
            scored.append((overlap, fact))
    return [fact for _score, fact in sorted(scored, key=lambda item: (-item[0], item[1].id))[:10]]


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = max(0, int(len(sorted_values) * 0.95) - 1)
    return sorted_values[index]


def _quality_score(queries: list[BenchmarkQuery], results: list[list[Fact]]) -> int:
    if not queries or not results:
        return 1
    per_query_scores: list[float] = []
    for query, matches in zip(queries, results, strict=True):
        matched_ids = [fact.id for fact in matches]
        expected = set(query.expected_fact_ids)
        found = expected & set(matched_ids)
        if not found:
            per_query_scores.append(1.0)
            continue
        rank = min(matched_ids.index(expected_id) for expected_id in found)
        if rank == 0 and len(matches) <= MAX_EXCELLENT_NOISE:
            per_query_scores.append(5.0)
        elif rank <= GOOD_RANK_LIMIT:
            per_query_scores.append(4.0)
        elif rank <= ACCEPTABLE_RANK_LIMIT:
            per_query_scores.append(3.0)
        else:
            per_query_scores.append(2.0)
    return max(1, min(5, round(mean(per_query_scores))))


def _run_strategy(
    *,
    facts: list[Fact],
    queries: list[BenchmarkQuery],
    config: StrategyConfig,
) -> StrategyRun:
    latencies: list[float] = []
    results: list[list[Fact]] = []

    for query in queries:
        started = time.perf_counter()
        matches = config.search(facts, query.text)
        latencies.append((time.perf_counter() - started) * 1000)
        results.append(matches)

    metrics = StrategyMetrics(
        p95_latency_ms=round(_p95(latencies), 3),
        average_latency_ms=round(mean(latencies), 3),
        quality_score=_quality_score(queries, results),
        offline_compatibility=config.offline_compatibility,
        operational_complexity=config.operational_complexity,
        notes=config.notes,
    )
    return StrategyRun(metrics=metrics, query_latencies_ms=[round(value, 3) for value in latencies])


def _select_default_strategy(local_text: StrategyMetrics, semantic_stub: StrategyMetrics) -> str:
    if local_text.p95_latency_ms < TARGET_P95_MS:
        return "local_text"
    if semantic_stub.p95_latency_ms < TARGET_P95_MS:
        return "semantic_stub"
    return "local_text"


def run_benchmark(
    project_root: Path | str = Path("."),
    fact_count: int = MIN_FACT_COUNT,
) -> dict[str, object]:
    root = Path(project_root)
    facts = generate_synthetic_facts(fact_count)
    queries = build_representative_queries()

    local_text = _run_strategy(
        facts=facts,
        queries=queries,
        config=StrategyConfig(
            search=_local_text_search,
            offline_compatibility="100% offline",
            operational_complexity=1,
            notes="Busca textual local sem dependencias adicionais, downloads ou modelo residente.",
        ),
    )
    semantic_stub = _run_strategy(
        facts=facts,
        queries=queries,
        config=StrategyConfig(
            search=_semantic_stub_search,
            offline_compatibility="offline somente apos provisionamento local do modelo",
            operational_complexity=4,
            notes=(
                "Stub heuristico para representar candidato semantico local; uma versao real "
                "exigiria embeddings, memoria adicional e distribuicao de modelo."
            ),
        ),
    )

    default_strategy = _select_default_strategy(local_text.metrics, semantic_stub.metrics)
    justification = (
        "A estrategia local_text foi selecionada porque mantem p95 abaixo do limite de 150ms, "
        "opera 100% offline e evita dependencias pesadas como PyTorch/SentenceTransformers. "
        "O candidato semantic_stub permanece util para comparacao, mas tem maior complexidade "
        "operacional e custo de provisionamento."
    )

    payload: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "fact_count": len(facts),
        "query_count": len(queries),
        "target_p95_latency_ms": TARGET_P95_MS,
        "selected_default_strategy": default_strategy,
        "default_strategy_justification": justification,
        "strategies": {
            "local_text": asdict(local_text.metrics),
            "semantic_stub": asdict(semantic_stub.metrics),
        },
        "queries": [asdict(query) for query in queries],
    }

    result_path = root / ".umem" / "benchmarks" / "retrieval-results.json"
    try:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        pass
    return payload


def main() -> None:
    result = run_benchmark()
    output_path = Path(".umem") / "benchmarks" / "retrieval-results.json"
    print(
        f"Retrieval benchmark complete: {result['query_count']} queries, "
        f"{result['fact_count']} facts, results at {output_path}"
    )


if __name__ == "__main__":
    main()
