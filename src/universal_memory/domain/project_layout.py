from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ProjectLayoutMode(StrEnum):
    legacy = "legacy"
    shared = "shared"
    partial = "partial"
    uninitialized = "uninitialized"


class ProjectLayoutPrecedence(StrEnum):
    shared_over_legacy = "shared_over_legacy"


class ProjectMemoryVisibility(StrEnum):
    shared = "shared"
    private = "private"
    legacy = "legacy"


class ProjectSkillVisibility(StrEnum):
    shared = "shared"
    private = "private"


class ProjectSkillCategory(StrEnum):
    user_facing = "user-facing"
    operational = "operational"


@dataclass(frozen=True, slots=True)
class ProjectLayoutResult:
    created: bool
    created_paths: list[str]
    existing_paths: list[str]


@dataclass(frozen=True, slots=True)
class ProjectLayoutPolicy:
    schema_version: str
    layout: ProjectLayoutMode
    shared_root: str
    operational_root: str
    precedence: ProjectLayoutPrecedence
    shared_operational_skills: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolvedProjectLayout:
    project_root: Path
    policy: ProjectLayoutPolicy
    shared_root_path: Path
    operational_root_path: Path
    shared_memory_root: Path
    shared_skills_root: Path
    operational_memory_root: Path
    operational_skills_root: Path
    operational_locks_root: Path

    @property
    def is_shared(self) -> bool:
        return self.policy.layout == ProjectLayoutMode.shared

    @property
    def shared_facts_path(self) -> Path:
        return self.shared_memory_root / "facts.jsonl"

    @property
    def shared_rules_path(self) -> Path:
        return self.shared_memory_root / "rules.jsonl"

    @property
    def shared_skills_registry_path(self) -> Path:
        return self.shared_skills_root / "skills.jsonl"

    @property
    def legacy_facts_path(self) -> Path:
        return self.operational_memory_root / "facts.jsonl"

    @property
    def legacy_rules_path(self) -> Path:
        return self.operational_memory_root / "rules.jsonl"

    @property
    def legacy_skills_registry_path(self) -> Path:
        return self.operational_memory_root / "skills.jsonl"

    @property
    def private_facts_path(self) -> Path:
        return self.operational_memory_root / "private_facts.jsonl"

    @property
    def private_rules_path(self) -> Path:
        return self.operational_memory_root / "private_rules.jsonl"


@dataclass(frozen=True, slots=True)
class ProjectLayoutInspection:
    operation: str
    layout: str
    shared_root: str
    operational_root: str
    precedence: str
    warnings: list[str]
    recommended_actions: list[str]
