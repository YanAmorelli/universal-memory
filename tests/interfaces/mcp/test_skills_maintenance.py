from __future__ import annotations

from pathlib import Path

import pytest

from tests.application.skills.conftest import sample_agent_skill
from tests.interfaces.mcp.test_skills import base_use_cases
from universal_memory.application.skills import (
    CleanupPlan,
    CleanupSkillCommand,
    CleanupSkillResult,
    RenameSkillCommand,
    RenameSkillResult,
)
from universal_memory.interfaces.mcp.server import configure_server, create_mcp_server


@pytest.mark.anyio
async def test_mcp_maintenance_tools_payloads_and_descriptions(tmp_path: Path) -> None:
    seen_rename: list[RenameSkillCommand] = []
    seen_cleanup: list[CleanupSkillCommand] = []

    def rename(command: RenameSkillCommand) -> RenameSkillResult:
        seen_rename.append(command)
        return RenameSkillResult(
            agent_skill=sample_agent_skill(slug=command.slug),
            old_path=".umem/skills/review-helper/SKILL.md",
            new_path=f".umem/skills/{command.slug}/SKILL.md",
            affected_paths=[".umem/skills/review-helper/SKILL.md"],
        )

    def cleanup(command: CleanupSkillCommand) -> CleanupSkillResult:
        seen_cleanup.append(command)
        return CleanupSkillResult(
            CleanupPlan(
                skill=command.skill_id_or_name,
                mode="targets",
                dry_run=command.dry_run,
                removable_paths=[".opencode/skills/review-helper"],
            )
        )

    server = configure_server(
        create_mcp_server(),
        base_use_cases(rename_skill=rename, cleanup_skill=cleanup),
        project_root=tmp_path,
    )

    tools = {tool.name: tool.description or "" for tool in await server.list_tools()}
    rename_payload = (
        await server.call_tool(
            "rename_skill",
            {"skill_id_or_name": "review-helper", "slug": "review-operator"},
        )
    ).structured_content
    cleanup_payload = (
        await server.call_tool("cleanup_skill", {"skill_id_or_name": "review-helper"})
    ).structured_content

    assert "update_canonical_skill" in tools
    assert "canonical" in tools["update_canonical_skill"].lower()
    assert "cleanup_skill" in tools
    assert "managed-only" in tools["cleanup_skill"]
    assert seen_rename[0].origin == "mcp"
    assert seen_cleanup[0].origin == "mcp"
    assert rename_payload is not None
    assert cleanup_payload is not None
    assert rename_payload["operation"] == "skills.rename"
    assert cleanup_payload["operation"] == "skills.cleanup"
