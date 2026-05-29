# Story 6.3: Gerar Estrutura Agent Skills

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário que aprovou uma nova skill,
eu quero que o sistema gere a estrutura padrão de Agent Skills,
para que a metodologia recorrente vire um artefato reutilizável por agentes.

## Acceptance Criteria

1. **Dado** uma proposta de skill aprovada, **Quando** a geração é executada, **Então** o sistema cria uma pasta de skill com o arquivo `SKILL.md` dentro de `.umem/skills/<slug>/` (ou no caminho de escopo correspondente), **E** inclui diretórios opcionais `scripts/` e `references/` somente quando necessários ao escopo aprovado.
2. **Dado** o conteúdo consolidado da latent skill, **Quando** `SKILL.md` é gerado, **Então** ele contém YAML frontmatter com `name`, `description` e `triggers` (gatilhos), seguido de diretrizes e instruções operacionais claras, **E** usa caminhos relativos em especificações, códigos e documentações conforme a regra do projeto.
3. **Dado** que já existe uma skill com nome conflitante, **Quando** a geração é solicitada, **Então** o sistema propõe um nome alternativo com sufixo incremental não conflitante (ex: `<slug>-2`) ou realiza uma atualização controlada, **E** nunca sobrescreve o conteúdo existente sem confirmação do usuário e a criação automática de um snapshot prévio.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes RED do use case de Geração de Estrutura de Skill** (AC: 1, 2, 3)
  - [x] Criar o arquivo `tests/application/skills/test_generate_skill.py`.
  - [x] Cobrir o fluxo completo de geração a partir de uma latent skill aprovada com status `active`.
  - [x] Testar a criação física do diretório da skill no diretório de destino del projeto (`.umem/skills/<slug>`) ou global.
  - [x] Testar a criação do arquivo `SKILL.md` validando o YAML frontmatter (campos `name`, `description`, `triggers`) e a presença das instruções operacionais de domínio.
  - [x] Testar a inclusão condicional dos diretórios opcionais `scripts/` e `references/`.
  - [x] Testar o comportamento de colisões de nomes (diretório já existente): a geração deve sugerir um slug não colidente adicionando um incremento numérico (ex: `my-skill-2`) ou atualizar sob consentimento explícito.
  - [x] Validar a integração estrita do pipeline de mutação seguro (criação automática de snapshot pré-escrita via `SnapshotRepository` e registro de trilha de auditoria via `AuditLogRepository`).

- [x] **Task 2: Implementar o usecase `GenerateSkillUseCase` e a lógica de geração física** (AC: 1, 2, 3)
  - [x] Criar o arquivo `src/universal_memory/application/skills/generate_skill.py` contendo `GenerateSkillUseCase`, `GenerateSkillCommand` e `GenerateSkillResult`.
  - [x] Implementar a lógica de negócios para a geração da pasta da skill e escrita do arquivo `SKILL.md`.
  - [x] Implementar rotina robusta de slugification para normalizar o nome da skill em um nome de diretório seguro (usando a mesma lógica de `_slug` implementada em `propose_skill.py`).
  - [x] Integrar o pipeline seguro de mutação:
    1. Validar a solicitação usando schemas Pydantic.
    2. Invocar `SnapshotRepository` para criar um snapshot do estado do diretório de skills antes da modificação (abortando em caso de falha com `SnapshotFailedError`).
    3. Escrever arquivos de skill de forma atômica no disco.
    4. Gravar o evento auditável no `AuditLogRepository` registrando a criação, caminhos afetados e referências.
  - [x] Implementar a resolução de conflitos de nome: se o diretório de destino já existir, sugerir e resolver com slug incremental ou realizar escrita segura preservando backups.
  - [x] Exportar o caso de uso e comandos no bootstraper em `src/universal_memory/application/skills/__init__.py`.

