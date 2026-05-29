# Story 6.4: Registrar e Listar Skills

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário gerenciando capacidades aprendidas,
eu quero listar e inspecionar as skills registradas no sistema,
para que eu saiba quais metodologias foram formalizadas, quais são candidatas e quais estão disponíveis.

## Acceptance Criteria

1. **Dado** skills registradas na base local (projeto) ou global, **Quando** o usuário lista skills via use case ou CLI, **Então** o sistema mostra nome, escopo, status, caminho relativo, data de criação, última atualização e origem, **E** diferencia visualmente (ou em campos) as skills ativas, desativadas e candidatas, **E** com `--format json`, retorna JSON puro com `skills[]` contendo `name`, `scope`, `status`, `relative_path`, `created_at`, `updated_at`, `origin` e `audit_reference`, **E** a saída segue o padrão definido em `_bmad-output/planning-artifacts/devex-interaction-spec.md`.
2. **Dado** nenhuma skill registrada na base local ou global, **Quando** a listagem é executada, **Então** o sistema retorna um estado vazio explícito, **E** sugere de forma proativa o comando ou fluxo de proposta de skill sem criar nenhum arquivo automaticamente, **E** com `--format json`, retorna um objeto contendo `skills: []` e a chave `recommended_action` com a sugestão de ação.
3. **Dado** uma skill específica, **Quando** o usuário solicita seus detalhes, **Então** o sistema mostra seus metadados, caminho relativo, gatilhos de uso (`triggers`) e a referência de auditoria, **E** não carrega de forma desnecessária arquivos grandes contidos no subdiretório `references/` a menos que explicitamente solicitado pelo usuário, **E** com `--format json`, retorna um objeto contendo as chaves `name`, `scope`, `status`, `relative_path`, `triggers`, `audit_reference` e `references_loaded: false` por padrão.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes unitários e de integração (RED) do Use Case de Listagem e Detalhes de Skills** (AC: 1, 2, 3)
  - [x] Criar o arquivo `tests/application/skills/test_list_skills.py`.
  - [x] Cobrir a listagem vazia e garantir que o resultado contenha `skills: []` e `recommended_action`.
  - [x] Cobrir a listagem de latent skills e skills ativas/desativadas/candidatas tanto no escopo local quanto global.
  - [x] Validar que o caminho relativo (`relative_path`) seja resolvido corretamente com base no escopo e status da skill (ex: `.umem/skills/<slug>/SKILL.md` para local ativa, ou `None` para candidata).
  - [x] Cobrir o caso de uso de detalhes de uma skill específica, validando o preenchimento de `triggers`, metadados de auditoria e a flag `references_loaded: False`.

- [x] **Task 2: Implementar use cases `ListSkillsUseCase` e `GetSkillDetailUseCase`** (AC: 1, 2, 3)
  - [x] Criar o arquivo `src/universal_memory/application/skills/list_skills.py`.
  - [x] Definir os comandos e resultados: `ListSkillsCommand`, `ListSkillsResult`, `GetSkillDetailCommand`, `GetSkillDetailResult`.
  - [x] Implementar a lógica em `ListSkillsUseCase`:
    - Ler as latent skills do repositório (`LatentSkillRepository.list()`).
    - Para cada latent skill, mapear para DTO contendo: `name`, `scope`, `status` (diferenciando `proposed` como candidata, `active` como ativa e `ignored` como desativada), `created_at`, `updated_at`, `origin`, `audit_reference` e calcular o `relative_path` correspondente (usando a lógica de slugificação do use case `propose_skill` ou `generate_skill` para verificar a existência do arquivo `SKILL.md` físico em `.umem/skills/<slug>/SKILL.md` ou `skills/<slug>/SKILL.md`).
    - Retornar a listagem ordenada de acordo com as datas ou prioridade.
  - [x] Implementar a lógica em `GetSkillDetailUseCase`:
    - Buscar a latent skill correspondente por ID ou nome.
    - Se ela for ativa e materializada fisicamente, ler os gatilhos (`triggers`) diretamente do YAML frontmatter do `SKILL.md` ou dos metadados da latent skill de backup.
    - Garantir que não sejam lidos arquivos grandes em `references/` a menos que solicitado.
    - Retornar o DTO com as chaves correspondentes.
  - [x] Registrar e exportar os novos use cases no bootstrap e em `src/universal_memory/application/skills/__init__.py`.

