import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from universal_memory.domain import ConfigValidationPort, InvalidConfigError, ProjectLayoutPort
from universal_memory.infrastructure.config.toml_loader import update_project_config

DEFAULT_ENABLED_HOST_IDS = ["codex", "claude_code"]
DEFAULT_UMEM_SKILL_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_UMEM_SKILL_NAME = "use-universal-memory"
DEFAULT_UMEM_SKILL_RELATIVE_PATH = ".umem/skills/use-universal-memory/SKILL.md"
DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH = ".umem/memory/latent_skills.jsonl"
DEFAULT_UMEM_SKILL_MARKDOWN = """---
name: "use-universal-memory"
description: "Use umem to inspect project memory, skills, and durable learnings."
triggers:
  - "inicio de uma sessao de trabalho"
  - "antes de implementar, investigar ou revisar codigo"
  - "quando precisar entender memoria, fatos ou skills do projeto"
---

# Use Universal Memory

## Quando Usar

- No inicio de uma sessao de trabalho relevante.
- Antes de implementar, investigar, revisar codigo ou responder sobre decisoes do projeto.
- Quando o usuario pedir para consultar memoria, contexto, fatos, regras ou skills.
- Depois de descobrir uma decisao duravel que deve ser lembrada em trabalhos futuros.

## Procedimento

1. Rode `umem status` para confirmar que o projeto esta inicializado.
2. Rode `umem context --scope project` para carregar fatos e preferencias relevantes.
3. Rode `umem skills list` para ver skills registradas ou candidatas.
4. Se uma skill parecer relevante, rode `umem skills detail <nome-ou-id>` antes de agir.
5. Use `umem facts list --scope project` quando precisar auditar fatos individuais.
6. Durante ou ao final da atividade, revisar aprendizados duraveis e registrar apenas fatos
   curtos, verificaveis e nao sensiveis.

## Memoria Global Vs Memoria De Projeto

- Use `--scope global` para preferencias pessoais, estilo de comunicacao, informacoes
  duraveis sobre o usuario, habitos recorrentes e comportamentos que devem valer entre
  projetos.
- Use `--scope project` para decisoes, arquitetura, comandos, restricoes, tarefas, bugs,
  dominio e aprendizados especificos do repositorio atual.
- `umem context --scope project` carrega a memoria do projeto junto com preferencias globais
  relevantes.

## Exemplos

```bash
umem remember "Preferir respostas objetivas em portugues." --scope global --tag preference
umem remember "Projeto usa Firebase Admin/ADC backend-only." --scope project --tag architecture
```

## Criterios Para Registrar Memoria

- Registre decisoes arquiteturais, convencoes recorrentes e preferencias do usuario no
  escopo correto.
- Nao registre passos transitorios, outputs enormes, logs brutos, segredos, credenciais,
  dados pessoais sensiveis ou informacoes incertas.
- Prefira fatos verificaveis e curtos, com tags como `architecture`, `workflow` ou `bug`.

## Guardrails

- Nao rode `purge`, `rollback` ou `hygiene` sem confirmacao explicita do usuario.
- Nao cole dumps completos de memoria em arquivos de instrucao de host.
- Nao persista tokens, chaves, dumps de env, dados sensiveis ou fatos que voce nao verificou.
- Se `umem status` indicar problema de inicializacao, reporte isso antes de continuar.
"""


@dataclass(frozen=True, slots=True)
class SetupProjectResult:
    project_path: Path
    config_path: Path
    memory_path: Path
    audit_path: Path
    snapshots_path: Path
    skills_path: Path
    benchmarks_path: Path
    created: bool
    already_initialized: bool
    created_paths: list[str]
    existing_paths: list[str]


def setup_project(
    project_root: Path,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
    global_config_path: Path | None = None,
    enabled_host_ids: list[str] | None = None,
) -> SetupProjectResult:
    normalized_project_root = project_root.resolve()
    layout_result = layout_port.ensure_project_layout(normalized_project_root)
    seeded_skill_paths = _ensure_default_umem_skill(normalized_project_root)
    if enabled_host_ids is not None:
        unsupported = [h for h in enabled_host_ids if h not in DEFAULT_ENABLED_HOST_IDS]
        if unsupported:
            raise InvalidConfigError(f"Hosts nao suportados: {', '.join(unsupported)}")

    hosts_enabled = enabled_host_ids if enabled_host_ids is not None else DEFAULT_ENABLED_HOST_IDS
    update_project_config(
        normalized_project_root,
        {"hosts": {"enabled": hosts_enabled}},
        global_config_path=global_config_path,
    )

    # Validate config after materializing defaults so downstream adapters can rely on valid TOML.
    config_validation_port.validate_project_config(
        project_root=normalized_project_root,
        global_config_path=global_config_path,
    )

    umem_root = Path(".umem")
    return SetupProjectResult(
        project_path=Path("."),
        config_path=umem_root / "config.toml",
        memory_path=umem_root / "memory",
        audit_path=umem_root / "audit" / "events.jsonl",
        snapshots_path=umem_root / "snapshots",
        skills_path=umem_root / "skills",
        benchmarks_path=umem_root / "benchmarks",
        created=layout_result.created,
        already_initialized=not layout_result.created,
        created_paths=[*layout_result.created_paths, *seeded_skill_paths["created"]],
        existing_paths=[*layout_result.existing_paths, *seeded_skill_paths["existing"]],
    )


def _ensure_default_umem_skill(project_root: Path) -> dict[str, list[str]]:
    created: list[str] = []
    existing: list[str] = []

    skill_path = project_root / DEFAULT_UMEM_SKILL_RELATIVE_PATH
    if skill_path.exists():
        existing.append(DEFAULT_UMEM_SKILL_RELATIVE_PATH)
    else:
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(DEFAULT_UMEM_SKILL_MARKDOWN, encoding="utf-8")
        created.append(DEFAULT_UMEM_SKILL_RELATIVE_PATH)

    latent_skills_path = project_root / DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH
    if _default_umem_skill_is_registered(latent_skills_path):
        existing.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)
    else:
        latent_skills_path.parent.mkdir(parents=True, exist_ok=True)
        with latent_skills_path.open("a", encoding="utf-8") as file:
            file.write(_default_umem_skill_jsonl_line())
        created.append(DEFAULT_UMEM_LATENT_SKILLS_RELATIVE_PATH)

    return {"created": created, "existing": existing}


def _default_umem_skill_is_registered(latent_skills_path: Path) -> bool:
    if not latent_skills_path.exists():
        return False
    try:
        content = latent_skills_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return DEFAULT_UMEM_SKILL_ID in content or DEFAULT_UMEM_SKILL_NAME in content


def _default_umem_skill_jsonl_line() -> str:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = {
        "schema_version": 1,
        "id": DEFAULT_UMEM_SKILL_ID,
        "created_at": timestamp,
        "updated_at": timestamp,
        "name": DEFAULT_UMEM_SKILL_NAME,
        "description": (
            "Use umem to inspect project memory, available skills, and durable learnings "
            "before and after substantial work."
        ),
        "scope": "project",
        "status": "active",
        "recurrence_count": 1,
        "metadata": {
            "origin": "umem-init",
            "audit_reference": "seeded-by-init",
            "triggers": [
                "inicio de uma sessao de trabalho",
                "antes de implementar, investigar ou revisar codigo",
                "quando precisar entender memoria, fatos ou skills do projeto",
            ],
            "evidence": [
                {
                    "origin": "umem-init",
                    "summary": "Default operational skill installed during project initialization.",
                }
            ],
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
