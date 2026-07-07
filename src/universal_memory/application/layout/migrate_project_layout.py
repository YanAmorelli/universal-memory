from __future__ import annotations

import hashlib
import json
import os
import sys
import tomllib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import tomli_w
from pydantic import ValidationError

from universal_memory.application.security import SafeWriteCommand, SafeWriteUseCase
from universal_memory.domain import StorageError, ValidationFailedError
from universal_memory.domain.entities import (
    AgentSkill,
    AuditEventScope,
    Fact,
    FactScope,
    Rule,
    RuleScope,
)
from universal_memory.domain.project_layout import ProjectLayoutMigrationReport
from universal_memory.infrastructure.config.project_layout import (
    render_project_layout_metadata,
    resolve_project_layout,
)

MigrationInclude = Literal["facts", "rules", "skills"]
OPERATIONAL_SKILL_SLUGS = {"use-universal-memory"}


@dataclass(frozen=True, slots=True)
class MigrateProjectLayoutCommand:
    target_layout: Literal["shared"] = "shared"
    dry_run: bool = True
    include: tuple[MigrationInclude, ...] = ("facts", "rules", "skills")
    private_fact_ids: tuple[str, ...] = ()
    private_skill_slugs: tuple[str, ...] = ()
    shared_operational_skill_slugs: tuple[str, ...] = ()


