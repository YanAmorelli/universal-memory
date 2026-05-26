# Story 2.3: Implementar Escrita Atômica com Auditoria

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um desenvolvedor implementando use cases de mutação,  
eu quero um pipeline obrigatório de escrita segura,  
para que nenhum adapter consiga persistir dados sem validação, scanner, snapshot e auditoria.

## Acceptance Criteria

1. **Dado** um use case que altera dados persistidos,  
   **Quando** a mutação é executada,  
   **Então** o pipeline segue a ordem: validar entrada, escanear segredos, resolver escopo e caminho, criar snapshot, escrever atomicamente e registrar auditoria,  
   **E** o resultado retorna uma referência de auditoria.

2. **Dado** um adapter CLI ou MCP,  
   **Quando** ele executa uma mutação,  
   **Então** ele invoca o use case compartilhado em vez de escrever diretamente no storage,  
   **E** testes impedem bypass do pipeline por adapters.

3. **Dado** uma falha durante a escrita atômica,  
   **Quando** o pipeline captura a exceção,  
   **Então** nenhum arquivo parcial permanece como estado final,  
   **E** um evento de auditoria de falha é registrado quando possível.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes unitários e de contrato (TDD) para `LocalAuditLogRepository`** (AC: 1, 3)
  - [x] Criar arquivo de teste `tests/infrastructure/security/test_local_audit_log_repository.py`.
  - [x] Testar cenário feliz: gravar evento de auditoria com sucesso e verificar que a entrada correspondente é adicionada em formato JSONL no arquivo `.umem/audit/events.jsonl`.
  - [x] Testar cenário de consulta/leitura: filtrar registros de auditoria por escopo (`AuditEventScope`) e recuperar por ID, validando ordenação correta por timestamp.
  - [x] Testar concorrência extrema: simular múltiplas escritas simultâneas de threads/processos diferentes e validar que o mecanismo de trava de arquivo (`.lock`) garante integridade sem sobrescrever ou perder logs.
  - [x] Testar comportamento resiliente caso o arquivo de log esteja inacessível ou corrompido, garantindo erros tipados adequados.

- [x] **Task 2: Implementar `LocalAuditLogRepository` em Infraestrutura** (AC: 1)
  - [x] Criar `src/universal_memory/infrastructure/security/local_audit_log_repository.py`.
  - [x] Implementar a classe concreta `LocalAuditLogRepository` herdando de `AuditLogRepository` (da porta `src/universal_memory/domain/ports/audit_log_repository.py`).
  - [x] Implementar escrita append-only em JSONL (JSON lines) garantindo que cada linha seja um evento JSON válido com `timestamp` em UTC formatado.
  - [x] Implementar o mecanismo de File Locking robusto (usando trava similar ao snapshot com arquivo temporário de lock `.lock` ou `os.open` concorrente) para proteger as atualizações concorrentes em `events.jsonl`.
  - [x] Exportar a nova classe em `src/universal_memory/infrastructure/security/__init__.py`.

- [x] **Task 3: Escrever testes unitários e de integração para o pipeline `SafeWriteUseCase`** (AC: 1, 2, 3)
  - [x] Criar arquivo de teste `tests/application/security/test_safe_write_use_case.py`.
  - [x] Testar cenário ideal: validar a entrada, passar pelo secret scanner, criar o snapshot do arquivo antigo (se ele existir), escrever atomicamente o novo conteúdo e registrar um evento de auditoria com resultado `"success"`.
  - [x] Testar cenário de bloqueio de segurança: se o `SecretScannerPort` lançar `SecretDetectedError`, validar que nenhuma escrita física ocorre, nenhum snapshot é gerado e o erro é propagado imediatamente.
  - [x] Testar cenário de falha de snapshot: se o `SnapshotRepository` falhar em criar o backup com `SnapshotFailedError`, validar que a mutação aborta imediatamente sem tocar no arquivo original.
  - [x] Testar cenário de falha física de escrita: simular erro de gravação de disco (e.g. `OSError` ou falta de espaço), garantir que nenhum estado parcial corrompido é deixado no disco, e validar que um evento de auditoria com resultado `"failure"` é persistido no log.

