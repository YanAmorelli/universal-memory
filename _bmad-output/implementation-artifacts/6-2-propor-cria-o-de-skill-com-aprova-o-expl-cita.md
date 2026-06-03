# Story 6.2: Propor Criação de Skill com Aprovação Explícita

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário controlando a evolução do sistema,
eu quero aprovar ou recusar a criação de uma skill quando uma recorrência for detectada,
para que o sistema aprenda sem automatizar decisões comportamentais sensíveis.

## Acceptance Criteria

1. **Dado** uma latent skill atinge o gatilho de recorrência configurado, **Quando** a proposta é apresentada ao usuário, **Então** o sistema oferece opções explícitas `Sim`, `Sempre` e `Não`, **E** explica o nome sugerido, propósito, escopo e evidências resumidas da recorrência, **E** a confirmação segue o padrão de decisão e segurança de [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md).
2. **Dado** o usuário escolhe `Sim`, **Quando** a proposta é aceita, **Então** o sistema cria uma solicitação de geração de skill para aquela ocorrência, **E** mantém futuras ocorrências sujeitas a nova confirmação.
3. **Dado** o usuário escolhe `Sempre`, **Quando** a proposta é aceita, **Então** o sistema registra preferência para aprovar automaticamente propostas equivalentes dentro do escopo configurado, **E** a decisão é auditável e reversível.
4. **Dado** o usuário escolhe `Não`, **Quando** a proposta é recusada, **Então** o sistema marca a latent skill como recusada/ignorada ou reduz sua prioridade (`ignored`), **E** não cria arquivos de skill.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes RED do use case de Proposta de Skill e preferências** (AC: 1, 2, 3, 4)
  - [x] Criar `tests/application/skills/test_propose_skill.py`.
  - [x] Cobrir fluxo de proposta apresentada ao usuário, oferecendo opções explícitas `Sim`, `Sempre` e `Não`.
  - [x] Testar cenário com escolha `Sim`: a proposta é aceita, muda o status da `LatentSkill` de `proposed` para `active` (ou agenda geração), mantendo futuras ocorrências sujeitas a nova confirmação.
  - [x] Testar cenário com escolha `Sempre`: a proposta é aceita e o sistema registra uma preferência de auto-aprovação no arquivo de configuração local `.umem/config.toml` (para propostas equivalentes com mesmo nome/padrão no escopo).
  - [x] Testar cenário com escolha `Não`: a proposta é recusada, marcando a latent skill com status `ignored` de forma persistente, sem criar arquivos de skill.
  - [x] Testar auditabilidade e rollback das decisões, inclusive do registro de preferências (reversível).
  - [x] Validar conformidade com o pipeline de mutação obrigatório (verificação de snapshot, escrita atômica e auditoria).

- [x] **Task 2: Implementar o usecase `ProposeSkillUseCase` e a lógica de decisão** (AC: 1, 2, 3, 4)
  - [x] Criar `src/universal_memory/application/skills/propose_skill.py` contendo `ProposeSkillUseCase` e seus comandos de entrada/saída (`ProposeSkillCommand`, `ProposeSkillResult`).
  - [x] Implementar a lógica de negócios para transições de status da `LatentSkill` com base na escolha do usuário (`Sim/Sempre/Não`).
  - [x] Implementar a persistência das preferências de auto-aprovação na configuração local `.umem/config.toml` usando as lógicas seguras de `toml_loader.py` e `update_project_config(...)` no caso de `Sempre`.
  - [x] Integrar o pipeline seguro completo:
    1. Validar a transição usando o modelo Pydantic do domínio (`LatentSkill`).
    2. Criar snapshot com `SnapshotRepository` (abortando em caso de erro com `SnapshotFailedError`).
    3. Gravar no repositório `LatentSkillRepository` de forma atômica.
    4. Registrar auditoria no `AuditLogRepository` (originando da CLI ou MCP) indicando a ação, decisão e referências.
    5. Retornar referência de auditoria e status da operação.
  - [x] Exportar `ProposeSkillUseCase` no `src/universal_memory/application/skills/__init__.py`.

- [x] **Task 3: Escrever testes RED da CLI de Proposta de Skills (`umem skills propose`)** (AC: 1, 2, 3, 4)
  - [x] Criar testes em `tests/interfaces/cli/test_skills_propose.py`.
  - [x] Testar renderização de Rich no terminal exibindo nome sugerido, propósito, escopo e evidências resumidas da recorrência de forma limpa.
  - [x] Testar interatividade do prompt aceitando `Sim` (ou `s`), `Sempre` (ou `e` / `sempre`), `Não` (ou `n`).
  - [x] Testar comportamento com `--yes` (para automações ou bypass) e compatibilidade estrita com `--format json` (retornando JSON puro sem Rich markups).
  - [x] Testar tratamento de erros e conformidade com o envelope de erro/sucesso padrão.

