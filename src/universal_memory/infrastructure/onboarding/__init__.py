"""Infrastructure adapters for optional onboarding bridges."""

from universal_memory.infrastructure.onboarding.official_skill_bridge import (
    DEFAULT_OFFICIAL_SKILL_MAPPINGS,
    ExternalActionAuditPort,
    LocalExternalActionAuditPort,
    LocalOfficialSkillConnectionStatePort,
    LocalOfficialSkillEnvironmentProbe,
    OfficialSkillBridgeMapping,
    OfficialSkillConnectionStatePort,
    OfficialSkillExternalActionExecutor,
    OfficialSkillMappedAgentDetector,
    StaticOfficialSkillMappingPort,
    StoredOfficialSkillConnection,
)

__all__ = [
    "DEFAULT_OFFICIAL_SKILL_MAPPINGS",
    "ExternalActionAuditPort",
    "LocalExternalActionAuditPort",
    "LocalOfficialSkillConnectionStatePort",
    "LocalOfficialSkillEnvironmentProbe",
    "OfficialSkillBridgeMapping",
    "OfficialSkillConnectionStatePort",
    "OfficialSkillExternalActionExecutor",
    "OfficialSkillMappedAgentDetector",
    "StaticOfficialSkillMappingPort",
    "StoredOfficialSkillConnection",
]
