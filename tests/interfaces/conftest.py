from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def skill_payload_assertions():
    def assert_lifecycle_payload(
        payload: dict[str, Any],
        *,
        operation: str,
        required_data_keys: set[str],
    ) -> None:
        assert payload["operation"] == operation
        assert payload["ok"] is True
        assert required_data_keys <= set(payload["data"])

    return assert_lifecycle_payload


@pytest.fixture
def layout_payload_assertions():
    def assert_layout_payload(
        payload: dict[str, Any],
        *,
        operation: str,
        required_keys: set[str],
    ) -> None:
        assert payload["operation"] == operation
        data = payload.get("data", payload)
        assert required_keys <= set(data)

    return assert_layout_payload


def summary_lines(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()]
