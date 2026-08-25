from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "benchmarks" / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_benchmark", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
bootstrap_benchmark = importlib.util.module_from_spec(SPEC)
sys.modules["bootstrap_benchmark"] = bootstrap_benchmark
SPEC.loader.exec_module(bootstrap_benchmark)

run_benchmark = bootstrap_benchmark.run_benchmark


def test_bootstrap_benchmark_records_round_trip_and_token_proxy_reductions(
    tmp_path: Path,
) -> None:
    result = run_benchmark(project_root=tmp_path, sample_count=1)
    result_path = tmp_path / ".umem" / "benchmarks" / "bootstrap-results.json"

    assert result_path.is_file()
    assert json.loads(result_path.read_text(encoding="utf-8")) == result
    assert result["round_trips"] == {
        "baseline": 3,
        "bootstrap": 1,
        "reduction_percent": 66.7,
    }
    assert result["sample_count"] == 1
    assert result["warmup_samples"] == 1

    for channel in ("cli_subprocess", "mcp_in_process"):
        assert set(result[channel]) == {"baseline", "bootstrap"}
        for variant in ("baseline", "bootstrap"):
            metrics = result[channel][variant]
            assert set(metrics) == {
                "median_duration_ms",
                "p95_duration_ms",
                "serialized_request_chars",
                "serialized_response_chars",
                "token_proxy",
            }
            assert metrics["median_duration_ms"] >= 0
            assert metrics["p95_duration_ms"] >= 0
        assert (
            result[channel]["bootstrap"]["token_proxy"] < result[channel]["baseline"]["token_proxy"]
        )