- [x] **Task 3: Escrever testes RED da CLI de Geração de Skills (`umem skills generate`)** (AC: 1, 2, 3)
  - [x] Criar testes em `tests/interfaces/cli/test_skills_generate.py`.
  - [x] Testar a exibição Rich no terminal exibindo o plano de geração física da skill (diretório a ser criado, caminhos afetados, snapshots de segurança).
  - [x] Testar prompt interativo solicitando confirmação segura do usuário.
  - [x] Testar comportamento sob `--yes` (execução não interativa) e com `--format json` (retornando JSON puro sem cabeçalhos textuais ou Rich markups).
  - [x] Testar tratamento de erros e conformidade com o envelope padrão de sucesso/erro.

- [x] **Task 4: Implementar o comando CLI `umem skills generate`** (AC: 1, 2, 3)
  - [x] Adicionar o novo subgrupo/comando em `src/universal_memory/interfaces/cli/init_command.py`.
  - [x] Formatar a saída padrão Rich em conformidade estrita com `devex-interaction-spec.md` (operação, escopo, caminhos relativos afetados, referências de auditoria e perguntas de confirmação sem segredos expostos).
  - [x] Tratar `--format json` para retornar JSON puro conforme o envelope de sucesso padrão.
  - [x] Registrar e fazer o bind correto da usecase no bootstrap da CLI em `src/universal_memory/bootstrap/cli.py`.

- [x] **Task 5: Implementar o Adapter MCP correspondente `generate_skill`** (AC: 1, 2, 3)
  - [x] Adicionar a ferramenta MCP `generate_skill` em `src/universal_memory/interfaces/mcp/server.py`.
  - [x] Tratar a natureza não interativa do MCP: em caso de conflitos ou erros de validação, mapear para os códigos de erro JSON-RPC e retornar envelopes informativos.
  - [x] Garantir paridade semântica total e asserts de validação com a CLI em conformidade com `devex-interaction-spec.md`.