class MigrateProjectLayoutUseCase:
    def __init__(
        self,
        *,
        project_root: Path,
        safe_write_use_case: SafeWriteUseCase | None = None,
        global_home: Path | None = None,
    ) -> None:
        self.project_root = project_root
        self.safe_write_use_case = safe_write_use_case
        self.global_home = global_home

    def execute(self, command: MigrateProjectLayoutCommand) -> dict[str, Any]:
        if command.target_layout != "shared":
            raise ValidationFailedError("Only migration to shared layout is supported.")
        if not command.include:
            raise ValidationFailedError("At least one content category must be included.")

        include = tuple(dict.fromkeys(command.include))
        invalid = set(include) - {"facts", "rules", "skills"}
        if invalid:
            raise ValidationFailedError(f"Unsupported migration include value: {sorted(invalid)}")

        layout = resolve_project_layout(self.project_root)
        copied: list[dict[str, str]] = []
        already_shared: list[dict[str, str]] = []
        skipped: list[dict[str, str]] = []
        conflicts: list[dict[str, str]] = []
        affected_paths: set[str] = {"umem/project.toml"}
        remaining_local: set[str] = set()

        if "facts" in include:
            self._migrate_facts(
                command=command,
                copied=copied,
                already_shared=already_shared,
                skipped=skipped,
                conflicts=conflicts,
                affected_paths=affected_paths,
                remaining_local=remaining_local,
            )
        if "rules" in include:
            self._migrate_rules(
                command=command,
                copied=copied,
                already_shared=already_shared,
                skipped=skipped,
                conflicts=conflicts,
                affected_paths=affected_paths,
                remaining_local=remaining_local,
            )
        if "skills" in include:
            self._migrate_skills(
                command=command,
                copied=copied,
                already_shared=already_shared,
                skipped=skipped,
                conflicts=conflicts,
                affected_paths=affected_paths,
                remaining_local=remaining_local,
            )

        self._report_global_records(include=include, skipped=skipped)

        if not command.dry_run:
            self._write_metadata(
                shared_operational_skill_slugs=command.shared_operational_skill_slugs
            )
            self._persist_report(
                copied=copied,
                already_shared=already_shared,
                skipped=skipped,
                conflicts=conflicts,
                remaining_local=remaining_local,
                affected_paths=affected_paths,
            )

        warnings = [
            f"{item['kind']} conflict for {item['id']} uses shared_over_legacy precedence."
            for item in conflicts
        ]
        next_steps = self._next_steps(command.dry_run, bool(conflicts))
        report = ProjectLayoutMigrationReport(
            operation="layout.migrate",
            source_layout=layout.policy.layout.value,
            target_layout=command.target_layout,
            dry_run=command.dry_run,
            copied=copied,
            already_shared=already_shared,
            skipped=skipped,
            conflicts=conflicts,
            remaining_local=sorted(remaining_local),
            affected_paths=sorted(affected_paths),
            next_steps=next_steps,
            warnings=warnings,
        )
        return {
            "operation": report.operation,
            "scope": "project",
            "data": asdict(report),
            "warnings": warnings,
        }

    def _migrate_facts(  # noqa: PLR0913
        self,
        *,
        command: MigrateProjectLayoutCommand,
        copied: list[dict[str, str]],
        already_shared: list[dict[str, str]],
        skipped: list[dict[str, str]],
        conflicts: list[dict[str, str]],
        affected_paths: set[str],
        remaining_local: set[str],
    ) -> None:
        layout = resolve_project_layout(self.project_root)
        legacy = self._load_jsonl_models(layout.legacy_facts_path, Fact)
        shared = {fact.id: fact for fact in self._load_jsonl_models(layout.shared_facts_path, Fact)}
        output = dict(shared)
        remaining_legacy: list[Fact] = []
        for fact in legacy:
            if fact.scope != FactScope.project:
                skipped.append(
                    self._item(
                        "fact",
                        fact.id,
                        "skipped_global",
                        layout.legacy_facts_path,
                    )
                )
                remaining_legacy.append(fact)
                continue
            if fact.id in command.private_fact_ids or fact.metadata.get("visibility") == "private":
                skipped.append(self._item("fact", fact.id, "private", layout.legacy_facts_path))
                remaining_local.add(self._relative(layout.legacy_facts_path))
                remaining_legacy.append(fact)
                continue
            candidate = self._shared_fact(fact, layout.shared_facts_path)
            existing = shared.get(fact.id)
            if existing is None:
                copied.append(self._item("fact", fact.id, "copied", layout.shared_facts_path))
                output[fact.id] = candidate
                affected_paths.add(self._relative(layout.shared_facts_path))
                affected_paths.add(self._relative(layout.legacy_facts_path))
                continue
            if self._entity_hash(candidate) == self._entity_hash(existing):
                already_shared.append(
                    self._item("fact", fact.id, "already_shared", layout.shared_facts_path)
                )
                affected_paths.add(self._relative(layout.legacy_facts_path))
            else:
                conflicts.append(
                    self._conflict(
                        "fact",
                        fact.id,
                        layout.legacy_facts_path,
                        layout.shared_facts_path,
                    )
                )
                remaining_local.add(self._relative(layout.legacy_facts_path))
                remaining_legacy.append(fact)
        if not command.dry_run and output != shared:
            self._write_jsonl(layout.shared_facts_path, list(output.values()))
        if not command.dry_run and remaining_legacy != legacy:
            self._write_jsonl(layout.legacy_facts_path, remaining_legacy)

    def _migrate_rules(  # noqa: PLR0913
        self,
        *,
        command: MigrateProjectLayoutCommand,
        copied: list[dict[str, str]],
        already_shared: list[dict[str, str]],
        skipped: list[dict[str, str]],
        conflicts: list[dict[str, str]],
        affected_paths: set[str],
        remaining_local: set[str],
    ) -> None:
        layout = resolve_project_layout(self.project_root)
        legacy = self._load_jsonl_models(layout.legacy_rules_path, Rule)
        shared = {rule.id: rule for rule in self._load_jsonl_models(layout.shared_rules_path, Rule)}
        output = dict(shared)
        for rule in legacy:
            if rule.scope != RuleScope.project:
                skipped.append(
                    self._item(
                        "rule",
                        rule.id,
                        "skipped_global",
                        layout.legacy_rules_path,
                    )
                )
                continue
            if rule.metadata.get("visibility") == "private":
                skipped.append(self._item("rule", rule.id, "private", layout.legacy_rules_path))
                remaining_local.add(self._relative(layout.legacy_rules_path))
                continue
            candidate = self._shared_rule(rule, layout.shared_rules_path)
            existing = shared.get(rule.id)
            if existing is None:
                copied.append(self._item("rule", rule.id, "copied", layout.shared_rules_path))
                output[rule.id] = candidate
                affected_paths.add(self._relative(layout.shared_rules_path))
                continue
            if self._entity_hash(candidate) == self._entity_hash(existing):
                already_shared.append(
                    self._item("rule", rule.id, "already_shared", layout.shared_rules_path)
                )
            else:
                conflicts.append(
                    self._conflict(
                        "rule",
                        rule.id,
                        layout.legacy_rules_path,
                        layout.shared_rules_path,
                    )
                )
                remaining_local.add(self._relative(layout.legacy_rules_path))
        if not command.dry_run and output != shared:
            self._write_jsonl(layout.shared_rules_path, list(output.values()))

    def _migrate_skills(  # noqa: PLR0913
        self,
        *,
        command: MigrateProjectLayoutCommand,
        copied: list[dict[str, str]],
        already_shared: list[dict[str, str]],
        skipped: list[dict[str, str]],
        conflicts: list[dict[str, str]],
        affected_paths: set[str],
        remaining_local: set[str],
    ) -> None:
        layout = resolve_project_layout(self.project_root)
        legacy = self._load_jsonl_models(layout.legacy_skills_registry_path, AgentSkill)
        shared = {
            skill.slug: skill
            for skill in self._load_jsonl_models(layout.shared_skills_registry_path, AgentSkill)
        }
        output = dict(shared)
        for skill in legacy:
            if skill.scope.value == "global":
                skipped.append(
                    self._item(
                        "skill",
                        skill.slug,
                        "skipped_global",
                        layout.legacy_skills_registry_path,
                    )
                )
                continue
            category = str(skill.metadata.get("category", "user-facing"))
            is_operational = category == "operational" or skill.slug in OPERATIONAL_SKILL_SLUGS
            explicitly_shared_operational = (
                is_operational and skill.slug in command.shared_operational_skill_slugs
            )
            if not explicitly_shared_operational and (
                skill.slug in command.private_skill_slugs
                or skill.metadata.get("visibility") == "private"
            ):
                skipped.append(
                    self._item(
                        "skill",
                        skill.slug,
                        "private",
                        layout.legacy_skills_registry_path,
                    )
                )
                remaining_local.add(self._relative(layout.legacy_skills_registry_path))
                continue
            if is_operational and skill.slug not in command.shared_operational_skill_slugs:
                skipped.append(
                    self._item(
                        "skill",
                        skill.slug,
                        "operational",
                        layout.legacy_skills_registry_path,
                    )
                )
                remaining_local.add(self._relative(layout.legacy_skills_registry_path))
                continue
            candidate = self._shared_skill(
                skill,
                layout.shared_skills_root / skill.slug / "SKILL.md",
            )
            existing = shared.get(skill.slug)
            if not self._legacy_skill_has_skill_file(skill):
                skipped.append(
                    self._item(
                        "skill",
                        skill.slug,
                        "invalid_missing_skill_file",
                        Path(skill.canonical_path),
                    )
                )
                remaining_local.add(self._relative(layout.legacy_skills_registry_path))
                continue
            if existing is None:
                copied.append(
                    self._item(
                        "skill",
                        skill.slug,
                        "copied",
                        layout.shared_skills_root / skill.slug,
                    )
                )
                output[skill.slug] = candidate
                affected_paths.add(self._relative(layout.shared_skills_registry_path))
                affected_paths.add(self._relative(layout.shared_skills_root / skill.slug))
                if not command.dry_run:
                    self._copy_skill_dir(skill, candidate)
                continue
            skill_dir_state = self._shared_skill_dir_state(skill, candidate)
            if (
                self._entity_hash(candidate) == self._entity_hash(existing)
                and skill_dir_state == "complete_match"
            ):
                already_shared.append(
                    self._item(
                        "skill",
                        skill.slug,
                        "already_shared",
                        layout.shared_skills_root / skill.slug,
                    )
                )
            elif (
                self._entity_hash(candidate) == self._entity_hash(existing)
                and skill_dir_state == "missing"
            ):
                copied.append(
                    self._item(
                        "skill",
                        skill.slug,
                        "copied_missing_shared_files",
                        layout.shared_skills_root / skill.slug,
                    )
                )
                affected_paths.add(self._relative(layout.shared_skills_root / skill.slug))
                if not command.dry_run:
                    self._copy_skill_dir(skill, candidate)
            else:
                conflicts.append(
                    self._conflict(
                        "skill",
                        skill.slug,
                        Path(skill.canonical_path),
                        Path(existing.canonical_path),
                    )
                )
                remaining_local.add(self._relative(layout.legacy_skills_registry_path))
        if not command.dry_run and output != shared:
            self._write_jsonl(layout.shared_skills_registry_path, list(output.values()))

    def _copy_skill_dir(self, legacy_skill: AgentSkill, shared_skill: AgentSkill) -> None:
        source = self.project_root / legacy_skill.canonical_path
        if source.name == "SKILL.md":
            source = source.parent
        target = self.project_root / shared_skill.canonical_path
        if target.name == "SKILL.md":
            target = target.parent
        skill_file = source / "SKILL.md"
        if not skill_file.is_file():
            raise StorageError(f"Legacy skill is missing {self._relative(skill_file)}")
        for source_file in sorted(file for file in source.rglob("*") if file.is_file()):
            relative_child = source_file.relative_to(source)
            target_file = target / relative_child
            try:
                content = source_file.read_text(encoding="utf-8")
            except UnicodeDecodeError as error:
                raise StorageError(
                    f"Migration only supports UTF-8 skill files: {self._relative(source_file)}"
                ) from error
            self._write_text(target_file, content, action="layout_migrate_skill_file")

    def _legacy_skill_has_skill_file(self, legacy_skill: AgentSkill) -> bool:
        source = self.project_root / legacy_skill.canonical_path
        if source.name == "SKILL.md":
            source = source.parent
        return (source / "SKILL.md").is_file()

    def _shared_skill_dir_state(
        self,
        legacy_skill: AgentSkill,
        shared_skill: AgentSkill,
    ) -> str:
        source = self.project_root / legacy_skill.canonical_path
        target = self.project_root / shared_skill.canonical_path
        if source.name == "SKILL.md":
            source = source.parent
        if target.name == "SKILL.md":
            target = target.parent
        if not source.exists() or not (source / "SKILL.md").is_file():
            return "missing"
        if not target.exists() or not (target / "SKILL.md").is_file():
            return "missing"
        if self._path_hash(source) == self._path_hash(target):
            return "complete_match"
        return "mismatch"

    def _report_global_records(
        self,
        *,
        include: tuple[MigrationInclude, ...],
        skipped: list[dict[str, str]],
    ) -> None:
        global_root = self._global_data_root()
        if "facts" in include:
            global_facts_path = global_root / "memory" / "facts.jsonl"
            for fact in self._load_jsonl_models(global_facts_path, Fact):
                skipped.append(
                    self._global_item("fact", fact.id, "skipped_global", global_facts_path)
                )
        if "rules" in include:
            global_rules_path = global_root / "memory" / "rules.jsonl"
            for rule in self._load_jsonl_models(global_rules_path, Rule):
                skipped.append(
                    self._global_item("rule", rule.id, "skipped_global", global_rules_path)
                )
        if "skills" in include:
            global_skills_path = global_root / "memory" / "skills.jsonl"
            for skill in self._load_jsonl_models(global_skills_path, AgentSkill):
                skipped.append(
                    self._global_item(
                        "skill",
                        skill.slug,
                        "skipped_global",
                        global_skills_path,
                    )
                )

    def _write_metadata(self, *, shared_operational_skill_slugs: tuple[str, ...]) -> None:
        project_toml = self.project_root / "umem" / "project.toml"
        data = self._load_project_toml_data(project_toml)
        data.update(
            {
                "schema_version": str(data.get("schema_version", "1")),
                "layout": "shared",
                "shared_root": str(data.get("shared_root", "umem")),
                "operational_root": str(data.get("operational_root", ".umem")),
                "precedence": str(data.get("precedence", "shared_over_legacy")),
            }
        )
        data.setdefault(
            "visibility_defaults",
            {
                "project_memories": "shared",
                "project_rules": "shared",
                "project_skills": "shared",
                "operational_skills": "private",
            },
        )
        existing_shared_operational = data.get("shared_operational_skills", [])
        if not isinstance(existing_shared_operational, list):
            existing_shared_operational = []
        data["shared_operational_skills"] = sorted(
            {*existing_shared_operational, *shared_operational_skill_slugs}
        )
        migration_data = data.get("migration")
        if not isinstance(migration_data, dict):
            migration_data = {}
        data["migration"] = {
            **migration_data,
            "status": "applied",
            "target_layout": "shared",
            "last_run_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "report_path": ".umem/layout/migration-report.json",
        }
        self._write_text(project_toml, tomli_w.dumps(data), action="layout_migrate_metadata")
        rendered = render_project_layout_metadata(layout="shared")
        if 'layout = "shared"' not in rendered:
            raise StorageError("Failed to render shared layout metadata.")

    def _load_project_toml_data(self, project_toml: Path) -> dict[str, Any]:
        if not project_toml.exists():
            return {}
        try:
            with project_toml.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as error:
            raise StorageError(f"Invalid TOML in umem/project.toml: {error}") from error
        except OSError as error:
            raise StorageError(f"Failed to read umem/project.toml: {error}") from error
        return dict(data)

    def _persist_report(  # noqa: PLR0913
        self,
        *,
        copied: list[dict[str, str]],
        already_shared: list[dict[str, str]],
        skipped: list[dict[str, str]],
        conflicts: list[dict[str, str]],
        remaining_local: set[str],
        affected_paths: set[str],
    ) -> None:
        report_path = self.project_root / ".umem" / "layout" / "migration-report.json"
        self._write_text(
            report_path,
            json.dumps(
                {
                    "operation": "layout.migrate",
                    "copied": copied,
                    "already_shared": already_shared,
                    "skipped": skipped,
                    "conflicts": conflicts,
                    "remaining_local": sorted(remaining_local),
                    "affected_paths": sorted(affected_paths),
                },
                sort_keys=True,
                indent=2,
            )
            + "\n",
            action="layout_migrate_report",
        )

    def _load_jsonl_models(
        self,
        path: Path,
        model: type[Fact] | type[Rule] | type[AgentSkill],
    ) -> list[Any]:
        if not path.exists():
            return []
        records: list[Any] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(model.model_validate(json.loads(line)))
            except (json.JSONDecodeError, ValidationError) as error:
                message = f"Corrupt migration candidate in {self._relative(path)}: {error}"
                raise StorageError(message) from error
        return records

    def _write_jsonl(self, path: Path, records: list[Any]) -> None:
        lines = [
            json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
            for record in records
        ]
        self._write_text(
            path,
            ("\n".join(lines) + "\n") if lines else "",
            action="layout_migrate_jsonl",
        )

    def _shared_fact(self, fact: Fact, path: Path) -> Fact:
        metadata = dict(fact.metadata)
        metadata.update(
            {
                "visibility": "shared",
                "storage_path": self._relative(path),
                "source_layout": "migrated_from_legacy",
            }
        )
        return fact.model_copy(update={"metadata": metadata})

    def _shared_rule(self, rule: Rule, path: Path) -> Rule:
        metadata = dict(rule.metadata)
        metadata.update(
            {
                "visibility": "shared",
                "storage_path": self._relative(path),
                "source_layout": "migrated_from_legacy",
            }
        )
        return rule.model_copy(update={"metadata": metadata})

    def _shared_skill(self, skill: AgentSkill, canonical_path: Path) -> AgentSkill:
        metadata = dict(skill.metadata)
        metadata.update(
            {
                "visibility": "shared",
                "category": metadata.get("category", "user-facing"),
                "source_layout": "migrated_from_legacy",
            }
        )
        return skill.model_copy(
            update={
                "canonical_path": self._relative(canonical_path),
                "metadata": metadata,
            }
        )

    def _entity_hash(self, entity: Any) -> str:
        payload = entity.model_dump(mode="json")
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def _path_hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        if path.is_file():
            digest.update(path.read_bytes())
            return digest.hexdigest()
        for child in sorted(file for file in path.rglob("*") if file.is_file()):
            digest.update(child.relative_to(path).as_posix().encode("utf-8"))
            digest.update(child.read_bytes())
        return digest.hexdigest()

    def _item(self, kind: str, id: str, reason: str, path: Path) -> dict[str, str]:
        return {"kind": kind, "id": id, "reason": reason, "path": self._relative(path)}

    def _global_item(self, kind: str, id: str, reason: str, path: Path) -> dict[str, str]:
        return {
            "kind": kind,
            "id": id,
            "reason": reason,
            "path": self._global_relative(path),
        }

    def _conflict(self, kind: str, id: str, legacy_path: Path, shared_path: Path) -> dict[str, str]:
        return {
            "kind": kind,
            "id": id,
            "reason": "content_mismatch",
            "legacy_path": self._relative(legacy_path),
            "shared_path": self._relative(shared_path),
            "precedence": "shared_over_legacy",
        }

    def _next_steps(self, dry_run: bool, has_conflicts: bool) -> list[str]:
        if has_conflicts:
            return ["Resolve reported conflicts before relying on migrated shared content."]
        if dry_run:
            return ["Review the report, then run umem layout migrate --to shared --apply."]
        return ["Review umem/ content and commit shared project memory intentionally."]

    def _global_data_root(self) -> Path:
        if self.global_home is not None:
            global_home = self.global_home
        elif "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
            global_home = self.project_root / ".umem_global_test_home"
        else:
            global_home = Path.home()
        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                return Path(local_appdata) / "umem"
            return global_home / "AppData" / "Local" / "umem"
        return global_home / ".local" / "share" / "umem"

    def _write_text(self, path: Path, content: str, *, action: str) -> None:
        if self.safe_write_use_case is None:
            raise StorageError("Safe write use case is required to apply layout migration.")
        self.safe_write_use_case.execute(
            SafeWriteCommand(
                relative_path=self._relative(path),
                content=content,
                scope=AuditEventScope.project,
                origin="migration",
                action=action,
            )
        )

    def _relative(self, path: Path) -> str:
        if not path.is_absolute():
            return path.as_posix()
        try:
            return path.resolve().relative_to(self.project_root.resolve()).as_posix()
        except ValueError:
            return self._global_relative(path)

    def _global_relative(self, path: Path) -> str:
        try:
            relative = path.resolve().relative_to(self._global_data_root().resolve())
        except ValueError:
            return "global:unknown"
        return f"global:{relative.as_posix()}"
