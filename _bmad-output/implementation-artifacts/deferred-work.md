## Deferred from: code review of 1-4-criar-layout-local-umem-e-configura-o-toml.md (2026-05-24)

- Definir estratégia de auto-reparo resiliente para estados específicos de `.umem/`, incluindo critérios explícitos para distinguir corrupção fatal de layout parcial reparável com segurança, antes de permitir recuperação automática no onboarding.

## Deferred from: code review of 2-4-listar-auditoria-e-snapshots.md (2026-05-26)

- Risco de atropelamento concorrente se operações de escrita excederem o limite fixo de STALE_LOCK_SECONDS = 10.0 em `local_audit_log_repository.py` e `local_snapshot_repository.py`.
- Leitura concorrente de auditoria (`LocalAuditLogRepository.list`) é feita sem adquirir lock, podendo levantar erro de decodificação de JSON ou ValidationError se ler uma linha truncada durante escrita concorrente.

## Deferred from: code review of 3-2-consultar-contexto-local-com-busca-textual.md (2026-05-27)

- Weak Domain Port Typing for `write()` and Abundant `cast(Any, ...)` Workarounds: Dynamic dynamic type checking and casts (`cast(Any, ...)`) due to domain port returning `object | None` instead of typed structures or split ports, indicating leaky design. [src/universal_memory/domain/ports/fact_repository.py:50]
- Clean Architecture Violation: Dynamic Runtime State and Injection on Repository Port: Injecting fields dynamically onto repository instances inside Use Case violating stateless Clean Architecture boundaries. [src/universal_memory/application/memory/remember_fact_use_case.py:40]
- **Skills para Agentes (Capacidades UMEM)**: Criar BMad/Agent Skills específicas para documentar e explicar aos agentes de IA externos cada capacidade entregue pelo UMEM (como a busca offline por substring/regex com metadados de destaque, escrita atômica segura com auditoria e restauração, etc.), permitindo que os agentes usem e gerenciem a memória local de forma totalmente autônoma.

