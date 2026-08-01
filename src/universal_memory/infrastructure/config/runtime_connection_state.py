from __future__ import annotations

from pathlib import Path

from universal_memory.application.onboarding.execute_agent_connections import (
    PersistedConnections,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.infrastructure.config.toml_loader import (
    ConfigWriteOptions,
    load_config,
    update_project_config,
)


class LocalConnectionStatePort:
    def __init__(self, *, project_root: Path, safe_write_use_case: SafeWriteUseCase) -> None:
        self._project_root = project_root
        self._safe_write_use_case = safe_write_use_case

    def persist(self, agent_ids: list[str], *, origin: str) -> PersistedConnections:
        loaded = load_config(self._project_root)
        runtimes = loaded.project_data.get("runtimes")
        current = runtimes.get("enabled", []) if isinstance(runtimes, dict) else []
        enabled = list(dict.fromkeys([*(str(item) for item in current), *agent_ids]))
        updated = update_project_config(
            self._project_root,
            {"runtimes": {"enabled": enabled}},
            write_options=ConfigWriteOptions(
                safe_write_use_case=self._safe_write_use_case,
                origin=origin,
                action="connect_agents",
            ),
        )
        audit_reference = (
            updated.write_result.audit_reference if updated.write_result is not None else None
        )
        return PersistedConnections(
            agent_ids=tuple(enabled),
            audit_reference=audit_reference,
        )
