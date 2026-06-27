from __future__ import annotations

from pathlib import Path

import pytest

from tests.application.skills.conftest import sample_agent_skill
from tests.interfaces.mcp.test_skills import base_use_cases
from universal_memory.application.skills import (
    CreateSkillDraftCommand,
    DraftSkillResult,
    SkillValidationReport,
    ValidateSkillCommand,
    ValidateSkillResult,
)
from universal_memory.interfaces.mcp.server import configure_server, create_mcp_server


@pytest.mark.anyio
async def test_mcp_draft_and_validate_tools_use_mcp_origin(tmp_path: Path) -> None:
    seen_draft: list[CreateSkillDraftCommand] = []
    seen_validate: list[ValidateSkillCommand] = []

    def draft(command: CreateSkillDraftCommand) -> DraftSkillResult:
        seen_draft.append(command)
        skill = sample_agent_skill(name=command.name, slug="review-helper")
        return DraftSkillResult(
            agent_skill=skill,
            slug="review-helper",
            draft_path=".umem/drafts/skills/review-helper/SKILL.md",
            affected_paths=[".umem/drafts/skills/review-helper/SKILL.md"],
            audit_reference="audit-1",
            snapshot_reference="snapshot-1",
        )

    def validate(command: ValidateSkillCommand) -> ValidateSkillResult:
        seen_validate.append(command)
        return ValidateSkillResult(
            SkillValidationReport(subject=command.skill_or_path, status="pass", checks=[])
        )

    server = configure_server(
        create_mcp_server(),
        base_use_cases(create_skill_draft=draft, validate_skill=validate),
        project_root=tmp_path,
    )

    tools = {tool.name: tool.description or "" for tool in await server.list_tools()}
    draft_payload = (
        await server.call_tool(
            "create_skill_draft",
            {
                "name": "Review Helper",
                "description": "Review implementation changes safely.",
            },
        )
    ).structured_content
    validate_payload = (
        await server.call_tool("validate_skill", {"skill_or_path": "review-helper"})
    ).structured_content

    assert "create_skill_draft" in tools
    assert "draft" in tools["create_skill_draft"].lower()
    assert "validate_skill" in tools
    assert seen_draft[0].origin == "mcp"
    assert seen_validate[0].skill_or_path == "review-helper"
    assert draft_payload is not None
    assert validate_payload is not None
    assert draft_payload["operation"] == "skills.draft.create"
    assert validate_payload["operation"] == "skills.validate"
