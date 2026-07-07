import json
import tomllib
from pathlib import Path

import pytest

from universal_memory.application.onboarding.setup_project import (
    DEFAULT_UMEM_SKILL_MARKDOWN,
    DEFAULT_UMEM_SKILL_REFERENCES,
    setup_project,
)
from universal_memory.infrastructure.config import (
    LocalConfigValidationPort,
    LocalProjectLayoutPort,
)


def test_setup_project_initializes_layout_and_returns_structured_result(
    tmp_path: Path,
) -> None:
    result = setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )

    assert result.created is True
    assert result.already_initialized is False
    assert result.project_path == Path(".")
    assert result.config_path == Path(".umem/config.toml")
    assert result.memory_path == Path(".umem/memory")
    assert result.audit_path == Path(".umem/audit/events.jsonl")
    assert result.snapshots_path == Path(".umem/snapshots")
    assert result.skills_path == Path(".umem/skills")
    assert result.benchmarks_path == Path(".umem/benchmarks")
    assert result.created_paths == [
        ".umem/config.toml",
        ".umem/memory",
        ".umem/audit/events.jsonl",
        ".umem/snapshots",
        ".umem/skills",
        ".umem/benchmarks",
        ".umem/benchmarks/retrieval-results.json",
        ".umem/skills/use-universal-memory/SKILL.md",
        ".umem/skills/use-universal-memory/references/startup-and-context.md",
        ".umem/skills/use-universal-memory/references/memory-facts.md",
        ".umem/skills/use-universal-memory/references/skills-lifecycle.md",
        ".umem/skills/use-universal-memory/references/host-instructions-sync.md",
        ".umem/skills/use-universal-memory/references/cli-mcp-parity.md",
        ".umem/skills/use-universal-memory/references/guardrails-and-recording.md",
        ".umem/memory/latent_skills.jsonl",
    ]
    default_skill = tmp_path / ".umem" / "skills" / "use-universal-memory" / "SKILL.md"
    assert default_skill.is_file()
    skill_content = default_skill.read_text(encoding="utf-8")
    assert 'name: "use-universal-memory"' in skill_content
    assert 'name: "Use Universal Memory"' not in skill_content
    assert "umem context --scope project" in skill_content
    assert "umem status --format json" in skill_content
    assert "umem skills list --format json" in skill_content
    assert "umem skills detail <skill-id-or-name> --format json" in skill_content
    assert "Reference Routing" in skill_content
    assert "references/startup-and-context.md" in skill_content
    assert "references/memory-facts.md" in skill_content
    assert "references/skills-lifecycle.md" in skill_content
    assert "references/host-instructions-sync.md" in skill_content
    assert "references/cli-mcp-parity.md" in skill_content
    assert "references/guardrails-and-recording.md" in skill_content
    assert "secrets" in skill_content
    assert "credentials" in skill_content
    assert "Record only curated, durable facts" in skill_content
    assert "References are loaded only on demand" in skill_content
    for expected_skill_guidance in (
        "Latent Skill Decision Loop",
        "track_latent_skill",
        "umem skills create",
        "umem skills import <path>",
        "do not call `track_latent_skill` just to",
    ):
        assert expected_skill_guidance in skill_content
    assert "Mandatory Startup" in skill_content
    assert "at the start of a work session or conversation" in skill_content
    assert "UMEM unavailable or uninitialized" in skill_content
    assert "Do not repeat the full startup sequence" in skill_content
    for relative_path in DEFAULT_UMEM_SKILL_REFERENCES:
        reference_file = tmp_path / relative_path
        assert reference_file.is_file()
        assert reference_file.read_text(encoding="utf-8").startswith("# ")
    latent_skill_line = (tmp_path / ".umem" / "memory" / "latent_skills.jsonl").read_text(
        encoding="utf-8"
    )
    latent_skill = json.loads(latent_skill_line)
    assert latent_skill["name"] == "use-universal-memory"
    assert latent_skill["description"] == (
        "Operational hub for using Universal Memory context, facts, host sync, "
        "and skills lifecycle."
    )
    assert latent_skill["metadata"]["triggers"] == [
        "at the start of a work session or conversation",
        "before implementing, investigating, reviewing, or planning in a repository with .umem",
        "when the user mentions memory, facts, context, skills, AGENTS.md, CLAUDE.md, "
        "host sync, or learned preferences",
        "before recording durable project or global knowledge",
        "before creating, updating, activating, or deactivating a UMEM skill",
    ]
    config = tomllib.loads((tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8"))
    assert config["project"] == {"name": "", "created_by": "universal-memory"}
    assert config["preferences"] == {"locale": "en"}
    assert config["runtimes"] == {
        "enabled": ["claude_code", "opencode", "codex", "cursor", "antigravity"]
    }
    assert "hosts" not in config


def test_setup_project_skills_lifecycle_documents_valid_create_command(tmp_path: Path) -> None:
    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )

    skills_lifecycle_content = (
        tmp_path
        / ".umem"
        / "skills"
        / "use-universal-memory"
        / "references"
        / "skills-lifecycle.md"
    ).read_text(encoding="utf-8")

    assert '--trigger "when to use it"' in skills_lifecycle_content
    assert (
        "umem skills import .agents/skills/<skill-name> --scope project "
        "--visibility shared --category user-facing --sync" in skills_lifecycle_content
    )
    assert "umem skills sync <skill-id-or-name> --format json" in skills_lifecycle_content
    assert "Official Workflows" in skills_lifecycle_content
    assert "do not pass a canonical `skill_id`" in skills_lifecycle_content
    assert "umem host sync --apply --yes --format json" in skills_lifecycle_content
    assert "Decision Guide For Agents" in skills_lifecycle_content
    assert "Playbook: Adopt Existing Native Skill Into UMEM" in skills_lifecycle_content
    assert "umem status --format json" in skills_lifecycle_content
    assert "umem context --scope project --format json" in skills_lifecycle_content
    assert "umem skills detail foo --format json" in skills_lifecycle_content
    assert "native_installations" in skills_lifecycle_content
    assert "Normal\n   `git status` can hide" in skills_lifecycle_content
    assert "Native\nwrappers are a repository policy choice" in skills_lifecycle_content
    assert "--file path/to/SKILL.md" not in skills_lifecycle_content


def test_setup_project_persists_selected_runtimes(tmp_path: Path) -> None:
    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        enabled_runtime_ids=["codex"],
    )

    assert '[runtimes]\nenabled = [\n    "codex",\n]\n' in (
        tmp_path / ".umem" / "config.toml"
    ).read_text(encoding="utf-8")


