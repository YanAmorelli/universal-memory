from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from universal_memory.application.skills import (
    GetSkillDetailCommand,
    GetSkillDetailUseCase,
    ListSkillsCommand,
    ListSkillsUseCase,
)
from universal_memory.domain import ValidationFailedError
from universal_memory.domain.entities import LatentSkill, LatentSkillScope, LatentSkillStatus
from universal_memory.domain.ports import LatentSkillRepository


class InMemoryLatentSkillRepository(LatentSkillRepository):
    def __init__(self, skills: list[LatentSkill] | None = None) -> None:
        self.skills = skills or []

    def read(self, id: str) -> LatentSkill:
        for skill in self.skills:
            if skill.id == id:
                return skill
        raise KeyError(id)

    def list(
        self, scope: LatentSkillScope | None = None, status: LatentSkillStatus | None = None
    ) -> list[LatentSkill]:
        skills = self.skills
        if scope is not None:
            skills = [skill for skill in skills if skill.scope == scope]
        if status is not None:
            skills = [skill for skill in skills if skill.status == status]
        return skills

    def write(self, entity: LatentSkill) -> None:
        self.skills.append(entity)

    def delete(self, id: str) -> None:
        self.skills = [skill for skill in self.skills if skill.id != id]

    def migrate(self, target_version: int) -> None:
        return None


def make_skill(
    *,
    name: str,
    scope: LatentSkillScope,
    status: LatentSkillStatus,
    created_at: datetime,
    metadata: dict[str, object] | None = None,
) -> LatentSkill:
    return LatentSkill(
        id=str(uuid4()),
        created_at=created_at,
        updated_at=created_at + timedelta(minutes=5),
        name=name,
        description=f"Descricao de {name}",
        scope=scope,
        status=status,
        recurrence_count=3,
        metadata=metadata or {},
    )


def test_list_skills_empty_returns_recommended_action(tmp_path: Path) -> None:
    use_case = ListSkillsUseCase(
        project_root=tmp_path,
        repository=InMemoryLatentSkillRepository(),
    )

    result = use_case.execute(ListSkillsCommand())

    assert result.to_payload() == {
        "skills": [],
        "recommended_action": (
            "Execute `umem skills propose <latent_skill_id>` para revisar uma skill candidata."
        ),
    }


def test_list_skills_maps_status_scope_paths_and_audit_reference(tmp_path: Path) -> None:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    local_active = make_skill(
        name="TDD Recorrente",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.active,
        created_at=now,
        metadata={"audit_reference": "audit-local", "origin": "cli"},
    )
    local_skill_file = tmp_path / ".umem" / "skills" / "tdd-recorrente" / "SKILL.md"
    local_skill_file.parent.mkdir(parents=True)
    local_skill_file.write_text("---\ntriggers:\n  - tdd\n---\n", encoding="utf-8")
    global_active = make_skill(
        name="Review Profundo",
        scope=LatentSkillScope.global_,
        status=LatentSkillStatus.active,
        created_at=now + timedelta(minutes=1),
        metadata={"audit_reference": "audit-global", "origin": "mcp"},
    )
    global_skill_file = tmp_path / "skills" / "review-profundo" / "SKILL.md"
    global_skill_file.parent.mkdir(parents=True)
    global_skill_file.write_text("---\ntriggers:\n  - review\n---\n", encoding="utf-8")
    candidate = make_skill(
        name="Brainstorm Guiado",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.proposed,
        created_at=now + timedelta(minutes=2),
        metadata={"audit_reference": "audit-candidate", "origin": "tracker"},
    )
    disabled = make_skill(
        name="Formato Antigo",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.ignored,
        created_at=now + timedelta(minutes=3),
        metadata={"audit_reference": "audit-disabled", "origin": "cli"},
    )
    repository = InMemoryLatentSkillRepository([disabled, candidate, global_active, local_active])
    use_case = ListSkillsUseCase(project_root=tmp_path, repository=repository)

    payload = use_case.execute(ListSkillsCommand()).to_payload()

    assert [skill["name"] for skill in payload["skills"]] == [
        "TDD Recorrente",
        "Review Profundo",
        "Brainstorm Guiado",
        "Formato Antigo",
    ]
    assert payload["skills"][0] == {
        "name": "TDD Recorrente",
        "scope": "project",
        "status": "active",
        "relative_path": ".umem/skills/tdd-recorrente/SKILL.md",
        "created_at": "2026-05-29T12:00:00Z",
        "updated_at": "2026-05-29T12:05:00Z",
        "origin": "cli",
        "audit_reference": "audit-local",
    }
    assert payload["skills"][1]["relative_path"] == "skills/review-profundo/SKILL.md"
    assert payload["skills"][2]["status"] == "candidate"
    assert payload["skills"][2]["relative_path"] is None
    assert payload["skills"][3]["status"] == "disabled"


