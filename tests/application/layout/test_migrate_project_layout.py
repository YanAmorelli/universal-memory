from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.application.security.test_safe_write_use_case import (
    RecordingAuditRepository,
    RecordingScanner,
    RecordingSnapshotRepository,
)
from universal_memory.application.layout import (
    MigrateProjectLayoutCommand,
    MigrateProjectLayoutUseCase,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.domain import SecretDetectedError
from universal_memory.domain.entities import (
    AgentSkill,
    AgentSkillStatus,
    Fact,
    FactScope,
    FactStatus,
    LatentSkillScope,
    Rule,
    RuleScope,
    RuleStatus,
)

NOW = datetime(2026, 6, 30, tzinfo=UTC)
FACT_ID = "11111111-1111-4111-8111-111111111111"
PRIVATE_FACT_ID = "22222222-2222-4222-8222-222222222222"
GLOBAL_FACT_ID = "33333333-3333-4333-8333-333333333333"
RULE_ID = "44444444-4444-4444-8444-444444444444"
PRIVATE_RULE_ID = "55555555-5555-4555-8555-555555555555"
SKILL_ID = "66666666-6666-4666-8666-666666666666"
SHARED_SKILL_ID = "77777777-7777-4777-8777-777777777777"
OPERATIONAL_SKILL_ID = "88888888-8888-4888-8888-888888888888"
GLOBAL_SKILL_ID = "99999999-9999-4999-8999-999999999999"


def test_migration_dry_run_apply_and_second_apply_are_idempotent(tmp_path: Path) -> None:
    fact = _fact(FACT_ID, "Use shared project memory.")
    rule = _rule(RULE_ID, "Review shared root before commit.")
    skill = _skill(SKILL_ID, "review-helper")
    _write_legacy_project(tmp_path, facts=[fact], rules=[rule], skills=[skill])

    dry_run = _migrate(tmp_path, dry_run=True)

    assert dry_run["data"]["dry_run"] is True
    assert _ids(dry_run["data"]["copied"]) == {FACT_ID, RULE_ID, "review-helper"}
    assert not (tmp_path / "umem" / "memory" / "facts.jsonl").exists()

    applied = _migrate(tmp_path, dry_run=False)

    assert applied["data"]["dry_run"] is False
    assert _ids(applied["data"]["copied"]) == {FACT_ID, RULE_ID, "review-helper"}
    assert (tmp_path / "umem" / "project.toml").is_file()
    assert (tmp_path / "umem" / "memory" / "facts.jsonl").is_file()
    assert (tmp_path / "umem" / "memory" / "rules.jsonl").is_file()
    assert (tmp_path / "umem" / "skills" / "review-helper" / "SKILL.md").is_file()
    assert (tmp_path / ".umem" / "layout" / "migration-report.json").is_file()

    second_apply = _migrate(tmp_path, dry_run=False)

    assert second_apply["data"]["copied"] == []
    assert _ids(second_apply["data"]["already_shared"]) == {
        FACT_ID,
        RULE_ID,
        "review-helper",
    }
    assert len(_read_jsonl(tmp_path / "umem" / "memory" / "facts.jsonl")) == 1
    assert len(_read_jsonl(tmp_path / "umem" / "memory" / "rules.jsonl")) == 1
    assert len(_read_jsonl(tmp_path / "umem" / "skills" / "skills.jsonl")) == 1


def test_migration_apply_uses_safe_write_for_shared_and_operational_outputs(
    tmp_path: Path,
) -> None:
    scanner = RecordingScanner()
    snapshots = RecordingSnapshotRepository()
    audit = RecordingAuditRepository()
    fact = _fact(FACT_ID, "Use shared project memory.")
    rule = _rule(RULE_ID, "Review shared root before commit.")
    skill = _skill(SKILL_ID, "review-helper")
    _write_legacy_project(tmp_path, facts=[fact], rules=[rule], skills=[skill])

    result = _migrate(
        tmp_path,
        dry_run=False,
        safe_write_use_case=_safe_write(
            tmp_path,
            scanner=scanner,
            snapshots=snapshots,
            audit=audit,
        ),
    )

    assert result["data"]["copied"]
    scanned_targets = {entry.split(":", 1)[0] for entry in scanner.scanned}
    assert scanned_targets == {"migration"}
    snapshot_paths = {snapshot.relative_path for snapshot in snapshots.written}
    assert {
        "umem/project.toml",
        "umem/memory/facts.jsonl",
        "umem/memory/rules.jsonl",
        "umem/skills/skills.jsonl",
        "umem/skills/review-helper/SKILL.md",
        ".umem/layout/migration-report.json",
    } <= snapshot_paths
    assert all(event.result == "success" for event in audit.written)
    assert len(audit.written) == len(snapshots.written)


def test_migration_apply_blocks_secret_before_writing_shared_files(tmp_path: Path) -> None:
    fact = _fact(FACT_ID, "Use shared project memory.")
    _write_legacy_project(tmp_path, facts=[fact], rules=[], skills=[])
    safe_write = _safe_write(
        tmp_path,
        scanner=RecordingScanner(SecretDetectedError("blocked", metadata={"span": (0, 6)})),
    )

    with pytest.raises(SecretDetectedError):
        _migrate(tmp_path, dry_run=False, safe_write_use_case=safe_write)

    assert not (tmp_path / "umem" / "memory" / "facts.jsonl").exists()


def test_migration_reports_conflicting_fact_rule_and_skill(tmp_path: Path) -> None:
    legacy_fact = _fact(FACT_ID, "Legacy fact.")
    legacy_rule = _rule(RULE_ID, "Legacy rule.")
    legacy_skill = _skill(SKILL_ID, "review-helper")
    shared_fact = _fact(FACT_ID, "Shared fact.")
    shared_rule = _rule(RULE_ID, "Shared rule.")
    shared_skill = _skill(
        SHARED_SKILL_ID,
        "review-helper",
        canonical_path="umem/skills/review-helper/SKILL.md",
        content_hash="different",
        metadata={"visibility": "shared", "category": "user-facing"},
    )
    _write_legacy_project(tmp_path, facts=[legacy_fact], rules=[legacy_rule], skills=[legacy_skill])
    _write_shared_project(tmp_path, facts=[shared_fact], rules=[shared_rule], skills=[shared_skill])

    result = _migrate(tmp_path, dry_run=True)

    conflicts = result["data"]["conflicts"]
    assert {(item["kind"], item["id"]) for item in conflicts} == {
        ("fact", FACT_ID),
        ("rule", RULE_ID),
        ("skill", "review-helper"),
    }
    assert all(item["precedence"] == "shared_over_legacy" for item in conflicts)
    assert result["warnings"]


def test_migration_skips_global_private_and_operational_records(tmp_path: Path) -> None:
    _write_legacy_project(
        tmp_path,
        facts=[
            _fact(FACT_ID, "Shared fact."),
            _fact(PRIVATE_FACT_ID, "Private fact.", metadata={"visibility": "private"}),
        ],
        rules=[_rule(PRIVATE_RULE_ID, "Private rule.", metadata={"visibility": "private"})],
        skills=[
            _skill(SKILL_ID, "user-facing"),
            _skill(
                OPERATIONAL_SKILL_ID,
                "use-universal-memory",
                metadata={"visibility": "private", "category": "operational"},
            ),
        ],
    )
    _write_global_project(
        tmp_path,
        facts=[_fact(GLOBAL_FACT_ID, "Global fact.", scope=FactScope.global_)],
        skills=[_skill(GLOBAL_SKILL_ID, "global-helper", scope=LatentSkillScope.global_)],
    )

    result = _migrate(
        tmp_path,
        dry_run=False,
        private_fact_ids=(PRIVATE_FACT_ID,),
        private_skill_slugs=("use-universal-memory",),
    )

    skipped = {(item["kind"], item["id"], item["reason"]) for item in result["data"]["skipped"]}
    assert ("fact", PRIVATE_FACT_ID, "private") in skipped
    assert ("rule", PRIVATE_RULE_ID, "private") in skipped
    assert ("skill", "use-universal-memory", "private") in skipped
    assert ("fact", GLOBAL_FACT_ID, "skipped_global") in skipped
    assert ("skill", "global-helper", "skipped_global") in skipped
    assert not (tmp_path / "umem" / "skills" / "use-universal-memory").exists()
    assert all(not Path(item["path"]).is_absolute() for item in result["data"]["skipped"])
    assert str(tmp_path) not in json.dumps(result["data"]["skipped"])


def test_migration_can_share_private_operational_skill_when_explicitly_allowed(
    tmp_path: Path,
) -> None:
    operational_skill = _skill(
        OPERATIONAL_SKILL_ID,
        "use-universal-memory",
        metadata={"visibility": "private", "category": "operational"},
    )
    _write_legacy_project(tmp_path, facts=[], rules=[], skills=[operational_skill])

    result = _migrate(
        tmp_path,
        dry_run=False,
        shared_operational_skill_slugs=("use-universal-memory",),
    )

    assert _ids(result["data"]["copied"]) == {"use-universal-memory"}
    assert (tmp_path / "umem" / "skills" / "use-universal-memory" / "SKILL.md").is_file()
    project_toml = tomllib.loads((tmp_path / "umem" / "project.toml").read_text(encoding="utf-8"))
    assert "use-universal-memory" in project_toml["shared_operational_skills"]


def test_migration_rerun_restores_missing_shared_skill_file(tmp_path: Path) -> None:
    skill = _skill(SKILL_ID, "review-helper")
    _write_legacy_project(tmp_path, facts=[], rules=[], skills=[skill])
    _migrate(tmp_path, dry_run=False)
    missing_file = tmp_path / "umem" / "skills" / "review-helper" / "SKILL.md"
    missing_file.unlink()

    result = _migrate(tmp_path, dry_run=False)

    assert _ids(result["data"]["copied"]) == {"review-helper"}
    assert not result["data"]["already_shared"]
    assert missing_file.read_text(encoding="utf-8") == "# Skill\n"


def test_migration_preserves_existing_project_toml_policy(tmp_path: Path) -> None:
    fact = _fact(FACT_ID, "Use shared project memory.")
    _write_legacy_project(tmp_path, facts=[fact], rules=[], skills=[])
    (tmp_path / "umem").mkdir()
    (tmp_path / "umem" / "project.toml").write_text(
        "\n".join(
            [
                'schema_version = "1"',
                'layout = "shared"',
                'shared_root = "umem"',
                'operational_root = ".umem"',
                'precedence = "shared_over_legacy"',
                'shared_operational_skills = ["existing-op"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    _migrate(
        tmp_path,
        dry_run=False,
        shared_operational_skill_slugs=("new-op",),
    )

    project_toml = tomllib.loads((tmp_path / "umem" / "project.toml").read_text(encoding="utf-8"))
    assert project_toml["shared_operational_skills"] == ["existing-op", "new-op"]
    assert project_toml["migration"]["status"] == "applied"


def _migrate(  # noqa: PLR0913
    project_root: Path,
    *,
    dry_run: bool,
    private_fact_ids: tuple[str, ...] = (),
    private_skill_slugs: tuple[str, ...] = (),
    shared_operational_skill_slugs: tuple[str, ...] = (),
    safe_write_use_case: SafeWriteUseCase | None = None,
) -> dict:
    return MigrateProjectLayoutUseCase(
        project_root=project_root,
        safe_write_use_case=safe_write_use_case or _safe_write(project_root),
    ).execute(
        MigrateProjectLayoutCommand(
            dry_run=dry_run,
            private_fact_ids=private_fact_ids,
            private_skill_slugs=private_skill_slugs,
            shared_operational_skill_slugs=shared_operational_skill_slugs,
        )
    )


def _safe_write(
    project_root: Path,
    *,
    scanner: RecordingScanner | None = None,
    snapshots: RecordingSnapshotRepository | None = None,
    audit: RecordingAuditRepository | None = None,
) -> SafeWriteUseCase:
    return SafeWriteUseCase(
        project_root=project_root,
        secret_scanner=scanner or RecordingScanner(),
        snapshot_repository=snapshots or RecordingSnapshotRepository(),
        audit_log_repository=audit or RecordingAuditRepository(),
    )


def _write_legacy_project(
    project_root: Path,
    *,
    facts: list[Fact],
    rules: list[Rule],
    skills: list[AgentSkill],
) -> None:
    (project_root / ".umem" / "memory").mkdir(parents=True, exist_ok=True)
    (project_root / ".umem" / "skills").mkdir(parents=True, exist_ok=True)
    _write_jsonl(project_root / ".umem" / "memory" / "facts.jsonl", facts)
    _write_jsonl(project_root / ".umem" / "memory" / "rules.jsonl", rules)
    _write_jsonl(project_root / ".umem" / "memory" / "skills.jsonl", skills)
    for skill in skills:
        skill_dir = project_root / ".umem" / "skills" / skill.slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")


def _write_shared_project(
    project_root: Path,
    *,
    facts: list[Fact],
    rules: list[Rule],
    skills: list[AgentSkill],
) -> None:
    (project_root / "umem" / "memory").mkdir(parents=True, exist_ok=True)
    (project_root / "umem" / "skills").mkdir(parents=True, exist_ok=True)
    (project_root / "umem" / "project.toml").write_text(
        'schema_version = "1"\nlayout = "shared"\n',
        encoding="utf-8",
    )
    _write_jsonl(project_root / "umem" / "memory" / "facts.jsonl", facts)
    _write_jsonl(project_root / "umem" / "memory" / "rules.jsonl", rules)
    _write_jsonl(project_root / "umem" / "skills" / "skills.jsonl", skills)
    for skill in skills:
        skill_dir = project_root / "umem" / "skills" / skill.slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Different Skill\n", encoding="utf-8")


def _write_global_project(
    project_root: Path,
    *,
    facts: list[Fact],
    skills: list[AgentSkill],
) -> None:
    global_memory = project_root / ".umem_global_test_home" / ".local" / "share" / "umem" / "memory"
    global_memory.mkdir(parents=True)
    _write_jsonl(global_memory / "facts.jsonl", facts)
    _write_jsonl(global_memory / "skills.jsonl", skills)


def _write_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record.model_dump(mode="json"), sort_keys=True) + "\n" for record in records
        ),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _ids(items: list[dict[str, str]]) -> set[str]:
    return {item["id"] for item in items}


def _fact(
    id: str,
    content: str,
    *,
    scope: FactScope = FactScope.project,
    metadata: dict | None = None,
) -> Fact:
    return Fact(
        id=id,
        created_at=NOW,
        updated_at=NOW,
        content=content,
        scope=scope,
        source="test",
        status=FactStatus.active,
        metadata=metadata or {},
    )


def _rule(id: str, content: str, *, metadata: dict | None = None) -> Rule:
    return Rule(
        id=id,
        created_at=NOW,
        updated_at=NOW,
        name=id,
        content=content,
        scope=RuleScope.project,
        status=RuleStatus.active,
        metadata=metadata or {},
    )


def _skill(  # noqa: PLR0913
    id: str,
    slug: str,
    *,
    scope: LatentSkillScope = LatentSkillScope.project,
    canonical_path: str | None = None,
    content_hash: str = "hash",
    metadata: dict | None = None,
) -> AgentSkill:
    return AgentSkill(
        id=id,
        created_at=NOW,
        updated_at=NOW,
        name=slug.replace("-", " ").title(),
        slug=slug,
        description="Skill.",
        scope=scope,
        status=AgentSkillStatus.active,
        canonical_path=canonical_path or f".umem/skills/{slug}/SKILL.md",
        origin="test",
        audit_reference="audit-ref",
        content_hash=content_hash,
        metadata=metadata or {"category": "user-facing"},
    )
