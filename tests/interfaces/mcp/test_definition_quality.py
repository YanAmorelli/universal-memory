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
    "create_skill_draft",
    "migrate_project_layout",
    "share_skill",
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


@pytest.mark.anyio
async def test_migration_preview_preserves_source_but_apply_prunes_migrated_facts(
    tmp_path: Path,
) -> None:
    from tests.application.layout.test_migrate_project_layout import (  # noqa: PLC0415
        FACT_ID,
        PRIVATE_FACT_ID,
        _fact,
        _read_jsonl,
        _safe_write,
        _write_legacy_project,
    )
    from universal_memory.application.layout import MigrateProjectLayoutUseCase  # noqa: PLC0415

    _write_legacy_project(
        tmp_path,
        facts=[_fact(FACT_ID, "Share this fact"), _fact(PRIVATE_FACT_ID, "Keep this fact private")],
        rules=[],
        skills=[],
    )
    legacy = tmp_path / ".umem/memory/facts.jsonl"
    original = legacy.read_bytes()
    use_case = MigrateProjectLayoutUseCase(
        project_root=tmp_path, safe_write_use_case=_safe_write(tmp_path)
    )
    server = configure_server(
        create_mcp_server(),
        base_use_cases(migrate_project_layout=use_case.execute),
        project_root=tmp_path,
    )
    arguments = {"include": ["facts"], "private_fact_ids": [PRIVATE_FACT_ID]}
    preview = (await server.call_tool("migrate_project_layout", arguments)).structured_content
    assert preview is not None and preview["ok"] is True
    assert legacy.read_bytes() == original
    assert not (tmp_path / "umem/memory/facts.jsonl").exists()
    applied = (
        await server.call_tool("migrate_project_layout", {**arguments, "dry_run": False})
    ).structured_content
    assert applied is not None and applied["ok"] is True
    assert {fact["id"] for fact in _read_jsonl(legacy)} == {PRIVATE_FACT_ID}
    assert {fact["id"] for fact in _read_jsonl(tmp_path / "umem/memory/facts.jsonl")} == {FACT_ID}
    tool = await server.get_tool("migrate_project_layout")
    assert tool is not None and tool.annotations is not None
    assert tool.annotations.destructiveHint is True
    assert "rewrites the legacy facts file" in " ".join((tool.description or "").split())


@pytest.mark.anyio
async def test_share_overwrites_existing_shared_destination_without_overwrite_confirmation(
    tmp_path: Path,
) -> None:
    from tests.application.skills.test_share_skill import build_shared_use_cases  # noqa: PLC0415
    from universal_memory.application.skills import CreateSkillCommand  # noqa: PLC0415
    from universal_memory.domain.entities import LatentSkillScope  # noqa: PLC0415

    root, _, create, share = build_shared_use_cases(tmp_path)
    skill = create.execute(
        CreateSkillCommand(
            name="Private Review Helper",
            description="Review implementation changes safely.",
            scope=LatentSkillScope.project,
            origin="test",
            visibility="private",
        )
    )
    source = root / skill.skill_file
    destination = root / "umem/skills/private-review-helper/SKILL.md"
    destination.parent.mkdir(parents=True)
    destination.write_text(source.read_text() + "\nExisting destination content to preserve.\n")
    assert destination.read_text() != source.read_text()
    server = configure_server(
        create_mcp_server(), base_use_cases(share_skill=share.execute), project_root=root
    )
    # No overwrite or operational confirmation is supplied for this user-facing skill.
    applied = (
        await server.call_tool("share_skill", {"skill_id_or_name": skill.slug})
    ).structured_content
    assert applied is not None and applied["ok"] is True
    assert destination.read_text() == source.read_text()
    assert applied["data"]["snapshot_reference"]
    tool = await server.get_tool("share_skill")
    assert tool is not None and tool.annotations is not None
    assert tool.annotations.destructiveHint is True
    assert "without a destination-conflict check" in " ".join((tool.description or "").split())


