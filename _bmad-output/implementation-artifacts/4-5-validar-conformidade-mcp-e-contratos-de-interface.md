# Story 4.5: Validar Conformidade MCP e Contratos de Interface

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do universal-memory,
quero uma suíte de validação robusta para o servidor MCP e testes de contrato de interface,
para garantir que mudanças ou refatorações futuras não quebrem a leitura, escrita e tratamento de erros por agentes externos.

## Acceptance Criteria

1. **Suíte de Conformidade MCP Local (Offline)**:
   - **Dado** o servidor MCP com suas capacidades públicas configuradas (`initialize_project`, `status`, `context`, `remember_fact`, `list_facts`, `purge_fact`, `list_audit_events`, `list_snapshots`, `rollback_scope`),
   - **Quando** a suíte de conformidade de testes roda,
   - **Então** ela deve testar todas as ferramentas MCP de forma integrada sem depender de conexões ou rede externa (offline-first).
   - **E** deve validar envelopes de sucesso e o tratamento de exceções de domínio/inesperadas mapeadas para erros estruturados JSON-RPC do MCP (`CallToolResult` com `isError=True` e `structuredContent` populado).

2. **Testes de Contrato de Interface CLI vs MCP**:
   - **Dado** as saídas da CLI executada com a flag `--format json` e as saídas estruturadas das ferramentas equivalentes do MCP,
   - **Quando** os testes de contrato comparam os dois resultados para a mesma operação,
   - **Então** os campos essenciais estruturados dos payloads devem ser semanticamente equivalentes e idênticos em seu formato (conforme `devex-interaction-spec.md`).
   - **E** diferenças nos adaptadores devem ficar estritamente restritas à camada de apresentação (Rich UI no CLI vs JSON estruturado puro no MCP).

3. **Garantia de Acionabilidade em Falha de Validação**:
   - **Dado** uma falha de validação de conformidade MCP ou uma divergência de chaves de contrato entre as interfaces,
   - **Quando** o teste falha,
   - **Então** a mensagem de falha deve apontar claramente qual capacidade, chave de contrato ou campo estruturado está divergente ou ausente.
   - **E** a suíte de conformidade deve atuar como blocker na CI para novos desenvolvimentos de interface.

## Tasks / Subtasks

- [x] **Task 1: Desenvolver a Suíte de Conformidade MCP** (AC: 1, 3)
  - [x] Criar ou expandir suíte de testes de conformidade integrada em `tests/interfaces/mcp/test_compliance.py` cobrindo o ciclo completo do protocolo MCP para as ferramentas expostas.
  - [x] Garantir validação de health check, leitura e escrita de contexto, propostas e ciclo de mutação seguro (incluindo stubs de permissões ou auditoria e reversões).
  - [x] Bloquear acessos de rede externa durante o bootstrapping e testes do servidor MCP para assegurar conformidade local offline.

- [x] **Task 2: Implementar Testes de Contrato CLI vs MCP** (AC: 2, 3)
  - [x] Refinar e estender o validador de contratos em `tests/interfaces/test_parity.py` para comparar a igualdade de chaves e tipos de payloads JSON-RPC versus CLI `--format json`.
  - [x] Garantir que chaves como `initialized`, `project_path`, `fact_counts`, `audit_reference`, `snapshots`, `events`, etc., possuam a mesma estrutura canônica de dados nas duas interfaces.
  - [x] Criar asserções amigáveis que, ao falharem, imprimam exatamente qual chave ou tipo está inconsistente entre as duas interfaces.

- [x] **Task 3: Validar Paridade Operacional e CI Guardrails** (AC: 1, 2)
  - [x] Assegurar que exclusões intencionais de paridade estejam documentadas e que novas capacidades ativem alertas ou erros de contrato.
  - [x] Validar a passagem íntegra de todos os testes através de `uv run pytest`.

### Review Findings

- [x] [Review][Dismiss] Dangerous cast on MCP tool error returns [src/universal_memory/interfaces/mcp/server.py:111-289] — dismissed, required by FastMCP runtime reflection behavior
- [x] [Review][Patch] Uncaught filesystem exceptions in _relative_path [src/universal_memory/interfaces/cli/init_command.py:1306-1313]
- [x] [Review][Patch] Inconsistent relative path roots and Path.cwd() dependency [src/universal_memory/interfaces/cli/init_command.py:981]

## Dev Notes

- **Adapters e Limpeza**: As saídas estruturadas JSON da CLI e MCP devem compartilhar a mesma origem mental e serializadores de dados do domínio. Os use cases de aplicação devem produzir os mesmos DTOs que são mapeados diretamente para JSON em ambas as extremidades.
- **Protocolo Offline-First**: O servidor FastMCP e suas dependências não devem inicializar sockets de escuta ou buscar portas na rede a menos que solicitados. Os testes devem simular tool calls diretamente por meio do `server.call_tool` exposto pelo FastMCP sem instanciar rede real.
- **Tratamento de Exceções**: Testar exaustivamente se as exceções de domínio são interceptadas pelo middleware ou tratadas com conformidade, retornando os códigos JSON-RPC corretos definidos no mapeamento de erros.

### Project Structure Notes

- O servidor MCP reside em `src/universal_memory/interfaces/mcp/server.py`.
- O adaptador CLI reside em `src/universal_memory/interfaces/cli/init_command.py`.
- A matriz de paridade e regras de interação CLI/MCP residem em `tests/interfaces/test_parity.py` e `tests/interfaces/test_errors.py`.
- A conformidade deve herdar padrões existentes, sem reinventar estruturas de dados ou lógica de negócios nos testes.

### References

- [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md) - Especificação de envelopes, chaves esperadas e envelopes de erro.
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L847-L851) - Residual Gap Analysis da suíte de conformidade MCP.
- [test_parity.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/tests/interfaces/test_parity.py) - Matriz de paridade e stubs das interfaces CLI e MCP.

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- `uv run pytest tests/interfaces/mcp/test_compliance.py` - red inicial ajustado para o envelope real do FastMCP; depois 4 passed.
- `uv run pytest tests/interfaces/test_parity.py` - red de path absoluto em `initialize_project.audit_path`; corrigido no serializador da CLI.
- `uv run ruff check` - import order e constante de erro corrigidos; final verde.
- `uv run pyright` - erro de tipo em retornos MCP tratado com `cast` sem alterar serializacao do FastMCP; final verde.
- `uv run pytest` - 230 passed.

### Completion Notes List

- Implementada suíte offline de conformidade MCP cobrindo inventário público completo, envelopes de sucesso, erros de domínio, erros inesperados e confirmação obrigatória para mutações destrutivas.
- Paridade CLI vs MCP ampliada para `init`, validação recursiva de chaves, tipos e valores escalares, além de fixtures não vazias para `events` e `snapshots`.
- Corrigida saída JSON da CLI `init` para emitir paths relativos ao projeto, alinhada ao contrato MCP e ao `devex-interaction-spec.md`.
- Ajustadas anotações internas do servidor MCP para satisfazer Pyright sem alterar o formato runtime esperado pelo FastMCP.

### File List

- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-05-28: Adicionada conformidade MCP offline, paridade recursiva CLI vs MCP e correção de paths relativos no JSON de `init`.
