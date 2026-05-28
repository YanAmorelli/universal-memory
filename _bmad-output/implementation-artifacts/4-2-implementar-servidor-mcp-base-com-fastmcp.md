# Story 4.2: Implementar Servidor MCP Base com FastMCP

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um agente externo compatível com MCP,
eu quero acessar o `universal-memory` por um servidor MCP nativo,
para que eu consiga ler contexto e invocar capacidades sem depender de subprocessos CLI.

## Acceptance Criteria

1. **Estrutura e Registro Base do FastMCP**:
   - **Dado** o pacote Python inicializado com a dependência `fastmcp>=0.1.0` configurada,
   - **Quando** o servidor MCP é executado,
   - **Then** ele deve instanciar e expor um servidor FastMCP com o nome `"universal-memory"`;
   - **And** deve registrar as ferramentas ou recursos base de forma limpa usando a API declarativa do FastMCP (`@mcp.tool` ou `@mcp.resource`).

2. **Exposição de Status (Health Check) e Leitura de Contexto**:
   - **Dado** o servidor MCP rodando,
   - **When** um cliente invoca a leitura de status (health check) ou a recuperação de contexto,
   - **Then** o servidor deve expor pelo menos:
     - Uma ferramenta/recurso correspondente ao comando `status` (`GetMemoryStatusUseCase`).
     - Uma ferramenta/recurso correspondente ao comando `context` (`AssembleContextSummaryUseCase`).
   - **And** as respostas MCP devem preservar exatamente os mesmos campos semânticos definidos em `_bmad-output/planning-artifacts/devex-interaction-spec.md` para a respectiva CLI JSON (envelope exato contendo `ok: true`, `operation`, `scope` e `data` com chaves correspondentes).

3. **Arquitetura Limpa e Acoplamento Zero com Repositories**:
   - **Dado** a chamada a qualquer endpoint MCP,
   - **When** o adapter MCP processa a requisição,
   - **Then** ele deve delegar a execução estritamente para a camada de Use Cases da aplicação (injeção de dependência via bootstrap);
   - **And** nunca deve instanciar ou acessar a camada de repositórios, persistência local ou lógica de negócio diretamente dentro dos decorators do MCP.

4. **Operações Offline-First e Robustez Locais**:
   - **Dado** um ambiente offline e sem conectividade com a internet,
   - **When** o servidor MCP inicializa ou executa capacidades locais (como ler o status ou obter o contexto de memória do projeto),
   - **Then** ele deve funcionar sem travar, sem realizar requisições externas e sem depender de nenhum host cloud;
   - **And** falhas em serviços externos de infraestrutura não devem impedir o funcionamento das operações locais básicas.

## Tasks / Subtasks

- [x] **Task 1: Estruturar o Diretório do Adapter MCP** (AC: 1, 3)
  - [x] Criar a pasta do adaptador em `src/universal_memory/interfaces/mcp/`.
  - [x] Criar o arquivo `src/universal_memory/interfaces/mcp/__init__.py`.
  - [x] Criar `src/universal_memory/interfaces/mcp/server.py` contendo a inicialização do FastMCP:
    ```python
    from fastmcp import FastMCP
    mcp = FastMCP("universal-memory")
    ```
  - [x] Definir a interface de injeção dos Use Cases no servidor MCP (por exemplo, criando uma função ou classe de configuração para registrar as rotas dinamicamente a partir dos use cases providos).

- [x] **Task 2: Criar o Bootstrap do Servidor MCP** (AC: 1, 3)
  - [x] Criar o módulo `src/universal_memory/bootstrap/mcp.py` responsible por instanciar a infraestrutura (ports, repositories, layout) e injetar os Use Cases na inicialização do servidor.
  - [x] Garantir o reuso absoluto das mesmas dependências e use cases injetados na CLI (`bootstrap/cli.py`), mantendo a integridade de injeção de dependência e evitando reinventar a roda.
  - [x] Adicionar um comando CLI `mcp start` ou criar um script de entrada para permitir que o usuário inicie o servidor MCP facilmente (ex: através do `umem mcp start` ou `python -m universal_memory.bootstrap.mcp`).

- [x] **Task 3: Implementar a Ferramenta / Recurso `status`** (AC: 2, 3)
  - [x] Expor o endpoint `status` como uma ferramenta do FastMCP (ou recurso `@mcp.resource`).
  - [x] Delegar a execução para `GetMemoryStatusUseCase` injetado.
  - [x] Garantir que o payload de resposta retornado possua a estrutura canônica definida em `devex-interaction-spec.md` (chaves `initialized`, `project_path`, `fact_counts`, `active_rules_count`, `registered_skills_count`, `approximate_size_bytes`, `last_health_check`, `host_validation`, `recommended_action` quando uninitialized).

- [x] **Task 4: Implementar a Ferramenta / Recurso `context`** (AC: 2, 3)
  - [x] Expor o endpoint `context` como uma ferramenta do FastMCP.
  - [x] Delegar a execução para `AssembleContextSummaryUseCase` injetado.
  - [x] Garantir que o payload de resposta preserve os campos definidos em `devex-interaction-spec.md` (chaves `project_summary`, `universal_preferences`, `active_rules`, `source_fact_ids`, `truncated`, `token_estimate`, `last_read_at`).

- [x] **Task 5: Tratamento de Erros Inicial e Mapeamento de Exceções** (AC: 2)
  - [x] Embora o mapeamento exato de códigos JSON-RPC seja o foco da Story 4.4, implementar tratamento básico no adapter MCP para capturar exceções de domínio e retorná-las com mensagens limpas e seguras de depuração.
  - [x] Garantir que segredos ou caminhos absolutos vazados não sejam expostos em mensagens de erro do MCP.

