from __future__ import annotations

from pathlib import Path

import pytest

from tests.application.skills.conftest import sample_agent_skill
from tests.interfaces.mcp.test_skills import base_use_cases
from universal_memory.application.skills import AdoptSkillCommand, AdoptSkillResult
from universal_memory.interfaces.mcp.server import configure_server, create_mcp_server


@pytest.mark.anyio
async def test_mcp_adopt_tool_payload_and_description(tmp_path: Path) -> None:
    seen: list[AdoptSkillCommand] = []

    def adopt(command: AdoptSkillCommand) -> AdoptSkillResult:
        seen.append(command)
        skill = sample_agent_skill(slug=command.slug or "review-helper")
        return AdoptSkillResult(
            agent_skill=skill,
            slug=skill.slug,
            skill_dir=f".umem/skills/{skill.slug}",
            skill_file=f".umem/skills/{skill.slug}/SKILL.md",
            adopted_source=".umem/skills/review-helper",
            affected_paths=[f".umem/skills/{skill.slug}/SKILL.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        )

    server = configure_server(
        create_mcp_server(),
        base_use_cases(adopt_skill=adopt),
        project_root=tmp_path,
    )

    tools = {tool.name: tool.description or "" for tool in await server.list_tools()}
    payload = (
        await server.call_tool(
            "adopt_skill",
            {"path": ".umem/skills/review-helper", "slug": "review-helper"},
        )
    ).structured_content

    assert "adopt_skill" in tools
    assert "adopt" in tools["adopt_skill"].lower()
    assert seen[0].origin == "mcp"
    assert seen[0].slug == "review-helper"
    assert payload is not None
    assert payload["operation"] == "skills.adopt"
    assert payload["data"]["adopted_source"] == ".umem/skills/review-helper"
