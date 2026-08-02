from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from universal_memory.application.skills.update_skill import _parse_skill_markdown
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkillScope
from universal_memory.domain.ports import AgentSkillRepository

SkillValidationStatus = Literal["pass", "warning", "fail"]
SkillFrontmatterStandard = Literal["umem", "agent_skills"]

_PLACEHOLDER_RE = re.compile(r"(TODO|TBD|FIXME|\\$ARGUMENTS|\\[.+?\\])", re.IGNORECASE)
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_ABSOLUTE_PATH_RE = re.compile(r"(?<![\w.-])/(?:[^/\s:]+/)+[^/\s:]+")
_RISKY_COMMAND_RE = re.compile(
    r"\b(rm\s+-rf|sudo\s+|curl\b.*\|\s*(?:sh|bash)|wget\b.*\|\s*(?:sh|bash))"
)
_AGENT_SKILLS_FRONTMATTER_KEYS = frozenset(
    {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
)


@dataclass(frozen=True, slots=True)
class SkillValidationCheck:
    name: str
    status: SkillValidationStatus
    message: str
    path: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {"name": self.name, "status": self.status, "message": self.message}
        if self.path is not None:
            payload["path"] = self.path
        return payload


@dataclass(frozen=True, slots=True)
class SkillValidationReport:
    subject: str
    status: SkillValidationStatus
    checks: list[SkillValidationCheck]
    blocking_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    affected_paths: list[str] = field(default_factory=list)
    recommended_next_steps: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "status": self.status,
            "checks": [check.to_payload() for check in self.checks],
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
            "affected_paths": self.affected_paths,
            "recommended_next_steps": self.recommended_next_steps,
        }


@dataclass(frozen=True, slots=True)
class ValidateSkillCommand:
    skill_or_path: str
    scope: LatentSkillScope | None = None


@dataclass(frozen=True, slots=True)
class ValidateSkillResult:
    report: SkillValidationReport

    def to_payload(self) -> dict[str, Any]:
        return {"validation": self.report.to_payload()}


class _ValidateSkillSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    skill_or_path: str = Field(min_length=1)
    scope: LatentSkillScope | None = None


class ValidateSkillUseCase:
    def __init__(self, *, project_root: Path, repository: AgentSkillRepository) -> None:
        self.project_root = project_root.resolve()
        self.repository = repository

    def execute(self, command: ValidateSkillCommand) -> ValidateSkillResult:
        validated = _ValidateSkillSchema.model_validate(command)
        subject = validated.skill_or_path.strip()
        skill_file = self._resolve_subject(subject, validated.scope)
        return ValidateSkillResult(
            report=validate_skill_tree(
                skill_file,
                project_root=self.project_root,
                subject=subject,
            )
        )

    def _resolve_subject(self, subject: str, scope: LatentSkillScope | None) -> Path:
        path = Path(subject)
        if not path.is_absolute():
            path = self.project_root / path
        if path.exists():
            return _skill_file_from_path(path)
        for skill in self.repository.list(scope=scope):
            if subject in {skill.id, skill.slug} or skill.name.casefold() == subject.casefold():
                base = self.project_root
                if skill.scope == LatentSkillScope.global_:
                    base = Path(getattr(self.repository, "global_data_root", self.project_root))
                relative_path = skill.draft_path or skill.canonical_path
                return base / relative_path
        raise ValidationFailedError(f"Skill or path not found: {subject}")


def validate_skill_tree(
    skill_file: Path,
    *,
    project_root: Path,
    subject: str | None = None,
    frontmatter_standard: SkillFrontmatterStandard = "umem",
) -> SkillValidationReport:
    skill_file = _skill_file_from_path(skill_file)
    skill_dir = skill_file.parent
    subject_name = subject or _relative_display(project_root, skill_file)
    checks: list[SkillValidationCheck] = []
    blocking: list[str] = []
    warnings: list[str] = []
    affected = [_relative_display(project_root, skill_file)]

    try:
        markdown = skill_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationFailedError(f"Failed to read SKILL.md: {subject_name}") from exc

    try:
        parsed = _parse_skill_markdown(markdown)
    except ValidationFailedError as exc:
        blocking.append(str(exc))
        checks.append(SkillValidationCheck("frontmatter", "fail", str(exc), affected[0]))
    else:
        checks.append(
            SkillValidationCheck(
                "frontmatter",
                "pass",
                f"Valid frontmatter for {parsed.name}.",
                affected[0],
            )
        )
        if not parsed.triggers and frontmatter_standard == "umem":
            warnings.append("Skill frontmatter has no triggers.")
            checks.append(
                SkillValidationCheck(
                    "triggers",
                    "warning",
                    "Add triggers so agents know when to use the skill.",
                    affected[0],
                )
            )
        elif parsed.triggers:
            checks.append(
                SkillValidationCheck("triggers", "pass", "Triggers are present.", affected[0])
            )
        if frontmatter_standard == "agent_skills":
            _check_agent_skills_frontmatter(markdown, affected[0], checks, blocking)

    _check_placeholders(markdown, affected[0], checks, blocking)
    _check_absolute_paths(markdown, affected[0], checks, warnings)
    _check_risky_commands(markdown, affected[0], checks, warnings)
    _check_links(markdown, skill_dir, project_root, checks, blocking, affected)

    if blocking:
        status: SkillValidationStatus = "fail"
    elif warnings:
        status = "warning"
    else:
        status = "pass"
    next_steps = _next_steps(status)
    return SkillValidationReport(
        subject=subject_name,
        status=status,
        checks=checks,
        blocking_issues=blocking,
        warnings=warnings,
        affected_paths=sorted(set(affected)),
        recommended_next_steps=next_steps,
    )