- [x] **Task 4: Implementar o comando CLI `umem skills propose`** (AC: 1, 2, 3, 4)
  - [x] Adicionar o novo subgrupo/comando de CLI para skills em `src/universal_memory/interfaces/cli/init_command.py` ou criar um módulo dedicado.
  - [x] Formatar a saída padrão Rich em conformidade estrita com `devex-interaction-spec.md` (operação, escopo, caminhos relativos afetados, referências de auditoria e perguntas de confirmação seguras sem segredos expostos).
  - [x] Tratar `--format json` para retornar JSON puro em conformidade com o envelope de sucesso/erro padrão.
  - [x] Fazer o bind correto no bootstraper `src/universal_memory/bootstrap/cli.py` injetando a usecase no `build_main`.

- [x] **Task 5: Implementar o Adapter MCP correspondente `propose_skill`** (AC: 1, 2, 3, 4)
  - [x] Adicionar a ferramenta MCP `propose_skill` em `src/universal_memory/interfaces/mcp/server.py`.
  - [x] Tratar a natureza não interativa do MCP: aceitar um parâmetro opcional `decision` ("sim", "sempre", "nao") ou, se omitido, retornar a proposta e as evidências com formato padronizado solicitando a chamada subsequente com a decisão.
  - [x] Garantir paridade semântica total de retorno e erros JSON-RPC com a CLI em conformidade com `devex-interaction-spec.md`.

