# Alpha Sandbox Test Plan

Objetivo: testar o `universal-memory` como usuario real, usando `umem` e `umem-mcp`, sem `pytest`, com validacoes por saida JSON, exit code e inspecao dos arquivos gerados.

## 1. Preparacao Do Sandbox

Criar um ambiente isolado:

```bash
SANDBOX="$(mktemp -d /tmp/umem-smoke.XXXXXX)"
PROJECT="$SANDBOX/project"
HOME_SANDBOX="$SANDBOX/home"

mkdir -p "$PROJECT" "$HOME_SANDBOX"
cd "$PROJECT"

export HOME="$HOME_SANDBOX"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
```

Executar comandos via pacote local:

```bash
uv sync
uv run umem --help
uv run umem-mcp --help
```

Validar:

- `umem --help` lista comandos principais.
- `umem-mcp` sobe sem erro quando iniciado pelo cliente MCP.
- Nenhum arquivo e criado fora de `$SANDBOX`.

## 2. Smoke CLI Basico

Comandos:

```bash
uv run umem status --format json
uv run umem init --yes --hosts codex --hosts claude_code --format json
uv run umem status --format json
```

Validar:

- Antes do `init`, `initialized=false` ou recomendacao de inicializacao.
- Depois do `init`, existem `.umem/config.toml`, `.umem/memory/`, `.umem/audit/events.jsonl`, `.umem/snapshots/`, `.umem/skills/` e `.umem/benchmarks/retrieval-results.json`.
- `.umem/config.toml` contem hosts habilitados `codex` e `claude_code`.
- Reexecutar `umem init --yes --format json` e idempotente e nao corrompe o layout.

## 3. Memoria Local E Global

Comandos:

```bash
uv run umem remember "O projeto usa arquitetura hexagonal." --scope project --tag architecture --format json
uv run umem remember "Preferir respostas objetivas em portugues." --scope global --tag preference --format json
uv run umem facts list --scope project --format json
uv run umem facts list --scope global --format json
uv run umem context --scope project --max-size-chars 4000 --format json
uv run umem context --scope global --format json
```

Validar:

- Fato local aparece em `.umem/memory/facts.jsonl`.
- Fato global aparece em `$HOME/.local/share/umem/memory/facts.jsonl`.
- `facts list` retorna os fatos corretos por escopo.
- `context` inclui os fatos esperados e respeita `max_size_chars`.
- `audit/events.jsonl` registra mutacoes locais.
- Audit global fica sob `$HOME/.local/share/umem/audit/events.jsonl` ou raiz global equivalente usada pelo codigo.

## 4. Seguranca, Snapshots E Rollback

Comandos:

```bash
uv run umem snapshots list --scope project --format json
uv run umem audit list --scope project --format json

uv run umem remember "aws_secret_access_key = AKIAIOSFODNN7EXAMPLE" --scope project --format json
```

Validar:

- `snapshots list` mostra snapshots criados antes das mutacoes.
- `audit list` mostra eventos de escrita segura.
- Tentativa com segredo retorna erro nao-zero ou payload `ok=false`.
- O segredo nao aparece em `.umem/memory/facts.jsonl`.
- Erros nao vazam stack trace em modo normal.

Rollback em sandbox separado:

```bash
uv run umem remember "Fato antes do rollback." --scope project --format json
uv run umem facts list --scope project --format json
uv run umem rollback --scope project --yes --format json
uv run umem facts list --scope project --format json
```

Validar:

- Rollback usa snapshot mais recente.
- Arquivo de memoria volta ao estado anterior esperado.
- Evento de rollback aparece no audit log.

## 5. Purge E Hygiene

Comandos:

```bash
FACT_ID="$(uv run umem facts list --scope project --format json | jq -r '.data.facts[0].id')"

uv run umem facts purge --id "$FACT_ID" --format json
uv run umem facts purge --id "$FACT_ID" --yes --format json
uv run umem facts list --scope project --status purged --format json
uv run umem facts hygiene --yes --format json
```

Validar:

- Sem `--yes`, purge destrutivo nao executa.
- Com `--yes`, fato muda para `purged` ou deixa de aparecer em `active`.
- `hygiene` executa sem erro e retorna contagem/resultado coerente.

## 6. Hosts

Comandos:

```bash
uv run umem host setup codex --yes --format json
uv run umem host setup claude_code --yes --format json
uv run umem host check codex --format json
uv run umem host check claude_code --format json
uv run umem host sync --no-apply --format json
uv run umem host sync --apply --yes --format json
```

Validar:

- `AGENTS.md` e criado para `codex`.
- `CLAUDE.md` e criado para `claude_code`.
- Blocos gerenciados UMEM aparecem com delimitadores validos.
- `host check` passa depois do setup.
- `host sync --no-apply` nao altera arquivos.
- `host sync --apply` altera apenas blocos gerenciados.

## 7. Skills

Como nao ha comando publico para track de latent skill, preparar fixture no sandbox:

- Criar uma linha JSONL valida em `.umem/memory/latent_skills.jsonl`.
- Usar UUID v4, `schema_version=1`, timestamps UTC, `scope=project`, `status=proposed`.

Depois executar:

```bash
uv run umem skills list --format json
uv run umem skills detail "$LATENT_SKILL_ID" --format json
uv run umem skills propose "$LATENT_SKILL_ID" --decision sim --format json
uv run umem skills generate "$LATENT_SKILL_ID" --yes --format json
uv run umem skills deactivate "$LATENT_SKILL_ID" --format json
uv run umem skills activate "$LATENT_SKILL_ID" --format json
uv run umem skills update "$LATENT_SKILL_ID" --name "Nova Skill" --trigger "quando revisar contexto" --format json
```

Validar:

- `skills list` mostra candidato.
- `propose` muda status conforme decisao.
- `generate` cria estrutura em `.umem/skills/`.
- `detail` resolve por ID ou nome.
- `activate`, `deactivate` e `update` persistem mudancas no JSONL.
- Snapshots e audit log sao atualizados.

## 8. MCP Black-Box

Subir `umem-mcp` via cliente MCP em sandbox proprio, usando o comando real:

```bash
HOME="$HOME_SANDBOX" uv run umem-mcp
```

Validar via cliente MCP ou MCP Inspector chamando estas tools:

```text
initialize_project
status
remember_fact
list_facts
context
purge_fact
list_audit_events
list_snapshots
rollback_scope
host_setup
host_check
sync_instructions
list_skills
get_skill_detail
propose_skill
generate_skill
deactivate_skill
activate_skill
update_skill
```

Sequencia recomendada:

1. `initialize_project`
2. `status`
3. `remember_fact(content="MCP grava fatos corretamente", scope="project", tags=["mcp"])`
4. `list_facts(scope="project")`
5. `context(scope="project")`
6. `purge_fact(confirm=false)` deve falhar com erro controlado
7. `purge_fact(id=<id>, confirm=true)` deve funcionar
8. `host_setup(host_id="codex", force=true)`
9. `host_check(host_id="codex")`
10. `list_audit_events(scope="project")`
11. `list_snapshots(scope="project")`
12. Criar fixture valida em `.umem/memory/latent_skills.jsonl`, como na secao de Skills
13. `list_skills()`
14. `get_skill_detail(name_or_id=<id>)`
15. `propose_skill(latent_skill_id=<id>, decision="sim")`
16. `generate_skill(latent_skill_id=<id>, update_existing=false)`
17. `deactivate_skill(latent_skill_id=<id>)`
18. `activate_skill(latent_skill_id=<id>)`
19. `update_skill(latent_skill_id=<id>, name="Nova Skill", triggers=["quando revisar contexto"])`

Validar:

- Toda resposta MCP segue envelope com `ok`, `operation`, `scope`, `data`, `warnings`.
- Erros destrutivos sem confirmacao retornam erro controlado.
- Tools MCP de skills usam os nomes de argumentos expostos pelo schema MCP; nao reutilizar flags CLI como `--yes`, `confirm` ou filtros nao expostos como `scope` em `list_skills()`.
- Estado criado pelo MCP e visivel depois pelo CLI `umem`.
- Estado criado pelo CLI e visivel depois pelo MCP.

## 9. Compatibilidade CLI/MCP

Teste cruzado:

```bash
uv run umem remember "Criado pela CLI, lido pelo MCP." --scope project --format json
```

Depois MCP:

```text
list_facts(scope="project")
context(scope="project")
```

E inverso:

```text
remember_fact(content="Criado pelo MCP, lido pela CLI", scope="project")
```

Depois CLI:

```bash
uv run umem facts list --scope project --format json
```

Validar:

- CLI e MCP compartilham o mesmo storage.
- IDs, escopos, status e tags aparecem de forma consistente.

## 10. Criterios De Aceite Final

O teste e aprovado se:

- Todos os comandos CLI principais executam com exit code esperado.
- Todas as tools MCP respondem com envelope valido.
- Mutacao local, global, audit, snapshot, rollback, purge, hosts e skills funcionam no sandbox.
- Nenhuma operacao escreve fora de `$SANDBOX`.
- Erros esperados sao amigaveis e nao corrompem estado.
- CLI e MCP enxergam o mesmo estado persistido.
