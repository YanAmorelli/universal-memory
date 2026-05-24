from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectLayoutResult:
    created: bool
    created_paths: list[str]
    existing_paths: list[str]
