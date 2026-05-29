# Story 5.5: Sincronizar Regras Consolidadas para Instruções

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário que aprova novas regras de comportamento,
Eu quero sincronizar regras consolidadas para arquivos de instrução suportados,
Para que agentes diferentes operem com diretrizes consistentes.

## Acceptance Criteria

1. **Dado** uma regra aprovada para promoção
   **Quando** a sincronização de instruções roda
   **Então** o sistema decide se a regra pertence a `shared_policy`, `provider_delta`, `scoped_rule` ou `canonical_doc`
   **And** atualiza apenas os targets correspondentes

2. **Dado** múltiplos hosts configurados
   **Quando** uma regra compartilhada é sincronizada
   **Então** `AGENTS.md` é escrito uma única vez por ciclo de mutação
   **And** hosts que consomem `AGENTS.md` não produzem cópias divergentes

3. **Dado** uma regra que aponta para conteúdo detalhado
   **Quando** ela é sincronizada
   **Então** o arquivo de instrução inclui ponteiro compacto para a fonte canônica
   **And** o conteúdo longo permanece em docs ou memória, conforme classificado

## Tasks / Subtasks

- [x] **Tarefa 1: Implementar o caso de uso `SyncInstructionsUseCase` no Domínio e Aplicação (AC: 1, 2, 3)**
  - [x] Criar as classes de comando e resultado `SyncInstructionsCommand` e `SyncInstructionsResult` em `src/universal_memory/application/host/sync_instructions_use_case.py`.
  - [x] Implementar a classe `SyncInstructionsUseCase` em `src/universal_memory/application/host/sync_instructions_use_case.py`.
  - [x] Fazer com que o caso de uso carregue regras ativas do `RuleRepository` e agrupe/classifique-as conforme suas categorias (`shared_policy`, `provider_delta`, `scoped_rule`, `canonical_doc`).
  - [x] Orquestrar a execução conjunta de escritas seguras de tal forma que `AGENTS.md` seja gerado e atualizado uma única vez por ciclo de sincronização (mesmo se múltiplos hosts o consumirem).
  - [x] Tratar a conversão de regras classificadas como `canonical_doc` para que seu conteúdo longo seja escrito em um arquivo na pasta `docs/` e apenas um link canônico seja incluído nos manifestos de instrução (`AGENTS.md`).
  - [x] Registrar adequadamente os eventos de auditoria e gerenciar snapshots e rollbacks coordenados no pipeline de escrita segura para múltiplos arquivos em caso de falha.

- [x] **Tarefa 2: Adicionar o comando de CLI correspondente `umem host sync` (AC: 1, 2)**
  - [x] No arquivo `src/universal_memory/interfaces/cli/init_command.py`, adicionar o comando `@host_app.command("sync")`.
  - [x] Configurar parâmetros para `--apply` / `--no-apply` (para dry-run/preview) e `--format json` / `--format human`.
  - [x] Garantir conformidade total com o `devex-interaction-spec.md` exibindo escopo da operação, caminhos afetados, snapshots planejados, referências de auditoria e solicitações de confirmação amigáveis (com opções Sim, Sempre e Não onde apropriado).
  - [x] Retornar o envelope JSON padronizado quando a flag correspondente for usada.

- [x] **Tarefa 3: Expor a funcionalidade de sincronização como uma ferramenta MCP (AC: 1)**
  - [x] Registrar a ferramenta `sync_instructions` no bootstrap do servidor MCP em `src/universal_memory/bootstrap/mcp.py`.
  - [x] Mapear adequadamente os parâmetros de entrada e formatar os retornos em conformidade com o protocolo JSON-RPC.

- [x] **Tarefa 4: Criar testes abrangentes para o fluxo de sincronização (AC: 1, 2, 3)**
  - [x] Escrever testes unitários em `tests/application/host/test_sync_instructions.py` validando o comportamento de roteamento de regras, a escrita única de `AGENTS.md` e a substituição de documentos canônicos por pointers.
  - [x] Escrever testes de integração para o comando CLI em `tests/interfaces/cli/test_host_sync.py`.

### Review Findings

