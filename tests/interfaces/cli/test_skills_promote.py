from __future__ import annotations

import json
from datetime import UTC, datetime

from universal_memory.application.skills import (
    CreateSkillResult,
    PromoteSkillRecommendationCommand,
    PromoteSkillRecommendationResult,
)
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
)
from universal_memory.interfaces.cli.init_command import main as cli_main

RECOMMENDATION_ID = "11111111-1111-4111-8111-111111111111"


def make_result() -> PromoteSkillRecommendationResult:
    now = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
    source = LatentSkill(
        id=RECOMMENDATION_ID,
        created_at=now,
        updated_at=now,
        name="Review Operator",
        description="Review code changes.",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.proposed,
        recurrence_count=3,
        metadata={"triggers": ["review code"]},
    )
    skill = AgentSkill(
        id="22222222-2222-4222-8222-222222222222",
        created_at=now,
        updated_at=now,
        name="Review Operator",
        slug="review-operator",
        description="Review code changes.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path=".umem/skills/review-operator/SKILL.md",
        origin="cli",
        audit_reference="audit-create",
        content_hash="hash-1",
        source_recommendation_id=RECOMMENDATION_ID,
        metadata={"triggers": ["review code"], "creation_flow": "promotion"},
    )
    promoted = source.model_copy(
        update={
            "status": LatentSkillStatus.active,
            "metadata": {
                "promotion": {
                    "promoted_skill_id": "22222222-2222-4222-8222-222222222222",
                    "promoted_at": "2026-06-12T12:00:00Z",
                }
            },
        }
    )
    create_result = CreateSkillResult(
        agent_skill=skill,
        slug="review-operator",
        skill_dir=".umem/skills/review-operator",
        skill_file=".umem/skills/review-operator/SKILL.md",
        created_paths=[".umem/skills/review-operator/SKILL.md"],
        affected_paths=[".umem/skills/review-operator/SKILL.md"],
        audit_reference="audit-create",
        snapshot_reference="snapshot-create",
    )
    return PromoteSkillRecommendationResult(
        create_result=create_result,
        source_recommendation=source,
        promoted_recommendation=promoted,
        audit_reference="audit-create, audit-promote",
        snapshot_reference="snapshot-create, snapshot-promote",
    )


def test_skills_promote_json_requires_yes(capsys) -> None:
    exit_code = cli_main(
        ["skills", "promote", RECOMMENDATION_ID, "--format", "json"],
        promote_skill_recommendation_command=lambda _command: make_result(),
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert "--yes" in payload["error"]["detail"]


def test_skills_promote_json_uses_cli_origin_and_optional_edits(capsys) -> None:
    seen: list[PromoteSkillRecommendationCommand] = []

    def promote(command: PromoteSkillRecommendationCommand) -> PromoteSkillRecommendationResult:
        seen.append(command)
        return make_result()

    exit_code = cli_main(
        [
            "skills",
            "promote",
            RECOMMENDATION_ID,
            "--yes",
            "--name",
            "Edited Review Operator",
            "--description",
            "Edited description.",
            "--trigger",
            "edited trigger",
            "--format",
            "json",
        ],
        promote_skill_recommendation_command=promote,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == [
        PromoteSkillRecommendationCommand(
            recommendation_id=RECOMMENDATION_ID,
            origin="cli",
            name="Edited Review Operator",
            description="Edited description.",
            triggers=["edited trigger"],
        )
    ]
    assert payload["operation"] == "skills.promote"
    assert payload["scope"] == "project"
    assert payload["data"]["source_recommendation_id"] == RECOMMENDATION_ID
    assert payload["data"]["canonical_skill"]["source_recommendation_id"] == RECOMMENDATION_ID


def test_skills_promote_human_output(capsys) -> None:
    exit_code = cli_main(
        ["skills", "promote", RECOMMENDATION_ID, "--yes"],
        promote_skill_recommendation_command=lambda _command: make_result(),
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Operation: skills.promote" in output
    assert f"Source recommendation: {RECOMMENDATION_ID}" in output
    assert ".umem/skills/review-operator/SKILL.md" in output
