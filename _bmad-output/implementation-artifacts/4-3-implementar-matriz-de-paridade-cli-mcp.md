# Story 4.3: Implementar Matriz de Paridade CLI/MCP

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do produto,
quero garantir que capacidades expostas em uma interface existam na outra,
para que humanos e agentes tenham acesso consistente ao mesmo comportamento.

## Acceptance Criteria

1. **Matriz de Paridade e Use Cases Públicos**:
   - **Dado** a matriz de paridade definida na arquitetura,
   - **Quando** uma capacidade pública é implementada,
   - **Então** devem existir pontos de entrada CLI e MCP equivalentes para as seguintes capacidades:
     - `init` (CLI: `umem init`, MCP: `initialize_project`)
     - `status` (CLI: `umem status`, MCP: `status`)
     - `context` (CLI: `umem context`, MCP: `context`)
     - `remember` (CLI: `umem remember`, MCP: `remember_fact`)
     - `list facts` (CLI: `umem facts list`, MCP: `list_facts`)
     - `purge fact` (CLI: `umem facts purge`, MCP: `purge_fact`)
     - `facts hygiene` (CLI: `umem facts hygiene` - *opcional/mcp se aplicável*)
     - `list audit events` (CLI: `umem audit list`, MCP: `list_audit_events`)
     - `list snapshots` (CLI: `umem snapshots list`, MCP: `list_snapshots`)
     - `rollback scope` (CLI: `umem rollback`, MCP: `rollback_scope`)
     - `host setup/check` (CLI: `umem host setup/check`, MCP: `check_host` - *backlog*)
     - `skill proposal/list` (CLI: `umem skills propose/list`, MCP: `propose_skill`, `list_skills` - *backlog*)
   - **E** todas as exceções internas de domínio devem ser capturadas e tratadas de forma equivalente e segura nas duas interfaces.

2. **Suíte de Testes de Paridade Automatizada**:
   - **Dado** a suíte de testes de paridade sob `tests/interfaces/test_parity.py`,
   - **Quando** a suíte roda,
   - **Então** ela deve inspecionar dinamicamente (ou por asserção estrita de contratos) as duas interfaces e falhar se um use case público estiver exposto somente em CLI ou somente em MCP sem uma justificativa explícita documentada no código de testes (evitando drift).
   - **And** deve validar que ambos os adaptadores CLI e MCP para a mesma capacidade retornam estruturas de dados semanticamente equivalentes (chaves JSON idênticas sob o envelope `data` para o mesmo use case).
   - **And** deve validar aderência estrita aos contratos de payload definidos em `_bmad-output/planning-artifacts/devex-interaction-spec.md`.

3. **Governança de Novas Capacidades**:
   - **Dado** o design de novas capacidades futuras (ex: Epic 5 e Epic 6),
   - **Quando** uma nova capacidade pública for introduzida,
   - **Então** o checklist de implementação deve exigir cobertura em ambas as interfaces (CLI e MCP).
   - **E** o contrato de resposta compartilhado deve ser atualizado na especificação antes da entrega final.

## Tasks / Subtasks

- [x] **Task 1: Implementar e Injetar Use Cases Faltantes nos Adaptadores** (AC: 1)
  - [x] Mapear e importar os use cases já implementados no domínio que estão ausentes na CLI ou MCP:
    - CLI precisa de: `AssembleContextSummaryUseCase` (comando `context`) e `RememberFactUseCase` (comando `remember`).
    - MCP precisa de: `SetupProjectUseCase` (`initialize_project`), `RememberFactUseCase` (`remember_fact`), `ListFactsUseCase` (`list_facts`), `PurgeFactUseCase` (`purge_fact`), `ListAuditLogUseCase` (`list_audit_events`), `ListSnapshotsUseCase` (`list_snapshots`) e `RollbackUseCase` (`rollback_scope`).
  - [x] Atualizar o bootstrap da CLI (`src/universal_memory/bootstrap/cli.py`) para injetar `AssembleContextSummaryUseCase` e `RememberFactUseCase` na CLI.
  - [x] Atualizar a classe `MCPUseCases` em `src/universal_memory/interfaces/mcp/server.py` para receber os novos use cases.
  - [x] Atualizar o bootstrap MCP (`src/universal_memory/bootstrap/mcp.py`) para instanciar e passar todos os novos use cases necessários para `configure_server`.

- [x] **Task 2: Desenvolver Comandos CLI Faltantes (`context` e `remember`)** (AC: 1)
  - [x] Criar o comando CLI `umem context` em `init_command.py` com suporte a `--scope` (project/global), `--max-size-chars` e formato human/json. Deve retornar o payload JSON canônico ou formatação Rich concisa de acordo com o `devex-interaction-spec.md`.
  - [x] Criar o comando CLI `umem remember` em `init_command.py` para gravar um fato. Deve suportar a flag `--scope` (project/global), `--tag` (múltiplas tags) e `--format` (human/json). Deve acionar o pipeline de escrita atômica segura (com secret scan e auditoria/snapshot).
  - [x] Garantir formatação humanizada Rich e envelopes de saída JSON pura estritamente alinhados ao `devex-interaction-spec.md`.

