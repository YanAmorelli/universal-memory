from pathlib import Path

from universal_memory.application.onboarding import (
    AgentConnectionPlanner,
    DetectedAgent,
    OfficialSkillInstallerPlannerAdapter,
    RegistrySignalAgentDetector,
)
from universal_memory.application.skills.official_skill_distribution import (
    OfficialSkillEnvironment,
)
from universal_memory.domain.entities.runtime import default_runtime_registry


class StubDetector:
    def __init__(self, *agent_ids: str) -> None:
        self.agent_ids = agent_ids

    def detect(self, project_root: Path, runtimes):
        del project_root
        by_id = {runtime.runtime_id.value: runtime for runtime in runtimes}
        return [
            DetectedAgent(
                agent_id=agent_id,
                display_name=by_id[agent_id].display_name,
                detected_by=(f".{agent_id}",),
            )
            for agent_id in self.agent_ids
        ]


class SkillEnvironment:
    def __init__(self, *, external_available: bool) -> None:
        self.external_available = external_available

    def resolve(self, *, agent_id: str) -> OfficialSkillEnvironment:
        del agent_id
        return OfficialSkillEnvironment(
            node_available=self.external_available,
            npx_available=self.external_available,
            network_available=self.external_available,
            agent_mapping_available=self.external_available,
            agents_md_available=True,
            umem_native_available=True,
            manual_copy_available=True,
        )


def test_registry_signal_detector_uses_typed_project_signals(tmp_path: Path) -> None:
    (tmp_path / ".codex").mkdir()
    detector = RegistrySignalAgentDetector(which=lambda _name: None, home=tmp_path / "home")

    detected = detector.detect(tmp_path, tuple(default_runtime_registry().runtimes))

    assert [(item.agent_id, item.detected_by) for item in detected] == [("codex", (".codex",))]


def test_planner_maps_registry_capabilities_without_exposing_mechanics(tmp_path: Path) -> None:
    planner = AgentConnectionPlanner(
        registry=default_runtime_registry(),
        detector=StubDetector("codex", "cursor"),
    )

    plan = planner.plan(tmp_path)

    assert [item.agent_id for item in plan.recommended_connections] == ["codex", "cursor"]
    native, portable = plan.recommended_connections
    assert native.connection_method == "native"
    assert native.support_tier == "tier_1_native_managed"
    assert portable.connection_method == "directed_cli"
    assert portable.support_tier == "tier_2_directed_cli"
    assert plan.requires_confirmation is True
    assert plan.is_safe_and_unambiguous is True
    assert plan.external_actions == ()
    assert plan.manual_steps_pending == (
        {
            "agent_id": "cursor",
            "step": "Connect portable instructions later, then run umem doctor.",
        },
    )


def test_planner_is_idempotent_for_existing_instruction_connection(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "<!-- UMEM: START -->\nRun `umem context --scope project`.\n<!-- UMEM: END -->\n"
    )
    planner = AgentConnectionPlanner(
        registry=default_runtime_registry(),
        detector=StubDetector("codex"),
    )

    plan = planner.plan(tmp_path)

    assert [item.agent_id for item in plan.existing_connections] == ["codex"]
    assert plan.recommended_connections == ()
    assert plan.requires_confirmation is False


def test_planner_rejects_empty_managed_markers_as_an_existing_connection(
    tmp_path: Path,
) -> None:
    (tmp_path / "AGENTS.md").write_text("<!-- UMEM: START -->\n<!-- UMEM: END -->\n")
    planner = AgentConnectionPlanner(
        registry=default_runtime_registry(),
        detector=StubDetector("codex"),
    )

    plan = planner.plan(tmp_path)

    assert plan.existing_connections == ()
    assert [item.agent_id for item in plan.recommended_connections] == ["codex"]


def test_planner_validates_runtime_specific_target_content(tmp_path: Path) -> None:
    target = tmp_path / ".cursor" / "rules" / "universal-memory.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("unrelated rules")
    planner = AgentConnectionPlanner(
        registry=default_runtime_registry(),
        detector=StubDetector("cursor"),
    )

    invalid_plan = planner.plan(tmp_path)
    target.write_text(
        "<!-- UMEM: START -->\nUse `umem context --scope project`.\n<!-- UMEM: END -->\n"
    )
    valid_plan = planner.plan(tmp_path)

    assert invalid_plan.existing_connections == ()
    assert [item.agent_id for item in invalid_plan.recommended_connections] == ["cursor"]
    assert [item.agent_id for item in valid_plan.existing_connections] == ["cursor"]
    assert valid_plan.recommended_connections == ()


def test_explicit_selection_preserves_automation_without_detection(tmp_path: Path) -> None:
    planner = AgentConnectionPlanner(
        registry=default_runtime_registry(),
        detector=StubDetector(),
    )

    plan = planner.plan(tmp_path, selected_agent_ids=["claude_code", "cursor"])

    assert [item.agent_id for item in plan.detected_agents] == ["claude_code", "cursor"]
    assert all(item.detected_by == ("explicit_selection",) for item in plan.detected_agents)


def test_named_directed_agent_without_portable_channel_yields_manual_fallback(
    tmp_path: Path,
) -> None:
    planner = AgentConnectionPlanner(
        registry=default_runtime_registry(),
        detector=StubDetector("cursor"),
    )

    plan = planner.plan(tmp_path)

    assert plan.external_actions == ()
    assert plan.manual_steps_pending == (
        {
            "agent_id": "cursor",
            "step": "Connect portable instructions later, then run umem doctor.",
        },
    )


def test_generic_directed_agent_consumes_official_skill_distribution_plan(
    tmp_path: Path,
) -> None:
    installer = OfficialSkillInstallerPlannerAdapter(
        environment_port=SkillEnvironment(external_available=True)
    )
    planner = AgentConnectionPlanner(
        registry=default_runtime_registry(),
        detector=StubDetector(),
        external_skill_installer=installer,
    )

    plan = planner.plan(tmp_path, selected_agent_ids=["windsurf"])

    recommendation = plan.recommended_connections[0]
    assert recommendation.agent_id == "windsurf"
    assert recommendation.connection_method == "directed_cli"
    action = plan.external_actions[0]
    assert action.action == "external_action"
    assert action.channel == "npx_skills"
    assert action.argv[:2] == ("npx", "--yes")
    assert action.argv[2].startswith("skills@")
    assert action.argv[3] == "add"
    assert dict(action.environment) == {"DISABLE_TELEMETRY": "1"}
    assert action.readiness_checks == (
        "instruction_presence",
        "umem_cli_available",
        "project_context_read",
    )


def test_official_skill_distribution_falls_back_without_external_execution(
    tmp_path: Path,
) -> None:
    installer = OfficialSkillInstallerPlannerAdapter(
        environment_port=SkillEnvironment(external_available=False)
    )
    planner = AgentConnectionPlanner(
        registry=default_runtime_registry(),
        detector=StubDetector(),
        external_skill_installer=installer,
    )

    plan = planner.plan(tmp_path, selected_agent_ids=["windsurf"])

    action = plan.external_actions[0]
    assert action.action == "managed_fallback"
    assert action.channel == "agents_md"
    assert action.argv == ()
    assert action.mutation_owner == "umem_or_user"