- [x] **Task 3: Escrever testes unitários e de integração (RED) para a CLI (`umem skills list` e `umem skills detail`)** (AC: 1, 2, 3)
  - [x] Criar o arquivo `tests/interfaces/cli/test_skills_list.py`.
  - [x] Testar a exibição no terminal para listagem padrão (mostrando tabela Rich formatada com nome, escopo, status colorido, caminho relativo e origem).
  - [x] Testar a exibição da listagem vazia exibindo o estado de aviso e a mensagem proativa sugerindo `umem skills propose`.
  - [x] Testar a listagem com a flag `--format json` validando que o envelope contenha `ok: true`, `operation: "skills.list"`, e no campo `data` a lista de `skills` no formato especificado.
  - [x] Testar o comando de detalhes CLI (`umem skills detail <name_or_id>`) e sua saída JSON com o envelope padrão.

- [x] **Task 4: Implementar os comandos CLI `umem skills list` e `umem skills detail`** (AC: 1, 2, 3)
  - [x] Adicionar os comandos CLI correspondentes em `src/universal_memory/interfaces/cli/init_command.py` dentro do subgrupo `skills_app`.
  - [x] Formatar a saída da listagem com tabelas Rich de alta fidelidade visual, exibindo de forma clara a diferenciação entre skills ativas, candidatas e desativadas.
  - [x] Formatar a exibição dos detalhes de uma skill com layout Rich apresentando YAML frontmatter, caminhos relativos e gatilhos de forma amigável.
  - [x] Garantir conformidade com `--format json` retornando envelopes limpos em caso de sucesso e erros mapeados com hints.
  - [x] Registrar as rotas de comando e realizar os bindings no bootstrapping CLI.

- [x] **Task 5: Implementar e expor ferramentas MCP correspondentes `list_skills` e `get_skill_detail`** (AC: 1, 2, 3)
  - [x] Adicionar `@server.tool(name="list_skills")` e `@server.tool(name="get_skill_detail")` no servidor FastMCP em `src/universal_memory/interfaces/mcp/server.py`.
  - [x] Garantir paridade semântica total de retorno das chaves JSON com a CLI (em conformidade com `devex-interaction-spec.md`).
  - [x] Adicionar casos de teste para as novas ferramentas MCP em `tests/interfaces/mcp/test_server.py`.

- [x] **Task 6: Verificação final de qualidade e conformidade** (AC: 1, 2, 3)
  - [x] Executar a suíte de testes completa do repositório: `uv run pytest`.
  - [x] Executar a checagem de estilo e formatação: `uv run ruff check .` e `uv run ruff format --check .`.
  - [x] Executar a checagem de tipos estáticos: `uv run pyright`.

## Dev Notes

- **Escopo desta story:** Foco exclusivo no fluxo de leitura e inspeção de skills. As mutações físicas ou de status não fazem parte desta história (são escopo das stories 6.3 e 6.5).
- **Diferenciação de status:**
  - **Ativa (Active):** Latent skill com status `active`. O `relative_path` aponta para `.umem/skills/<slug>/SKILL.md` (local) ou `skills/<slug>/SKILL.md` (global).
  - **Desativada (Disabled/Ignored):** Latent skill com status `ignored`.
  - **Candidata (Candidate/Proposed):** Latent skill com status `proposed`. O `relative_path` é `None` pois o scaffold de arquivos markdown ainda não foi criado.
- **Resolução de Caminhos:** Sempre retornar caminhos relativos ao projeto para manter a conformidade com as regras de ambiente e evitar a exposição de caminhos absolutos do sistema operacional do host.
- **Audit reference:** Na listagem ou detalhes de uma skill, retornar também a `audit_reference` relacionada à última mutação/criação no repositório de latent skills.

### Project Structure Notes