- [x] **Task 6: Verificação de qualidade e conformidade** (AC: 1, 2, 3, 4)
  - [x] Executar a suíte de testes completa: `uv run pytest`.
  - [x] Executar o linter e formatador: `uv run ruff check .` e `uv run ruff format --check .`.
  - [x] Executar a checagem estática de tipos: `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Rollback de Auto-Aprovação não reverte as preferências no TOML do projeto [src/universal_memory/application/skills/propose_skill.py:128]
- [x] [Review][Patch] Prompt de confirmação interativo viola o Confirmation Contract da especificação [src/universal_memory/interfaces/cli/init_command.py:651]
- [x] [Review][Patch] Falta de paridade e duplicação inconsistente na conversão de decisão [src/universal_memory/interfaces/cli/init_command.py:678]
- [x] [Review][Patch] CLI encerra com sucesso em ambiente não-TTY sem decisão fornecida [src/universal_memory/interfaces/cli/init_command.py:1299]
- [x] [Review][Patch] CLI gera stack trace e crash ao receber Ctrl+C ou Ctrl+D no prompt [src/universal_memory/interfaces/cli/init_command.py:1318]
- [x] [Review][Patch] CLI aceita decisões inválidas e sai silenciosamente com status de sucesso [src/universal_memory/interfaces/cli/init_command.py:1320]
- [x] [Review][Patch] Falta de atomicidade transacional e tratamento de rollback automático em falhas [src/universal_memory/application/skills/propose_skill.py:121]
- [x] [Review][Patch] Falta de captura do KeyError na CLI quando o ID da latent skill é inexistente [src/universal_memory/interfaces/cli/init_command.py:1308]
- [x] [Review][Patch] Modificação de entidade usa model_copy ignorando validações do Pydantic [src/universal_memory/application/skills/propose_skill.py:160]
- [x] [Review][Patch] Testes de erro CLI ausentes no arquivo de suíte de testes [tests/interfaces/cli/test_skills_propose.py:1]
- [x] [Review][Patch] Risco de colisão de slug para nomes de skills não-latinos ou especiais [src/universal_memory/application/skills/propose_skill.py:212]
- [x] [Review][Patch] Crash de AttributeError em carregamento de metadata nulo (None) [src/universal_memory/application/skills/propose_skill.py:154]
- [x] [Review][Patch] Imports ausentes de ValidationError e sys no CLI [src/universal_memory/interfaces/cli/init_command.py:49]
- [x] [Review][Patch] Gravação de regras de auto-aprovação viola o isolamento de escopo global [src/universal_memory/application/skills/propose_skill.py:168]
- [x] [Review][Patch] Caminho do config chumbado estaticamente em update_project_config [src/universal_memory/infrastructure/config/toml_loader.py:65]
- [x] [Review][Patch] Gambiarra arquitetural em testes de domínio acopla domínio à aplicação [tests/domain/test_ports.py:1031]
- [x] [Review][Patch] Ausência de validação de transição de estado da latent skill no caso de uso [src/universal_memory/application/skills/propose_skill.py:111]
- [x] [Review][Patch] Condições de corrida na escrita simultânea concorrente do config.toml [src/universal_memory/infrastructure/config/toml_loader.py:65]

## Dev Notes

- **Escopo desta story:** Criar o use case de proposta e decisão de skills, persistindo a aprovação explícita e regras de auto-aprovação na configuração local de forma segura e auditável. Integrar isso na CLI sob `umem skills propose` e MCP sob `propose_skill`. Não implementar nesta história a geração física de estruturas de pastas nem a escrita de arquivos `SKILL.md` (isso pertence à história 6.3).
- **Paridade CLI/MCP:** Conforme `devex-interaction-spec.md`, cada comando deve ter um respectivo adapter CLI e MCP, operando o mesmo caso de uso sob as mesmas validações.
- **Pipeline Seguro de Mutação:** Todas as escritas e alterações na configuração local `.umem/config.toml` ou no status da latent skill devem obrigatoriamente criar snapshots via `SnapshotRepository` e registrar trilhas detalhadas e auditáveis via `AuditLogRepository`.

### Project Structure Notes

- O novo use case deve viver sob `src/universal_memory/application/skills/propose_skill.py`.
- O bind da CLI e MCP deve ser feito em `src/universal_memory/bootstrap/cli.py` e `src/universal_memory/interfaces/mcp/server.py`.
- O registro de auto-aprovação deve estender o schema de configurações do `config.toml` do projeto usando o adapter de TOML existente.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR19, FR24, FR25, FR26, FR28) - [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)
- `_bmad-output/planning-artifacts/architecture.md` (Mutation Pipeline, Clean Architecture, Storage Contract) - [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (CLI output, JSON CLI output, Confirmation contract, skills command contracts) - [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- `src/universal_memory/domain/entities/latent_skill.py` - [latent_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/entities/latent_skill.py)
- `src/universal_memory/application/skills/track_latent_skill.py` - [track_latent_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/skills/track_latent_skill.py)

## Dev Agent Record

### Agent Model Used

Gemini 1.5 Pro (via Antigravity)

### Debug Log References

- 2026-05-29: Criada story a partir do fluxo bmad create-story para o epic-6 story-2.
- 2026-05-29: Analisadas dependências de persistência em config, lógicas do pipeline de mutação seguro e conformidade com `devex-interaction-spec.md`.
- 2026-05-29: Implementado `ProposeSkillUseCase` com testes RED/GREEN para preview, decisões `Sim`, `Sempre` e `Não`, preferência reversível em `.umem/config.toml`, snapshot e auditoria.
- 2026-05-29: Implementados adapters CLI `umem skills propose` e MCP `propose_skill`, incluindo paridade semântica e inventário de conformidade MCP.
- 2026-05-29: Validação final executada com `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run pyright`.

### Completion Notes List

- Análise de contexto e arquitetura concluída - guia compreensivo de implementação criado.
- História configurada como pronta para desenvolvimento com escopo e tarefas detalhados.
- Integração obrigatória do pipeline seguro de mutação explicitada na tarefa do use case.
- Padrão interativo `Sim/Sempre/Não` e sua paridade CLI/MCP detalhados nas tarefas operacionais.
- `ProposeSkillUseCase` criado e exportado, com transições persistentes para `active`/`ignored` e registro de aprovação em metadata.
- Decisão `Sempre` grava preferência de auto-aprovação em `.umem/config.toml` por escrita segura com snapshot e auditoria.
- CLI `umem skills propose` suporta preview, prompt interativo, `--decision`, `--yes` e `--format json` com envelope padrão.
- MCP `propose_skill` suporta preview sem decisão e decisão explícita não interativa com o mesmo contrato semântico da CLI.
- Suíte completa e checks de qualidade passaram: 318 testes, ruff check, ruff format check e pyright.

### File List

- `_bmad-output/implementation-artifacts/6-2-propor-cria-o-de-skill-com-aprova-o-expl-cita.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/application/skills/propose_skill.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/infrastructure/config/toml_loader.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/skills/test_propose_skill.py`
- `tests/domain/test_ports.py`
- `tests/infrastructure/storage/test_local_latent_skill_repository.py`
- `tests/interfaces/cli/test_skills_propose.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_server.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-05-29: Implementada proposta de criação de skill com aprovação explícita, preferência `Sempre`, CLI/MCP e validações completas.