- [x] **Task 4: Implementar o Use Case de Pipeline Seguro (`SafeWriteUseCase`)** (AC: 1, 3)
  - [x] Criar `src/universal_memory/application/security/safe_write_use_case.py`.
  - [x] Implementar a classe `SafeWriteUseCase` (ou similar) recebendo as portas `SecretScannerPort`, `SnapshotRepository` e `AuditLogRepository` via injeção de dependência no construtor.
  - [x] Implementar o fluxo estrito:
    1. **Validação**: Verificar formato/parâmetros de entrada.
    2. **Secret Scanning**: Executar `secret_scanner.scan(...)` antes de qualquer alteração.
    3. **Snapshot**: Se o arquivo alvo já existir, calcular seu SHA-256 e salvar snapshot antes da escrita; se não existir, registrar como criação sem backup físico prévio (hash padrão).
    4. **Atomic Write**: Gravar o conteúdo em arquivo temporário `.tmp` no mesmo diretório e renomear via `os.replace` para substituir o arquivo original atomicamente.
    5. **Audit**: Em caso de sucesso, salvar `AuditEvent` de sucesso; em caso de falha física na escrita, limpar o arquivo temporário `.tmp`, salvar `AuditEvent` de falha e propagar a exceção original.

- [x] **Task 5: Garantir paridade e evitar bypass de adapters** (AC: 2)
  - [x] Criar testes e validações para garantir que os adapters CLI (Typer) e futuros adaptadores MCP invoquem o use case `SafeWriteUseCase` para gravar memórias/regras/skills em vez de usar escrita direta via `pathlib` ou hooks de filesystem.
  - [x] Atualizar referências e documentar o uso obrigatório do use case seguro nos adapters.

