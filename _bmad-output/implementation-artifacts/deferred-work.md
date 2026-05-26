## Deferred from: code review of 1-4-criar-layout-local-umem-e-configura-o-toml.md (2026-05-24)

- Definir estratégia de auto-reparo resiliente para estados específicos de `.umem/`, incluindo critérios explícitos para distinguir corrupção fatal de layout parcial reparável com segurança, antes de permitir recuperação automática no onboarding.

## Deferred from: code review of 2-4-listar-auditoria-e-snapshots.md (2026-05-26)

- Risco de atropelamento concorrente se operações de escrita excederem o limite fixo de STALE_LOCK_SECONDS = 10.0 em `local_audit_log_repository.py` e `local_snapshot_repository.py`.
- Leitura concorrente de auditoria (`LocalAuditLogRepository.list`) é feita sem adquirir lock, podendo levantar erro de decodificação de JSON ou ValidationError se ler uma linha truncada durante escrita concorrente.