def test_setup_project_shared_layout_creates_visible_root_and_keeps_umem_skill_private(
    tmp_path: Path,
) -> None:
    result = setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        layout="shared",
    )

    assert result.layout == "shared"
    assert result.shared_root == Path("umem")
    assert result.operational_root == Path(".umem")
    assert result.shared_paths == ["umem/project.toml", "umem/memory", "umem/skills"]
    assert (tmp_path / "umem" / "project.toml").is_file()
    assert (tmp_path / "umem" / "memory").is_dir()
    assert (tmp_path / "umem" / "skills").is_dir()
    assert (tmp_path / ".umem" / "skills" / "use-universal-memory" / "SKILL.md").is_file()
    assert not (tmp_path / "umem" / "skills" / "use-universal-memory").exists()
    policy = tomllib.loads((tmp_path / "umem" / "project.toml").read_text(encoding="utf-8"))
    assert policy["visibility_defaults"]["operational_skills"] == "private"
    assert policy["shared_operational_skills"] == []


def test_setup_project_accepts_runtime_aliases_and_rejects_unknown_runtime(
    tmp_path: Path,
) -> None:
    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        enabled_runtime_ids=["claude-code", "opencode"],
    )

    config = tomllib.loads((tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8"))
    assert config["runtimes"]["enabled"] == ["claude_code", "opencode"]

    with pytest.raises(Exception, match="Unsupported runtimes: unknown"):
        setup_project(
            tmp_path,
            layout_port=LocalProjectLayoutPort(),
            config_validation_port=LocalConfigValidationPort(),
            enabled_runtime_ids=["unknown"],
        )


def test_setup_project_preserves_existing_locale(tmp_path: Path) -> None:
    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.write_text(
        '[project]\nname = ""\ncreated_by = "universal-memory"\n\n'
        '[preferences]\nlocale = "pt-BR"\n\n'
        '[hosts]\nenabled = [\n    "codex",\n]\n',
        encoding="utf-8",
    )

    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )

    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert config["preferences"]["locale"] == "pt-BR"
    assert config["runtimes"]["enabled"] == ["codex"]
    assert config["hosts"]["enabled"] == ["codex"]


def test_setup_project_without_selection_preserves_legacy_hosts_enabled(
    tmp_path: Path,
) -> None:
    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )
    config_path = tmp_path / ".umem" / "config.toml"
    config_path.write_text(
        '[project]\nname = ""\ncreated_by = "universal-memory"\n\n'
        '[hosts]\nenabled = ["claude_code"]\n',
        encoding="utf-8",
    )

    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )

    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert config["runtimes"]["enabled"] == ["claude_code"]
    assert config["hosts"]["enabled"] == ["claude_code"]