- [x] **Task 6: Adicionar Testes de Paridade e Integração para MCP** (AC: 1, 2, 3, 4)
  - [x] Criar arquivo `tests/interfaces/mcp/test_server.py`.
  - [x] Testar que a instância do servidor MCP inicializa offline com sucesso.
  - [x] Testar a ferramenta `status` injetando um mock do Use Case e assertando que o payload retornado segue exatamente a estrutura do `devex-interaction-spec.md`.
  - [x] Testar a ferramenta `context` com um mock do use case equivalente, validando os campos e a coerência semântica.
  - [x] Rodar a suíte inteira usando `pytest` e garantir 100% de sucesso.

### Review Findings

- [x] [Review][Decision] Missing Compiled Context Content in context Tool Response — The context tool processes all metadata but omits the actual assembled context string (context_markdown) in the returned data envelope. Since the devex-interaction-spec.md spec does not list a specific key for the full markdown text in the JSON keys, we need to decide how to return this.
- [x] [Review][Decision] Hardcoded Portuguese Error Messages — The error message mappings return Portuguese text (e.g. "Conteudo sensivel bloqueado."), whereas the rest of the codebase and exceptions are in English. While consistent with user-facing CLI localization, we should confirm if this is the desired behavior for MCP tools.
- [x] [Review][Patch] Registered MCP tools lack docstrings [src/universal_memory/interfaces/mcp/server.py:56]
- [x] [Review][Patch] Unused global FastMCP instance [src/universal_memory/interfaces/mcp/server.py:32]
- [x] [Review][Patch] Secondary AttributeError risk in sanitization handler [src/universal_memory/interfaces/mcp/server.py:198]
- [x] [Review][Patch] Unix-centric regular expression in path sanitization [src/universal_memory/interfaces/mcp/server.py:199]
- [x] [Review][Patch] scope parameter type validation and json schema auto-docs [src/universal_memory/interfaces/mcp/server.py:143]
- [x] [Review][Patch] Path.cwd() exception risk in build_server [src/universal_memory/bootstrap/mcp.py:27]
- [x] [Review][Defer] Tool calls catch-all wrapper prevents JSON-RPC standard error signaling [src/universal_memory/interfaces/mcp/server.py:58] — deferred, pre-existing
- [x] [Review][Defer] Static project root binding prevents dynamic multi-project directory switching [src/universal_memory/bootstrap/mcp.py:26] — deferred, pre-existing

## Dev Notes

- **Reuse, Don't Reinvent**: Não recrie a lógica de leitura do status ou agrupamento de fatos/regras! Todo o comportamento de negócio reside em `GetMemoryStatusUseCase` e `AssembleContextSummaryUseCase`. O adaptador FastMCP deve ser uma casca extremamente fina (~thin adapter~).
- **Synchronous Use Cases & FastMCP Threading**: Conforme a arquitetura, os Use Cases locais de I/O são síncronos. O FastMCP gerencia automaticamente a execução de funções síncronas em sua thread pool interna, garantindo compatibilidade assíncrona com o protocolo JSON-RPC sem que você precise assincronizar os use cases.
- **Strict Separation of Concerns**:
  - `interfaces/mcp/server.py` contém os decorators e a inicialização de rotas.
  - `bootstrap/mcp.py` instancia os repositórios reais e injeta nos use cases, que são injetados nas rotas do servidor.

### Project Structure Notes

Seguir estritamente o layout modular Clean Arch:
- A lógica de exposição do protocolo MCP fica sob `src/universal_memory/interfaces/mcp/`.
- O bootstrapper real do servidor fica sob `src/universal_memory/bootstrap/mcp.py`.

### References

- [epics.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/epics.md#L702-L726) - Especificação original da Story 4.2.
- [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md#L133-L162) - Definição dos campos semânticos de Status e Contexto.
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L392-L397) - Estrutura de arquivos do adaptador MCP recomendada.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-28T11:50:25-03:00: RED inicial com `uv run pytest tests/interfaces/mcp/test_server.py` falhou por ausencia de `universal_memory.interfaces.mcp`.
- 2026-05-28T11:50:25-03:00: GREEN focado com `uv run pytest tests/interfaces/mcp/test_server.py` passou com 5 testes.
- 2026-05-28T11:50:25-03:00: Regressao e qualidade validadas com `uv run pytest` (201 passed), `uv run ruff check .` e `uv run pyright`.

### Completion Notes List

- Implementado adapter MCP fino em `src/universal_memory/interfaces/mcp/server.py`, com `FastMCP("universal-memory")`, injeção explícita via `MCPUseCases` e ferramentas declarativas `status` e `context`.
- Implementado bootstrap MCP em `src/universal_memory/bootstrap/mcp.py`, reutilizando as mesmas dependências locais da composição CLI para `GetMemoryStatusUseCase` e `AssembleContextSummaryUseCase`.
- Adicionado script de entrada `umem-mcp` em `pyproject.toml`; `python -m universal_memory.bootstrap.mcp` também inicia o servidor.
- Adicionado tratamento básico de erros do adapter MCP com códigos semânticos e sanitização de detalhes para evitar vazamento de segredos e caminhos absolutos.
- Adicionada cobertura de paridade/integracao em `tests/interfaces/mcp/test_server.py` para inicialização offline, payloads de `status` e `context`, sanitização de erros e bootstrap real.

### File List

- `_bmad-output/implementation-artifacts/4-2-implementar-servidor-mcp-base-com-fastmcp.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `pyproject.toml`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/mcp/__init__.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/interfaces/mcp/test_server.py`

### Change Log

- 2026-05-28T11:50:25-03:00: Implementado servidor MCP base com FastMCP, bootstrap local, ferramentas `status`/`context`, sanitizacao de erros e testes de paridade/offline.
