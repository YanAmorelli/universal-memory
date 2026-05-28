# Story 4.4: Mapear Erros de Domínio para CLI e JSON-RPC

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como usuário ou agente consumidor da interface,
quero receber erros consistentes e acionáveis,
para que eu consiga entender falhas sem depender de detalhes internos do sistema.

## Acceptance Criteria

1. **Tratamento de Exceções de Domínio na CLI**:
   - **Dado** que uma exceção de domínio conhecida ocorra (`SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, `StorageError`),
   - **Quando** ela é capturada pelo adaptador CLI (`init_command.py`),
   - **Então** a CLI deve renderizar uma mensagem clara usando componentes Rich (`Panel`, `Text`), apresentando um resumo amigável, detalhe seguro e hint de recuperação.
   - **E** a CLI não deve imprimir stack trace (rastreamento de pilha) por padrão para esses erros de negócio esperados.
   - **E** a CLI deve encerrar a execução com código de status de saída não-zero (ex: `1`).
   - **E** se o formato de saída for `--format json`, deve retornar estritamente o envelope JSON de erro especificado em `devex-interaction-spec.md`.

2. **Mapeamento de Exceções de Domínio no MCP**:
   - **Dado** que uma exceção de domínio conhecida ocorra,
   - **Quando** ela é capturada pelo adaptador MCP (`server.py`),
   - **Então** ela deve ser mapeada para um código JSON-RPC apropriado:
     - `SecretDetectedError` -> `-32010`
     - `SnapshotFailedError` -> `-32020`
     - `ValidationFailedError` -> `-32602` (padrão JSON-RPC de Invalid Params)
     - `FactNotFoundError` -> `-32040`
     - `InvalidConfigError` -> `-32050`
     - `StorageError` -> `-32060`
   - **E** a resposta deve incluir `data.detail` sanitizado de forma segura contra segredos ou caminhos absolutos locais do sistema de arquivos.
   - **E** deve incluir `data.recovery_hint` para orientar ações corretivas seguras.

3. **Tratamento Seguro de Erros Inesperados**:
   - **Dado** que um erro inesperado e não classificado ocorra (qualquer subclasse genérica de `Exception` que não seja de domínio),
   - **Quando** ele ocorre em qualquer adaptador (CLI ou MCP),
   - **Então** o sistema deve retornar um erro genérico seguro (ex: `"Unexpected error."` no CLI ou código `-32603` no MCP).
   - **E** a stack trace completa e os detalhes brutos devem ser registrados apenas em canais de diagnósticos diagnósticos adequados (como stderr ou log de auditoria interno) para preservar a segurança contra o vazamento de segredos na saída principal entregue ao usuário ou agente.

## Tasks / Subtasks

- [x] **Task 1: Unificar e Centralizar a Sanitização de Detalhes de Erro** (AC: 1, 2, 3)
  - [x] Garantir que a lógica de sanitização de caminhos absolutos (Unix e Windows) e de strings que se parecem com chaves e segredos de API (ex: `sk-`, `pk-`) seja executada de maneira centralizada e consistente para ambos os adaptadores (CLI e MCP).
  - [x] Certificar-se de que o erro `SecretDetectedError` nunca ecoe o segredo ou partes do segredo na saída do terminal ou no payload de resposta de erros.
  - [x] Desenvolver ou refinar helper de formatação/redação de erro no domínio ou nas interfaces.

- [x] **Task 2: Refinar Lógica de Erros no Adaptador CLI** (AC: 1, 3)
  - [x] Mapear as capturas de exceção (`except`) nos helpers de execução da CLI (`_run_remember`, `_run_facts_list`, `_run_context`, `_run_rollback`, etc.) para garantir que todas as exceções de domínio conhecidas sejam passadas para `_print_expected_error` de forma limpa.
  - [x] Garantir que para erros inesperados (`except Exception`), o CLI imprima uma stack trace adequada se o modo debug ou verbose estiver ativado, mas de forma padrão retorne um painel limpo informando "Erro inesperado" com código de status `1`.
  - [x] Assegurar que os payloads JSON de erro da CLI sigam exatamente a estrutura canônica:
    ```json
    {
      "ok": false,
      "error": {
        "code": "validation_failed",
        "message": "Configuration is invalid.",
        "detail": "Missing project memory path.",
        "recovery_hint": "Run umem init from the project root.",
        "audit_reference": null
      }
    }
    ```

- [x] **Task 3: Refinar Lógica de Sinalização de Erros no Servidor MCP** (AC: 2, 3)
  - [x] Resolver o feedback de arquitetura/deferred-work do Epic 4-2: A ferramenta MCP intercepta todas as exceções de domínio e retorna `{"ok": False, "error": ...}` dentro de um envelope de sucesso do FastMCP. Isso impede que o host cliente de JSON-RPC detecte a falha real da ferramenta.
  - [x] Ajustar os endpoints de tool do MCP em `server.py` para lançar exceções apropriadas (como `ValidationError` ou encapsular a exceção em uma exceção que o FastMCP interprete como falha de execução de ferramenta com o código e mensagem JSON-RPC corretos) se necessário, OU garantir conformidade explícita com o comportamento esperado de tratamento de erro do protocolo MCP.
  - [x] Validar que todas as ferramentas MCP (`initialize_project`, `status`, `context`, `remember_fact`, `list_facts`, `purge_fact`, `list_audit_events`, `list_snapshots`, `rollback_scope`) implementam e respeitam o mapeamento e sanitização de erro.

- [x] **Task 4: Implementar Suíte de Testes de Erro e Robustez** (AC: 1, 2, 3)
  - [x] Criar testes sob `tests/interfaces/test_errors.py` ou expandir `tests/interfaces/test_parity.py` para injetar use cases com falhas mockadas.
  - [x] Testar a CLI sob as saídas `human` e `json` para cada uma das exceções de domínio conhecidas. Assertar o código de saída `1` e a estrutura Rich e JSON respectivamente.
  - [x] Testar o MCP para cada uma das exceções, garantindo que o código JSON-RPC (`-32010`, `-32020`, `-32602`, `-32040`, `-32050`, `-32060`) esteja correto e que os caminhos e segredos mockados sejam devidamente mascarados no `detail`.
  - [x] Testar cenários de erro inesperado (ex: lançando `RuntimeError` genérico), assertando que stack traces brutas são omitidas da saída amigável e que logs diagnósticos contêm os dados para manutenção.

### Review Findings

- [x] [Review][Patch] Exposição de exceções genéricas nativas (ValueError/OSError) como erros esperados do domínio [src/universal_memory/interfaces/errors.py]
- [x] [Review][Patch] Fragilidade e potencial vazamento de segredos na extração de recovery_hint via "Hint:" [src/universal_memory/interfaces/errors.py:129-134]
- [x] [Review][Patch] Formato inconsistente (Human em vez de JSON) para exceções não capturadas no CLI global main [src/universal_memory/interfaces/cli/init_command.py:125-135]
- [x] [Review][Patch] Crash (TypeError) se UniversalMemoryError possuir atributo message igual a None [src/universal_memory/interfaces/errors.py:142-146]
- [x] [Review][Patch] Omissão de tipagem de retorno -> dict[str, Any] em ferramentas MCP [src/universal_memory/interfaces/mcp/server.py]
- [x] [Review][Defer] Importação redundante e namespace poluído em server.py [src/universal_memory/interfaces/mcp/server.py:44-50] — deferred, pre-existing
- [x] [Review][Defer] Expressões regulares simplistas em sanitização de caminhos absolutos e chaves [src/universal_memory/interfaces/errors.py] — deferred, pre-existing
- [x] [Review][Defer] Lógica de internacionalização (locale) hardcoded nos payloads de erro [src/universal_memory/interfaces/errors.py:157-165] — deferred, pre-existing
- [x] [Review][Defer] Acesso direto a variáveis de ambiente (os.environ) em adapters CLI [src/universal_memory/interfaces/cli/init_command.py:1282] — deferred, pre-existing
- [x] [Review][Defer] Violação DRY na repetição de lógica de capturas de exceções OSError na CLI [src/universal_memory/interfaces/cli/init_command.py] — deferred, pre-existing

## Dev Notes


### Diretrizes de Arquitetura e Limpeza
- **Adapters Finos e Reuso**: CLI e MCP apenas adaptam as entradas e saídas. A lógica de qual erro disparar e as informações essenciais residem no Use Case ou Repositório do Domínio. As interfaces apenas realizam a tradução e a sanitização.
- **Sanitização de Caminhos Locais**: Muito importante para privacidade e DevEx. Caminhos absolutos como `/Users/amorelliaoyan/projects/...` devem ser transformados em `<path>` ou caminhos relativos ao projeto para não expor a estrutura de diretórios do usuário local.
- **Protocolo MCP e FastMCP Error Handling**: No FastMCP, se uma ferramenta levanta uma exceção, ela é capturada pelo servidor e convertida em um erro JSON-RPC. Precisamos garantir que as exceções levantadas sejam convertidas com os códigos customizados correspondentes (`-32010`, etc.) de acordo com a especificação, ou que o payload retornado sinalize a falha corretamente caso o FastMCP exija que a ferramenta lance uma exceção específica de erro.

### Componentes a Alterar no Source Tree
- `src/universal_memory/interfaces/cli/init_command.py` -> Revisar capture e exibição em `_print_expected_error`, garantindo que toda a suite CLI capture as exceções de forma homogênea.
- `src/universal_memory/interfaces/mcp/server.py` -> Ajustar wrappers de tools para tratamento de erros JSON-RPC e conformidade com hosts.
- `tests/interfaces/test_parity.py` (ou `tests/interfaces/test_errors.py`) -> Testar cobertura de caminhos de erro e sanitização.

### References
- [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md#L93-L113) - Tabela de Mapeamento de Erros de Domínio e Envelope de Erro Canônico.
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L738-L751) - Mapeamento técnico de códigos JSON-RPC para exceções.
- [deferred-work.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/implementation-artifacts/deferred-work.md#L28-L32) - Feedback de Tool Calls Catch-all do MCP.

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Implementation Plan
- Centralizar descritores, codigos, hints e sanitizacao de erro em helper compartilhado de interfaces.
- Fazer a CLI consumir o helper para erros esperados e retornar erro inesperado generico por padrao.
- Fazer o MCP consumir o mesmo helper, preservar os codigos JSON-RPC e marcar falhas como resultado de tool com `isError=true`.
- Cobrir dominio, CLI e MCP com testes de envelope, redacao e falhas inesperadas.

### Debug Log References
- 2026-05-28: `uv run pytest tests/interfaces/test_errors.py tests/interfaces/test_parity.py tests/interfaces/mcp/test_server.py` -> 29 passed.
- 2026-05-28: `uv run pytest` -> 225 passed.
- 2026-05-28: `uv run ruff check .` -> All checks passed.
- 2026-05-28: `uv run pyright` -> 0 errors, 0 warnings, 0 informations.

### Completion Notes List
- Implementado helper compartilhado de contrato de erro e sanitizacao em `src/universal_memory/interfaces/errors.py`.
- CLI agora usa captura homogênea de exceções de dominio conhecidas, envelope JSON canonico e painel Rich com detalhe sanitizado.
- Erros inesperados na CLI retornam mensagem generica por padrao; stack trace so e emitida quando `UMEM_DEBUG_ERRORS=1`.
- MCP agora centraliza mapeamento para codigos JSON-RPC, inclui `data.detail` e `data.recovery_hint`, e retorna resultado de tool com `isError=true` para falhas estruturadas.
- Cobertura adicionada para excecoes de dominio, segredo/caminho absoluto, saida CLI human/json, erros MCP e cenarios inesperados.

### File List
- `src/universal_memory/interfaces/errors.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/interfaces/test_errors.py`
- `tests/interfaces/test_parity.py`
- `tests/interfaces/mcp/test_server.py`

### Change Log
- 2026-05-28: Implementado mapeamento centralizado de erros CLI/MCP, sanitizacao compartilhada e suite de testes de robustez.
