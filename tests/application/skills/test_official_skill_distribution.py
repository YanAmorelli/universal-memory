import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any, cast

import click
import pytest
from typer.main import get_command

from universal_memory.application.skills.official_skill_distribution import (
    OFFICIAL_SKILLS_CLI_PACKAGE,
    OfficialSkillAgent,
    OfficialSkillDistributionPlanner,
    OfficialSkillEnvironment,
    SkillInstallMethod,
    SkillInstallScope,
)
from universal_memory.application.skills.validate_skill import validate_skill_tree
from universal_memory.domain import ValidationFailedError
from universal_memory.interfaces.cli.init_command import create_typer_app

OFFICIAL_SKILL_ROOT = Path("skills/universal-memory")
MAX_SKILL_LINES = 130
MAX_BOOTSTRAP_WORDS = 100
TEST_SOURCE_REF = "a" * 40


def _planner() -> OfficialSkillDistributionPlanner:
    return OfficialSkillDistributionPlanner(source_ref=TEST_SOURCE_REF)


def test_published_distribution_uses_the_current_release_tag() -> None:
    planner = OfficialSkillDistributionPlanner.for_published_distribution()

    assert planner.source_ref == "v0.5.1"
    assert "/tree/v0.5.1/skills/universal-memory" in planner.skill_source


@pytest.mark.parametrize("source_ref", ["main", "../v0.5.0", "deadbeef"])
def test_planner_rejects_mutable_or_ambiguous_source_refs(source_ref: str) -> None:
    with pytest.raises(ValidationFailedError, match="source ref"):
        OfficialSkillDistributionPlanner(source_ref=source_ref)


def _environment(**overrides: bool) -> OfficialSkillEnvironment:
    values = {
        "node_available": True,
        "npx_available": True,
        "network_available": True,
        "agent_mapping_available": True,
        "agents_md_available": True,
        "umem_native_available": True,
        "manual_copy_available": True,
    }
    values.update(overrides)
    return OfficialSkillEnvironment(**values)


def test_official_skill_is_valid_concise_and_uses_relative_references() -> None:
    report = validate_skill_tree(
        OFFICIAL_SKILL_ROOT,
        project_root=Path.cwd(),
        subject="official universal-memory skill",
        frontmatter_standard="agent_skills",
    )

    assert report.status == "pass"
    skill_markdown = (OFFICIAL_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert 'name: "universal-memory"' in skill_markdown
    assert "triggers:" not in skill_markdown
    assert len(skill_markdown.splitlines()) <= MAX_SKILL_LINES
    for relative_reference in (
        "references/startup-and-context.md",
        "references/memory-facts.md",
        "references/skills-lifecycle.md",
        "references/host-instructions-sync.md",
        "references/cli-mcp-parity.md",
        "references/guardrails-and-recording.md",
    ):
        assert f"]({relative_reference})" in skill_markdown
        assert (OFFICIAL_SKILL_ROOT / relative_reference).is_file()
    assert "](/" not in skill_markdown


def test_agent_skills_validation_rejects_non_standard_frontmatter(tmp_path: Path) -> None:
    skill_root = tmp_path / "portable-skill"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\n"
        'name: "portable-skill"\n'
        'description: "Use this skill for portable work."\n'
        "triggers:\n"
        '  - "portable work"\n'
        "---\n\n"
        "# Portable Skill\n",
        encoding="utf-8",
    )

    report = validate_skill_tree(
        skill_root,
        project_root=tmp_path,
        frontmatter_standard="agent_skills",
    )

    assert report.status == "fail"
    assert report.blocking_issues == [
        "Agent Skills frontmatter contains unsupported fields: triggers"
    ]


def test_official_skill_encodes_the_complete_directed_cli_contract() -> None:
    skill_markdown = (OFFICIAL_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    references = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((OFFICIAL_SKILL_ROOT / "references").glob("*.md"))
    )
    contract = f"{skill_markdown}\n{references}".lower()

    for required_guidance in (
        "umem status --format json",
        "umem context --scope project --format json",
        "current repository",
        "explicit user instructions",
        "secrets",
        "credentials",
        "raw logs",
        "stack traces",
        "transient task progress",
        "unverified assumptions",
        "confirmation",
        "durable",
        "final response",
    ):
        assert required_guidance in contract
    assert 'Do not wait for the user to say "use UMEM"' in skill_markdown


def test_agents_bootstrap_is_compact_and_complements_the_official_skill() -> None:
    bootstrap = (OFFICIAL_SKILL_ROOT / "assets" / "agents-md-bootstrap.md").read_text(
        encoding="utf-8"
    )

    assert len(bootstrap.split()) <= MAX_BOOTSTRAP_WORDS
    assert "universal-memory" in bootstrap
    assert "umem status --format json" in bootstrap
    assert "umem context --scope project --format json" in bootstrap
    assert "stable, reusable, and safe" in bootstrap
    assert "umem skills track" not in bootstrap
    assert "umem remember" not in bootstrap