@pytest.mark.anyio
@pytest.mark.parametrize("supply_markdown", [False, True])
async def test_latent_update_omitted_markdown_regenerates_file_and_loses_custom_body(
    tmp_path: Path, supply_markdown: bool
) -> None:
    from tests.application.skills.test_update_skill import (  # noqa: PLC0415
        build_safe_write,
        make_skill,
        write_skill_markdown,
    )
    from universal_memory.application.skills import UpdateSkillUseCase  # noqa: PLC0415
    from universal_memory.domain.entities import LatentSkillStatus  # noqa: PLC0415

    safe_write, repository, snapshots, _, _ = build_safe_write(tmp_path)
    skill = make_skill(status=LatentSkillStatus.active)
    repository.write(skill)
    write_skill_markdown(tmp_path)
    skill_file = tmp_path / ".umem/skills/tdd-recorrente/SKILL.md"
    sentinel = "Keep this custom workflow body SENTINEL."
    original = skill_file.read_text() + f"\n{sentinel}\n"
    skill_file.write_text(original)
    snapshots.written.clear()
    use_case = UpdateSkillUseCase(
        project_root=tmp_path, repository=repository, safe_write_use_case=safe_write
    )
    server = configure_server(
        create_mcp_server(), base_use_cases(update_skill=use_case.execute), project_root=tmp_path
    )
    arguments: dict[str, Any] = {"latent_skill_id": skill.id}
    if supply_markdown:
        arguments["raw_markdown"] = original
    result = (await server.call_tool("update_skill", arguments)).structured_content
    assert result is not None and result["ok"] is True
    assert (sentinel in skill_file.read_text()) is supply_markdown
    assert any(
        snapshot.relative_path == ".umem/skills/tdd-recorrente/SKILL.md"
        for snapshot in snapshots.written
    )
    tool = await server.get_tool("update_skill")
    assert tool is not None and tool.annotations is not None
    assert tool.annotations.destructiveHint is True
    assert "can discard custom body" in tool.parameters["properties"]["raw_markdown"]["description"]


@pytest.mark.anyio
async def test_recommendations_count_duplicate_nonempty_evidence_entries(tmp_path: Path) -> None:
    from tests.application.skills.test_recommend_skills import (  # noqa: PLC0415
        ReadOnlyLatentSkillRepository,
        make_skill,
    )
    from universal_memory.application.skills import RecommendSkillsUseCase  # noqa: PLC0415

    repository = ReadOnlyLatentSkillRepository(
        [
            make_skill(evidence=["Same curated observation", "Same curated observation"]),
        ]
    )
    use_case = RecommendSkillsUseCase(repository=repository)
    server = configure_server(
        create_mcp_server(),
        base_use_cases(recommend_skills=use_case.execute),
        project_root=tmp_path,
    )
    result = (await server.call_tool("recommend_skills", {})).structured_content
    assert result is not None and result["ok"] is True
    assert result["data"]["recommendations"][0]["evidence_summaries"] == [
        "Same curated observation",
        "Same curated observation",
    ]
    assert not repository.write_called
    tool = await server.get_tool("recommend_skills")
    assert tool is not None
    assert "no distinctness check" in tool.parameters["properties"]["min_recurrence"]["description"]


