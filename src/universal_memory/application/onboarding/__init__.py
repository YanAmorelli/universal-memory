"""Onboarding use cases for universal-memory."""

from universal_memory.application.onboarding.setup_project import (
    SetupProjectResult,
    setup_project,
)

__all__ = ["SetupProjectResult", "setup_project"]
from universal_memory.application.onboarding.agent_connections import (
    AgentConnectionPlan,
    AgentConnectionPlanner,
    AgentDetectorPort,
    ConnectionRecommendation,
    DetectedAgent,
    ExternalSkillAction,
    ExternalSkillInstallerPort,
    OfficialSkillAgentMapping,
    OfficialSkillAgentMappingPort,
    OfficialSkillEnvironmentPort,
    OfficialSkillInstallerPlannerAdapter,
    RegistrySignalAgentDetector,
    UnavailableExternalSkillInstaller,
    default_agent_connection_planner,
)
from universal_memory.application.onboarding.execute_agent_connections import (
    AgentConnectionExecution,
    ConnectionStatePort,
    ExecuteAgentConnectionsUseCase,
    ExternalActionExecution,
    ExternalActionExecutorPort,
    McpAvailabilityPort,
    PendingExternalActionExecutor,
    PersistedConnections,
    UnavailableMcpAvailability,
)

__all__ = [
    "AgentConnectionExecution",
    "AgentConnectionPlan",
    "AgentConnectionPlanner",
    "AgentDetectorPort",
    "ConnectionRecommendation",
    "ConnectionStatePort",
    "DetectedAgent",
    "ExecuteAgentConnectionsUseCase",
    "ExternalActionExecution",
    "ExternalActionExecutorPort",
    "ExternalSkillAction",
    "ExternalSkillInstallerPort",
    "McpAvailabilityPort",
    "OfficialSkillAgentMapping",
    "OfficialSkillAgentMappingPort",
    "OfficialSkillEnvironmentPort",
    "OfficialSkillInstallerPlannerAdapter",
    "PendingExternalActionExecutor",
    "PersistedConnections",
    "RegistrySignalAgentDetector",
    "UnavailableExternalSkillInstaller",
    "UnavailableMcpAvailability",
    "default_agent_connection_planner",
]