def test_planner_builds_safe_project_scoped_copy_plan_by_default() -> None:
    plan = _planner().plan(
        OfficialSkillAgent(agent_id="cursor", display_name="Cursor"),
        _environment(),
    )

    assert plan.action == "external_action"
    assert plan.channel == "npx_skills"
    assert plan.ready is False
    assert plan.support_tier == "tier_2_directed_cli"
    assert plan.scope == SkillInstallScope.project
    assert plan.install_method == SkillInstallMethod.copy
    assert plan.argv == (
        "npx",
        "--yes",
        OFFICIAL_SKILLS_CLI_PACKAGE,
        "add",
        (
            "https://github.com/YanAmorelli/universal-memory/tree/"
            f"{TEST_SOURCE_REF}/skills/universal-memory"
        ),
        "--skill",
        "universal-memory",
        "--agent",
        "cursor",
        "--copy",
        "-y",
    )
    assert "--global" not in plan.argv
    assert "--copy" in plan.argv
    assert plan.environment == {"DISABLE_TELEMETRY": "1"}
    assert plan.display_command.startswith(
        f"DISABLE_TELEMETRY=1 npx --yes {OFFICIAL_SKILLS_CLI_PACKAGE} add"
    )
    assert plan.primary_prompt == "Connect Universal Memory to Cursor?"
    assert plan.requires_confirmation is True
    assert plan.fallbacks == ()


def test_planner_discloses_external_installer_boundaries_and_readiness_checks() -> None:
    plan = _planner().plan(
        OfficialSkillAgent(agent_id="cursor", display_name="Cursor"),
        _environment(),
    )
    details = plan.technical_details

    assert details["installer"] == "npx skills"
    assert details["installer_package"] == OFFICIAL_SKILLS_CLI_PACKAGE
    assert details["skill_source_ref"] == TEST_SOURCE_REF
    assert details["agent"] == "cursor"
    assert details["scope"] == "project"
    assert details["install_method"] == "copy"
    assert details["network_required"] is True
    assert details["anonymous_telemetry"] == "disabled"
    assert details["mutation_boundary"] == "external_unmanaged"
    assert "snapshot" in details["mutation_disclosure"]
    assert "audit" in details["mutation_disclosure"]
    assert "rollback" in details["mutation_disclosure"]
    assert details["exact_command"] == plan.display_command
    assert plan.readiness_checks == (
        "instruction_presence",
        "umem_cli_available",
        "project_context_read",
    )


def test_planner_supports_explicit_global_copy_plan() -> None:
    plan = _planner().plan(
        OfficialSkillAgent(agent_id="claude-code", display_name="Claude Code"),
        _environment(),
        scope=SkillInstallScope.global_,
        install_method=SkillInstallMethod.copy,
    )

    assert plan.scope == SkillInstallScope.global_
    assert plan.install_method == SkillInstallMethod.copy
    assert plan.argv[-3:] == ("--global", "--copy", "-y")
    assert plan.requires_confirmation is True


def test_planner_rejects_false_symlink_semantics_for_pinned_installer() -> None:
    with pytest.raises(ValidationFailedError, match="no deterministic symlink mode"):
        _planner().plan(
            OfficialSkillAgent(agent_id="cursor", display_name="Cursor"),
            _environment(),
            install_method=SkillInstallMethod.symlink,
        )


@pytest.mark.parametrize(
    ("capability_override", "reason"),
    [
        ({"node_available": False}, "node_unavailable"),
        ({"npx_available": False}, "npx_unavailable"),
        ({"network_available": False}, "network_unavailable"),
        ({"agent_mapping_available": False}, "agent_mapping_unavailable"),
    ],
)
def test_planner_returns_non_fatal_fallback_when_external_install_is_unavailable(
    capability_override: dict[str, bool],
    reason: str,
) -> None:
    plan = _planner().plan(
        OfficialSkillAgent(agent_id="cursor", display_name="Cursor"),
        _environment(**capability_override),
    )

    assert plan.action == "managed_fallback"
    assert plan.channel == "agents_md"
    assert plan.ready is False
    assert plan.unavailable_reason == reason
    assert plan.argv == ()
    assert plan.environment == {}
    assert [fallback.channel for fallback in plan.fallbacks] == [
        "agents_md",
        "umem_native",
        "manual_copy",
    ]
    assert plan.fallbacks[0].recommended is True
    assert plan.fallbacks[0].source_package == "universal_memory"
    assert plan.fallbacks[0].source_path == (
        "resources/skills/universal-memory/assets/agents-md-bootstrap.md"
    )
    assert plan.readiness_checks[-1] == "project_context_read"