- [x] **Task 3: Desenvolver Ferramentas MCP Faltantes** (AC: 1)
  - [x] Em `src/universal_memory/interfaces/mcp/server.py`, registrar as ferramentas usando os decorators do FastMCP:
    - `@server.tool(name="initialize_project")`
    - `@server.tool(name="remember_fact")`
    - `@server.tool(name="list_facts")`
    - `@server.tool(name="purge_fact")`
    - `@server.tool(name="list_audit_events")`
    - `@server.tool(name="list_snapshots")`
    - `@server.tool(name="rollback_scope")`
  - [x] Garantir o reuso absoluto dos mesmos Use Cases da aplicação injetados no servidor MCP.
  - [x] Certificar que todos os payloads retornados pelas novas ferramentas MCP sigam os formatos de chaves descritos em `devex-interaction-spec.md`.

- [x] **Task 4: Tratar Capacidades de Backlog (Rules, Hosts e Skills)** (AC: 1, 2)
  - [x] Para as capacidades do Epic 5 (hosts) e Epic 6 (skills) e `propose_rule` que estão na matriz, mas não possuem use cases reais de negócio:
    - Adicionar mapeamento/justificativa de backlog explícito na lista de exclusão autorizada do teste de paridade (ex: `PARITY_EXCLUSIONS = ["propose_rule", "check_host", "propose_skill", "list_skills"]` com comentários claros referenciando que serão implementados nos seus respectivos Epics futuros).
    - Isso garante que a suíte de paridade passe em verde sem requerer a escrita prematura de código de negócio falso.

- [x] **Task 5: Implementar Suíte de Testes de Paridade e Contratos** (AC: 2)
  - [x] Criar o arquivo de testes `tests/interfaces/test_parity.py`.
  - [x] Implementar um teste que carregue dinamicamente a aplicação Typer CLI (`create_typer_app`) e o servidor MCP (`create_mcp_server`), listando todos os comandos CLI e ferramentas MCP ativas.
  - [x] Validar que, exceto pelos itens explicitamente autorizados na lista de exclusão, cada funcionalidade exposta em CLI possui equivalência MCP direta sob a Matriz de Paridade (evitando drift).
  - [x] Escrever testes de paridade de esquema, mockando as respostas dos use cases e injetando as mesmas estruturas de dados fictícias na CLI e no MCP. Assertar que os payloads de saída JSON de ambas as interfaces possuem exatamente as mesmas chaves sob o envelope `data`.
  - [x] Validar que todas as novas ferramentas MCP tratam e mapeiam exceções de domínio adequadamente para os códigos JSON-RPC corretos definidos na `architecture.md#L738-L751`.

## Dev Notes

### Principais Guardrails de Arquitetura e Erros
- **Adapters Finos (Thin Adapters)**: CLI e MCP são camadas de entrega puras. Nenhum código de acesso a banco, escrita de arquivos, verificação de segredos ou regras de domínio deve ser implementado diretamente neles. Eles apenas traduzem argumentos, invocam o use case e envelopam o resultado.
- **Tratamento de Erros e Sanitização**: Todo erro nas novas ferramentas MCP deve passar por `_error_envelope` e retornar os códigos JSON-RPC corretos. Detalhes devem ser sanitizados por `_sanitize_error_detail` para prevenir vazamento de caminhos absolutos ou tokens/segredos.
- **Semantização de Respostas**: O envelope retornado nas ferramentas MCP e no formato JSON da CLI deve ser estritamente igual. Atente-se à correspondência de chaves de sucesso (`ok`, `operation`, `scope`, `data`, `warnings`) e de erro (`code`, `message`, `detail`).

### Componentes a Alterar no Source Tree
- `src/universal_memory/interfaces/cli/init_command.py` -> Adicionar comandos `context` e `remember`.
- `src/universal_memory/interfaces/mcp/server.py` -> Adicionar decorators MCP e payloads para as novas ferramentas.
- `src/universal_memory/bootstrap/cli.py` -> Injetar novos use cases de memória no construtor CLI.
- `src/universal_memory/bootstrap/mcp.py` -> Instanciar e injetar novos use cases na classe de use cases do MCP.
- `tests/interfaces/test_parity.py` -> Criar a suíte de testes de paridade estrita.

