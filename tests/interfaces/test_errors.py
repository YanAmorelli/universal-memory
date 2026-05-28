from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest

from universal_memory.application.memory import GetMemoryStatusCommand, GetMemoryStatusResult
from universal_memory.domain import (
    FactNotFoundError,
    InvalidConfigError,
    SecretDetectedError,
    SnapshotFailedError,
    StorageError,
    ValidationFailedError,
)
from universal_memory.interfaces.cli.init_command import main as cli_main
from universal_memory.interfaces.mcp.server import (
    JSON_RPC_FACT_NOT_FOUND,
    JSON_RPC_INVALID_CONFIG,
    JSON_RPC_SECRET_DETECTED,
    JSON_RPC_SNAPSHOT_FAILED,
    JSON_RPC_STORAGE_ERROR,
    JSON_RPC_VALIDATION_FAILED,
    MCPUseCases,
    configure_server,
    create_mcp_server,
)

SECRET_SENTINEL = "sk-test-secret-value"  # noqa: S105 - sentinel used to verify redaction.


@pytest.mark.parametrize(
    ("error", "slug"),
    [
        (SecretDetectedError(f"blocked /Users/test/project: {SECRET_SENTINEL}"), "secret_detected"),
        (SnapshotFailedError("snapshot failed at /Users/test/project/.umem"), "snapshot_failed"),
        (ValidationFailedError("missing field api_key=abcd1234"), "validation_failed"),
        (
            FactNotFoundError("fact not found: /Users/test/project/.umem/facts.jsonl"),
            "fact_not_found",
        ),
        (InvalidConfigError("invalid config C:\\Users\\test\\config.toml"), "invalid_config"),
        (StorageError("storage failed at /Users/test/project/.umem"), "storage_error"),
    ],
)
def test_cli_json_errors_use_canonical_envelope_and_redact_detail(
    capsys: pytest.CaptureFixture[str],
    error: Exception,
    slug: str,
) -> None:
    def status_error(_command: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        raise error

    exit_code = cli_main(["status", "--format", "json"], status_command=status_error)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert set(payload["error"]) == {
        "code",
        "message",
        "detail",
        "recovery_hint",
        "audit_reference",
    }
    assert payload["error"]["code"] == slug
    assert "/Users/test" not in payload["error"]["detail"]
    assert "C:\\Users\\test" not in payload["error"]["detail"]
    assert SECRET_SENTINEL not in payload["error"]["detail"]


def test_cli_human_unexpected_error_is_clean_by_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def status_error(_command: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        raise RuntimeError(f"boom {SECRET_SENTINEL} /Users/test/project")

    exit_code = cli_main(["status"], status_command=status_error)
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Erro inesperado" in captured.err
    assert "Traceback" not in captured.err
    assert SECRET_SENTINEL not in captured.err
    assert "/Users/test" not in captured.err


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "json_rpc_code"),
    [
        (
            SecretDetectedError(f"blocked /Users/test/project: {SECRET_SENTINEL}"),
            JSON_RPC_SECRET_DETECTED,
        ),
        (
            SnapshotFailedError("snapshot failed at /Users/test/project/.umem"),
            JSON_RPC_SNAPSHOT_FAILED,
        ),
        (ValidationFailedError("missing field api_key=abcd1234"), JSON_RPC_VALIDATION_FAILED),
        (
            FactNotFoundError("fact not found: /Users/test/project/.umem/facts.jsonl"),
            JSON_RPC_FACT_NOT_FOUND,
        ),
        (
            InvalidConfigError("invalid config C:\\Users\\test\\config.toml"),
            JSON_RPC_INVALID_CONFIG,
        ),
        (StorageError("storage failed at /Users/test/project/.umem"), JSON_RPC_STORAGE_ERROR),
    ],
)
async def test_mcp_domain_errors_use_json_rpc_mapping_and_tool_error_result(
    error: Exception,
    json_rpc_code: int,
) -> None:
    def status_error(_command: GetMemoryStatusCommand) -> GetMemoryStatusResult:
        raise error

    use_cases = replace(mcp_use_cases(), status=status_error)
    server = configure_server(create_mcp_server(), use_cases)

    payload = _mcp_error_payload((await server.call_tool("status", {})).structured_content)

    assert payload["isError"] is True
    assert payload["structuredContent"]["ok"] is False
    assert payload["structuredContent"]["error"]["code"] == json_rpc_code
    assert "/Users/test" not in payload["structuredContent"]["error"]["data"]["detail"]
    assert "C:\\Users\\test" not in payload["structuredContent"]["error"]["data"]["detail"]
    assert SECRET_SENTINEL not in payload["structuredContent"]["error"]["data"]["detail"]
    assert payload["structuredContent"]["error"]["data"]["recovery_hint"]


def _mcp_error_payload(structured_content: dict[str, Any] | None) -> dict[str, Any]:
    assert structured_content is not None
    if "isError" in structured_content:
        return structured_content
    return {
        "isError": True,
        "structuredContent": structured_content,
    }


def mcp_use_cases() -> MCPUseCases:
    return MCPUseCases(
        status=lambda _command: pytest.fail("status use case should be replaced"),
        context=lambda _command: pytest.fail("context use case not expected"),
    )