def assert_validation_passes(report: SkillValidationReport) -> None:
    if report.status == "fail":
        raise ValidationFailedError("; ".join(report.blocking_issues) or "Skill validation failed.")


def validate_slug(slug: str) -> str:
    normalized = slug.strip()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", normalized):
        raise ValidationFailedError(
            "Skill slug must use lowercase letters, numbers, and single hyphens."
        )
    return normalized


def validate_project_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValidationFailedError(
            f"Path must be project-relative and stay inside the project: {value}"
        )
    return path.as_posix()


def _skill_file_from_path(path: Path) -> Path:
    if path.is_dir():
        path = path / "SKILL.md"
    if path.name != "SKILL.md":
        raise ValidationFailedError("Skill path must be a SKILL.md file or skill directory.")
    if not path.is_file():
        raise ValidationFailedError(f"SKILL.md not found: {path.as_posix()}")
    return path.resolve()


def _check_placeholders(
    markdown: str,
    path: str,
    checks: list[SkillValidationCheck],
    blocking: list[str],
) -> None:
    if _PLACEHOLDER_RE.search(markdown):
        message = "Skill content contains placeholder markers."
        blocking.append(message)
        checks.append(SkillValidationCheck("placeholders", "fail", message, path))
        return
    checks.append(SkillValidationCheck("placeholders", "pass", "No placeholders found.", path))


def _check_agent_skills_frontmatter(
    markdown: str,
    path: str,
    checks: list[SkillValidationCheck],
    blocking: list[str],
) -> None:
    frontmatter = markdown.lstrip("\ufeff").replace("\r\n", "\n").split("---\n", 2)[1]
    keys = {
        line.split(":", 1)[0].strip()
        for line in frontmatter.splitlines()
        if line and not line[0].isspace() and ":" in line
    }
    unsupported = sorted(keys - _AGENT_SKILLS_FRONTMATTER_KEYS)
    if unsupported:
        message = "Agent Skills frontmatter contains unsupported fields: " + ", ".join(unsupported)
        blocking.append(message)
        checks.append(SkillValidationCheck("agent_skills_frontmatter", "fail", message, path))
        return
    checks.append(
        SkillValidationCheck(
            "agent_skills_frontmatter",
            "pass",
            "Frontmatter uses only open Agent Skills fields.",
            path,
        )
    )


def _check_absolute_paths(
    markdown: str,
    path: str,
    checks: list[SkillValidationCheck],
    warnings: list[str],
) -> None:
    if _ABSOLUTE_PATH_RE.search(markdown):
        message = "Skill content appears to contain absolute filesystem paths."
        warnings.append(message)
        checks.append(SkillValidationCheck("relative_paths", "warning", message, path))
        return
    checks.append(SkillValidationCheck("relative_paths", "pass", "No absolute paths found.", path))


def _check_risky_commands(
    markdown: str,
    path: str,
    checks: list[SkillValidationCheck],
    warnings: list[str],
) -> None:
    if _RISKY_COMMAND_RE.search(markdown):
        message = "Skill content contains commands that require extra human review."
        warnings.append(message)
        checks.append(SkillValidationCheck("risky_commands", "warning", message, path))
        return
    checks.append(
        SkillValidationCheck("risky_commands", "pass", "No risky command patterns found.", path)
    )


def _check_links(  # noqa: PLR0913
    markdown: str,
    skill_dir: Path,
    project_root: Path,
    checks: list[SkillValidationCheck],
    blocking: list[str],
    affected: list[str],
) -> None:
    links = [match.group(1).split("#", 1)[0] for match in _MARKDOWN_LINK_RE.finditer(markdown)]
    local_links = [
        link for link in links if link and "://" not in link and not link.startswith("mailto:")
    ]
    if not local_links:
        checks.append(SkillValidationCheck("local_links", "pass", "No local links to resolve."))
        return
    for link in local_links:
        link_path = Path(link)
        if link_path.is_absolute() or ".." in link_path.parts:
            message = f"Local link must stay inside the skill directory: {link}"
            blocking.append(message)
            checks.append(SkillValidationCheck("local_links", "fail", message))
            continue
        target = (skill_dir / link_path).resolve()
        try:
            target.relative_to(skill_dir.resolve())
        except ValueError:
            message = f"Local link resolves outside the skill directory: {link}"
            blocking.append(message)
            checks.append(SkillValidationCheck("local_links", "fail", message))
            continue
        if not target.exists():
            message = f"Local link target is missing: {link}"
            blocking.append(message)
            checks.append(SkillValidationCheck("local_links", "fail", message))
            continue
        affected.append(_relative_display(project_root, target))
    if not any(check.name == "local_links" and check.status == "fail" for check in checks):
        checks.append(SkillValidationCheck("local_links", "pass", "Local links resolve."))


def _next_steps(status: SkillValidationStatus) -> list[str]:
    if status == "fail":
        return ["Fix blocking issues, then run skills validate again."]
    if status == "warning":
        return ["Review warnings before publishing or syncing."]
    return ["Skill is ready for publish, adopt, update, or sync."]


def _relative_display(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
