"""Verify advertised metadata and preserve the dev API captured at 85a9982.

The schema fixture is from the unmodified dev server, not regenerated from this
implementation. Descriptions are the only input/output schema difference allowed.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from tests.interfaces.mcp.test_skills import base_use_cases
from universal_memory.interfaces.mcp.server import configure_server, create_mcp_server

EXPECTED_TOOL_COUNT = 38
EXPECTED_PARAMETER_COUNT = 111

READ_ONLY = {
    "status",
    "inspect_project_layout",
    "doctor",
    "list_facts",
    "list_audit_events",
    "list_snapshots",
    "validate_skill",
    "list_skills",
    "recommend_skills",
    "get_skill_detail",
}
DESTRUCTIVE = {
    "initialize_project",
    "deactivate_skill",
    "purge_fact",
    "rollback_scope",
    "cleanup_skill",
    "repair_skills",
    "sync_skills",
    "update_canonical_skill",
    "update_skill",
    "rename_skill",
    "import_skill",
    "adopt_skill",
    "generate_skill",
    "host_setup",
    "sync_instructions",
}


def without_descriptions(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key == "description":
                continue
            if key == "properties":
                # Preserve an input property literally named description.
                result[key] = {name: without_descriptions(schema) for name, schema in item.items()}
            else:
                result[key] = without_descriptions(item)
        return result
    if isinstance(value, list):
        return [without_descriptions(item) for item in value]
    return value


@pytest.mark.anyio
async def test_wire_definitions_are_complete_and_compatible(tmp_path: Path) -> None:
    baseline = json.loads(
        (Path(__file__).parent / "fixtures/definitions_dev_85a9982.json").read_text()
    )
    server = configure_server(create_mcp_server(), base_use_cases(), project_root=tmp_path)
    # Client exercises actual MCP tools/list serialization, not Python annotations alone.
    async with Client(server) as client:
        tools = await client.list_tools()
    assert len(tools) == len({tool.name for tool in tools}) == EXPECTED_TOOL_COUNT
    assert {tool.name for tool in tools} == set(baseline)
    parameter_count = 0
    for tool in tools:
        assert tool.description, tool.name
        for name, prop in tool.inputSchema.get("properties", {}).items():
            parameter_count += 1
            assert prop.get("description", "").strip(), f"{tool.name}.{name}"
        assert without_descriptions(tool.inputSchema) == baseline[tool.name]["input"], tool.name
        assert without_descriptions(tool.outputSchema) == baseline[tool.name]["output"], tool.name
        hints = tool.annotations
        assert hints is not None, tool.name
        # Pin the full classification, including optional destructive/apply modes.
        assert hints.readOnlyHint is (tool.name in READ_ONLY), tool.name
        assert hints.destructiveHint is (tool.name in DESTRUCTIVE), tool.name
        assert hints.idempotentHint is (tool.name in READ_ONLY), tool.name
        assert hints.openWorldHint is (tool.name == "initialize_project"), tool.name
    assert parameter_count == EXPECTED_PARAMETER_COUNT


@pytest.mark.anyio
async def test_read_like_operations_disclose_persistent_writes(tmp_path: Path) -> None:
    server = configure_server(create_mcp_server(), base_use_cases(), project_root=tmp_path)
    tools = {tool.name: tool for tool in await server.list_tools()}
    for name in ("context", "bootstrap", "host_check"):
        tool = tools[name]
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is False
        assert tool.annotations.idempotentHint is False
        assert "audit" in (tool.description or "").lower()
    # A preview default does not make an operation safe in every supported mode.
    for name in ("cleanup_skill", "repair_skills", "host_setup", "sync_instructions"):
        tool = tools[name]
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is False
        assert tool.annotations.destructiveHint is True
    cleanup = tools["cleanup_skill"]
    assert "currently ignored" in cleanup.parameters["properties"]["targets"]["description"].lower()
    recommend = tools["recommend_skills"]
    assert "false does not enable" in recommend.parameters["properties"]["dry_run"]["description"]


@pytest.mark.anyio
async def test_context_retries_really_create_summaries_and_audit_events(tmp_path: Path) -> None:
    from tests.application.memory.test_assemble_context_summary_use_case import (  # noqa: PLC0415
        build_use_case,
    )

    use_case, summaries, audit = build_use_case(facts=[])
    server = configure_server(
        create_mcp_server(),
        replace(base_use_cases(), context=use_case.execute),
        project_root=tmp_path,
    )
    first = (await server.call_tool("context", {})).structured_content
    second = (await server.call_tool("context", {})).structured_content
    assert first is not None and first["ok"] is True
    assert second is not None and second["ok"] is True
    assert len(summaries.written) == len(audit.events) == 2  # noqa: PLR2004
    assert summaries.written[0].id != summaries.written[1].id
    tool = await server.get_tool("context")
    assert tool is not None
    assert tool.annotations is not None and tool.annotations.readOnlyHint is False


@pytest.mark.anyio
async def test_tracking_retries_increment_observations(tmp_path: Path) -> None:
    from tests.application.skills.test_track_latent_skill import (  # noqa: PLC0415
        RecordingLatentSkillRepository,
    )
    from universal_memory.application.skills import TrackLatentSkillUseCase  # noqa: PLC0415

    repository = RecordingLatentSkillRepository()
    use_case = TrackLatentSkillUseCase(repository=repository)
    server = configure_server(
        create_mcp_server(),
        base_use_cases(track_latent_skill=use_case.execute),
        project_root=tmp_path,
    )
    arguments = {"name": "Review changes", "description": "Review repository changes safely"}
    first = (await server.call_tool("track_latent_skill", arguments)).structured_content
    second = (await server.call_tool("track_latent_skill", arguments)).structured_content
    assert first is not None and first["ok"] is True
    assert second is not None and second["ok"] is True
    assert first["data"]["matched_existing"] is False
    assert second["data"]["matched_existing"] is True
    assert second["data"]["latent_skill"]["recurrence_count"] == 2  # noqa: PLR2004
    tool = await server.get_tool("track_latent_skill")
    assert tool is not None
    assert tool.annotations is not None and tool.annotations.idempotentHint is False


@pytest.mark.anyio
async def test_cleanup_compatibility_flag_does_not_prevent_deletion(tmp_path: Path) -> None:
    from tests.application.skills.conftest import sample_agent_skill  # noqa: PLC0415
    from tests.application.skills.test_track_latent_skill import build_safe_write  # noqa: PLC0415
    from universal_memory.application.skills import CleanupSkillUseCase  # noqa: PLC0415
    from universal_memory.infrastructure.storage import LocalAgentSkillRepository  # noqa: PLC0415

    write, _, snapshots, _ = build_safe_write(tmp_path)
    repository = LocalAgentSkillRepository(project_root=tmp_path, safe_write_use_case=write)
    native = tmp_path / ".opencode/skills/review-helper/SKILL.md"
    native.parent.mkdir(parents=True)
    native.write_text("managed content\n")
    canonical = tmp_path / ".umem/skills/review-helper/SKILL.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("canonical content\n")
    repository.write(
        sample_agent_skill(
            native_installations=[
                {"path": ".opencode/skills/review-helper", "manifest": ["SKILL.md"]},
            ]
        )
    )
    snapshot_count = len(snapshots.written)
    use_case = CleanupSkillUseCase(project_root=tmp_path, repository=repository)
    server = configure_server(
        create_mcp_server(), base_use_cases(cleanup_skill=use_case.execute), project_root=tmp_path
    )
    arguments = {"skill_id_or_name": "review-helper", "targets": False}
    preview = (await server.call_tool("cleanup_skill", arguments)).structured_content
    assert preview is not None and preview["ok"] is True
    assert preview["data"]["removed_paths"] == []
    assert native.exists()
    applied = (
        await server.call_tool("cleanup_skill", {**arguments, "dry_run": False})
    ).structured_content
    assert applied is not None and applied["ok"] is True
    assert applied["data"]["removed_paths"] == [".opencode/skills/review-helper"]
    assert not native.exists()
    assert canonical.read_text() == "canonical content\n"
    assert len(snapshots.written) == snapshot_count
    tool = await server.get_tool("cleanup_skill")
    assert tool is not None
    assert tool.annotations is not None and tool.annotations.destructiveHint is True