- [x] **Task 6: Verificação de Qualidade e Ausência de Regressões** (AC: 1, 2, 3)
  - [x] Executar toda a suíte de testes do projeto: `uv run pytest`.
  - [x] Validar conformidade de formatação e análise estática: `uv run ruff check .` e `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Bypass de auditoria em caso de falha na gravação do log de sucesso — A gravação física (`_atomic_write`) ocorre antes do registro de auditoria de sucesso (`_record_audit`). Se a gravação de auditoria falhar (ex: disco cheio), a exceção é lançada sugerindo falha da operação inteira, mas o arquivo físico no disco já terá sido modificado, criando uma alteração de estado não auditada e contornando a conformidade de segurança.
- [x] [Review][Decision] Bloqueios de escrita pelo Secret Scanner não são auditados no log — Quando o `secret_scanner.scan` detecta segredos e lança `SecretDetectedError`, o caso de uso aborta imediatamente e nenhuma auditoria de bloqueio/falha de segurança é gravada para notificar as equipes de segurança de possíveis tentativas de vazamento.
- [x] [Review][Patch] Risco de Lock Estático (Stale Lock) causando Negação de Serviço (DoS) permanente [src/universal_memory/infrastructure/security/local_audit_log_repository.py:25]
- [x] [Review][Patch] Falha catastrófica de leitura por corrupção e riscos de concorrência [src/universal_memory/infrastructure/security/local_audit_log_repository.py:86]
- [x] [Review][Patch] Full Table Scan linear O(N) em leituras e buscas de eventos de auditoria [src/universal_memory/infrastructure/security/local_audit_log_repository.py:57]
- [x] [Review][Patch] Validação vulnerável contra Path Traversal usando contra-barras (`\`) em POSIX [src/universal_memory/application/security/safe_write_use_case.py:96]
- [x] [Review][Patch] Fragilidade e pontos cegos no teste de AST-Guardrail para adapters [tests/interfaces/test_adapter_mutation_guardrails.py:1]
- [x] [Review][Patch] Normalização inconsistente de fuso horário em dicionários aninhados [src/universal_memory/infrastructure/security/local_audit_log_repository.py:99]
- [x] [Review][Patch] Condição de Corrida (TOCTOU) ao ler arquivo original para snapshot [src/universal_memory/application/security/safe_write_use_case.py:75]
- [x] [Review][Patch] Falhas de gravação de snapshot abortam a mutação sem registrar auditoria de falha [src/universal_memory/application/security/safe_write_use_case.py:77]
- [x] [Review][Patch] Fuga de exceção não-OSError causa vazamento de arquivos temporários e falha na auditoria [src/universal_memory/application/security/safe_write_use_case.py:82]

## Dev Notes

- **Escopo desta story**: Implementar o repositório de auditoria local robusto (`LocalAuditLogRepository`), o use case de pipeline seguro de escrita (`SafeWriteUseCase`) e testes integrados de resiliência. As alterações CLI/MCP completas de visualização de auditoria e listagem de snapshots pertencem à Story 2.4.
- **Escrita Atômica**: O uso de escrita em arquivo temporário seguido de `os.replace` é fundamental para evitar arquivos corrompidos ou estados inconsistentes em caso de travamentos ou falhas de energia a meio do processo.
- **Segurança de Auditoria**: Nunca gravar a string sensível ou segredo detectado em nenhum log de auditoria, metadados de erro ou mensagens públicas. Usar apenas metadados seguros (IDs, timestamps, escopo, etc.).
- **UTC Garantido**: Garantir que todos os timestamps gerados para os logs de auditoria e snapshots usem timezone-aware UTC para evitar inconsistências cronológicas.

### Project Structure Notes

- A classe de auditoria concreta deve viver em `src/universal_memory/infrastructure/security/local_audit_log_repository.py`.
- O use case de pipeline seguro deve viver na camada de aplicação em `src/universal_memory/application/security/safe_write_use_case.py`.
- Os testes unitários devem seguir a estrutura espelhada em `tests/infrastructure/security/` e `tests/application/security/`.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 2, Story 2.3, FR22, FR23, FR24, FR25, FR26)
- `_bmad-output/planning-artifacts/architecture.md` (Security & Guardrails, Clean Architecture, Persistence Format, Mutation Pipeline)
- `_bmad-output/planning-artifacts/prd.md` (Secret & ENV Guardrails, Backup & Recovery guardrails)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (Relative paths, structured output)
- `_bmad-output/implementation-artifacts/2-1-implementar-scanner-de-segredos.md` (Learn-from reference)
- `_bmad-output/implementation-artifacts/2-2-criar-snapshot-antes-de-muta-o.md` (Learn-from reference)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

GPT-5 Codex

### Debug Log References

- 2026-05-26: história alvo resolvida a partir de "sprint-status.yaml": `2-3-implementar-escrita-at-mica-com-auditoria`.
- 2026-05-26: analisados `sprint-status.yaml`, `epics.md`, `architecture.md`, `prd.md` e `devex-interaction-spec.md`.
- 2026-05-26: inspecionados `src/universal_memory/domain/`, `src/universal_memory/infrastructure/`, `tests/` e commits anteriores no repositório.
- 2026-05-26: definida a estrutura da Story 2.3 em português do Brasil com tasks TDD detalhadas para repositório concreto de auditoria em JSONL com file locking e use case `SafeWriteUseCase` com escrita física atômica.
- 2026-05-26: executada fase RED com testes focados; falha esperada por ausência de `LocalAuditLogRepository` e `application.security`.
- 2026-05-26: implementados `LocalAuditLogRepository`, `SafeWriteUseCase`, DTOs de comando/resultado e guardrail estático de adapters.
- 2026-05-26: validações finais concluídas com `uv run pytest`, `uv run ruff check .` e `uv run pyright`.

### Implementation Plan

- Implementar primeiro testes de contrato para auditoria JSONL append-only, consulta por escopo, leitura por ID, concorrência com lock e corrupção de log.
- Implementar o repositório local de auditoria seguindo o padrão de lock já usado em snapshots e serialização UTC em JSONL.
- Implementar `SafeWriteUseCase` como use case síncrono da camada de aplicação, recebendo scanner, snapshots e auditoria por portas.
- Cobrir o fluxo obrigatório: validar caminho relativo, escanear conteúdo, criar snapshot, escrever via arquivo temporário + `os.replace`, auditar sucesso ou falha física.
- Adicionar teste de guardrail para impedir escrita direta em adapters de interface.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Escopo delimitado para repositório concreto de auditoria local em JSONL com file locking e use case de pipeline seguro com escrita atômica física.
- Guardrails detalhados de TDD, UTC, segurança de logs contra vazamento de segredos e prevenção de bypass por adapters CLI/MCP.
- `LocalAuditLogRepository` implementado com `.umem/audit/events.jsonl`, append-only JSONL, lock via criação exclusiva de `events.jsonl.lock`, leitura ordenada por timestamp e erros `StorageError` para falhas tipadas.
- `SafeWriteUseCase` implementado com validação de caminho relativo, scanner antes de qualquer escrita, snapshot do estado anterior, escrita atômica com `.tmp` e auditoria de sucesso/falha.
- Guardrail de interface adicionado para detectar chamadas diretas de mutação em adapters (`open`, `write_text`, `write_bytes`, `os.replace`/equivalentes).
- Validações executadas com sucesso: `uv run pytest` (`105 passed`), `uv run ruff check .`, `uv run pyright`.

### File List

- `_bmad-output/implementation-artifacts/2-3-implementar-escrita-at-mica-com-auditoria.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/security/__init__.py`
- `src/universal_memory/application/security/safe_write_use_case.py`
- `src/universal_memory/domain/__init__.py`
- `src/universal_memory/infrastructure/security/__init__.py`
- `src/universal_memory/infrastructure/security/local_audit_log_repository.py`
- `tests/application/security/test_safe_write_use_case.py`
- `tests/infrastructure/security/test_local_audit_log_repository.py`
- `tests/interfaces/test_adapter_mutation_guardrails.py`

### Change Log

- 2026-05-26: Implementada escrita atômica segura com auditoria local e testes de contrato para pipeline obrigatório.