### References
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L695-L712) - Definição da Matriz de Paridade CLI to MCP original.
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L738-L751) - Tabela de mapeamento de erros JSON-RPC e CLI.
- [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md#L226-L244) - Contrato de Paridade e Requisitos de Testes de Integração.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest tests/interfaces/test_parity.py` falhou inicialmente confirmando a ausência de `context_command`, `remember_command` e novos campos em `MCPUseCases`.
- `uv run pytest tests/interfaces/test_parity.py tests/interfaces/mcp/test_server.py tests/interfaces/cli` passou após implementar adaptadores CLI/MCP e contratos de paridade.
- `uv run ruff check .` passou.
- `uv run pyright` passou com 0 erros.
- `uv run pytest` passou com 211 testes.

### Completion Notes List

- Injetados `AssembleContextSummaryUseCase` e `RememberFactUseCase` no bootstrap CLI, preservando adapters finos e pipeline seguro de escrita.
- Expandida a composição MCP para inicialização, memória, auditoria, snapshots e rollback usando os mesmos use cases da aplicação.
- Adicionados comandos CLI `context` e `remember` com saída human/json alinhada ao `devex-interaction-spec.md`.
- Registradas tools MCP faltantes: `initialize_project`, `remember_fact`, `list_facts`, `purge_fact`, `list_audit_events`, `list_snapshots` e `rollback_scope`.
- Criada suíte de paridade com exclusões explícitas para capacidades em backlog (`propose_rule`, `check_host`, `propose_skill`, `list_skills`) e validação de chaves `data` equivalentes.
- MCP agora retorna códigos JSON-RPC numéricos para erros de domínio e mantém sanitização de caminhos absolutos/segredos.

### File List

- `_bmad-output/implementation-artifacts/4-3-implementar-matriz-de-paridade-cli-mcp.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/interfaces/mcp/test_server.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-05-28: Implementada paridade CLI/MCP para capacidades públicas existentes, adicionados contratos automatizados e movida a story para revisão.

### Review Findings

#### Decision Needed
- [x] [Review][Decision] Missing Confirmation Prompt/Mechanisms for Destructive MCP Mutations — The DevEx spec dictates that confirmations are strictly required before purging facts and rolling back snapshots. While the CLI does this interactively, the MCP server executes them instantly without any confirmation checkpoints or arguments. We need to decide if we should require a confirmation boolean parameter in the MCP tool call, or if we accept instant execution for agents in MCP.
- [x] [Review][Decision] Option Drift on `context` Command (`agent_session_key`) — The MCP `context` tool accepts `agent_session_key`, but the CLI `context` command does not, creating an option drift between interfaces. Should we add `--agent-session-key` to the CLI command?

#### Action Items (Patches)
- [x] [Review][Patch] Python Runtime TypeError Crash Risk on Non-Empty Logs in MCP `_entry_dict` [src/universal_memory/interfaces/mcp/server.py:375]
- [x] [Review][Patch] Inconsistent Scope Parameter Parsing and Lack of Typo/Case Handling in MCP Tools [src/universal_memory/interfaces/mcp/server.py:395]
- [x] [Review][Patch] Global Configured Project Root Ignored in MCP Path Calculations [src/universal_memory/interfaces/mcp/server.py:379]
- [x] [Review][Patch] Swallowed Stack Traces in MCP Tool Exception Handlers [src/universal_memory/interfaces/mcp/server.py:103]
- [x] [Review][Patch] Duplicated Fallback Constant for Max Context Size [src/universal_memory/interfaces/cli/init_command.py:206]
- [x] [Review][Patch] Inconsistent ISO 8601 Datetime Serialization [src/universal_memory/interfaces/mcp/server.py:314]
- [x] [Review][Patch] Direct Port Instantiation Bypassing Dependency Injection [src/universal_memory/bootstrap/mcp.py:116]
- [x] [Review][Patch] Duplicate Exception Handling Boilerplate in CLI Command Runners [src/universal_memory/interfaces/cli/init_command.py:299]
- [x] [Review][Patch] Unhandled `ValueError` in CLI `_run_remember` [src/universal_memory/interfaces/cli/init_command.py:336]
- [x] [Review][Patch] Generic JSON-RPC Error Mapping for standard ValueError or OSError in MCP [src/universal_memory/interfaces/mcp/server.py:421]
- [x] [Review][Patch] MCP Error Envelope Missing Standard Keys `recovery_hint` and `audit_reference` [src/universal_memory/interfaces/mcp/server.py:407]

#### Deferred Items (Pre-existing)
- [x] [Review][Defer] Localization Bleed (Portuguese in CLI Option Help vs English Codebase) [src/universal_memory/interfaces/cli/init_command.py:195] — deferred, pre-existing
- [x] [Review][Defer] Crude and Hardcoded Token Count Estimation [src/universal_memory/interfaces/cli/init_command.py:1008] — deferred, pre-existing
- [x] [Review][Defer] Hardcoded `"not-implemented-yet"` Placeholders in Production Contracts [src/universal_memory/interfaces/cli/init_command.py:64] — deferred, pre-existing