@pytest.mark.anyio
@pytest.mark.parametrize("tool_name", ["create_skill", "create_skill_draft"])
@pytest.mark.parametrize("supply_empty_triggers", [False, True])
async def test_generated_skill_triggers_fall_back_to_name_and_draft_can_overwrite_unregistered_file(
    tmp_path: Path, tool_name: str, supply_empty_triggers: bool
) -> None:
    from tests.application.skills.test_share_skill import build_shared_use_cases  # noqa: PLC0415
    from universal_memory.application.skills import CreateSkillDraftUseCase  # noqa: PLC0415
    from universal_memory.application.skills.update_skill import (  # noqa: PLC0415
        _parse_skill_markdown,
    )

    root, repository, create, share = build_shared_use_cases(tmp_path)
    draft = CreateSkillDraftUseCase(
        project_root=root, repository=repository, safe_write_use_case=share.safe_write_use_case
    )
    draft_path = root / ".umem/drafts/skills/review-helper/SKILL.md"
    if tool_name == "create_skill_draft":
        draft_path.parent.mkdir(parents=True)
        draft_path.write_text("Existing unregistered draft SENTINEL.\n")
    handler = draft.execute if tool_name == "create_skill_draft" else create.execute
    server = configure_server(
        create_mcp_server(), base_use_cases(**{tool_name: handler}), project_root=root
    )
    arguments: dict[str, Any] = {
        "name": "Review Helper",
        "description": "Review implementation changes safely.",
    }
    if supply_empty_triggers:
        arguments["triggers"] = []
    result = (await server.call_tool(tool_name, arguments)).structured_content
    assert result is not None and result["ok"] is True
    path_key = "draft_path" if tool_name == "create_skill_draft" else "skill_file"
    generated = (root / result["data"][path_key]).read_text()
    assert _parse_skill_markdown(generated).triggers == ["Review Helper"]
    tool = await server.get_tool(tool_name)
    assert tool is not None
    if tool_name == "create_skill_draft":
        assert "SENTINEL" not in draft_path.read_text()
        assert result["data"]["snapshot_reference"]
        assert tool.annotations is not None and tool.annotations.destructiveHint is True
        assert "unregistered file" in " ".join((tool.description or "").split())


@pytest.mark.anyio
async def test_global_draft_uses_workspace_file_with_user_memory_registration(
    tmp_path: Path,
) -> None:
    from universal_memory.bootstrap.mcp import build_server  # noqa: PLC0415

    # Use production wiring: draft creation receives the project SafeWriteUseCase.
    # Storage repositories isolate global memory under this workspace during pytest.
    server = build_server(project_root=tmp_path)
    result = (
        await server.call_tool(
            "create_skill_draft",
            {
                "name": "Global Draft",
                "description": "Review implementation changes safely.",
                "scope": "global",
            },
        )
    ).structured_content
    assert result is not None and result["ok"] is True
    assert result["scope"] == "global"
    assert result["data"]["draft_path"] == "drafts/skills/global-draft/SKILL.md"
    assert (tmp_path / "drafts/skills/global-draft/SKILL.md").is_file()
    assert not (tmp_path / ".umem/drafts/skills/global-draft/SKILL.md").exists()
    global_home = tmp_path / ".umem_global_test_home"
    registry_files = list(global_home.rglob("skills.jsonl"))
    assert registry_files
    records = [
        json.loads(line) for file in registry_files for line in file.read_text().splitlines()
    ]
    record = next(item for item in records if item["id"] == result["data"]["skill_id"])
    assert record["scope"] == "global"
    assert record["canonical_path"] == "drafts/skills/global-draft/SKILL.md"
    assert not list(global_home.rglob("SKILL.md"))
    project_events = [
        json.loads(line)
        for line in (tmp_path / ".umem/audit/events.jsonl").read_text().splitlines()
    ]
    draft_events = [event for event in project_events if event["action"] == "create_skill_draft"]
    assert draft_events and all(event["scope"] == "project" for event in draft_events)
    global_events = [
        json.loads(line)
        for file in global_home.rglob("events.jsonl")
        for line in file.read_text().splitlines()
    ]
    assert all(event["action"] != "create_skill_draft" for event in global_events)
    tool = await server.get_tool("create_skill_draft")
    assert tool is not None
    description = tool.parameters["properties"]["scope"]["description"]
    assert "global writes drafts/skills/<slug>/SKILL.md" in description
    assert "Global does not place the draft file in the user memory directory" in description
