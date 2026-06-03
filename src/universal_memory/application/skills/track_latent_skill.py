from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.domain.ports import LatentSkillRepository

MATCH_THRESHOLD = 0.72
MAX_EVIDENCE_COUNT = 15


@dataclass(frozen=True, slots=True)
class TrackLatentSkillCommand:
    name: str
    description: str
    scope: LatentSkillScope
    origin: str
    evidence_summary: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TrackLatentSkillResult:
    latent_skill: LatentSkill
    matched_existing: bool
    audit_reference: str
    snapshot_reference: str


class TrackLatentSkillUseCase:
    def __init__(
        self,
        *,
        repository: LatentSkillRepository,
    ) -> None:
        self.repository = repository

    def execute(self, command: TrackLatentSkillCommand) -> TrackLatentSkillResult:
        command = self._validated(command)
        existing = self._find_high_confidence_match(command)
        if existing is None:
            skill = self._new_skill(command)
            matched_existing = False
        else:
            skill = self._increment_skill(existing, command)
            matched_existing = True

        write_result = self.repository.write(skill)
        audit_ref = "UNAUDITED"
        snapshot_ref = ""
        if write_result is not None:
            audit_ref = write_result.audit_reference
            snapshot_ref = write_result.snapshot_reference

        return TrackLatentSkillResult(
            latent_skill=skill,
            matched_existing=matched_existing,
            audit_reference=audit_ref,
            snapshot_reference=snapshot_ref,
        )

    @staticmethod
    def _validated(command: TrackLatentSkillCommand) -> TrackLatentSkillCommand:
        name = command.name.strip()
        description = command.description.strip()
        if not name or not description:
            raise ValidationFailedError("Skill name and description are required.")
        return replace(command, name=name, description=description)

    def _find_high_confidence_match(self, command: TrackLatentSkillCommand) -> LatentSkill | None:
        candidates = self.repository.list(scope=command.scope, status=LatentSkillStatus.proposed)
        candidates.extend(
            self.repository.list(scope=command.scope, status=LatentSkillStatus.active)
        )
        best: tuple[float, LatentSkill] | None = None
        command_text = f"{command.name} {command.description}"
        command_tags = set(command.tags)

        for candidate in candidates:
            score = self._similarity(command_text, f"{candidate.name} {candidate.description}")
            candidate_tags = set(candidate.metadata.get("tags", []))
            if command_tags and candidate_tags:
                overlap = len(command_tags & candidate_tags) / len(command_tags | candidate_tags)
                score = (score * 0.75) + (overlap * 0.25)
            if best is None or score > best[0]:
                best = (score, candidate)

        if best is not None and best[0] >= MATCH_THRESHOLD:
            return best[1]
        return None

    def _new_skill(self, command: TrackLatentSkillCommand) -> LatentSkill:
        timestamp = datetime.now(UTC)
        metadata = dict(command.metadata)
        metadata["tags"] = list(command.tags)
        metadata["evidence"] = [self._evidence(command)]
        return LatentSkill(
            id=str(uuid4()),
            created_at=timestamp,
            updated_at=timestamp,
            name=command.name,
            description=command.description,
            scope=command.scope,
            status=LatentSkillStatus.proposed,
            recurrence_count=1,
            metadata=metadata,
        )

    def _increment_skill(self, skill: LatentSkill, command: TrackLatentSkillCommand) -> LatentSkill:
        metadata = dict(skill.metadata)
        metadata["tags"] = sorted(set(metadata.get("tags", [])) | set(command.tags))
        evidence = list(metadata.get("evidence", []))
        evidence.append(self._evidence(command))
        if len(evidence) > MAX_EVIDENCE_COUNT:
            evidence = evidence[-MAX_EVIDENCE_COUNT:]
        metadata["evidence"] = evidence
        return skill.model_copy(
            update={
                "updated_at": datetime.now(UTC),
                "recurrence_count": skill.recurrence_count + 1,
                "metadata": metadata,
            }
        )

    @staticmethod
    def _evidence(command: TrackLatentSkillCommand) -> dict[str, str]:
        return {"origin": command.origin, "summary": command.evidence_summary}

    @classmethod
    def _similarity(cls, left: str, right: str) -> float:
        left_tokens = cls._tokens(left)
        right_tokens = cls._tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    @staticmethod
    def _tokens(value: str) -> set[str]:
        decomposed = unicodedata.normalize("NFKD", value)
        without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
        return set(re.findall(r"[a-z0-9]{2,}", without_accents.casefold()))