- [x] [Review][Decision] Dependência de Repositório Vazio em Produção — Nos arquivos de bootstrap (cli.py e mcp.py), o caso de uso SyncInstructionsUseCase é instanciado com EmptyRuleRepository(), tornando a sincronização inoperante em produção. Devemos plugar um repositório real ou manter assim temporariamente?
- [x] [Review][Decision] Acoplamento Extremo com Métodos Privados — A classe SyncInstructionsUseCase acessa diretamente múltiplos métodos privados (iniciados com '_') de ConfigureHostUseCase (como _drift_content, _host_for, etc.). Devemos refatorar para expor métodos públicos limpos ou prosseguir com o acesso privado atual?
- [x] [Review][Patch] Crash por AttributeError quando rule.metadata é nulo [src/universal_memory/application/host/sync_instructions_use_case.py:405-408]
- [x] [Review][Patch] Ausência de rollbacks coordenados em caso de falha de escrita [src/universal_memory/application/host/sync_instructions_use_case.py:330-363]
- [x] [Review][Patch] Filtro de host_ids ignorado forçando sync do Codex [src/universal_memory/application/host/sync_instructions_use_case.py:372-383]
- [x] [Review][Patch] Vulnerabilidade de Path Traversal nos caminhos de regras [src/universal_memory/application/host/sync_instructions_use_case.py:405-430]
- [x] [Review][Patch] Omissão de warnings no payload JSON de SyncInstructionsResult [src/universal_memory/application/host/sync_instructions_use_case.py:100-115]
- [x] [Review][Patch] Mensagem enganosa no Dry-Run da CLI e falta de tabela rica [src/universal_memory/interfaces/cli/init_command.py:673-724]
- [x] [Review][Patch] Ausência do Escopo na tabela de preview da CLI [src/universal_memory/interfaces/cli/init_command.py:762-781]
- [x] [Review][Patch] Falta de testes de integração para a UX humana e interatividade da CLI [tests/interfaces/cli/test_host_sync.py:1-82]
- [x] [Review][Patch] Poluição de referências com valores not-applied/planned concatenados [src/universal_memory/application/host/sync_instructions_use_case.py:330-363]
- [x] [Review][Patch] Sequestro de parâmetro host_ids quando passado vazio [src/universal_memory/application/host/sync_instructions_use_case.py:120-130]
- [x] [Review][Patch] Omissão de ações conflitantes em caminhos físicos duplicados [src/universal_memory/application/host/sync_instructions_use_case.py:250-260]

## Dev Notes

- **Aproveitamento de Recursos Existentes:** O `ConfigureHostUseCase` em `setup_host_use_case.py` já possui lógica avançada para particionamento de instruções (`partition_instruction_blocks`), preservação de conteúdo fora do bloco UMEM (`_merge_managed_block`), tratamento de documentos canônicos (`_render_canonical_document`) e validação de drift para Claude Code. O novo caso de uso `SyncInstructionsUseCase` deve se integrar e alavancar esses métodos ao invés de duplicá-los.
- **RuleRepository:** Atualmente, `bootstrap/cli.py` e `bootstrap/mcp.py` injetam um `EmptyRuleRepository`. Para testar e implementar o fluxo real, certifique-se de que o repositório correto possa fornecer as regras cadastradas ou forneça uma implementação local fake nos testes.
- **Escrita Única:** Ao planejar mudanças para múltiplos hosts (como `codex` e `claude_code`), ambos podem referenciar a pasta `docs/` ou exigir a validação de `AGENTS.md`. Garanta que a mutação física de `AGENTS.md` ocorra em uma transação lógica única de escrita segura com um único snapshot e evento de auditoria correspondente.

### Project Structure Notes

- O código deve seguir o padrão arquitetural DDD / Clean Architecture estabelecido, colocando o caso de uso em `application/host/sync_instructions_use_case.py` e registrando as dependências in `bootstrap/cli.py` e `bootstrap/mcp.py`.

### References

- [Architecture Guidelines: Host Support Matrix](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#Host%20Support%20Matrix)
- [Architecture Guidelines: Rules and Manifest Strategy](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#Rules%20and%20Manifest%20Strategy)
- [Acceptance Criteria: Epic 5 Story 5.5](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/epics.md#Story%205.5)
- [DevEx CLI & Mutation Specifications](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- `uv run pytest tests/application/host/test_sync_instructions.py tests/interfaces/cli/test_host_command.py tests/interfaces/mcp/test_server.py`
- `uv run ruff check src tests`
- `uv run pytest`

### Completion Notes List

- Implementado `SyncInstructionsUseCase` com comando/resultado próprios, leitura de regras ativas do `RuleRepository`, classificação por metadata e reaproveitamento da renderização/validação de host existente.
- A sincronização conjunta escreve `AGENTS.md` uma única vez por ciclo, preserva deltas de `CLAUDE.md`, move `canonical_doc` para `docs/` e mantém apenas ponteiros compactos no manifesto.
- Adicionado `umem host sync` com preview, `--apply/--no-apply`, JSON padronizado e confirmação para mutações em modo humano/JSON apply com `--yes`.
- Exposta a tool MCP `sync_instructions` e atualizado o contrato de compliance MCP.
- Validação concluída com `ruff` limpo e suíte completa: `287 passed`.

### File List

- `src/universal_memory/application/host/sync_instructions_use_case.py`
- `src/universal_memory/application/host/__init__.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/host/test_sync_instructions.py`
- `tests/interfaces/cli/test_host_sync.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_server.py`
- `_bmad-output/implementation-artifacts/5-5-sincronizar-regras-consolidadas-para-instru-es.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-05-29: Implementada a sincronização de instruções para regras aprovadas, CLI `host sync`, tool MCP `sync_instructions`, cobertura de testes/compliance e correções do Code Review.