def test_get_skill_detail_reads_triggers_without_loading_references(tmp_path: Path) -> None:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    skill = make_skill(
        name="TDD Recorrente",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.active,
        created_at=now,
        metadata={
            "audit_reference": "audit-1",
            "origin": "cli",
            "triggers": ["metadata fallback"],
        },
    )
    skill_dir = tmp_path / ".umem" / "skills" / "tdd-recorrente"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: TDD Recorrente\n"
        "triggers:\n"
        "  - red green refactor\n"
        "  - implementar story\n"
        "---\n"
        "# TDD Recorrente\n",
        encoding="utf-8",
    )
    references_dir = skill_dir / "references"
    references_dir.mkdir()
    (references_dir / "large.md").write_text(
        "conteudo que nao deve ser carregado",
        encoding="utf-8",
    )

    result = GetSkillDetailUseCase(
        project_root=tmp_path,
        repository=InMemoryLatentSkillRepository([skill]),
    ).execute(GetSkillDetailCommand(name_or_id="TDD Recorrente"))

    assert result.to_payload() == {
        "name": "TDD Recorrente",
        "scope": "project",
        "status": "active",
        "relative_path": ".umem/skills/tdd-recorrente/SKILL.md",
        "triggers": ["red green refactor", "implementar story"],
        "audit_reference": "audit-1",
        "references_loaded": False,
    }


def test_list_skills_resolves_materialized_skill_file_with_alternate_slug(tmp_path: Path) -> None:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    skill = make_skill(
        name="TDD Recorrente",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.active,
        created_at=now,
        metadata={"audit_reference": "audit-1", "origin": "cli"},
    )
    skill_file = tmp_path / ".umem" / "skills" / "tdd-recorrente-2" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "---\nname: \"TDD Recorrente\"\ntriggers:\n  - tdd\n---\n",
        encoding="utf-8",
    )

    payload = ListSkillsUseCase(
        project_root=tmp_path,
        repository=InMemoryLatentSkillRepository([skill]),
    ).execute(ListSkillsCommand()).to_payload()

    assert payload["skills"][0]["relative_path"] == ".umem/skills/tdd-recorrente-2/SKILL.md"


def test_get_skill_detail_rejects_ambiguous_skill_name(tmp_path: Path) -> None:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    shared_name = "TDD Recorrente"
    repository = InMemoryLatentSkillRepository(
        [
            make_skill(
                name=shared_name,
                scope=LatentSkillScope.project,
                status=LatentSkillStatus.active,
                created_at=now,
            ),
            make_skill(
                name=shared_name,
                scope=LatentSkillScope.global_,
                status=LatentSkillStatus.ignored,
                created_at=now + timedelta(minutes=1),
            ),
        ]
    )

    use_case = GetSkillDetailUseCase(project_root=tmp_path, repository=repository)

    try:
        use_case.execute(GetSkillDetailCommand(name_or_id=shared_name))
    except ValidationFailedError as error:
        assert "Informe o ID" in str(error)
    else:
        raise AssertionError("Expected ambiguous skill name to fail")


def test_get_skill_detail_reads_triggers_from_bom_crlf_and_escaped_yaml(tmp_path: Path) -> None:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    skill = make_skill(
        name="TDD Recorrente",
        scope=LatentSkillScope.project,
        status=LatentSkillStatus.active,
        created_at=now,
        metadata={"audit_reference": "audit-1", "origin": "cli"},
    )
    skill_dir = tmp_path / ".umem" / "skills" / "tdd-recorrente"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "\ufeff---\r\n"
        'name: "TDD Recorrente"\r\n'
        'triggers:\r\n'
        '  - "red \\\"green\\\" refactor"\r\n'
        '  - "linha 1\\nlinha 2"\r\n'
        '---\r\n'
        '# TDD Recorrente\r\n',
        encoding="utf-8",
    )

    result = GetSkillDetailUseCase(
        project_root=tmp_path,
        repository=InMemoryLatentSkillRepository([skill]),
    ).execute(GetSkillDetailCommand(name_or_id="TDD Recorrente"))

    assert result.triggers == ['red "green" refactor', "linha 1\nlinha 2"]
