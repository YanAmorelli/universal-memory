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


## Deferred from: code review of 4-4-mapear-erros-de-dom-nio-para-cli-e-json-rpc.md (2026-05-28)

- Importação redundante e namespace poluído: Importa todo o módulo `errors` sob o alias `interface_errors` e, na sequência imediata, importa individualmente funções e chaves do mesmo módulo, poluindo o namespace local. [src/universal_memory/interfaces/mcp/server.py:44-50]
- Expressões regulares simplistas em sanitização de caminhos absolutos e chaves: Expressões regulares de caminho não capturam caminhos contendo espaços, nem caminhos relativos perigosos. As de chaves de API podem sofrer de falsos positivos em variáveis legítimas. [src/universal_memory/interfaces/errors.py]
- Lógica de internacionalização (locale) hardcoded nos payloads de erro: O método `error_payload` realiza uma verificação binária simples baseada na string `"pt-BR"` para traduzir ou não a mensagem técnica, misturando lógica de localização de interface direto na construção dos dados. [src/universal_memory/interfaces/errors.py:157-165]
- Acesso direto a variáveis de ambiente (os.environ) em adapters CLI: Chamadas estáticas diretas a `os.environ.get("UMEM_DEBUG_ERRORS")` dificultam o teste unitário isolado e controle programático do comportamento do CLI. [src/universal_memory/interfaces/cli/init_command.py:1282]
- Violação DRY na repetição de lógica de capturas de exceções OSError na CLI: Repetição de tratamento de `OSError` e mapeamento idêntico de erros em quase todos os comandos da CLI (`_run_init`, `_run_status`, etc.), gerando código boilerplate desnecessário. [src/universal_memory/interfaces/cli/init_command.py]

## Deferred from: code review of 5-1-modelar-hosts-e-alvos-de-instru-o.md (2026-05-28)

- Untyped escape hatch in metadata field: `dict[str, Any]` allows arbitrary data without domain validation. [src/universal_memory/domain/entities/host.py:86]
- Missing access mode classification (read-only vs write) for Host targets: Adiado para a camada de casos de uso (camada de aplicação) nas próximas stories.
- Missing Instruction Entity and Serialization Validation: Adiado para as próximas stories (5.2/5.3), mantendo o escopo de 5.1 na infraestrutura básica de hosts e targets.
- Lack of relationship validation between Host and InstructionTarget ownership: Adiado para a validação na camada de aplicação/serviço onde os repositórios estarão acessíveis.

## Deferred from: code review of 5-3-configurar-host-claude-code-com-claude-md.md (2026-05-28)

- Lack of Transactional Multi-File Rollback: The sequential write loop for canonical documents and target file does not implement rollbacks on intermediate failure, despite the host configuring `rollback_behavior="snapshot_rollback"`. [src/universal_memory/application/host/setup_host_use_case.py:321-344]

## Deferred from: code review of 5-4-validar-leitura-de-contexto-por-host.md (2026-05-29)

- In-memory O(N) linear scan scalability bottleneck in audit log listing: The status use case loads all project-scoped audit events and groups/filters them in memory to find the latest check. As the audit log grows, this will degrade command response time linearly. [src/universal_memory/application/memory/get_memory_status_use_case.py:323-349]
- Missing implementation of "manual_pending" validation status: AC 1 specifies that validation must return "success", "failure", or "manual_pending". [src/universal_memory/application/host/setup_host_use_case.py:188-194] — Simplificar o MVP com validações 100% automatizadas e binárias, postergando tratamentos de onboarding manual.

## Deferred from: code review of 5-6-fluxo-de-sele-o-de-hosts-no-onboarding.md (2026-05-29)

- Violação de camadas da Clean Architecture (caso de uso importando infraestrutura): O caso de uso `SyncInstructionsUseCase` importa e usa `load_config` diretamente da camada de infraestrutura (`toml_loader.py`), violando a regra de inversão de dependências. [src/universal_memory/application/host/sync_instructions_use_case.py:27]
- Dependência acoplada do relógio do sistema (datetime.now(UTC)): O caso de uso usa diretamente `datetime.now(UTC)` dentro de sua execução lógica, dificultando testes unitários isolados e determinismo de testes. [src/universal_memory/application/host/sync_instructions_use_case.py:63]
- Validação de hosts suportados no caso de uso em vez de camada de validação dedicada: A validação estrutural de quais hosts configurados no arquivo TOML são suportados está implementada diretamente no fluxo do caso de uso em vez de uma porta de validação estrutural. [src/universal_memory/application/host/sync_instructions_use_case.py:360]
- Ausência de teste e especificidade no comportamento de mesclagem de listas de _deep_merge: A função `update_project_config` utiliza `_deep_merge` para fundir dados de configuração sem garantias formais contra duplicação de itens de lista em execuções subsequentes. [src/universal_memory/infrastructure/config/toml_loader.py:174]

## Deferred from: code review of 6-1-registrar-latent-skills-por-recorr-ncia.md (2026-05-29)

- Alta concorrência e redundância de locks (listagens e escritas repetidas): O Caso de Uso faz múltiplas chamadas `list()` e depois `write()`, cada uma disputando e adquirindo individualmente travas exclusivas. Otimizações de I/O em lote ou locks compartilhados para leitura são recomendados no futuro. [src/universal_memory/application/skills/track_latent_skill.py:83-90]
- Ausência de fluxo interativo de confirmação em ocorrências ambíguas: O Caso de Uso apenas registra candidatos propostos separados para similaridades baixas, sem gancho para confirmação interativa do usuário. [src/universal_memory/application/skills/track_latent_skill.py:81-90]
