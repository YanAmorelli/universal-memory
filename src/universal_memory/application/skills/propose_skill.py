import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.domain.ports import LatentSkillRepository
from universal_memory.infrastructure.config.toml_loader import (
    ConfigWriteOptions,
    LoadedConfig,
    update_project_config,
)


class ProposeSkillDecision(StrEnum):
    sim = "sim"
    sempre = "sempre"
    nao = "nao"


@dataclass(frozen=True, slots=True)
class ProposeSkillCommand:
    latent_skill_id: str
    origin: str
    decision: ProposeSkillDecision | None = None


@dataclass(frozen=True, slots=True)
class ProposeSkillResult:
    latent_skill: LatentSkill
    proposal: dict[str, Any]
    choices: list[str] = field(default_factory=lambda: ["Sim", "Sempre", "Não"])
    requires_decision: bool = False
    accepted: bool = False
    auto_approval_recorded: bool = False
    audit_reference: str = ""
    snapshot_reference: str = ""
    rollback_hint: str | None = None


class ProposeSkillUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        repository: LatentSkillRepository,
        safe_write_use_case: SafeWriteUseCase,
    ) -> None:
        self.project_root = project_root
        self.repository = repository
        self.safe_write_use_case = safe_write_use_case

    def execute(self, command: ProposeSkillCommand) -> ProposeSkillResult:
        skill = self.repository.read(command.latent_skill_id)

        # State Transition Validation
        if skill.status != LatentSkillStatus.proposed and command.decision is not None:
            raise ValidationFailedError(
                f"Nao e possivel propor ou decidir sobre a latent skill {skill.id} "
                f"porque ela ja esta no status {skill.status.value}."
            )

        proposal = self._proposal_for(skill)
        if command.decision is None:
            return ProposeSkillResult(
                latent_skill=skill,
                proposal=proposal,
                requires_decision=True,
            )

        updated = self._apply_decision(skill, command)

        # Consistent transaction sequence of operations
        try:
            write_result = self.repository.write(updated)
        except Exception as exc:
            raise exc

        audit_reference = write_result.audit_reference if write_result is not None else "UNAUDITED"
        snapshot_reference = write_result.snapshot_reference if write_result is not None else ""
        auto_approval_recorded = False
        rollback_hint = None

        if command.decision == ProposeSkillDecision.sempre:
            try:
                config_loaded = self._record_auto_approval(updated, command)
                auto_approval_recorded = True
                if config_loaded.write_result is not None:
                    # Combine snapshot and audit references
                    snapshot_reference = (
                        f"{snapshot_reference}, {config_loaded.write_result.snapshot_reference}"
                    )
                    audit_reference = (
                        f"{audit_reference}, {config_loaded.write_result.audit_reference}"
                    )
                rollback_hint = "Use o snapshot registrado para reverter a preferencia."
            except Exception as exc:
                # Rollback repository update to proposed on configuration failure
                try:
                    self.repository.write(skill)
                except Exception as rollback_err:
                    exc.add_note(f"Failed to rollback latent skill status: {rollback_err}")
                raise exc

        return ProposeSkillResult(
            latent_skill=updated,
            proposal=proposal,
            requires_decision=False,
            accepted=command.decision in {ProposeSkillDecision.sim, ProposeSkillDecision.sempre},
            auto_approval_recorded=auto_approval_recorded,
            audit_reference=audit_reference,
            snapshot_reference=snapshot_reference,
            rollback_hint=rollback_hint,
        )

    def _apply_decision(
        self,
        skill: LatentSkill,
        command: ProposeSkillCommand,
    ) -> LatentSkill:
        status = (
            LatentSkillStatus.ignored
            if command.decision == ProposeSkillDecision.nao
            else LatentSkillStatus.active
        )
        metadata = dict(skill.metadata) if skill.metadata is not None else {}
        metadata["approval"] = {
            "decision": command.decision.value if command.decision is not None else "",
            "origin": command.origin,
            "decided_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        # Reconstruct to trigger Pydantic validation
        dump = skill.model_dump()
        dump.update(
            {
                "status": status,
                "updated_at": datetime.now(UTC),
                "metadata": metadata,
            }
        )
        return LatentSkill.model_validate(dump)

    def _record_auto_approval(
        self,
        skill: LatentSkill,
        command: ProposeSkillCommand,
    ) -> LoadedConfig:
        preference_key = f"{skill.scope.value}:{self._slug(skill.name)}"
        scope_str = "global" if skill.scope == LatentSkillScope.global_ else "project"
        return update_project_config(
            self.project_root,
            {
                "skills": {
                    "auto_approval": {
                        preference_key: {
                            "name": skill.name,
                            "scope": skill.scope.value,
                            "pattern": skill.name,
                            "decision": ProposeSkillDecision.sempre.value,
                            "origin": command.origin,
                            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                            "reversible": True,
                        }
                    }
                }
            },
            write_options=ConfigWriteOptions(
                safe_write_use_case=self.safe_write_use_case,
                origin=command.origin,
                action="update_skill_auto_approval",
                scope=scope_str,
            ),
        )

    @staticmethod
    def _proposal_for(skill: LatentSkill) -> dict[str, Any]:
        metadata = skill.metadata if skill.metadata is not None else {}
        return {
            "suggested_name": skill.name,
            "purpose": skill.description,
            "scope": skill.scope.value,
            "evidence": [
                str(item.get("summary", ""))
                for item in metadata.get("evidence", [])
                if isinstance(item, dict) and item.get("summary")
            ],
        }

    @staticmethod
    def _slug(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value)
        ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
        if not slug:
            h = hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
            return f"skill-{h}"
        return slug