- O caso de uso deve residir em `src/universal_memory/application/skills/list_skills.py`.
- O registro dos comandos CLI deve estar integrado em `src/universal_memory/interfaces/cli/init_command.py`.
- A integração com MCP deve estar em `src/universal_memory/interfaces/mcp/server.py`.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR21) - [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)
- `_bmad-output/planning-artifacts/architecture.md` (Skill Engine, CLI to MCP Parity Matrix) - [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (Output Contract, Command Contracts: skills list/detail) - [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- `src/universal_memory/domain/entities/latent_skill.py` - [latent_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/entities/latent_skill.py)
- `src/universal_memory/application/skills/generate_skill.py` - [generate_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/skills/generate_skill.py)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- 2026-05-29: Criada story a partir do fluxo bmad create-story para o epic-6 story-4 (Registrar e Listar Skills).
- 2026-05-29: RED application: `uv run pytest tests/application/skills/test_list_skills.py` falhou por ausência dos novos contratos exportados.
- 2026-05-29: GREEN application: `uv run pytest tests/application/skills/test_list_skills.py` passou com 3 testes.
- 2026-05-29: RED CLI: `uv run pytest tests/interfaces/cli/test_skills_list.py` falhou por ausência dos handlers/comandos list/detail.
- 2026-05-29: GREEN CLI: `uv run pytest tests/interfaces/cli/test_skills_list.py` passou com 4 testes.
- 2026-05-29: RED MCP: `uv run pytest tests/interfaces/mcp/test_server.py -k 'list_skills or get_skill_detail'` falhou por ausência dos handlers MCP.
- 2026-05-29: GREEN MCP: `uv run pytest tests/interfaces/mcp/test_server.py -k 'list_skills or get_skill_detail'` passou com 2 testes.
- 2026-05-29: Validação focada: `uv run pytest tests/application/skills/test_list_skills.py tests/interfaces/cli/test_skills_list.py tests/interfaces/mcp/test_server.py` passou com 22 testes.
- 2026-05-29: Validação completa inicial: `uv run pytest` falhou em `tests/interfaces/mcp/test_compliance.py` por inventário MCP desatualizado.
- 2026-05-29: Validação final: `uv run pytest` passou com 347 testes.
- 2026-05-29: Validação final: `uv run ruff check .`, `uv run ruff format --check .` e `uv run pyright` passaram.

### Completion Notes List

- Implementados `ListSkillsUseCase` e `GetSkillDetailUseCase` com DTOs/payloads para listagem vazia, status normalizados (`active`, `candidate`, `disabled`), paths relativos, auditoria/origem e leitura de triggers do frontmatter sem carregar `references/`.
- Adicionados comandos CLI `umem skills list` e `umem skills detail` com saída human via Rich e envelopes JSON puros `skills.list`/`skills.detail`.
- Expostas ferramentas MCP `list_skills` e `get_skill_detail`, com contrato semântico alinhado à CLI e cobertura no teste de conformidade MCP.
- Todos os Acceptance Criteria foram cobertos por testes de application, CLI e MCP.

### File List

- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `src/universal_memory/bootstrap/mcp.py`
- `tests/application/skills/test_list_skills.py`
- `tests/interfaces/cli/test_skills_list.py`
- `tests/interfaces/mcp/test_server.py`
- `tests/interfaces/mcp/test_compliance.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/6-4-registrar-e-listar-skills.md`

### Change Log

- 2026-05-29: Implementados list/detail de skills nos use cases, CLI e MCP; adicionada cobertura de testes e conformidade; story marcada como pronta para review.

### Review Findings

- [x] [Review][Patch] Saida humana de `skills list` nao mostra `created_at` [src/universal_memory/interfaces/cli/init_command.py:2155]  
  A story exige que a listagem via CLI mostre nome, escopo, status, caminho relativo, data de criacao, ultima atualizacao e origem. `_format_human_skill_list()` renderiza apenas `Nome`, `Escopo`, `Status`, `Caminho relativo`, `Origem` e `Atualizada em`, sem expor a data de criacao.
- [x] [Review][Patch] Resolucao de `relative_path` pode apontar para slug errado [src/universal_memory/application/skills/list_skills.py:159]  
  `skills list/detail` rederiva o caminho como `.../{_slug(skill.name)}/SKILL.md`, mas `generate_skill` pode materializar um slug alternativo em caso de colisao (`foo-2`) ou fallback hash (`skill-<hash>`). Nesses casos a listagem passa a devolver um caminho inexistente e `skills detail` deixa de ler os `triggers` reais do arquivo.
- [x] [Review][Patch] `skills detail <nome>` nao trata nomes ambiguos [src/universal_memory/application/skills/list_skills.py:133]  
  `_find_skill()` retorna o primeiro match por `name.casefold()` sem desambiguar por escopo ou quantidade de ocorrencias. Se houver duas skills com o mesmo nome, a CLI/MCP pode exibir a skill errada em silencio em vez de exigir ID ou informar ambiguidade.
- [x] [Review][Patch] Parser manual de frontmatter perde `triggers` validos [src/universal_memory/application/skills/list_skills.py:176]  
  `_read_frontmatter_triggers()` depende de `---\n` e do prefixo literal `"  - "`, entao falha com BOM, `CRLF`, listas inline YAML ou escalares escapados gerados pelo proprio projeto. O efeito e fallback silencioso para metadata ou nome da skill, produzindo detalhes incorretos sem erro explicito.
