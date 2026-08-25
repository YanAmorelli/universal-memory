from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BASELINE_CLI_CALLS = (
    ("status", "--format", "json"),
    ("context", "--scope", "project", "--format", "json"),
    ("skills", "list", "--format", "json"),
)
BOOTSTRAP_CLI_CALL = ("bootstrap", "--format", "json")
BASELINE_MCP_CALLS = (("status", {}), ("context", {}), ("list_skills", {}))
BOOTSTRAP_MCP_CALL = ("bootstrap", {})
TOKEN_PROXY_CHARS = 4


def _percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(0.95 * (len(ordered) - 1))))
    return ordered[index]


def _metric(
    durations_ms: list[float],
    request_chars: list[int],
    response_chars: list[int],
) -> dict[str, float | int]:
    median_request = round(statistics.median(request_chars))
    median_response = round(statistics.median(response_chars))
    return {
        "median_duration_ms": round(statistics.median(durations_ms), 3),
        "p95_duration_ms": round(_percentile_95(durations_ms), 3),
        "serialized_request_chars": median_request,
        "serialized_response_chars": median_response,
        "token_proxy": round((median_request + median_response) / TOKEN_PROXY_CHARS),
    }


def _umem_executable() -> str:
    sibling = Path(sys.executable).with_name("umem")
    if sibling.is_file():
        return str(sibling)
    executable = shutil.which("umem")
    if executable is None:
        raise RuntimeError("The umem executable is required to run the bootstrap benchmark.")
    return executable


def _run_cli(executable: str, args: tuple[str, ...], cwd: Path) -> tuple[float, int, int]:
    request = json.dumps({"command": "umem", "args": args}, separators=(",", ":"))
    started = time.perf_counter()
    completed = subprocess.run(  # noqa: S603
        [executable, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    duration_ms = (time.perf_counter() - started) * 1000
    json.loads(completed.stdout)
    return duration_ms, len(request), len(completed.stdout)


def _initialize_cli_project(executable: str, project_root: Path) -> None:
    subprocess.run(  # noqa: S603
        [executable, "init", "--yes", "--format", "json"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )


def _measure_cli(sample_count: int, root: Path) -> dict[str, Any]:
    executable = _umem_executable()
    baseline_root = root / "cli-baseline"
    bootstrap_root = root / "cli-bootstrap"
    baseline_root.mkdir()
    bootstrap_root.mkdir()
    _initialize_cli_project(executable, baseline_root)
    _initialize_cli_project(executable, bootstrap_root)

    baseline_duration: list[float] = []
    baseline_request: list[int] = []
    baseline_response: list[int] = []
    bootstrap_duration: list[float] = []
    bootstrap_request: list[int] = []
    bootstrap_response: list[int] = []

    for index in range(sample_count + 1):
        duration = request = response = 0
        for args in BASELINE_CLI_CALLS:
            call_duration, call_request, call_response = _run_cli(executable, args, baseline_root)
            duration += call_duration
            request += call_request
            response += call_response
        one_duration, one_request, one_response = _run_cli(
            executable, BOOTSTRAP_CLI_CALL, bootstrap_root
        )
        if index > 0:
            baseline_duration.append(duration)
            baseline_request.append(request)
            baseline_response.append(response)
            bootstrap_duration.append(one_duration)
            bootstrap_request.append(one_request)
            bootstrap_response.append(one_response)

    return {
        "baseline": _metric(baseline_duration, baseline_request, baseline_response),
        "bootstrap": _metric(bootstrap_duration, bootstrap_request, bootstrap_response),
    }


async def _call_mcp_routine(
    server: Any,
    calls: tuple[tuple[str, dict[str, Any]], ...],
) -> tuple[float, int, int]:
    request_chars = 0
    response_chars = 0
    started = time.perf_counter()
    for tool_name, arguments in calls:
        request_chars += len(
            json.dumps(
                {"tool": tool_name, "arguments": arguments},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        result = await server.call_tool(tool_name, arguments)
        payload = result.structured_content
        if payload is None or payload.get("ok") is not True:
            raise RuntimeError(f"MCP benchmark call failed: {tool_name}")
        response_chars += len(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return (time.perf_counter() - started) * 1000, request_chars, response_chars


async def _measure_mcp_async(sample_count: int, root: Path) -> dict[str, Any]:
    from universal_memory.bootstrap.mcp import build_server  # noqa: PLC0415

    executable = _umem_executable()
    baseline_root = root / "mcp-baseline"
    bootstrap_root = root / "mcp-bootstrap"
    baseline_root.mkdir()
    bootstrap_root.mkdir()
    _initialize_cli_project(executable, baseline_root)
    _initialize_cli_project(executable, bootstrap_root)
    baseline_server = build_server(baseline_root)
    bootstrap_server = build_server(bootstrap_root)

    baseline_samples: list[tuple[float, int, int]] = []
    bootstrap_samples: list[tuple[float, int, int]] = []
    baseline_calls = tuple(BASELINE_MCP_CALLS)
    bootstrap_calls = (BOOTSTRAP_MCP_CALL,)
    for index in range(sample_count + 1):
        baseline = await _call_mcp_routine(baseline_server, baseline_calls)
        bootstrap = await _call_mcp_routine(bootstrap_server, bootstrap_calls)
        if index > 0:
            baseline_samples.append(baseline)
            bootstrap_samples.append(bootstrap)

    return {
        "baseline": _metric(
            [sample[0] for sample in baseline_samples],
            [sample[1] for sample in baseline_samples],
            [sample[2] for sample in baseline_samples],
        ),
        "bootstrap": _metric(
            [sample[0] for sample in bootstrap_samples],
            [sample[1] for sample in bootstrap_samples],
            [sample[2] for sample in bootstrap_samples],
        ),
    }


def run_benchmark(
    *,
    project_root: Path | None = None,
    sample_count: int = 5,
) -> dict[str, Any]:
    if sample_count < 1:
        raise ValueError("sample_count must be at least 1")
    output_root = (project_root or Path.cwd()).resolve()
    with tempfile.TemporaryDirectory(prefix="umem-bootstrap-benchmark-") as temp_dir:
        benchmark_root = Path(temp_dir)
        cli_metrics = _measure_cli(sample_count, benchmark_root)
        mcp_metrics = asyncio.run(_measure_mcp_async(sample_count, benchmark_root))

    payload: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "sample_count": sample_count,
        "warmup_samples": 1,
        "token_proxy_chars_per_token": TOKEN_PROXY_CHARS,
        "round_trips": {
            "baseline": 3,
            "bootstrap": 1,
            "reduction_percent": 66.7,
        },
        "cli_subprocess": cli_metrics,
        "mcp_in_process": mcp_metrics,
    }
    output_path = output_root / ".umem" / "benchmarks" / "bootstrap-results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure the UMEM session bootstrap routine.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args()
    result = run_benchmark(sample_count=args.samples)
    if args.format == "json":
        print(json.dumps(result, sort_keys=True))
        return
    print(
        "Bootstrap benchmark complete: "
        f"{result['round_trips']['baseline']} -> {result['round_trips']['bootstrap']} "
        "public round-trips; results at .umem/benchmarks/bootstrap-results.json"
    )


if __name__ == "__main__":
    main()