- [x] **Task 6: Verificação final de qualidade e conformidade** (AC: 1, 2, 3)
  - [x] Executar a suíte de testes completa: `uv run pytest`.
  - [x] Executar a checagem de estilo e formatação: `uv run ruff check .` e `uv run ruff format --check .`.
  - [x] Executar a checagem de tipos estáticos: `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Resolução automática de colisão de slugs em vez de proposição interativa — A especificação (AC 3) diz que o sistema deve propor um nome alternativo com sufixo incremental. Atualmente, o UseCase cria e grava automaticamente o novo slug alternativo sem dar ao usuário a chance de propor ou escolher um nome diferente interativamente no terminal. Como devemos tratar essa proposição?
- [x] [Review][Patch] Geração manual de YAML frontmatter frágil [src/universal_memory/application/skills/generate_skill.py:224-229]
- [x] [Review][Patch] Auditoria e snapshots múltiplos quebram atomicidade [src/universal_memory/application/skills/generate_skill.py:128-151]
- [x] [Review][Patch] Mensagem de colisão incorreta na CLI quando update_existing é True [src/universal_memory/interfaces/cli/init_command.py:578-580]
- [x] [Review][Patch] Tratamento de exceção do port LatentSkillRepository incompleto [src/universal_memory/bootstrap/cli.py:174]
- [x] [Review][Patch] Correção do stripped path no Windows [src/universal_memory/application/skills/generate_skill.py:249]
- [x] [Review][Patch] Risco de crash no FastMCP quando project_root é None [src/universal_memory/bootstrap/mcp.py:127]
- [x] [Review][Patch] Placeholders estáticos de caminhos no plano de geração da CLI [src/universal_memory/interfaces/cli/init_command.py:549-560]
- [x] [Review][Patch] Ausência de aviso explícito ao atualizar pasta de skill existente [src/universal_memory/interfaces/cli/init_command.py:485-492]
- [x] [Review][Patch] Travamento da CLI sob redirecionamento de saída [src/universal_memory/interfaces/cli/init_command.py:485-492]
- [x] [Review][Patch] Geração de valores None literais em Markdown a partir de metadados vazios [src/universal_memory/application/skills/generate_skill.py:255]
- [x] [Review][Patch] Tratamento de colisão contra arquivos regulares [src/universal_memory/application/skills/generate_skill.py:178-189]
- [x] [Review][Defer] TOCTOU na resolução de slugs [src/universal_memory/application/skills/generate_skill.py:178-189] — deferred, pre-existing
- [x] [Review][Defer] Tratamento estético de ValidationError do Pydantic na CLI [src/universal_memory/interfaces/cli/init_command.py:501-504] — deferred, pre-existing
- [x] [Review][Defer] Tratamento de caminhos quando project_root é resolved para / [src/universal_memory/application/skills/generate_skill.py:249] — deferred, pre-existing

## Dev Notes

- **Escopo desta story:** Foco exclusivo na criação física da estrutura de diretórios e arquivos de Agent Skills. As skills devem ser geradas em `.umem/skills/<slug>/` para o escopo do projeto, ou no diretório global equivalente se for escopo global.
- **Formato de `SKILL.md`:**
  O arquivo gerado deve conter obrigatoriamente um YAML frontmatter demarcado por `---`, contendo:
  - `name`: Nome legível da skill.
  - `description`: Descrição de propósito da skill.
  - `triggers`: Lista de gatilhos de uso.
  - O restante do arquivo deve ser markdown estruturado com diretrizes de uso operacionais claras extraídas da latent skill, empregando caminhos relativos ao invés de caminhos absolutos.
- **Pipeline Seguro de Mutação:** Como se trata de escrita física no disco, a criação de snapshots via `SnapshotRepository` e a trilha universal em `AuditLogRepository` devem ser estritamente seguidas antes do commit definitivo dos arquivos.

### Project Structure Notes

- O caso de uso deve ser localizado em `src/universal_memory/application/skills/generate_skill.py`.
- O registro dos bindings deve ser configurado em `src/universal_memory/bootstrap/cli.py` e `src/universal_memory/interfaces/mcp/server.py`.
- A estrutura de arquivos a ser criada deve estar em perfeita sintria com a definição do layout de projeto em `project_layout.py`.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR20) - [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)
- `_bmad-output/planning-artifacts/architecture.md` (Mutation Pipeline, Skill Engine, Storage Contract) - [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (CLI human/JSON contracts, errors, confirmations) - [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- `src/universal_memory/domain/entities/latent_skill.py` - [latent_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/entities/latent_skill.py)
- `src/universal_memory/application/skills/propose_skill.py` - [propose_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/skills/propose_skill.py)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- 2026-05-29: Criada story a partir do fluxo bmad create-story para o epic-6 story-3 (Gerar Estrutura Agent Skills).
- 2026-05-29: Implementado `GenerateSkillUseCase`, comando CLI `skills generate`, ferramenta MCP `generate_skill` e testes de aplicação/interface.

### Completion Notes List

- Análise de contexto e arquitetura concluída - guia compreensivo de implementação criado.
- História configurada como pronta para desenvolvimento com escopo e tarefas detalhados.
- Implementado use case de geração física de Agent Skills a partir de latent skills `active`, com `SKILL.md` contendo frontmatter `name`, `description` e `triggers`, instruções operacionais e evidências.
- Geração usa caminhos relativos e `SafeWriteUseCase` para escrita atômica, snapshots e auditoria em `SKILL.md` e diretórios opcionais materializados por `.gitkeep`.
- Resolução de colisões preserva diretórios existentes por padrão e cria slug incremental, com opção controlada `update_existing` para atualização explícita.
- Adicionados `umem skills generate` e tool MCP `generate_skill`, ambos com envelopes de sucesso/erro e paridade de contrato.
- Validações finais concluídas com sucesso: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run pyright`.

### File List

- `src/universal_memory/application/skills/generate_skill.py`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/skills/test_generate_skill.py`
- `tests/interfaces/cli/test_skills_generate.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_server.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-05-29: Implementada geração de estrutura Agent Skills com CLI, MCP, testes e validações finais; status movido para review.