def test_planner_recommends_only_fallbacks_declared_available() -> None:
    plan = _planner().plan(
        OfficialSkillAgent(agent_id="cursor", display_name="Cursor"),
        _environment(
            node_available=False,
            agents_md_available=False,
            manual_copy_available=False,
        ),
    )

    assert [fallback.channel for fallback in plan.fallbacks] == ["umem_native"]
    assert plan.channel == "umem_native"
    assert plan.fallbacks[0].recommended is True


@pytest.mark.parametrize(
    "agent_id", ["", "--global", "Cursor Agent", "cursor;echo", "cursor-", "cursor--agent"]
)
def test_planner_rejects_unsafe_or_invalid_agent_ids(agent_id: str) -> None:
    with pytest.raises(ValidationFailedError, match="agent ID"):
        _planner().plan(
            OfficialSkillAgent(agent_id=agent_id, display_name="Cursor"),
            _environment(),
        )


def test_planner_rejects_display_names_with_control_lines() -> None:
    with pytest.raises(ValidationFailedError, match="display name"):
        _planner().plan(
            OfficialSkillAgent(agent_id="cursor", display_name="Cursor\nInjected"),
            _environment(),
        )


def test_planner_rejects_any_terminal_control_character_in_display_name() -> None:
    with pytest.raises(ValidationFailedError, match="display name"):
        _planner().plan(
            OfficialSkillAgent(agent_id="cursor", display_name="Cursor\x1b[2Jspoof"),
            _environment(),
        )


def test_planner_rejects_non_boolean_environment_capabilities() -> None:
    invalid_environment = OfficialSkillEnvironment(
        node_available=cast(Any, "false"),
        npx_available=True,
        network_available=True,
        agent_mapping_available=True,
        agents_md_available=True,
        umem_native_available=True,
        manual_copy_available=True,
    )

    with pytest.raises(ValidationFailedError, match="node_available"):
        _planner().plan(
            OfficialSkillAgent(agent_id="cursor", display_name="Cursor"),
            invalid_environment,
        )


def test_planner_returns_pending_when_no_installation_channel_is_available() -> None:
    plan = _planner().plan(
        OfficialSkillAgent(agent_id="cursor", display_name="Cursor"),
        _environment(
            node_available=False,
            agents_md_available=False,
            umem_native_available=False,
            manual_copy_available=False,
        ),
    )

    assert plan.action == "pending"
    assert plan.channel is None
    assert plan.fallbacks == ()
    assert plan.ready is False


def test_packaged_fallback_assets_match_the_public_skill_source() -> None:
    packaged_root = Path("src/universal_memory/resources/skills/universal-memory")
    public_files = {
        path.relative_to(OFFICIAL_SKILL_ROOT): path.read_bytes()
        for path in OFFICIAL_SKILL_ROOT.rglob("*")
        if path.is_file()
    }
    packaged_files = {
        path.relative_to(packaged_root): path.read_bytes()
        for path in packaged_root.rglob("*")
        if path.is_file()
    }

    assert packaged_files == public_files


def test_wheel_contains_every_official_skill_fallback_asset(tmp_path: Path) -> None:
    uv_path = shutil.which("uv")
    assert uv_path is not None
    build_environment = os.environ.copy()
    build_environment["UV_CACHE_DIR"] = str(tmp_path / "uv-cache")
    completed = subprocess.run(  # noqa: S603
        [uv_path, "build", "--wheel", "--out-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        env=build_environment,
    )
    assert completed.returncode == 0, completed.stderr
    wheel = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        wheel_files = set(archive.namelist())

    expected_prefix = "universal_memory/resources/skills/universal-memory/"
    assert {
        f"{expected_prefix}{path.relative_to(OFFICIAL_SKILL_ROOT).as_posix()}"
        for path in OFFICIAL_SKILL_ROOT.rglob("*")
        if path.is_file()
    } <= wheel_files
    assert (tmp_path / "uv-cache").is_dir()


@pytest.mark.parametrize(
    ("command", "expected_options"),
    [
        (("status",), ("--format",)),
        (("context",), ("--scope", "--format")),
        (("remember",), ("--scope", "--tag", "--format")),
        (("facts", "list"), ("--scope", "--format")),
        (("skills", "list"), ("--format",)),
        (("skills", "detail"), ("--format",)),
    ],
)
def test_official_skill_commands_are_real_cli_surfaces(
    command: tuple[str, ...], expected_options: tuple[str, ...]
) -> None:
    cli_command: click.Command = get_command(create_typer_app())
    for command_name in command:
        assert isinstance(cli_command, click.Group)
        assert command_name in cli_command.commands
        cli_command = cli_command.commands[command_name]

    available_options = {
        option
        for parameter in cli_command.params
        if isinstance(parameter, click.Option)
        for option in parameter.opts
    }
    for option in expected_options:
        assert option in available_options
