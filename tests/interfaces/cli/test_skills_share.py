from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime

from universal_memory.application.skills import ShareSkillCommand, ShareSkillResult
from universal_memory.bootstrap.cli import main as bootstrap_cli_main
from universal_memory.domain.entities import AgentSkill, AgentSkillStatus, LatentSkillScope
from universal_memory.interfaces.cli.init_command import main as cli_main


def make_result() -> ShareSkillResult:
    now = datetime.now(UTC)
    skill = AgentSkill(
        id="11111111-1111-4111-8111-111111111111",
        created_at=now,
        updated_at=now,
        name="Use Universal Memory",
        slug="use-universal-memory",
        description="Operational bootstrap guidance.",
        scope=LatentSkillScope.project,
        status=AgentSkillStatus.active,
        canonical_path="umem/skills/use-universal-memory/SKILL.md",
        origin="cli",
        audit_reference="audit-1",
        content_hash="hash-1",
        metadata={"visibility": "shared", "category": "operational"},
    )
    return ShareSkillResult(
        agent_skill=skill,
        old_canonical_path=".umem/skills/use-universal-memory/SKILL.md",
        new_canonical_path="umem/skills/use-universal-memory/SKILL.md",
        affected_paths=[
            "umem/skills/use-universal-memory/SKILL.md",
            "umem/project.toml",
        ],
        audit_reference="audit-1",
        snapshot_reference="snapshot-1",
    )


def test_skills_share_operational_json_uses_cli_origin_and_confirmation(capsys) -> None:
    seen: list[ShareSkillCommand] = []

    def share_skill(command: ShareSkillCommand) -> ShareSkillResult:
        seen.append(command)
        return make_result()

    exit_code = cli_main(
        [
            "skills",
            "share",
            "use-universal-memory",
            "--category",
            "operational",
            "--yes",
            "--format",
            "json",
        ],
        share_skill_command=share_skill,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == [
        ShareSkillCommand(
            skill_id_or_name="use-universal-memory",
            category="operational",
            confirm_operational=True,
            origin="cli",
        )
    ]
    assert payload["operation"] == "skills.share"
    assert payload["scope"] == "project"
    assert payload["data"]["new_canonical_path"] == "umem/skills/use-universal-memory/SKILL.md"
    assert payload["data"]["visibility"] == "shared"
    assert payload["data"]["category"] == "operational"


def test_skills_share_default_umem_skill_after_shared_init(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert bootstrap_cli_main(["init", "--layout", "shared", "--yes", "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        bootstrap_cli_main(
            [
                "skills",
                "share",
                "use-universal-memory",
                "--category",
                "operational",
                "--yes",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    policy = tomllib.loads((tmp_path / "umem" / "project.toml").read_text(encoding="utf-8"))

    assert payload["operation"] == "skills.share"
    assert payload["data"]["category"] == "operational"
    assert payload["data"]["new_canonical_path"] == "umem/skills/universal-memory/SKILL.md"
    assert policy["shared_operational_skills"] == ["universal-memory"]


def test_skills_share_existing_operational_default_category_requires_confirmation(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert bootstrap_cli_main(["init", "--layout", "shared", "--yes", "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        bootstrap_cli_main(
            [
                "skills",
                "create",
                "--name",
                "Operational Helper",
                "--description",
                "Local workflow bootstrap.",
                "--category",
                "operational",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        bootstrap_cli_main(
            [
                "skills",
                "share",
                "operational-helper",
                "--format",
                "json",
            ]
        )
        == 1
    )
    payload = json.loads(capsys.readouterr().out)
    policy = tomllib.loads((tmp_path / "umem" / "project.toml").read_text(encoding="utf-8"))

    assert payload["ok"] is False
    assert "explicit confirmation" in payload["error"]["detail"]
    assert policy["shared_operational_skills"] == []
