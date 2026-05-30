import json
from pathlib import Path

import pytest

from universal_memory.application.onboarding.setup_project import setup_project
from universal_memory.domain import StorageError
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
        ".umem/memory/latent_skills.jsonl",
    ]
    default_skill = tmp_path / ".umem" / "skills" / "use-universal-memory" / "SKILL.md"
    assert default_skill.is_file()
    skill_content = default_skill.read_text(encoding="utf-8")
    assert 'name: "use-universal-memory"' in skill_content
    assert 'name: "Use Universal Memory"' not in skill_content
    assert "umem context --scope project" in skill_content
    assert "--scope global" in skill_content
    assert "--scope project" in skill_content
    assert "--tag preference" in skill_content
    assert "--tag architecture" in skill_content
    assert "segredos" in skill_content
    assert "credenciais" in skill_content
    assert "dados pessoais sensiveis" in skill_content
    assert "revisar aprendizados" in skill_content
    latent_skill_line = (tmp_path / ".umem" / "memory" / "latent_skills.jsonl").read_text(
        encoding="utf-8"
    )
    latent_skill = json.loads(latent_skill_line)
    assert latent_skill["name"] == "use-universal-memory"
    assert (tmp_path / ".umem" / "config.toml").read_text(encoding="utf-8") == (
        '[project]\nname = ""\ncreated_by = "universal-memory"\n\n'
        '[hosts]\nenabled = [\n    "codex",\n    "claude_code",\n]\n'
    )


def test_setup_project_persists_selected_hosts(tmp_path: Path) -> None:
    setup_project(
        tmp_path,
        layout_port=LocalProjectLayoutPort(),
        config_validation_port=LocalConfigValidationPort(),
        enabled_host_ids=["codex"],
    )

    assert '[hosts]\nenabled = [\n    "codex",\n]\n' in (
        tmp_path / ".umem" / "config.toml"
    ).read_text(encoding="utf-8")


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
        ".umem/memory/latent_skills.jsonl",
    ]


def test_setup_project_fails_for_partial_layout_state(tmp_path: Path) -> None:
    (tmp_path / ".umem").mkdir()
    (tmp_path / ".umem" / "memory").mkdir()

    with pytest.raises(StorageError, match="partial or corrupted"):
        setup_project(
            tmp_path,
            layout_port=LocalProjectLayoutPort(),
            config_validation_port=LocalConfigValidationPort(),
        )