def test_setup_project_is_idempotent_and_reports_existing_layout(tmp_path: Path) -> None:
    first_result = setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )
    second_result = setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )

    assert first_result.created is True
    assert second_result.created is False
    assert second_result.already_initialized is True
    assert second_result.created_paths == []
    assert second_result.existing_paths == [
        ".umem/config.toml",
        ".umem/memory",
        ".umem/audit/events.jsonl",
        ".umem/snapshots",
        ".umem/skills",
        ".umem/benchmarks",
        ".umem/benchmarks/retrieval-results.json",
        ".umem/skills/use-universal-memory/SKILL.md",
        ".umem/skills/use-universal-memory/references/startup-and-context.md",
        ".umem/skills/use-universal-memory/references/memory-facts.md",
        ".umem/skills/use-universal-memory/references/skills-lifecycle.md",
        ".umem/skills/use-universal-memory/references/host-instructions-sync.md",
        ".umem/skills/use-universal-memory/references/cli-mcp-parity.md",
        ".umem/skills/use-universal-memory/references/guardrails-and-recording.md",
        ".umem/memory/latent_skills.jsonl",
    ]


def test_setup_project_shared_layout_is_idempotent_and_reports_existing_paths(
    tmp_path: Path,
) -> None:
    first_result = setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        layout="shared",
    )
    second_result = setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        layout="shared",
    )

    assert first_result.created is True
    assert "umem/project.toml" in first_result.created_paths
    assert second_result.created is False
    assert second_result.already_initialized is True
    assert second_result.created_paths == []
    assert "umem/project.toml" in second_result.existing_paths
    assert "umem/memory" in second_result.existing_paths
    assert "umem/skills" in second_result.existing_paths


def test_setup_project_does_not_overwrite_existing_default_umem_skill_reference(
    tmp_path: Path,
) -> None:
    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )
    lifecycle_path = (
        tmp_path
        / ".umem"
        / "skills"
        / "use-universal-memory"
        / "references"
        / "skills-lifecycle.md"
    )
    custom_content = "# Skills Lifecycle\n\nExisting project guidance must stay intact.\n"
    lifecycle_path.write_text(custom_content, encoding="utf-8")

    result = setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )

    assert result.already_initialized is True
    assert lifecycle_path.read_text(encoding="utf-8") == custom_content
    assert (
        ".umem/skills/use-universal-memory/references/skills-lifecycle.md" in result.existing_paths
    )


def test_setup_project_repairs_partial_layout_state(tmp_path: Path) -> None:
    (tmp_path / ".umem").mkdir()
    (tmp_path / ".umem" / "memory").mkdir()

    result = setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
    )

    assert result.created is True
    assert result.already_initialized is False
    assert result.created_paths == [
        ".umem/config.toml",
        ".umem/audit/events.jsonl",
        ".umem/snapshots",
        ".umem/skills",
        ".umem/benchmarks",
        ".umem/benchmarks/retrieval-results.json",
        ".umem/skills/use-universal-memory/SKILL.md",
        ".umem/skills/use-universal-memory/references/startup-and-context.md",
        ".umem/skills/use-universal-memory/references/memory-facts.md",
        ".umem/skills/use-universal-memory/references/skills-lifecycle.md",
        ".umem/skills/use-universal-memory/references/host-instructions-sync.md",
        ".umem/skills/use-universal-memory/references/cli-mcp-parity.md",
        ".umem/skills/use-universal-memory/references/guardrails-and-recording.md",
        ".umem/memory/latent_skills.jsonl",
    ]
    assert result.existing_paths == [".umem/memory"]


def test_default_umem_skill_templates_match_project_owned_skill_files() -> None:
    skill_root = Path(".umem") / "skills" / "use-universal-memory"

    assert DEFAULT_UMEM_SKILL_MARKDOWN == (skill_root / "SKILL.md").read_text(encoding="utf-8")
    for relative_path, expected_content in DEFAULT_UMEM_SKILL_REFERENCES.items():
        assert expected_content == Path(relative_path).read_text(encoding="utf-8")
