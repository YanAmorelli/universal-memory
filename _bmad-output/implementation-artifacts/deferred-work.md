## Deferred from: code review of 1-4-criar-layout-local-umem-e-configura-o-toml.md (2026-05-24)

- Definir estratégia de auto-reparo resiliente para estados específicos de `.umem/`, incluindo critérios explícitos para distinguir corrupção fatal de layout parcial reparável com segurança, antes de permitir recuperação automática no onboarding.

## Deferred from: code review of 2-4-listar-auditoria-e-snapshots.md (2026-05-26)

- Risco de atropelamento concorrente se operações de escrita excederem o limite fixo de STALE_LOCK_SECONDS = 10.0 em `local_audit_log_repository.py` e `local_snapshot_repository.py`.
- Leitura concorrente de auditoria (`LocalAuditLogRepository.list`) é feita sem adquirir lock, podendo levantar erro de decodificação de JSON ou ValidationError se ler uma linha truncada durante escrita concorrente.

## Deferred from: code review of 3-2-consultar-contexto-local-com-busca-textual.md (2026-05-27)

- Weak Domain Port Typing for `write()` and Abundant `cast(Any, ...)` Workarounds: Dynamic dynamic type checking and casts (`cast(Any, ...)`) due to domain port returning `object | None` instead of typed structures or split ports, indicating leaky design. [src/universal_memory/domain/ports/fact_repository.py:50]
- Clean Architecture Violation: Dynamic Runtime State and Injection on Repository Port: Injecting fields dynamically onto repository instances inside Use Case violating stateless Clean Architecture boundaries. [src/universal_memory/application/memory/remember_fact_use_case.py:40]
- **Skills para Agentes (Capacidades UMEM)**: Criar BMad/Agent Skills específicas para documentar e explicar aos agentes de IA externos cada capacidade entregue pelo UMEM (como a busca offline por substring/regex com metadados de destaque, escrita atômica segura com auditoria e restauração, etc.), permitindo que os agentes usem e gerenciem a memória local de forma totalmente autônoma.


## Deferred from: code review of 3-3-implementar-benchmark-de-recupera-o.md (2026-05-27)

- Duplicação da constante `MIN_REGEX_QUERY_LENGTH` em múltiplos arquivos de teste e produção (`search_facts_use_case.py`, `local_fact_repository.py`, `test_memory_use_cases.py`), reduzindo o DRY.
- Duplicação da lógica de normalização de texto (remoção de acentos via `unicodedata` e `casefold`) entre produção e o script de benchmark.
- Silenciamento silencioso e inseguro de exceções de Expressões Regulares (`except re.error: pass`) ocultando consultas inválidas no repositório de fatos.
- Exposição teórica a vulnerabilidades de negação de serviço por expressões regulares (ReDoS) na busca padrão via entrada direta de strings sem validação de tamanho.

## Deferred from: code review of 3-5-exibir-status-da-mem-ria.md (2026-05-27)

- Inefficient full-database scan to count facts: The status command fetches all facts in memory via `fact_repository.list()` and iterates over them to count them by scope and status. If a user has a massive repository history, this full scan will consume excessive memory and CPU. The repository interface should expose a lightweight count or metadata method instead. [src/universal_memory/application/memory/get_memory_status_use_case.py]

## Deferred from: code review of 4-2-implementar-servidor-mcp-base-com-fastmcp.md (2026-05-28)

- Tool calls catch-all wrapper prevents standard JSON-RPC error signaling: The server catches all exceptions and wraps them in a standard JSON response (`{"ok": False, "error": ...}`) within the success stream, rather than raising exceptions that the JSON-RPC host can catch and mark as failed tool executions. Returning a success status blocks the standard error handling flow of the MCP protocol. [src/universal_memory/interfaces/mcp/server.py:58]
- Static project root binding prevents dynamic multi-project directory switching: The project root is statically bound at configuration time to `Path.cwd()`. Long-running MCP processes used across different editor windows or workspaces will always query the startup directory instead of dynamically adapting to the client's current file path. [src/universal_memory/bootstrap/mcp.py:26]

## Deferred from: code review of 4-3-implementar-matriz-de-paridade-cli-mcp.md (2026-05-28)

- Localization Bleed (Portuguese in CLI Option Help vs English Codebase): The CLI help texts are written in Portuguese while the entire rest of the codebase (including MCP tools, options, JSON keys, and exception names) is designed in English. [src/universal_memory/interfaces/cli/init_command.py:195]
- Crude and Hardcoded Token Count Estimation: Both CLI and MCP approximate token counts using a crude, hardcoded divide-by-four logic rather than leveraging a real tokenizer. [src/universal_memory/interfaces/cli/init_command.py:1008]
- Hardcoded "not-implemented-yet" Placeholders in Production Contracts: The CLI `AUDIT_REFERENCE_PLACEHOLDER` and the MCP `_init_payload` both fallback to the hardcoded string "not-implemented-yet" for the `audit_reference` field, violating production contract readiness. [src/universal_memory/interfaces/cli/init_command.py:64]

