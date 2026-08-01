from hashlib import sha256
from pathlib import PurePosixPath

from universal_memory.application.skills.official_skill_distribution import (
    OFFICIAL_SKILLS_CLI_PACKAGE,
)
from universal_memory.infrastructure.onboarding.official_skill_bridge import (
    DEFAULT_OFFICIAL_SKILL_MAPPINGS,
    StaticOfficialSkillMappingPort,
)
from universal_memory.infrastructure.onboarding.pinned_skills_catalog import (
    PINNED_SKILLS_AGENTS,
    PINNED_SKILLS_CATALOG_PACKAGE,
)

EXPECTED_REVIEWED_AGENT_COUNT = 75
EXPECTED_ID_PATH_SNAPSHOT = "d85cd33c7dd0eccd8cb949091800653433b341b9d7e7f03cddfc29f5aff9a1eb"


def test_catalog_is_atomic_with_the_pinned_installer_and_has_safe_project_targets() -> None:
    assert PINNED_SKILLS_CATALOG_PACKAGE == OFFICIAL_SKILLS_CLI_PACKAGE
    assert len(PINNED_SKILLS_AGENTS) == EXPECTED_REVIEWED_AGENT_COUNT
    snapshot = "\n".join(
        f"{agent_id}\0{agent.project_skills_directory}"
        for agent_id, agent in sorted(PINNED_SKILLS_AGENTS.items())
    )
    assert sha256(snapshot.encode()).hexdigest() == EXPECTED_ID_PATH_SNAPSHOT

    for agent_id, agent in PINNED_SKILLS_AGENTS.items():
        path = PurePosixPath(agent.project_skills_directory)
        assert agent_id
        assert agent.display_name.strip()
        assert not path.is_absolute()
        assert ".." not in path.parts
        assert agent.instruction_target == (
            f"{agent.project_skills_directory}/universal-memory/SKILL.md"
        )


def test_catalog_resolves_known_agents_and_rejects_unknown_ids() -> None:
    mappings = StaticOfficialSkillMappingPort(DEFAULT_OFFICIAL_SKILL_MAPPINGS)

    zed = mappings.get(agent_id="zed")

    assert zed is not None
    assert zed.display_name == "Zed"
    assert zed.instruction_targets == (".agents/skills/universal-memory/SKILL.md",)
    assert mappings.get(agent_id="made-up-agent") is None


def test_windsurf_remains_the_only_legacy_detection_adapter() -> None:
    assert [mapping.agent_id for mapping in DEFAULT_OFFICIAL_SKILL_MAPPINGS] == ["windsurf"]
    assert DEFAULT_OFFICIAL_SKILL_MAPPINGS[0].detection_paths == (".windsurf",)
    assert DEFAULT_OFFICIAL_SKILL_MAPPINGS[0].instruction_targets == (
        ".windsurf/skills/universal-memory/SKILL.md",
    )
